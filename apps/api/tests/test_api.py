"""Gateway integration tests — start → pause → decision → complete, streamed via
the bus; plus BYOK validation + key redaction (CLAUDE.md §6, §10)."""

from __future__ import annotations

import asyncio
import json
import time

import httpx

from cadenza_api.bus import EventBus

DENTAL = "Market for AI scheduling assistants for US dental clinics"


async def _wait_status(client: httpx.AsyncClient, run_id: str, target: str, timeout: float = 5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        body = (await client.get(f"/api/runs/{run_id}")).json()
        if body["status"] == target:
            return body
        await asyncio.sleep(0.02)
    raise AssertionError(f"run {run_id} never reached '{target}'")


async def test_healthz(client: httpx.AsyncClient):
    r = await client.get("/healthz")
    assert r.status_code == 200 and r.json()["status"] == "ok"


async def test_no_key_runs_in_demo_mode(client: httpx.AsyncClient):
    r = await client.post("/api/runs", json={"query": DENTAL})
    assert r.status_code == 200
    assert r.json()["mode"] == "demo"


async def test_invalid_key_is_rejected_before_run(client: httpx.AsyncClient):
    r = await client.post(
        "/api/runs", json={"query": DENTAL, "provider": "anthropic", "api_key": "oops"}
    )
    assert r.status_code == 400


async def test_decision_on_unknown_run_is_404(client: httpx.AsyncClient):
    r = await client.post("/api/runs/does-not-exist/decision", json={"decision": "approve"})
    assert r.status_code == 404


async def test_full_run_completes_and_never_leaks_the_key(client: httpx.AsyncClient, bus: EventBus):
    key = "sk-ant-SECRET-do-not-leak-1234"
    r = await client.post(
        "/api/runs",
        json={"query": DENTAL, "provider": "anthropic", "model": "claude-sonnet", "api_key": key},
    )
    assert r.status_code == 200
    body = r.json()
    run_id = body["run_id"]
    assert body["mode"] == "live"

    await _wait_status(client, run_id, "paused")
    pre = await bus.replay(run_id)
    pre_types = [e["type"] for e in pre]
    assert "hitl.requested" in pre_types
    assert any(e["type"] == "injection.screened" and e["status"] == "blocked" for e in pre)
    assert "brief.released" not in pre_types  # not until approved

    r2 = await client.post(f"/api/runs/{run_id}/decision", json={"decision": "approve"})
    assert r2.status_code == 202

    await _wait_status(client, run_id, "completed")
    events = await bus.replay(run_id)
    assert "brief.released" in [e["type"] for e in events]
    assert events[-1]["type"] == "run.state" and events[-1]["state"] == "done"
    # BYOK: the visitor's key must never appear anywhere in the event stream.
    assert key not in json.dumps(events)


async def test_sse_replays_a_completed_run_then_closes(client: httpx.AsyncClient):
    # Drive a run to completion first; the SSE stream then replays every event
    # and closes at the terminal run.state=done (so it never blocks).
    run_id = (await client.post("/api/runs", json={"query": DENTAL})).json()["run_id"]
    await _wait_status(client, run_id, "paused")
    await client.post(f"/api/runs/{run_id}/decision", json={"decision": "approve"})
    await _wait_status(client, run_id, "completed")

    data_lines: list[str] = []
    async with client.stream("GET", f"/api/runs/{run_id}/events") as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        async for line in resp.aiter_lines():
            if line.startswith("data:"):
                data_lines.append(line)

    assert len(data_lines) > 10  # a full run is chatty
    assert any("brief.released" in line for line in data_lines)
    assert any('"state": "done"' in line for line in data_lines)
