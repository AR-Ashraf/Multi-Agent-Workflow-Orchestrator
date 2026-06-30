"""Store + retention + redaction unit tests (CLAUDE.md §10), on file-backed
SQLite (the same SQLAlchemy code runs on Postgres in prod)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from cadenza_api.redact import redact_events, redact_text
from cadenza_api.store import NullRunStore, SqlRunStore, build_record


def _events(query: str) -> list[dict]:
    return [
        {
            "type": "run.started",
            "query": query,
            "provider": "anthropic",
            "modelLabel": "Claude Sonnet",
            "mode": "live",
            "seq": 0,
        },
        {
            "type": "run.completed",
            "tokens": 100,
            "costUsd": 0.05,
            "claimsVerified": {"verified": 3, "total": 3},
            "seq": 1,
        },
        {
            "type": "brief.released",
            "brief": {
                "title": "T",
                "query": query,
                "byline": "b",
                "sections": [{"heading": "h", "body": f"see {query}"}],
                "sources": [],
                "claimsVerified": {"verified": 3, "total": 3},
                "mode": "live",
                "model": "Claude Sonnet",
                "permalink": "cadenza.devs-core.com/run/x",
            },
            "seq": 2,
        },
    ]


def test_redact_text_scrubs_keys_and_emails():
    out = redact_text("ping a@b.com key sk-ant-ABCDEF123456 and AIzaSy0123456789abc")
    assert "a@b.com" not in out and "sk-ant-ABCDEF123456" not in out
    assert "AIzaSy0123456789abc" not in out
    assert "[redacted-email]" in out and "[redacted-key]" in out


def test_redact_events_scrubs_nested_brief_and_query():
    events = redact_events(_events("dental sk-ant-LEAKLEAK123456 market"))
    started = next(e for e in events if e["type"] == "run.started")
    brief = next(e for e in events if e["type"] == "brief.released")["brief"]
    assert "sk-ant-LEAKLEAK123456" not in started["query"]
    assert "sk-ant-LEAKLEAK123456" not in brief["query"]
    assert "sk-ant-LEAKLEAK123456" not in brief["sections"][0]["body"]


async def test_store_roundtrip_then_delete(tmp_path):
    store = SqlRunStore(f"sqlite+aiosqlite:///{tmp_path}/r.db", retention_days=30)
    await store.init()
    rec = build_record(
        run_id="r1", status="completed", events=_events("dental market"), retention_days=30
    )
    await store.save(rec)

    got = await store.get("r1")
    assert got is not None
    assert got["run_id"] == "r1" and got["brief"]["title"] == "T"
    assert got["claims_verified"] == {"verified": 3, "total": 3}
    assert isinstance(got["created_at"], str)  # datetimes serialized for JSON

    assert await store.delete("r1") is True
    assert await store.get("r1") is None
    assert await store.delete("r1") is False
    await store.aclose()


async def test_save_is_idempotent_upsert(tmp_path):
    store = SqlRunStore(f"sqlite+aiosqlite:///{tmp_path}/r.db")
    await store.init()
    rec = build_record(run_id="r1", status="completed", events=_events("q"), retention_days=30)
    await store.save(rec)
    await store.save(rec)  # must not raise on duplicate PK
    assert await store.get("r1") is not None
    await store.aclose()


async def test_purge_removes_only_expired(tmp_path):
    store = SqlRunStore(f"sqlite+aiosqlite:///{tmp_path}/r.db")
    await store.init()
    await store.save(
        build_record(run_id="fresh", status="completed", events=_events("q"), retention_days=30)
    )
    expired = build_record(run_id="old", status="completed", events=_events("q"), retention_days=30)
    expired["expires_at"] = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1)
    await store.save(expired)

    assert await store.purge_expired() == 1
    assert await store.get("fresh") is not None
    await store.aclose()


async def test_null_store_is_disabled_and_noops():
    store = NullRunStore()
    assert store.enabled is False
    await store.init()
    assert await store.get("x") is None
    assert await store.delete("x") is False
    assert await store.purge_expired() == 0
    await store.aclose()
