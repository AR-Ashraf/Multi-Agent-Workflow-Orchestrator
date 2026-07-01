"""Planner — decomposes the question into parallel sub-questions (emits its reasoning).

Real path: prompts the model for three focused research sub-questions. Mock /
fallback path: the fixed `SUBTASKS`, so the graph is deterministic in CI.
"""

from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig

from ..llm import LLMError, parse_json
from ..state import ResearchState
from ._base import ctx_from, is_real

SUBTASKS = ["market size", "top competitors", "pricing"]

_SYSTEM = (
    "You are the Planner in a market-research workflow. Decompose the user's "
    "question into exactly THREE focused, parallel research sub-questions that "
    "together cover demand/market size, competitors, and pricing. "
    'Respond with ONLY a JSON array of three short strings, e.g. ["...","...","..."].'
)


def _plan_subtasks(ctx, query: str) -> tuple[list[str], Any]:
    """Return (subtasks, llm_result). Falls back to SUBTASKS off the real path."""
    res = ctx.llm.complete(
        system=_SYSTEM, prompt=query, model=ctx.api_model_for("planner"), max_tokens=300
    )
    if is_real(ctx):
        try:
            data = parse_json(res.text)
            items = [str(x).strip() for x in data if str(x).strip()][:3]
            if len(items) == 3:
                return items, res
        except (LLMError, TypeError):
            pass
    return SUBTASKS, res


def planner(state: ResearchState, config: RunnableConfig) -> dict[str, Any]:
    ctx = ctx_from(config)
    ctx.step()
    e = ctx.emitter

    e.step_changed(1, 8)
    e.node_status("planner", "active")

    subtasks, res = _plan_subtasks(ctx, state["query"])

    # decision rationale as real fields (feature 2)
    e.agent_rationale(
        "planner",
        "A useful brief needs demand, rivals, and price anchors — so the question splits into three.",
        items=subtasks,
    )
    e.log(
        "rationale",
        "Planner",
        f"chose {len(subtasks)} sub-questions — " + ", ".join(subtasks) + ".",
        "planner",
    )
    ctx.charge(res)
    e.log(
        "info",
        "Planner",
        f"emitted {len(subtasks)} research tasks → dispatching researchers in parallel.",
        "planner",
    )
    e.node_status("planner", "done")
    for edge in ("planner->researcher-a", "planner->researcher-b", "planner->researcher-c"):
        e.edge_status(edge, "flow")
    e.step_changed(2, 8)

    return {"subtasks": subtasks, "critic_attempts": 0}
