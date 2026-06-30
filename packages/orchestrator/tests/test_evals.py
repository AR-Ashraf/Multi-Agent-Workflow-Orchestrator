"""Smoke test for the eval harness (CLAUDE.md §7) — the mocked run must score as
fully cited and fully grounded, so a regression in either is caught."""

from __future__ import annotations

from cadenza_orchestrator.evals import EVAL_CASES, run_evals
from cadenza_orchestrator.evals.harness import score_case


def test_eval_harness_scores_the_mock_as_fully_cited_and_grounded():
    captured: dict = {}
    report = run_evals(sink=lambda r: captured.update(r))
    s = report["summary"]
    assert s["all_passed"] is True
    assert s["citation_coverage"] == 1.0
    assert s["claims_grounded"] == 1.0
    assert s["passed"] == s["cases"]
    assert captured == report  # the sink received the full report


def test_each_case_is_grounded_and_cited():
    for case in EVAL_CASES:
        score = score_case(case)
        assert score.format_valid, case.id
        assert score.claims_grounded == 1.0, case.id
        assert score.citation_coverage == 1.0, case.id
        assert score.passed, case.id
