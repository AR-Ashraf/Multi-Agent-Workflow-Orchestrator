"""Planner — decomposes the question into parallel sub-questions (emits its reasoning)."""

from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig

from ..state import ResearchState
from ._base import ctx_from

SUBTASKS = ["market size", "top competitors", "pricing"]


def planner(state: ResearchState, config: RunnableConfig) -> dict[str, Any]:
    ctx = ctx_from(config)
    ctx.step()
    e = ctx.emitter

    e.step_changed(1, 8)
    e.node_status("planner", "active")

    res = ctx.llm.complete(system="You are the Planner.", prompt=state["query"], model=ctx.model_id)

    # decision rationale as real fields (feature 2)
    e.agent_rationale(
        "planner",
        "A useful brief needs demand, rivals, and price anchors — so the question splits into three.",
        items=SUBTASKS,
    )
    e.log(
        "rationale",
        "Planner",
        "chose 3 sub-questions — market size, top competitors, pricing.",
        "planner",
    )
    ctx.charge(res)
    e.log(
        "info",
        "Planner",
        "emitted 3 research tasks → dispatching researchers in parallel.",
        "planner",
    )
    e.node_status("planner", "done")
    for edge in ("planner->researcher-a", "planner->researcher-b", "planner->researcher-c"):
        e.edge_status(edge, "flow")
    e.step_changed(2, 8)

    return {"subtasks": SUBTASKS, "critic_attempts": 0}
