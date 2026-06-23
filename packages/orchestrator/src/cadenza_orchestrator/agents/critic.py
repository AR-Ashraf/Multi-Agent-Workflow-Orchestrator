"""Critic — verifies every key claim against its cited source (feature 4).

On the first pass claim 3 is unsupported, so the Critic rejects and loops back to
the Writer (the retry edge). On the second pass the revised claim is grounded and
the Critic accepts. Real claim verification against fetched sources replaces this
mock logic in Unit 5; the emitted `claim.verified` shape is already final.
"""

from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig

from ..constants import MAX_CRITIC_RETRIES
from ..state import ResearchState
from ._base import ctx_from


def critic(state: ResearchState, config: RunnableConfig) -> dict[str, Any]:
    ctx = ctx_from(config)
    ctx.step()
    e = ctx.emitter
    attempts = state.get("critic_attempts", 0)

    e.edge_status("writer->critic", "done")
    e.node_status("critic", "active")

    if attempts == 0:
        e.step_changed(6, 8)
        # first pass — verify every key claim against its source
        e.claim_verified("c1", "183k US dentists", "Source 1", "grounded")
        e.log(
            "verify", "Critic", 'claim 1 — "183k US dentists" → grounded in Source 1. ✓', "critic"
        )
        ctx.charge(ctx.llm.complete(system="Critic", prompt="verify claim 1", model=ctx.model_id))
        e.claim_verified("c2", "competitor pricing $300–$800/mo", "Source 3", "grounded")
        e.log(
            "verify",
            "Critic",
            'claim 2 — "competitor pricing $300–$800/mo" → grounded in Source 3. ✓',
            "critic",
        )
        ctx.charge(ctx.llm.complete(system="Critic", prompt="verify claim 2", model=ctx.model_id))

        # claim 3 unsupported → reject and retry
        e.claim_verified(
            "c3",
            "no-show cost figure",
            "Source 2",
            "unsupported",
            detail="Draft cited a number not supported by the source.",
        )
        e.log(
            "security",
            "Critic",
            'claim 3 — "no-show cost" → not supported by the source. ✗ Rejecting draft.',
            "critic",
        )
        e.step_changed(7, 8)
        e.node_status("critic", "blocked")
        e.edge_status("critic->writer", "retry-flow")
        e.agent_rationale(
            "critic",
            "Fix claim 3 to match Source 2's actual figure, then re-verify.",
            verdict="retry",
        )
        e.log(
            "rationale",
            "Critic",
            "verdict: retry — fix claim 3 to match Source 2's actual figure, then re-verify.",
            "critic",
        )
        return {"critic_attempts": attempts + 1, "verdict": "retry"}

    # retry pass — only the previously-failed claim is re-checked → grounded → accept
    e.claim_verified(
        "c3",
        "no-show cost $50k–$70k/yr",
        "Source 2",
        "grounded",
        detail="Re-checked after revision.",
    )
    e.log(
        "verify",
        "Critic",
        "claim 3 — re-checked → now grounded in Source 2. ✓ All 3 claims verified.",
        "critic",
    )
    ctx.charge(ctx.llm.complete(system="Critic", prompt="re-verify claim 3", model=ctx.model_id))
    e.node_status("critic", "done")
    e.edge_status("critic->output", "flow")
    return {"critic_attempts": attempts + 1, "verdict": "accept"}


def route_after_critic(state: ResearchState) -> str:
    """Conditional edge: retry back to the Writer, or release to output."""
    if state.get("verdict") == "accept" or state.get("critic_attempts", 0) > MAX_CRITIC_RETRIES:
        return "output"
    return "writer"
