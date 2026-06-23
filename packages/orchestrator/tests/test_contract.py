"""Cross-language contract test — the orchestrator's emitted events must validate
against the canonical event schema exported from @cadenza/shared (events.ts).

This is the single source of truth for the FE/BE contract (CLAUDE.md §4, §5, §7):
the TS Zod schema is exported to JSON Schema and the Python side is held to it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cadenza_orchestrator import run_research_brief

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3]
    / "packages"
    / "shared"
    / "schema"
    / "cadenza-events.schema.json"
)


def _load_schema() -> dict:
    if not _SCHEMA_PATH.exists():
        pytest.skip(
            f"schema not generated yet: run `pnpm --filter @cadenza/shared gen:schema` ({_SCHEMA_PATH})"
        )
    return json.loads(_SCHEMA_PATH.read_text())


def test_every_emitted_event_matches_the_shared_schema():
    import jsonschema

    schema = _load_schema()
    validator = jsonschema.Draft7Validator(schema)

    events = run_research_brief(run_id="contract", decision="approve")["events"]
    assert len(events) > 30  # a full run is chatty

    for e in events:
        errors = sorted(validator.iter_errors(e), key=lambda err: err.path)
        assert (
            not errors
        ), f"event {e.get('type')} @seq {e.get('seq')} violates contract: {errors[0].message}"


def test_adjust_path_also_conforms():
    import jsonschema

    schema = _load_schema()
    validator = jsonschema.Draft7Validator(schema)
    for e in run_research_brief(run_id="c2", decision="adjust")["events"]:
        assert validator.is_valid(e), f"{e.get('type')} invalid"
