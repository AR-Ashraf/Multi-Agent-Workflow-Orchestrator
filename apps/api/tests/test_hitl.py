"""HITL wiring tests (CLAUDE.md §1 feature, §4) — the interrupt/resume bridge
end-to-end over the gateway: the adjust note reaches the Writer, an abandoned
checkpoint times out cleanly, the decision works without a live stream, and a
reconnecting client replays the checkpoint then resumes to completion.

All on fakeredis + the mock LLM — deterministic, nothing billed."""

from __future__ import annotations

import json

import httpx
from _helpers import make_client, wait_status

DENTAL = "Market for AI scheduling assistants for US dental clinics"
KEY = "sk-ant-test-key-123456"


async def _start_live(client: httpx.AsyncClient) -> str:
    r = await client.post("/api/runs", json={"query": DENTAL, "api_key": KEY})
    assert r.status_code == 200 and r.json()["mode"] == "live"
    return r.json()["run_id"]


async def test_adjust_note_flows_through_to_the_writer():
    async with make_client() as (client, manager):
        run_id = await _start_live(client)
        await wait_status(manager, run_id, "paused")

        note = "emphasize pricing & the mid-market gap"
        r = await client.post(
            f"/api/runs/{run_id}/decision", json={"decision": "adjust", "note": note}
        )
        assert r.status_code == 202
        await wait_status(manager, run_id, "completed")

        events = await manager.bus.replay(run_id)
        resolved = next(e for e in events if e["type"] == "hitl.resolved")
        assert resolved["decision"] == "adjust"
        assert resolved["note"] == note
        # The Writer visibly acted on the human's note.
        assert any(
            e["type"] == "log" and e.get("nodeId") == "writer" and note in e["text"] for e in events
        )
        assert "brief.released" in [e["type"] for e in events]


async def test_abandoned_checkpoint_times_out_cleanly():
    # A 1s approval window: no decision is submitted, so the run must cancel
    # itself rather than hang forever holding resources.
    async with make_client(hitl_timeout_seconds=1) as (client, manager):
        run_id = await _start_live(client)
        await wait_status(manager, run_id, "paused")
        await wait_status(manager, run_id, "error", timeout=6.0)

        events = await manager.bus.replay(run_id)
        assert any(e["type"] == "error" and e["code"] == "hitl_timeout" for e in events)
        assert events[-1]["type"] == "run.state" and events[-1]["state"] == "error"


async def test_decision_resolves_without_a_live_stream_then_reconnect_replays():
    # The approval POST is independent of any SSE connection (resilient to drops);
    # a client that (re)connects afterwards replays from its last seq through the
    # checkpoint to completion, and the stream closes at the terminal event.
    async with make_client() as (client, manager):
        run_id = await _start_live(client)
        await wait_status(manager, run_id, "paused")

        # No SSE open at all — approve purely over REST.
        assert (
            await client.post(f"/api/runs/{run_id}/decision", json={"decision": "approve"})
        ).status_code == 202
        await wait_status(manager, run_id, "completed")

        # Reconnect from an early seq (simulating a drop mid-research).
        data: list[str] = []
        headers = {"last-event-id": "3"}
        async with client.stream("GET", f"/api/runs/{run_id}/events", headers=headers) as resp:
            assert resp.status_code == 200
            async for line in resp.aiter_lines():
                if line.startswith("data:"):
                    data.append(line)

        seqs = [json.loads(line[5:].strip())["seq"] for line in data]
        assert min(seqs) > 3  # only events after the reconnect point
        types = {json.loads(line[5:].strip())["type"] for line in data}
        assert {"hitl.requested", "hitl.resolved", "brief.released"} <= types
        assert any('"state": "done"' in line for line in data)
