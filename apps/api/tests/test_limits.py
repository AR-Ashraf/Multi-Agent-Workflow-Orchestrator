"""Cost & safety guardrail tests (CLAUDE.md §8) — per-IP rate limiting, the
house spend cap, the graceful demo fallback, and per-run ceilings. Everything
runs on fakeredis + the offline mock LLM, so nothing is billed and the suite is
deterministic."""

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

DENTAL = "Market for AI scheduling assistants for US dental clinics"
KEY = "sk-ant-test-key-123456"


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


async def _wait_status(manager: RunManager, run_id: str, target: str, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        rec = manager.get(run_id)
        if rec and rec.status == target:
            return
        await asyncio.sleep(0.02)
    raise AssertionError(f"run {run_id} never reached '{target}'")


async def test_byok_runs_are_throttled_then_fall_back_to_demo():
    # 2 live BYOK runs allowed per window; the 3rd is gracefully served demo.
    async with make_client(rate_limit_max_runs=2, rate_limit_window_seconds=60) as (client, _):
        body = {"query": DENTAL, "provider": "anthropic", "api_key": KEY}
        first = (await client.post("/api/runs", json=body)).json()
        second = (await client.post("/api/runs", json=body)).json()
        third = (await client.post("/api/runs", json=body)).json()

    assert first["mode"] == "live" and first["run_id"]
    assert second["mode"] == "live"
    assert third["mode"] == "demo"
    assert third["run_id"] is None
    assert third["reason"] == "rate_limited"


async def test_no_key_without_house_funding_is_demo_no_key():
    async with make_client(house_api_key=None) as (client, _):
        r = (await client.post("/api/runs", json={"query": DENTAL})).json()
    assert r["mode"] == "demo"
    assert r["reason"] == "no_key"
    assert r["run_id"] is None


async def test_house_funding_runs_a_real_backend_run_when_under_cap():
    async with make_client(house_api_key="sk-ant-house-key", daily_spend_cap_usd=5.0) as (
        client,
        manager,
    ):
        r = (await client.post("/api/runs", json={"query": DENTAL})).json()
        assert r["mode"] == "live"  # funded by the house, not the visitor
        assert r["run_id"]
        rec = manager.get(r["run_id"])
        assert rec is not None and rec.funded_by == "house"


async def test_house_funding_falls_back_to_demo_when_cap_is_exhausted():
    # Cap below the per-run reservation → the very first no-key run is declined.
    async with make_client(
        house_api_key="sk-ant-house-key",
        daily_spend_cap_usd=0.0,
        estimated_run_cost_usd=0.30,
    ) as (client, _):
        r = (await client.post("/api/runs", json={"query": DENTAL})).json()
    assert r["mode"] == "demo"
    assert r["reason"] == "daily_cap"


async def test_house_spend_counter_settles_to_actual_cost():
    settings_overrides = dict(
        house_api_key="sk-ant-house-key",
        daily_spend_cap_usd=5.0,
        estimated_run_cost_usd=0.30,
    )
    async with make_client(**settings_overrides) as (client, manager):
        r = (await client.post("/api/runs", json={"query": DENTAL})).json()
        run_id = r["run_id"]
        await _wait_status(manager, run_id, "paused")
        await client.post(f"/api/runs/{run_id}/decision", json={"decision": "approve"})
        await _wait_status(manager, run_id, "completed")
        # After settlement the day's counter reflects the run's actual (mock) cost,
        # not the 0.30 reservation.
        spent = await manager.limiter.daily_spend()
        rec = manager.get(run_id)
        assert rec is not None
        from cadenza_api.runs import _run_cost

        assert abs(spent - _run_cost(rec.session)) < 1e-6
        assert spent < 0.30  # the mock run is far cheaper than the reservation


async def test_per_run_step_ceiling_ends_the_run_cleanly():
    # A tiny step ceiling trips the orchestrator's budget guard immediately; the
    # run ends in 'error' with a budget_exceeded event rather than hanging.
    async with make_client(per_run_max_steps=1) as (client, manager):
        r = (await client.post("/api/runs", json={"query": DENTAL, "api_key": KEY})).json()
        run_id = r["run_id"]
        await _wait_status(manager, run_id, "error")
        rec = manager.get(run_id)
        assert rec is not None
        types = [(e.get("type"), e.get("code")) for e in rec.session.events]
        assert ("error", "budget_exceeded") in types
