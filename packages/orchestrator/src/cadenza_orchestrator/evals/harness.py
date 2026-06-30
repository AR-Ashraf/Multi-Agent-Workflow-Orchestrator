"""Eval runner + scoring (CLAUDE.md §7).

For each case it runs the research graph to completion (mocked LLM, auto-approved
HITL) and scores three things:

  * **citation_coverage** — fraction of the brief's cited sources actually
    referenced by an inline `[Source N]` marker in the body.
  * **claims_grounded** — verified/total from the Critic's claim-verification
    (the anti-hallucination guarantee, feature 4).
  * **format_valid** — the brief has a title, sections, sources, and a permalink.

`judge_score` is a deterministic placeholder for an LLM-as-judge; `run_evals`
prints a JSON report by default, but accepts a `sink` (the seam for a Langfuse
writer in prod). A drop in coverage or grounding is a release blocker (§7).
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any

from .. import run_research_brief
from .dataset import EVAL_CASES, EvalCase

_CITE = re.compile(r"\[Source \d+\]")

# Release-blocking thresholds (§7): the cited, claim-verified brief must be fully
# grounded and fully cited.
MIN_CITATION_COVERAGE = 1.0
MIN_CLAIMS_GROUNDED = 1.0


@dataclass
class CaseScore:
    id: str
    query: str
    format_valid: bool
    citation_coverage: float
    claims_grounded: float
    judge_score: float
    passed: bool


def _last(events: list[dict[str, Any]], type_: str) -> dict[str, Any] | None:
    return next((e for e in reversed(events) if e.get("type") == type_), None)


def _heuristic_judge(format_valid: bool, coverage: float, grounded: float) -> float:
    """Deterministic stand-in for an LLM-as-judge (§7). Replace with a real judge."""
    return round((float(format_valid) + min(coverage, 1.0) + min(grounded, 1.0)) / 3, 3)


def score_case(case: EvalCase) -> CaseScore:
    result = run_research_brief(query=case.query, decision="approve")
    events: list[dict[str, Any]] = result["events"]

    brief = result["state"].get("brief")
    if brief is None:
        released = _last(events, "brief.released")
        brief = released["brief"] if released else {}

    completed = _last(events, "run.completed") or {}
    cv = completed.get("claimsVerified", {"verified": 0, "total": 0})
    grounded = cv["verified"] / cv["total"] if cv.get("total") else 0.0

    sources = brief.get("sources", [])
    body = " ".join(s.get("body", "") for s in brief.get("sections", []))
    cited = set(_CITE.findall(body))
    coverage = len(cited) / len(sources) if sources else 0.0

    format_valid = bool(
        brief.get("title") and brief.get("sections") and sources and brief.get("permalink")
    )
    passed = format_valid and coverage >= MIN_CITATION_COVERAGE and grounded >= MIN_CLAIMS_GROUNDED
    return CaseScore(
        id=case.id,
        query=case.query,
        format_valid=format_valid,
        citation_coverage=round(coverage, 3),
        claims_grounded=round(grounded, 3),
        judge_score=_heuristic_judge(format_valid, coverage, grounded),
        passed=passed,
    )


def run_evals(
    cases: list[EvalCase] | None = None,
    sink: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    cases = cases or EVAL_CASES
    scores = [score_case(c) for c in cases]
    n = len(scores)
    summary = {
        "cases": n,
        "passed": sum(s.passed for s in scores),
        "citation_coverage": round(sum(s.citation_coverage for s in scores) / n, 3),
        "claims_grounded": round(sum(s.claims_grounded for s in scores) / n, 3),
        "judge_score": round(sum(s.judge_score for s in scores) / n, 3),
        "all_passed": all(s.passed for s in scores),
    }
    report = {"summary": summary, "cases": [asdict(s) for s in scores]}
    (sink or _print_report)(report)
    return report


def _print_report(report: dict[str, Any]) -> None:
    print(json.dumps(report, indent=2))
