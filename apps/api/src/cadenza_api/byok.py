"""Bring-your-own-key handling (CLAUDE.md §5/§6).

The visitor supplies their own provider key. We do a cheap, offline FORMAT check
before starting a run (real provider probe lands with the live adapters), and we
NEVER store or log the key — it lives only in the request scope. `redact` exists
so that if a key ever must be referenced, it is masked.
"""

from __future__ import annotations

_PREFIXES: dict[str, str] = {
    "anthropic": "sk-ant-",
    "openai": "sk-",
    "google": "AIza",
    "groq": "gsk_",
    "mistral": "",
}


def validate_key(provider: str, key: str) -> tuple[bool, str]:
    key = key.strip()
    if not key:
        return False, "API key is empty"
    if len(key) < 8:
        return False, "API key looks too short"
    prefix = _PREFIXES.get(provider, "")
    if prefix and not key.startswith(prefix):
        return False, f"a {provider} key should start with '{prefix}'"
    return True, "ok"


def redact(key: str) -> str:
    key = key.strip()
    if len(key) <= 8:
        return "…"
    return f"{key[:6]}…{key[-2:]}"
