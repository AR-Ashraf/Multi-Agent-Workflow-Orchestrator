"""Test fixtures — a fakeredis-backed bus + limiter (no real Redis in CI) and an
ASGI client wired to a RunManager. The bus and the limiter share one fake Redis
server so rate-limit / spend keys live alongside the event buffers."""

from __future__ import annotations

from collections.abc import AsyncIterator

import fakeredis
import fakeredis.aioredis
import httpx
import pytest
import pytest_asyncio

from cadenza_api.bus import EventBus
from cadenza_api.config import Settings
from cadenza_api.limits import Limiter
from cadenza_api.main import create_app
from cadenza_api.runs import RunManager


@pytest.fixture
def redis_server() -> fakeredis.FakeServer:
    return fakeredis.FakeServer()


@pytest.fixture
def async_redis(redis_server: fakeredis.FakeServer) -> fakeredis.aioredis.FakeRedis:
    return fakeredis.aioredis.FakeRedis(server=redis_server, decode_responses=True)


@pytest.fixture
def bus(redis_server: fakeredis.FakeServer, async_redis: fakeredis.aioredis.FakeRedis) -> EventBus:
    sync_client = fakeredis.FakeStrictRedis(server=redis_server, decode_responses=True)
    return EventBus(sync_client, async_redis, ttl_seconds=60)


@pytest.fixture
def settings() -> Settings:
    # Default test posture: rate limit effectively off, house funding off
    # (Option A — pure BYOK, $0 floor), and the mock graph (no live LLM calls).
    return Settings(rate_limit_max_runs=1000, house_api_key=None, real_llm_enabled=False)


@pytest.fixture
def limiter(async_redis: fakeredis.aioredis.FakeRedis, settings: Settings) -> Limiter:
    return Limiter(async_redis, settings)


@pytest.fixture
def manager(bus: EventBus, settings: Settings, limiter: Limiter) -> RunManager:
    return RunManager(bus, settings, limiter)


@pytest_asyncio.fixture
async def client(manager: RunManager) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(manager)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await manager.shutdown()
