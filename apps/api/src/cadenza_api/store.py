"""Durable run store + retention (CLAUDE.md §10, §4).

On completion a run is persisted so its cited, claim-verified brief and full
event stream can be loaded/replayed from a shareable permalink. Records carry an
`expires_at` and auto-expire after the retention window (default 30 days); a
specific run can also be purged on request.

Backed by SQLAlchemy async Core so the same code runs on Postgres in prod
(`postgresql+asyncpg://…`) and on in-memory SQLite in tests. `NullRunStore` is
used when no `database_url` is configured (local dev without a DB) — persistence
simply no-ops and permalinks 404.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    delete,
    insert,
    select,
)
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

metadata = MetaData()

runs_table = Table(
    "runs",
    metadata,
    Column("run_id", String(64), primary_key=True),
    Column("created_at", DateTime, nullable=False),
    Column("expires_at", DateTime, nullable=False, index=True),
    Column("query", Text, nullable=False, default=""),
    Column("provider", String(32), nullable=False, default=""),
    Column("model_label", String(64), nullable=False, default=""),
    Column("mode", String(16), nullable=False, default="demo"),
    Column("status", String(16), nullable=False, default="completed"),
    Column("tokens", Integer, nullable=False, default=0),
    Column("cost_usd", Float, nullable=False, default=0.0),
    Column("claims_verified", JSON, nullable=False),
    Column("brief", JSON, nullable=True),
    Column("events", JSON, nullable=False),
)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class RunStore(Protocol):
    enabled: bool

    async def init(self) -> None: ...
    async def save(self, record: dict[str, Any]) -> None: ...
    async def get(self, run_id: str) -> dict[str, Any] | None: ...
    async def delete(self, run_id: str) -> bool: ...
    async def purge_expired(self, now: datetime | None = None) -> int: ...
    async def aclose(self) -> None: ...


class NullRunStore:
    """No-op store for local dev without a database. Permalinks 404 gracefully."""

    enabled = False

    async def init(self) -> None: ...
    async def save(self, record: dict[str, Any]) -> None: ...
    async def get(self, run_id: str) -> dict[str, Any] | None:
        return None

    async def delete(self, run_id: str) -> bool:
        return False

    async def purge_expired(self, now: datetime | None = None) -> int:
        return 0

    async def aclose(self) -> None: ...


class SqlRunStore:
    enabled = True

    def __init__(self, url: str, *, retention_days: int = 30) -> None:
        self._engine: AsyncEngine = create_async_engine(url)
        self.retention_days = retention_days

    async def init(self) -> None:
        async with self._engine.begin() as conn:
            await conn.run_sync(metadata.create_all)

    async def save(self, record: dict[str, Any]) -> None:
        # Portable upsert: delete-then-insert in one transaction.
        async with self._engine.begin() as conn:
            await conn.execute(delete(runs_table).where(runs_table.c.run_id == record["run_id"]))
            await conn.execute(insert(runs_table).values(**record))

    async def get(self, run_id: str) -> dict[str, Any] | None:
        async with self._engine.connect() as conn:
            row = (
                (await conn.execute(select(runs_table).where(runs_table.c.run_id == run_id)))
                .mappings()
                .first()
            )
        if row is None:
            return None
        if row["expires_at"] <= _utcnow():  # treat an expired row as gone
            return None
        return serialize_record(dict(row))

    async def delete(self, run_id: str) -> bool:
        async with self._engine.begin() as conn:
            result = await conn.execute(delete(runs_table).where(runs_table.c.run_id == run_id))
        return bool(result.rowcount)

    async def purge_expired(self, now: datetime | None = None) -> int:
        cutoff = now or _utcnow()
        async with self._engine.begin() as conn:
            result = await conn.execute(delete(runs_table).where(runs_table.c.expires_at <= cutoff))
        return int(result.rowcount or 0)

    async def aclose(self) -> None:
        await self._engine.dispose()


def serialize_record(row: dict[str, Any]) -> dict[str, Any]:
    """JSON-friendly: datetimes → ISO strings."""
    for key in ("created_at", "expires_at"):
        value = row.get(key)
        if isinstance(value, datetime):
            row[key] = value.isoformat()
    return row


def build_record(
    *,
    run_id: str,
    status: str,
    events: list[dict[str, Any]],
    retention_days: int,
) -> dict[str, Any]:
    """Summarize a finished run's events into a persistable row."""
    started = next((e for e in events if e.get("type") == "run.started"), {})
    completed = next((e for e in reversed(events) if e.get("type") == "run.completed"), {})
    brief_ev = next((e for e in reversed(events) if e.get("type") == "brief.released"), None)
    now = _utcnow()
    return {
        "run_id": run_id,
        "created_at": now,
        "expires_at": now + timedelta(days=retention_days),
        "query": started.get("query", ""),
        "provider": started.get("provider", ""),
        "model_label": started.get("modelLabel", ""),
        "mode": started.get("mode", "demo"),
        "status": status,
        "tokens": int(completed.get("tokens", 0)),
        "cost_usd": float(completed.get("costUsd", 0.0)),
        "claims_verified": completed.get("claimsVerified", {"verified": 0, "total": 0}),
        "brief": brief_ev["brief"] if brief_ev else None,
        "events": events,
    }


def make_store(url: str | None, *, retention_days: int = 30) -> RunStore:
    if not url:
        return NullRunStore()
    return SqlRunStore(url, retention_days=retention_days)
