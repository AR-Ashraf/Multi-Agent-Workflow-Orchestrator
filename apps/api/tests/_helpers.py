"""Shared test scaffolding: an ASGI client wired to a RunManager over fakeredis,
with arbitrary Settings overrides (rate limits, spend cap, HITL timeout, ...)."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import fakeredis
import fakeredis.aioredis
import httpx

from cadenza_api.bus import EventBus
from cadenza_api.config import Settings
from cadenza_api.limits import Limiter
from cadenza_api.main import create_app
from cadenza_api.runs import RunManager


@asynccontextmanager
async def make_client(**overrides: object) -> AsyncIterator[tuple[httpx.AsyncClient, RunManager]]:
    settings = Settings(**overrides)  # type: ignore[arg-type]
    server = fakeredis.FakeServer()
    sync = fakeredis.FakeStrictRedis(server=server, decode_responses=True)
    aio = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
    bus = EventBus(sync, aio, ttl_seconds=60)
    manager = RunManager(bus, settings, Limiter(aio, settings))
    transport = httpx.ASGITransport(app=create_app(manager))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        try:
            yield c, manager
        finally:
            await manager.shutdown()


async def wait_status(manager: RunManager, run_id: str, target: str, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        rec = manager.get(run_id)
        if rec and rec.status == target:
            return
        await asyncio.sleep(0.02)
    raise AssertionError(f"run {run_id} never reached '{target}'")
