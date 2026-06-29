"""PII / secret redaction for anything we persist or expose (CLAUDE.md §10).

Saved runs and permalinks are PUBLIC, so before a run is written to Postgres we
scrub the free-text fields a visitor could have typed into — emails and
API-key-shaped tokens — from the query and every event. This is defence in
depth: BYOK keys never enter the event stream in the first place, but a visitor
could still paste a secret into their research question.
"""

from __future__ import annotations

import re
from typing import Any

_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_KEY = re.compile(
    r"\b(?:sk-ant-[A-Za-z0-9_\-]{6,}|sk-[A-Za-z0-9]{12,}|AIza[A-Za-z0-9_\-]{10,}"
    r"|gsk_[A-Za-z0-9]{10,}|xox[baprs]-[A-Za-z0-9\-]{8,})\b"
)
_BEARER = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{8,}")

# Event fields that can carry user-influenced free text.
_TEXT_FIELDS = ("text", "detail", "summary", "query", "note", "label")


def redact_text(value: str) -> str:
    out = _KEY.sub("[redacted-key]", value)
    out = _BEARER.sub("Bearer [redacted-key]", out)
    out = _EMAIL.sub("[redacted-email]", out)
    return out


def _redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [_redact_value(v) for v in value]
    if isinstance(value, dict):
        return {k: (_redact_value(v) if k in _TEXT_FIELDS else v) for k, v in value.items()}
    return value


def redact_event(event: dict[str, Any]) -> dict[str, Any]:
    """Return a shallow-redacted copy of one event (only known text fields)."""
    out = dict(event)
    for field in _TEXT_FIELDS:
        if field in out:
            out[field] = _redact_value(out[field])
    # Briefs embed the query + body text; scrub those nested fields too.
    if isinstance(out.get("brief"), dict):
        out["brief"] = _redact_brief(out["brief"])
    return out


def _redact_brief(brief: dict[str, Any]) -> dict[str, Any]:
    out = dict(brief)
    if "query" in out and isinstance(out["query"], str):
        out["query"] = redact_text(out["query"])
    if "byline" in out and isinstance(out["byline"], str):
        out["byline"] = redact_text(out["byline"])
    if isinstance(out.get("sections"), list):
        out["sections"] = [
            {**s, "body": redact_text(s["body"])} if isinstance(s.get("body"), str) else s
            for s in out["sections"]
        ]
    return out


def redact_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [redact_event(e) for e in events]
