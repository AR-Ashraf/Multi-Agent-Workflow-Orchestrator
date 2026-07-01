"""Writer — drafts the brief from approved insights + the cited sources (no web access).

Real path: prompts the model for brief sections (with inline [Source N] markers)
and structured claims, where each claim's `value` is an EXACT short quote from
its cited source — so the Critic can ground it deterministically. Mock path: the
corpus claims, whose first draft deliberately hallucinates claim 3 so the Critic
retry loop fires (unchanged in CI).
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.runnables import RunnableConfig

from ..corpus import CLAIMS, HALLUCINATED_VALUE
from ..llm import LLMError, parse_json
from ..state import ResearchState
from ._base import ctx_from, is_real

_SYSTEM = (
    "You are the Writer. Using the approved direction and the provided sources, "
    "draft a concise market-research brief. Cite sources inline as [Source N]. "
    'Respond with ONLY JSON: {"sections": [{"heading": str, "body": str}], '
    '"claims": [{"id": str, "text": str, "source_id": "Source N", "value": str}]}. '
    "Every claim's `value` MUST be a short EXACT quote copied verbatim from that "
    "source's content, so it can be verified."
)

_FIX_SYSTEM = (
    "You are the Writer revising a draft. Some claims were not grounded in their "
    "cited source. For each flagged claim id, set `value` to a short EXACT quote "
    "copied verbatim from that source's content. Respond with ONLY the same JSON "
    'shape: {"sections": [...], "claims": [...]}.'
)


def _initial_claims() -> list[dict[str, str]]:
    return [{**c, "value": HALLUCINATED_VALUE.get(c["id"], c["value"])} for c in CLAIMS]


def _corrected_claims(prev: list[dict[str, str]], failed: set[str]) -> list[dict[str, str]]:
    correct = {c["id"]: c["value"] for c in CLAIMS}
    return [{**c, "value": correct[c["id"]] if c["id"] in failed else c["value"]} for c in prev]


def _sources_prompt(state: ResearchState) -> str:
    sources = state.get("sources", [])
    return json.dumps(
        {
            "insights": state.get("insights", ""),
            "direction": state.get("direction", []),
            "sources": [
                {"id": s["id"], "label": s["label"], "content": s["content"]} for s in sources
            ],
        }
    )


def _parse_draft(text: str, version: int) -> dict[str, Any] | None:
    try:
        data = parse_json(text)
    except LLMError:
        return None
    if not isinstance(data, dict):
        return None
    sections = [
        {"heading": str(s["heading"]), "body": str(s.get("body", ""))}
        for s in data.get("sections", [])
        if isinstance(s, dict) and s.get("heading")
    ]
    claims = [
        {
            "id": str(c.get("id") or f"c{i + 1}"),
            "text": str(c.get("text", "")),
            "source_id": str(c.get("source_id", "")),
            "value": str(c.get("value", "")),
        }
        for i, c in enumerate(data.get("claims", []))
        if isinstance(c, dict)
    ]
    if sections and claims:
        return {"version": version, "sections": sections, "claims": claims}
    return None


def writer(state: ResearchState, config: RunnableConfig) -> dict[str, Any]:
    ctx = ctx_from(config)
    ctx.step()
    e = ctx.emitter
    attempts = state.get("critic_attempts", 0)
    real = is_real(ctx) and bool(state.get("sources"))

    if attempts == 0:
        e.step_changed(5, 8)
        e.edge_status("hitl->writer", "done")
        e.node_status("writer", "active")
        # Honour the human's HITL decision: an "adjust" note steers this draft.
        note = (state.get("hitl_note") or "").strip()
        if state.get("hitl_decision") == "adjust" and note:
            e.log("info", "Writer", f'incorporating your adjustment: "{note}".', "writer")
        e.log(
            "info", "Writer", "drafting brief with citations from approved sources only.", "writer"
        )

        if real:
            res = ctx.llm.complete(
                system=_SYSTEM,
                prompt=_sources_prompt(state),
                model=ctx.api_model_for("writer"),
                max_tokens=2000,
            )
            ctx.charge(res)
            draft = _parse_draft(res.text, 1) or {"version": 1, "claims": _initial_claims()}
        else:
            ctx.charge(ctx.llm.complete(system="Writer", prompt="draft brief", model=ctx.model_id))
            draft = {"version": 1, "claims": _initial_claims()}

        e.node_status("writer", "done")
        e.edge_status("writer->critic", "flow")
        return {"draft": draft}

    # revision after the Critic rejected unsupported claim(s) (error recovery)
    failed = set(state.get("failed_claims", []))
    prev = state.get("draft", {}).get("claims", [])
    e.node_status("writer", "active")
    e.log("info", "Writer", "revised the flagged claim to the source-supported figure.", "writer")

    if real:
        res = ctx.llm.complete(
            system=_FIX_SYSTEM,
            prompt=json.dumps(
                {
                    "flagged": sorted(failed),
                    "previous_claims": prev,
                    "sources": [
                        {"id": s["id"], "content": s["content"]} for s in state.get("sources", [])
                    ],
                }
            ),
            model=ctx.api_model_for("writer"),
            max_tokens=1500,
        )
        ctx.charge(res)
        fixed = _parse_draft(res.text, 2)
        draft = fixed or {"version": 2, "claims": _corrected_claims(prev, failed)}
    else:
        ctx.charge(
            ctx.llm.complete(system="Writer", prompt="revise flagged claims", model=ctx.model_id)
        )
        draft = {"version": 2, "claims": _corrected_claims(prev, failed)}

    e.edge_status("critic->writer", "retry")  # stop the flowing animation
    e.node_status("writer", "done")
    e.edge_status("writer->critic", "flow")
    return {"draft": draft}
