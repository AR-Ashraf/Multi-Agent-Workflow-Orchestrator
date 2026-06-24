"""Test fixtures — a fakeredis-backed bus (no real Redis in CI) and an ASGI
client wired to a RunManager."""

from __future__ import annotations

from collections.abc import AsyncIterator

import fakeredis
import fakeredis.aioredis
import httpx
import pytest
import pytest_asyncio

from cadenza_api.bus import EventBus
from cadenza_api.main import create_app
from cadenza_api.runs import RunManager


@pytest.fixture
def bus() -> EventBus:
    server = fakeredis.FakeServer()
    sync_client = fakeredis.FakeStrictRedis(server=server, decode_responses=True)
    async_client = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
    return EventBus(sync_client, async_client, ttl_seconds=60)


@pytest.fixture
def manager(bus: EventBus) -> RunManager:
    return RunManager(bus)


@pytest_asyncio.fixture
async def client(manager: RunManager) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(manager)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await manager.shutdown()
