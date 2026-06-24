"""Cadenza orchestrator — the LangGraph multi-agent engine.

ALL orchestration logic lives here (CLAUDE.md §5). The FastAPI gateway is a thin
caller; the UI is a thin SSE client.
"""

from .context import BudgetExceeded, RunContext
from .events import Emitter, Event
from .graphs import RunSession, build_graph, run_research_brief
from .llm import LLMClient, LLMResult, MockLLMClient

__all__ = [
    "BudgetExceeded",
    "Emitter",
    "Event",
    "LLMClient",
    "LLMResult",
    "MockLLMClient",
    "RunContext",
    "RunSession",
    "build_graph",
    "run_research_brief",
]
