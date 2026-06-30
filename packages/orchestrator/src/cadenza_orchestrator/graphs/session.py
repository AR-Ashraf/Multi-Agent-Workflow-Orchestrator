"""RunSession — drives a single run in two phases so a real human supplies the
HITL decision between them (used by the FastAPI gateway).

`start()` runs the graph to the LangGraph interrupt (state persisted by the
checkpointer) and returns whether it paused; `resume(decision)` continues to
completion. Each emitted event flows to the `sink` (the API publishes it to
Redis pub/sub) as it is produced.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from ..constants import MAX_STEPS, MAX_TOKENS
from ..context import BudgetExceeded, RunContext
from ..events import Emitter, Event
from ..llm import LLMClient, MockLLMClient
from ..tools import SearchClient, WebFetcher
from .research_graph import _emit_preamble, build_graph


class RunSession:
    def __init__(
        self,
        *,
        run_id: str,
        query: str,
        provider: str = "anthropic",
        model_id: str = "claude-sonnet",
        routing: bool = True,
        mode: str = "demo",
        llm: LLMClient | None = None,
        search: SearchClient | None = None,
        fetch: WebFetcher | None = None,
        sink: Callable[[Event], None] | None = None,
        max_tokens: int | None = None,
        max_steps: int | None = None,
    ) -> None:
        self.run_id = run_id
        self.query = query
        self.provider = provider
        self.model_id = model_id
        self.routing = routing
        self.mode = mode
        self.emitter = Emitter(run_id, sink)
        # Tool clients default to offline fixtures (mock/demo); the API injects
        # real Tavily + Firecrawl (our server-side keys) for live BYOK runs.
        ctx_kwargs: dict[str, Any] = {}
        if search is not None:
            ctx_kwargs["search"] = search
        if fetch is not None:
            ctx_kwargs["fetch"] = fetch
        self.ctx = RunContext(
            emitter=self.emitter,
            llm=llm or MockLLMClient(),
            query=query,
            provider=provider,
            model_id=model_id,
            routing=routing,
            mode=mode,
            max_tokens=max_tokens if max_tokens is not None else MAX_TOKENS,
            max_steps=max_steps if max_steps is not None else MAX_STEPS,
            **ctx_kwargs,
        )
        self._graph = build_graph()
        self._config: RunnableConfig = {"configurable": {"thread_id": run_id, "ctx": self.ctx}}
        self.paused = False
        self.completed = False
        self.errored = False

    @property
    def events(self) -> list[Event]:
        return self.emitter.events

    def start(self) -> bool:
        """Run to the HITL interrupt (or completion). Returns True if paused."""
        _emit_preamble(
            self.emitter,
            query=self.query,
            provider=self.provider,
            model_id=self.model_id,
            routing=self.routing,
            mode=self.mode,
        )
        try:
            result = self._graph.invoke({"query": self.query}, self._config)
        except BudgetExceeded as ex:
            self._fail(ex)
            return False
        self.paused = "__interrupt__" in result
        self.completed = not self.paused
        return self.paused

    def resume(self, decision: str = "approve", note: str | None = None) -> None:
        """Resume a paused run with the human decision, to completion."""
        try:
            self._graph.invoke(Command(resume={"decision": decision, "note": note}), self._config)
        except BudgetExceeded as ex:
            self._fail(ex)
            return
        self.paused = False
        self.completed = True

    def _fail(self, ex: BudgetExceeded) -> None:
        self.errored = True
        self.emitter.error("budget_exceeded", str(ex), recoverable=False)
        self.emitter.run_state("error", "Stopped · budget exceeded")

    def cancel(self, reason: str, *, code: str = "cancelled", label: str | None = None) -> None:
        """End a paused/abandoned run cleanly without resuming the graph.

        Used by the gateway when a run sits at the HITL checkpoint past the
        approval timeout — it emits a terminal error event so SSE subscribers
        stop and the run's resources can be reclaimed.
        """
        if self.completed or self.errored:
            return
        self.errored = True
        self.emitter.log("human", "Workflow", f"run ended — {reason}.", "hitl")
        self.emitter.error(code, reason, recoverable=False)
        self.emitter.run_state("error", label or "Stopped")
