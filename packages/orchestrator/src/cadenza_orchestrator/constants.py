"""Graph + model constants — the Python mirror of @cadenza/shared.

Kept deliberately in sync with packages/shared (topology.ts, models.ts). The
canonical FE/BE *event* contract is the exported JSON Schema, which the contract
test validates emitted events against; these constants are the orchestrator-side
helpers for routing and node identity.
"""

from __future__ import annotations

# --- topology (mirrors topology.ts) ---------------------------------------

NODE_IDS: tuple[str, ...] = (
    "planner",
    "researcher-a",
    "researcher-b",
    "researcher-c",
    "analyst",
    "hitl",
    "writer",
    "critic",
    "output",
)

RESEARCHER_NODE_IDS: tuple[str, ...] = ("researcher-a", "researcher-b", "researcher-c")

TOTAL_STEPS = 8

# --- cost & safety caps (CLAUDE.md §8.3) ----------------------------------
# Enforced even on BYOK runs to protect the visitor from a runaway loop.
MAX_TOKENS = 250_000
MAX_STEPS = 24
MAX_CRITIC_RETRIES = 2
PRICE_PER_TOKEN = 0.000002  # mock estimate; real accounting comes from provider usage

# --- provider / model registry (mirrors models.ts) ------------------------

SMART_NODES: tuple[str, ...] = ("planner", "analyst", "critic")
MECHANICAL_NODES: tuple[str, ...] = ("researcher-a", "researcher-b", "researcher-c", "writer")

PROVIDERS: dict[str, dict] = {
    "anthropic": {
        "label": "Anthropic (Claude)",
        "fast_badge": "Haiku",
        "default_index": 1,
        "models": [
            {"id": "claude-opus", "label": "Claude Opus", "badge": "Opus"},
            {"id": "claude-sonnet", "label": "Claude Sonnet", "badge": "Sonnet"},
            {"id": "claude-haiku", "label": "Claude Haiku", "badge": "Haiku"},
        ],
    },
    "openai": {
        "label": "OpenAI (GPT)",
        "fast_badge": "mini",
        "default_index": 0,
        "models": [
            {"id": "gpt-5", "label": "GPT-5", "badge": "GPT-5"},
            {"id": "gpt-5-mini", "label": "GPT-5 mini", "badge": "mini"},
            {"id": "gpt-4.1", "label": "GPT-4.1", "badge": "4.1"},
            {"id": "o4-mini", "label": "o4-mini", "badge": "o4-mini"},
        ],
    },
    "google": {
        "label": "Google (Gemini)",
        "fast_badge": "Flash",
        "default_index": 0,
        "models": [
            {"id": "gemini-2.5-pro", "label": "Gemini 2.5 Pro", "badge": "2.5 Pro"},
            {"id": "gemini-2.5-flash", "label": "Gemini 2.5 Flash", "badge": "Flash"},
        ],
    },
    "groq": {
        "label": "Groq (Llama / Mixtral)",
        "fast_badge": "8B",
        "default_index": 0,
        "models": [
            {"id": "llama-3.3-70b", "label": "Llama 3.3 70B", "badge": "70B"},
            {"id": "llama-3.1-8b", "label": "Llama 3.1 8B", "badge": "8B"},
            {"id": "mixtral-8x7b", "label": "Mixtral 8x7B", "badge": "Mixtral"},
        ],
    },
    "mistral": {
        "label": "Mistral",
        "fast_badge": "Small",
        "default_index": 0,
        "models": [
            {"id": "mistral-large", "label": "Mistral Large", "badge": "Large"},
            {"id": "mistral-small", "label": "Mistral Small", "badge": "Small"},
        ],
    },
}


def resolve_model(provider: str, model_id: str) -> dict:
    info = PROVIDERS[provider]
    for m in info["models"]:
        if m["id"] == model_id:
            return m
    return info["models"][info["default_index"]]


def assign_models(provider: str, model_id: str, routing: bool) -> list[dict]:
    """Per-node model badge + tier. Mirrors models.ts assignModels()."""
    info = PROVIDERS[provider]
    smart_badge = resolve_model(provider, model_id)["badge"]
    mech_badge = info["fast_badge"] if routing else smart_badge
    out: list[dict] = [
        {"nodeId": n, "modelLabel": smart_badge, "tier": "smart"} for n in SMART_NODES
    ]
    out += [
        {"nodeId": n, "modelLabel": mech_badge, "tier": "fast" if routing else "smart"}
        for n in MECHANICAL_NODES
    ]
    return out


def model_badge_for(node_id: str, provider: str, model_id: str, routing: bool) -> str:
    for a in assign_models(provider, model_id, routing):
        if a["nodeId"] == node_id:
            return a["modelLabel"]
    return resolve_model(provider, model_id)["badge"]
