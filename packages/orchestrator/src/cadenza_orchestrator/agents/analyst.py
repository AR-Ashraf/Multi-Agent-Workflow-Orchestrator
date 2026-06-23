"""Analyst — synthesizes researcher findings, proposes a direction, then triggers
the human checkpoint.

The HITL surface events (paused state + hitl.requested) are emitted here, at the
*end* of the analyst node, rather than inside the `hitl` node. The hitl node body
is re-executed on resume, so keeping it free of emits avoids double-emitting the
checkpoint prompt.
"""

from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig

from ..state import ResearchState
from ._base import ctx_from

DIRECTION = [
    "Lead with US market size + growth for the niche",
    "Profile the 3 strongest competitors & their pricing",
    "Close with the gap Devs Core could win",
]


def analyst(state: ResearchState, config: RunnableConfig) -> dict[str, Any]:
    ctx = ctx_from(config)
    ctx.step()
    e = ctx.emitter

    e.step_changed(3, 8)
    for edge in ("researcher-a->analyst", "researcher-b->analyst", "researcher-c->analyst"):
        e.edge_status(edge, "done")
    e.node_status("analyst", "active")

    ctx.charge(
        ctx.llm.complete(
            system="Analyst", prompt=str(state.get("findings", [])), model=ctx.model_id
        )
    )

    e.agent_rationale(
        "analyst",
        "Clustered findings into market size, 3 competitors, and a pricing band; flagged the underserved mid-market as the angle.",
    )
    e.log(
        "rationale",
        "Analyst",
        "clustered findings into market size, 3 competitors, pricing band; flagged the underserved mid-market.",
        "analyst",
    )
    e.node_status("analyst", "done")
    e.edge_status("analyst->hitl", "flow")
    e.edge_status("analyst->hitl", "done")

    # --- enter the human-in-the-loop checkpoint ---
    e.node_status("hitl", "hitl")
    e.step_changed(4, 8)
    e.run_state("paused", "Paused · waiting for you")
    e.log("human", "Workflow", "interrupted at HITL checkpoint — awaiting human approval.", "hitl")
    e.hitl_requested(
        "Before the Writer drafts anything, approve or adjust the proposed direction.",
        DIRECTION,
        ["approve", "adjust"],
    )

    return {"insights": "mid-market is underserved", "direction": DIRECTION}
