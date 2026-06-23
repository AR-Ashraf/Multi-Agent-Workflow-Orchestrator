"""Writer — drafts the brief from approved insights (no web access; least-privilege).

Runs twice in the prototype flow: the initial draft, then a revision after the
Critic rejects an unsupported claim. The pass is distinguished by
`critic_attempts` so step/edge visuals match the prototype.
"""

from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig

from ..state import ResearchState
from ._base import ctx_from


def writer(state: ResearchState, config: RunnableConfig) -> dict[str, Any]:
    ctx = ctx_from(config)
    ctx.step()
    e = ctx.emitter
    attempts = state.get("critic_attempts", 0)

    if attempts == 0:
        # initial draft
        e.step_changed(5, 8)
        e.edge_status("hitl->writer", "done")
        e.node_status("writer", "active")
        e.log(
            "info", "Writer", "drafting brief with citations from approved sources only.", "writer"
        )
        ctx.charge(ctx.llm.complete(system="Writer", prompt="draft brief", model=ctx.model_id))
        e.node_status("writer", "done")
        e.edge_status("writer->critic", "flow")
        return {"draft": {"version": 1}}

    # revision after a rejected claim (error recovery)
    e.node_status("writer", "active")
    e.log(
        "info", "Writer", "revised claim 3 to the source-supported range ($50k–$70k/yr).", "writer"
    )
    ctx.charge(ctx.llm.complete(system="Writer", prompt="revise claim 3", model=ctx.model_id))
    e.edge_status("critic->writer", "retry")  # stop the flowing animation
    e.node_status("writer", "done")
    e.edge_status("writer->critic", "flow")
    return {"draft": {"version": 2}}
