"""RunContext — per-run dependencies + budget enforcement, threaded through the
graph via the LangGraph config (`configurable.ctx`).

Carries the emitter, the (BYOK) LLM client, the run parameters, and the
token/step ceilings from CLAUDE.md §8.3. Caps are enforced even on BYOK runs so
a runaway loop can't burn the visitor's tokens or our infra.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .constants import (
    MAX_STEPS,
    MAX_TOKENS,
    MECHANICAL_NODES,
    PRICE_PER_TOKEN,
    api_model_id,
    model_badge_for,
)
from .events import Emitter
from .llm import LLMClient, LLMResult
from .tools import FixtureFetcher, FixtureSearchClient, SearchClient, WebFetcher


class BudgetExceeded(Exception):
    """Raised when a run exceeds its token or step ceiling."""

    def __init__(self, kind: str, used: int, cap: int) -> None:
        super().__init__(f"{kind} budget exceeded: {used} > {cap}")
        self.kind = kind
        self.used = used
        self.cap = cap


@dataclass
class RunContext:
    emitter: Emitter
    llm: LLMClient
    query: str
    provider: str
    model_id: str
    routing: bool
    mode: str
    max_tokens: int = MAX_TOKENS
    max_steps: int = MAX_STEPS
    steps_used: int = field(default=0)
    # Tool clients default to offline fixtures; the API layer (Unit 6) injects
    # real Tavily/Brave + Firecrawl clients (our server-side keys, not the visitor's).
    search: SearchClient = field(default_factory=FixtureSearchClient)
    fetch: WebFetcher = field(default_factory=FixtureFetcher)

    def model_label(self, node_id: str) -> str:
        return model_badge_for(node_id, self.provider, self.model_id, self.routing)

    def api_model_for(self, node_id: str) -> str:
        """Real API model id for a node — the fast model on mechanical steps when
        cost-routing is on (§8.4), the selected model otherwise."""
        fast = self.routing and node_id in MECHANICAL_NODES
        return api_model_id(self.provider, self.model_id, fast=fast)

    def step(self) -> None:
        """Count a node execution against the step ceiling."""
        self.steps_used += 1
        if self.steps_used > self.max_steps:
            raise BudgetExceeded("step", self.steps_used, self.max_steps)

    def charge(self, result: LLMResult) -> None:
        """Record token usage + estimated cost, emit a meters update, enforce cap."""
        tokens = result.total_tokens
        cost = tokens * PRICE_PER_TOKEN
        self.emitter.meters(tokens, cost)
        if self.emitter.tokens > self.max_tokens:
            raise BudgetExceeded("token", self.emitter.tokens, self.max_tokens)
