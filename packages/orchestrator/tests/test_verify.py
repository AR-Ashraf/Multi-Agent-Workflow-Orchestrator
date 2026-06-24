"""Claim/citation verification tests (CLAUDE.md §7, feature 4) — the verifier in
isolation, plus the real reject→fix→accept loop inside the graph."""

from __future__ import annotations

from cadenza_orchestrator import run_research_brief
from cadenza_orchestrator.corpus import CLAIMS, HALLUCINATED_VALUE, verify_claim


def _claim(cid: str) -> dict[str, str]:
    return next(c for c in CLAIMS if c["id"] == cid)


def test_grounded_claim_is_supported():
    assert verify_claim(_claim("c1")).grounded is True
    assert verify_claim(_claim("c2")).grounded is True
    assert verify_claim(_claim("c3")).grounded is True


def test_hallucinated_value_is_unsupported():
    bad = {**_claim("c3"), "value": HALLUCINATED_VALUE["c3"]}
    assert verify_claim(bad).grounded is False


def test_unknown_source_is_unsupported():
    assert (
        verify_claim({"id": "x", "text": "t", "source_id": "Source 99", "value": "v"}).grounded
        is False
    )


def test_verification_checks_the_cited_source_not_just_any_source():
    # Source 3's pricing value, but cited (wrongly) to Source 1 → must fail.
    miscited = {
        "id": "c",
        "text": "t",
        "source_id": "Source 1",
        "value": "$300–$800 per location per month",
    }
    assert verify_claim(miscited).grounded is False


def test_critic_rejects_hallucination_then_accepts_after_revision():
    events = run_research_brief(run_id="verify", decision="approve")["events"]
    claims = [e for e in events if e["type"] == "claim.verified"]
    assert len(claims) == 4  # c1✓ c2✓ c3✗ then c3✓
    c3 = [e for e in claims if e["claimId"] == "c3"]
    assert [e["verdict"] for e in c3] == ["unsupported", "grounded"]
    assert any(e["type"] == "brief.released" for e in events)
    assert events[-1]["state"] == "done"
