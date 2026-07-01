"""Analyst — synthesizes researcher findings, proposes a direction, then triggers
the human checkpoint.

Real path: clusters the screened findings into insights + a 3-point proposed
direction, and numbers the gathered pages as the citable Source list the Writer
and Critic use. Mock path: the fixed `DIRECTION` (deterministic CI).

The HITL surface events (paused state + hitl.requested) are emitted here, at the
*end* of the analyst node, rather than inside the `hitl` node. The hitl node body
is re-executed on resume, so keeping it free of emits avoids double-emitting the
checkpoint prompt.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.runnables import RunnableConfig

from ..llm import LLMError, parse_json
from ..state import ResearchState
from ._base import ctx_from, is_real

DIRECTION = [
    "Lead with US market size + growth for the niche",
    "Profile the 3 strongest competitors & their pricing",
    "Close with the gap Devs Core could win",
]

_SYSTEM = (
    "You are the Analyst. You are given JSON research findings (each with a "
    "sub-task and screened page content). Cluster them into a short insight and "
    "propose a 3-point direction for a market-research brief. Respond with ONLY "
    'JSON: {"insights": "<2-3 sentences>", "direction": ["<point1>","<point2>","<point3>"]}.'
)


def _build_sources(findings: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Number the screened pages as Source 1..N (stable order by node id)."""
    have = sorted((f for f in findings if f.get("content")), key=lambda f: f.get("node", ""))
    return [
        {
            "id": f"Source {i + 1}",
            "label": str(f.get("title") or f.get("source") or f"Source {i + 1}"),
            "url": str(f.get("source", "")),
            "content": str(f.get("content", "")),
        }
        for i, f in enumerate(have)
    ]


def _synthesize(ctx, findings: list[dict[str, Any]]):
    """Return (insights, direction, sources, llm_result)."""
    real = is_real(ctx)
    if not real:
        res = ctx.llm.complete(system="Analyst", prompt=str(findings), model=ctx.model_id)
        return "mid-market is underserved", DIRECTION, [], res

    sources = _build_sources(findings)
    prompt = json.dumps(
        [{"subtask": s["label"], "source": s["id"], "content": s["content"]} for s in sources]
        or findings
    )
    res = ctx.llm.complete(
        system=_SYSTEM, prompt=prompt, model=ctx.api_model_for("analyst"), max_tokens=800
    )
    insights, direction = "mid-market is underserved", DIRECTION
    try:
        data = parse_json(res.text)
        if isinstance(data, dict):
            insights = str(data.get("insights") or insights)
            dirs = [str(x).strip() for x in (data.get("direction") or []) if str(x).strip()]
            if dirs:
                direction = dirs[:4]
    except (LLMError, TypeError):
        pass
    return insights, direction, sources, res


def analyst(state: ResearchState, config: RunnableConfig) -> dict[str, Any]:
    ctx = ctx_from(config)
    ctx.step()
    e = ctx.emitter

    e.step_changed(3, 8)
    for edge in ("researcher-a->analyst", "researcher-b->analyst", "researcher-c->analyst"):
        e.edge_status(edge, "done")
    e.node_status("analyst", "active")

    insights, direction, sources, res = _synthesize(ctx, state.get("findings", []))
    ctx.charge(res)

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
        direction,
        ["approve", "adjust"],
    )

    out: dict[str, Any] = {"insights": insights, "direction": direction}
    if sources:
        out["sources"] = sources
    return out
