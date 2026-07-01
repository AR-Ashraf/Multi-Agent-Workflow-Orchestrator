"""Critic — verifies every key claim against its cited source (feature 4).

Real verification (no LLM in the loop): each claim's value must appear in the
text of its cited source (`corpus.verify_claim`). On the real path the sources
are the pages the Researchers actually fetched and screened; on the mock path
they are the dental fixtures. Unsupported claims are rejected and the draft loops
back to the Writer; on the retry pass only the previously-failed claims are
re-checked. The grounding decision stays deterministic and fully testable.
"""

from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig

from ..constants import MAX_CRITIC_RETRIES
from ..context import RunContext
from ..corpus import SOURCES, verify_claim
from ..state import ResearchState
from ._base import ctx_from


def _verify_and_emit(
    ctx: RunContext, claim: dict[str, str], sources: list[dict[str, str]], *, recheck: bool
) -> bool:
    e = ctx.emitter
    verdict = verify_claim(claim, sources)
    status = "grounded" if verdict.grounded else "unsupported"
    e.claim_verified(
        claim["id"],
        claim["text"],
        claim["source_id"],
        status,
        detail=("re-checked after revision; " if recheck else "") + verdict.reason,
    )
    mark = "✓" if verdict.grounded else "✗"
    prefix = "re-checked " if recheck else ""
    e.log(
        "verify" if verdict.grounded else "security",
        "Critic",
        f'{prefix}claim "{claim["text"]}" → {status} in {claim["source_id"]}. {mark}',
        "critic",
    )
    ctx.charge(
        ctx.llm.complete(system="Critic", prompt=f"verify {claim['id']}", model=ctx.model_id)
    )
    return verdict.grounded


def critic(state: ResearchState, config: RunnableConfig) -> dict[str, Any]:
    ctx = ctx_from(config)
    ctx.step()
    e = ctx.emitter
    attempts = state.get("critic_attempts", 0)
    claims: list[dict[str, str]] = state.get("draft", {}).get("claims", [])
    sources: list[dict[str, str]] = state.get("sources") or SOURCES
    total = len(claims)

    e.edge_status("writer->critic", "done")
    e.node_status("critic", "active")

    if attempts == 0:
        e.step_changed(6, 8)
        failed = [c["id"] for c in claims if not _verify_and_emit(ctx, c, sources, recheck=False)]
        if failed:
            e.step_changed(7, 8)
            e.node_status("critic", "blocked")
            e.edge_status("critic->writer", "retry-flow")
            e.agent_rationale(
                "critic",
                f"{len(failed)} claim(s) not grounded in the cited source — send back to the Writer, then re-verify.",
                verdict="retry",
            )
            e.log(
                "rationale",
                "Critic",
                "verdict: retry — fix the unsupported claim(s) to match the cited source, then re-verify.",
                "critic",
            )
            return {"critic_attempts": attempts + 1, "verdict": "retry", "failed_claims": failed}

        e.node_status("critic", "done")
        e.edge_status("critic->output", "flow")
        return {
            "critic_attempts": attempts + 1,
            "verdict": "accept",
            "claims_verified": {"verified": total, "total": total},
        }

    # retry pass — re-verify only the previously-failed claims
    failed_ids = set(state.get("failed_claims", []))
    by_id = {c["id"]: c for c in claims}
    still_failed = [
        cid
        for cid in failed_ids
        if cid in by_id and not _verify_and_emit(ctx, by_id[cid], sources, recheck=True)
    ]

    if still_failed and attempts <= MAX_CRITIC_RETRIES:
        e.node_status("critic", "blocked")
        e.edge_status("critic->writer", "retry-flow")
        e.agent_rationale("critic", "claim still unsupported — retry.", verdict="retry")
        e.log(
            "rationale",
            "Critic",
            "verdict: retry — claim still unsupported after revision.",
            "critic",
        )
        return {"critic_attempts": attempts + 1, "verdict": "retry", "failed_claims": still_failed}

    e.log("verify", "Critic", "all key claims grounded in their cited sources. ✓", "critic")
    e.node_status("critic", "done")
    e.edge_status("critic->output", "flow")
    return {
        "critic_attempts": attempts + 1,
        "verdict": "accept",
        "claims_verified": {"verified": total - len(still_failed), "total": total},
    }


def route_after_critic(state: ResearchState) -> str:
    """Conditional edge: retry back to the Writer, or release to output."""
    if state.get("verdict") == "accept" or state.get("critic_attempts", 0) > MAX_CRITIC_RETRIES:
        return "output"
    return "writer"
