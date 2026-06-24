"""Cited-source corpus + claim verifier (CLAUDE.md §9, feature 4).

The Critic's anti-hallucination check is REAL here: `verify_claim` grounds each
claim's key value against the text of its cited source. A claim is `grounded`
only if its value actually appears in the cited source; otherwise it is
`unsupported`. This is a deterministic, no-LLM check (fully testable) and the
seam where an LLM grounding judge can be added later — exactly like the guard.

The dental fixtures drive the retry loop for real: the Writer's first draft cites
a no-show-cost figure that is NOT in Source 2, so the Critic rejects it; the
revision uses the source-supported figure, which verifies.
"""

from __future__ import annotations

from dataclasses import dataclass

SOURCES: list[dict[str, str]] = [
    {
        "id": "Source 1",
        "label": "ADA Health Policy Institute — Supply of Dentists in the US (2024)",
        "url": "https://example.test/source-1",
        "content": "ADA data: the US has roughly 183,000 practicing dentists across about 135,000 practices.",
    },
    {
        "id": "Source 2",
        "label": "Dental practice operations & no-show cost analysis (2025)",
        "url": "https://example.test/source-2",
        "content": "Front-desk no-shows cost a typical practice $50,000–$70,000 a year in lost chair time.",
    },
    {
        "id": "Source 3",
        "label": "Patient-communication platform pricing pages (accessed Jun 2026)",
        "url": "https://example.test/source-3",
        "content": "Vendors bundle AI scheduling into suites priced at $300–$800 per location per month.",
    },
]

# The key claims the Writer makes, each with the source-supported value.
CLAIMS: list[dict[str, str]] = [
    {
        "id": "c1",
        "text": "183,000 US dentists",
        "source_id": "Source 1",
        "value": "183,000 practicing dentists",
    },
    {
        "id": "c2",
        "text": "competitor pricing $300–$800/mo",
        "source_id": "Source 3",
        "value": "$300–$800 per location per month",
    },
    {
        "id": "c3",
        "text": "front-desk no-show cost",
        "source_id": "Source 2",
        "value": "$50,000–$70,000 a year",
    },
]

# The Writer's first-draft hallucination — NOT supported by Source 2.
HALLUCINATED_VALUE: dict[str, str] = {"c3": "$80,000–$100,000 a year"}


@dataclass(frozen=True)
class ClaimVerdict:
    grounded: bool
    reason: str


def _norm(text: str) -> str:
    return " ".join(text.replace("—", "-").replace("–", "-").lower().split())


def source_by_id(source_id: str, sources: list[dict[str, str]] = SOURCES) -> dict[str, str] | None:
    return next((s for s in sources if s["id"] == source_id), None)


def verify_claim(claim: dict[str, str], sources: list[dict[str, str]] = SOURCES) -> ClaimVerdict:
    """Grounded iff the claim's value appears in the text of its cited source."""
    src = source_by_id(claim["source_id"], sources)
    if src is None:
        return ClaimVerdict(False, f"cited {claim['source_id']} not found")
    if _norm(claim["value"]) in _norm(src["content"]):
        return ClaimVerdict(True, f"grounded in {claim['source_id']}")
    return ClaimVerdict(False, f"value not supported by {claim['source_id']}")
