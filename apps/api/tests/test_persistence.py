"""Permalink persistence over the gateway (CLAUDE.md §10): a finished run is saved
and served via its permalink, can be purged, falls back to memory without a DB,
and never persists a visitor's pasted secret/PII."""

from __future__ import annotations

import json

import httpx
from _helpers import make_client, wait_status

DENTAL = "Market for AI scheduling assistants for US dental clinics"
KEY = "sk-ant-test-key-123456"


async def _complete(client: httpx.AsyncClient, manager, query: str = DENTAL) -> str:
    run_id = (await client.post("/api/runs", json={"query": query, "api_key": KEY})).json()[
        "run_id"
    ]
    await wait_status(manager, run_id, "paused")
    await client.post(f"/api/runs/{run_id}/decision", json={"decision": "approve"})
    await wait_status(manager, run_id, "completed")
    return run_id


async def test_completed_run_is_saved_and_served_via_permalink(tmp_path):
    url = f"sqlite+aiosqlite:///{tmp_path}/r.db"
    async with make_client(database_url=url) as (client, manager):
        run_id = await _complete(client, manager)
        r = await client.get(f"/api/runs/{run_id}/record")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "completed"
        assert body["brief"]["claimsVerified"] == {"verified": 3, "total": 3}
        assert body["run_id"] == run_id
        assert body["brief"]["permalink"].endswith(run_id)
        assert any(e["type"] == "brief.released" for e in body["events"])


async def test_delete_purges_the_saved_run(tmp_path):
    url = f"sqlite+aiosqlite:///{tmp_path}/r.db"
    async with make_client(database_url=url) as (client, manager):
        run_id = await _complete(client, manager)
        assert (await client.delete(f"/api/runs/{run_id}")).status_code == 200
        assert (await client.get(f"/api/runs/{run_id}/record")).status_code == 404
        assert (await client.delete(f"/api/runs/{run_id}")).status_code == 404


async def test_permalink_falls_back_to_memory_without_a_database(tmp_path):
    # No database_url → NullStore; the finished run is still summarizable from
    # memory for the life of the process (durable permalinks need the DB).
    async with make_client() as (client, manager):
        run_id = await _complete(client, manager)
        r = await client.get(f"/api/runs/{run_id}/record")
        assert r.status_code == 200
        assert r.json()["run_id"] == run_id


async def test_unknown_permalink_is_404(tmp_path):
    url = f"sqlite+aiosqlite:///{tmp_path}/r.db"
    async with make_client(database_url=url) as (client, _):
        assert (await client.get("/api/runs/nope/record")).status_code == 404


async def test_pasted_secret_and_pii_are_redacted_before_persistence(tmp_path):
    url = f"sqlite+aiosqlite:///{tmp_path}/r.db"
    leaked = "sk-ant-SECRETLEAK987654"
    query = f"{DENTAL} — reach me at founder@example.com {leaked}"
    async with make_client(database_url=url) as (client, manager):
        run_id = await _complete(client, manager, query=query)
        body = (await client.get(f"/api/runs/{run_id}/record")).json()
        blob = json.dumps(body)
        assert leaked not in blob
        assert "founder@example.com" not in blob
        assert "[redacted-key]" in blob and "[redacted-email]" in blob
