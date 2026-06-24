"""The AI Market Research Brief graph — LangGraph topology mirroring the UI 1:1.

    START → planner → {researcher-a, researcher-b, researcher-c} → analyst
          → hitl (interrupt) → writer → critic ⇄ writer (retry) → output → END

HITL uses a native LangGraph `interrupt()`; the run pauses with state persisted by
the checkpointer and resumes via `Command(resume=...)`. The Critic→Writer retry is
a conditional edge driven by the Critic's verdict.
"""

from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from ..agents._base import ctx_from
from ..agents.analyst import analyst
from ..agents.brief import build_brief
from ..agents.critic import critic, route_after_critic
from ..agents.planner import planner
from ..agents.researchers import make_researcher
from ..agents.writer import writer
from ..constants import MAX_STEPS, MAX_TOKENS, TOTAL_STEPS, assign_models, resolve_model
from ..context import BudgetExceeded, RunContext
from ..events import Emitter
from ..llm import LLMClient, MockLLMClient
from ..state import ResearchState


def hitl_node(state: ResearchState, config: RunnableConfig) -> dict[str, Any]:
    """Pause for human approval. Nothing is emitted before `interrupt()` because
    this node body re-runs on resume."""
    direction = state.get("direction", [])
    decision = interrupt(
        {
            "prompt": "Before the Writer drafts anything, approve or adjust the proposed direction.",
            "proposedDirection": direction,
            "options": ["approve", "adjust"],
        }
    )

    ctx = ctx_from(config)
    ctx.step()
    e = ctx.emitter

    if isinstance(decision, dict):
        d = str(decision.get("decision", "approve"))
        note = decision.get("note")
    else:
        d = str(decision)
        note = None

    e.hitl_resolved(d, note)
    if d == "adjust":
        e.log("human", "You", "✎ adjusted scope. Resuming the run.", "hitl")
    else:
        e.log("human", "You", "✓ approved the proposed direction. Resuming the run.", "hitl")
    e.run_state("running", "Running")
    e.edge_status("hitl->writer", "flow")
    e.node_status("hitl", "done")

    return {"hitl_decision": d, "hitl_note": note or ""}


def output_node(state: ResearchState, config: RunnableConfig) -> dict[str, Any]:
    ctx = ctx_from(config)
    ctx.step()
    e = ctx.emitter

    e.step_changed(8, 8)
    e.edge_status("critic->output", "done")
    e.node_status("output", "done")

    brief = build_brief(ctx.query, ctx.model_label("planner"), ctx.mode, e.run_id)
    e.log(
        "verify",
        "Workflow",
        "run complete — cited, claim-verified brief released. Permalink saved.",
        "output",
    )
    e.brief_released(brief)
    e.run_completed({"verified": 3, "total": 3})
    e.run_state("done", "Complete")

    return {"brief": brief}


def build_graph():
    """Compile the research graph with an in-memory checkpointer (enables HITL)."""
    g: StateGraph = StateGraph(ResearchState)

    def add(name: str, fn: Any) -> None:
        # LangGraph runs (state, config) node callables fine; its stubs don't
        # model that overload cleanly, so register through an Any seam.
        g.add_node(name, fn)

    add("planner", planner)
    add("researcher-a", make_researcher("researcher-a"))
    add("researcher-b", make_researcher("researcher-b"))
    add("researcher-c", make_researcher("researcher-c"))
    add("analyst", analyst)
    add("hitl", hitl_node)
    add("writer", writer)
    add("critic", critic)
    add("output", output_node)

    g.add_edge(START, "planner")
    for r in ("researcher-a", "researcher-b", "researcher-c"):
        g.add_edge("planner", r)
        g.add_edge(r, "analyst")
    g.add_edge("analyst", "hitl")
    g.add_edge("hitl", "writer")
    g.add_edge("writer", "critic")
    g.add_conditional_edges("critic", route_after_critic, {"writer": "writer", "output": "output"})
    g.add_edge("output", END)

    return g.compile(checkpointer=InMemorySaver())


def _emit_preamble(emitter: Emitter, *, query, provider, model_id, routing, mode) -> None:
    model_label = resolve_model(provider, model_id)["label"]
    emitter.run_started(
        query=query,
        provider=provider,
        model_id=model_id,
        model_label=model_label,
        routing=routing,
        mode=mode,
        total_steps=TOTAL_STEPS,
    )
    emitter.run_state("running", "Running")
    emitter.model_routing(routing, assign_models(provider, model_id, routing))
    if mode == "live":
        setup = (
            f"running on {provider} · {model_label} via your API key"
            + (" · cost-routing on" if routing else "")
            + ". Tokens billed to your account."
        )
    else:
        setup = (
            f"no API key entered — running a cached demo of {model_label} (free, nothing billed)."
        )
    emitter.log("info", "Setup", setup)


def run_research_brief(
    *,
    query: str = "Market for AI scheduling assistants for US dental clinics",
    provider: str = "anthropic",
    model_id: str = "claude-sonnet",
    routing: bool = True,
    mode: str = "demo",
    run_id: str = "run",
    decision: str = "approve",
    llm: LLMClient | None = None,
    sink: Any = None,
    max_tokens: int | None = None,
    max_steps: int | None = None,
) -> dict[str, Any]:
    """Convenience end-to-end driver used by tests and demo replay: emits the
    preamble, runs to the HITL interrupt, then resumes with `decision`.

    The FastAPI layer (Unit 6) will instead call the start/resume primitives so a
    real human supplies the decision between the two phases.
    """
    llm = llm or MockLLMClient()
    emitter = Emitter(run_id, sink)
    ctx = RunContext(
        emitter=emitter,
        llm=llm,
        query=query,
        provider=provider,
        model_id=model_id,
        routing=routing,
        mode=mode,
        max_tokens=max_tokens if max_tokens is not None else MAX_TOKENS,
        max_steps=max_steps if max_steps is not None else MAX_STEPS,
    )

    graph = build_graph()
    config: RunnableConfig = {"configurable": {"thread_id": run_id, "ctx": ctx}}

    _emit_preamble(
        emitter, query=query, provider=provider, model_id=model_id, routing=routing, mode=mode
    )

    try:
        result = graph.invoke({"query": query}, config)
        if "__interrupt__" in result:
            result = graph.invoke(Command(resume={"decision": decision}), config)
    except BudgetExceeded as ex:
        emitter.error("budget_exceeded", str(ex), recoverable=False)
        emitter.run_state("error", "Stopped · budget exceeded")
        return {"events": emitter.events, "state": {}, "emitter": emitter, "error": str(ex)}

    return {"events": emitter.events, "state": result, "emitter": emitter}
