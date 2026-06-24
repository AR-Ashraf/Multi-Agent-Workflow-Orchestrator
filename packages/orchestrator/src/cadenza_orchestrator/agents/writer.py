"""Writer — drafts the brief's claims from approved insights (no web access).

Produces structured claims (text + cited source + value) so the Critic can verify
each against its source. The first draft deliberately hallucinates claim 3's
figure (not supported by Source 2); the revision corrects exactly the claims the
Critic flagged. Mirrors the prototype's draft → reject → fix loop, now driven by
real verification.
"""

from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig

from ..corpus import CLAIMS, HALLUCINATED_VALUE
from ..state import ResearchState
from ._base import ctx_from


def _initial_claims() -> list[dict[str, str]]:
    return [{**c, "value": HALLUCINATED_VALUE.get(c["id"], c["value"])} for c in CLAIMS]


def _corrected_claims(prev: list[dict[str, str]], failed: set[str]) -> list[dict[str, str]]:
    correct = {c["id"]: c["value"] for c in CLAIMS}
    return [{**c, "value": correct[c["id"]] if c["id"] in failed else c["value"]} for c in prev]


def writer(state: ResearchState, config: RunnableConfig) -> dict[str, Any]:
    ctx = ctx_from(config)
    ctx.step()
    e = ctx.emitter
    attempts = state.get("critic_attempts", 0)

    if attempts == 0:
        # initial draft (with a hallucinated claim 3)
        e.step_changed(5, 8)
        e.edge_status("hitl->writer", "done")
        e.node_status("writer", "active")
        e.log(
            "info", "Writer", "drafting brief with citations from approved sources only.", "writer"
        )
        ctx.charge(ctx.llm.complete(system="Writer", prompt="draft brief", model=ctx.model_id))
        e.node_status("writer", "done")
        e.edge_status("writer->critic", "flow")
        return {"draft": {"version": 1, "claims": _initial_claims()}}

    # revision after the Critic rejected unsupported claim(s) (error recovery)
    failed = set(state.get("failed_claims", []))
    prev = state.get("draft", {}).get("claims", [])
    e.node_status("writer", "active")
    e.log("info", "Writer", "revised the flagged claim to the source-supported figure.", "writer")
    ctx.charge(
        ctx.llm.complete(system="Writer", prompt="revise flagged claims", model=ctx.model_id)
    )
    e.edge_status("critic->writer", "retry")  # stop the flowing animation
    e.node_status("writer", "done")
    e.edge_status("writer->critic", "flow")
    return {"draft": {"version": 2, "claims": _corrected_claims(prev, failed)}}
