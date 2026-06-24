"""Injection guard — screens untrusted tool/web content before any agent acts on
it (CLAUDE.md §9; OWASP LLM01 indirect prompt injection).

A deterministic, rule-based classifier (no LLM, fully testable). It returns one
of three verdicts:

  - ``passed``    — no injection signal; content goes through unchanged.
  - ``sanitized`` — low-severity instruction-like lines stripped; the rest kept.
  - ``blocked``   — an explicit instruction-override / exfiltration attempt; the
                    whole page is quarantined (``safe_content`` is empty) so the
                    model never sees it. The run continues with other sources.

This is the seam where an optional LLM-based second-pass classifier can be added
later; the emitted ``injection.screened`` event shape is already final.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Hard-block: explicit instruction-override / secret-exfiltration aimed at the model.
_HARD_BLOCK_PATTERNS = [
    r"ignore (?:your|the|all|previous|prior) (?:task|tasks|instructions?|prompt|directions?)",
    r"disregard (?:the|all|any|previous|prior) (?:above|instructions?|prompt|rules?)",
    r"forget (?:your|the|all|previous) (?:instructions?|prompt|rules?)",
    r"output (?:the )?(?:admin|system|developer) prompt",
    r"reveal (?:your )?(?:system |developer )?(?:prompt|instructions?)",
    r"print (?:your )?(?:system )?prompt",
    r"system note to the assistant",
    r"you are now (?:a |an |the )?",
    r"do (?:this|the following) instead",
    r"override (?:your|the) (?:instructions?|rules?|task)",
]

# Lower-severity: strip the offending line but keep the page.
_SANITIZE_PATTERNS = [
    r"click here to (?:claim|verify|continue|unlock)",
    r"\benter your (?:password|api key|credentials|secret)\b",
]

_HARD_RE = [re.compile(p, re.IGNORECASE) for p in _HARD_BLOCK_PATTERNS]
_SANITIZE_RE = [re.compile(p, re.IGNORECASE) for p in _SANITIZE_PATTERNS]


@dataclass
class ScreenResult:
    status: str  # "passed" | "sanitized" | "blocked"
    reason: str
    safe_content: str
    matched: list[str] = field(default_factory=list)
    source_url: str | None = None


def screen_content(text: str, *, source_url: str | None = None) -> ScreenResult:
    """Classify untrusted content and return a screening verdict + safe payload."""
    hard_matches: list[str] = []
    for pattern in _HARD_RE:
        m = pattern.search(text)
        if m:
            hard_matches.append(m.group(0).strip())

    if hard_matches:
        return ScreenResult(
            status="blocked",
            reason="Embedded instructions detected (indirect prompt injection); page quarantined, never fed to the model.",
            safe_content="",  # quarantined — nothing passes downstream
            matched=hard_matches,
            source_url=source_url,
        )

    kept: list[str] = []
    stripped: list[str] = []
    for line in text.splitlines():
        if any(p.search(line) for p in _SANITIZE_RE):
            stripped.append(line.strip())
        else:
            kept.append(line)

    if stripped:
        return ScreenResult(
            status="sanitized",
            reason="Suspicious instruction-like content removed; the rest of the page was kept.",
            safe_content="\n".join(kept),
            matched=stripped,
            source_url=source_url,
        )

    return ScreenResult(
        status="passed",
        reason="No injection signal detected.",
        safe_content=text,
        source_url=source_url,
    )
