"""FastAPI app — REST endpoints + the SSE stream.

`create_app(manager)` builds the routes around an injected RunManager (tests
inject a fakeredis-backed bus). `build_app()` wires the real Redis clients from
settings for `uvicorn cadenza_api.main:app`.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from .bus import EventBus
from .config import Settings, get_settings
from .limits import Limiter
from .runs import DecisionNotAllowed, RunManager
from .schemas import DecisionRequest, RunStatusResponse, StartRunRequest, StartRunResponse


def _client_ip(request: Request) -> str:
    """Caller IP for rate limiting — honours the first X-Forwarded-For hop set by
    the Caddy reverse proxy, falling back to the socket peer."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "anon"


def create_app(manager: RunManager, *, cors_origins: list[str] | None = None) -> FastAPI:
    app = FastAPI(title="Cadenza API", version="0.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins or ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/runs", response_model=StartRunResponse)
    async def start_run(req: StartRunRequest, request: Request) -> StartRunResponse:
        try:
            admission = await manager.admit(req, _client_ip(request))
        except ValueError as ex:  # invalid key format
            raise HTTPException(status_code=400, detail=str(ex)) from ex
        if admission.mode == "demo":
            # Graceful refusal (§8.1/§8.6): no backend run; client replays cached.
            return StartRunResponse(
                run_id=None, status="demo", mode="demo", reason=admission.reason
            )
        rec = await manager.start_run(req, admission)
        return StartRunResponse(
            run_id=rec.run_id, status=rec.status, mode=rec.mode, reason=admission.reason
        )

    @app.get("/api/runs/{run_id}", response_model=RunStatusResponse)
    async def run_status(run_id: str) -> RunStatusResponse:
        rec = manager.get(run_id)
        if rec is None:
            raise HTTPException(status_code=404, detail="run not found")
        return RunStatusResponse(run_id=rec.run_id, status=rec.status, mode=rec.mode)

    @app.post("/api/runs/{run_id}/decision", status_code=202)
    async def submit_decision(run_id: str, body: DecisionRequest) -> dict[str, bool]:
        try:
            await manager.submit_decision(run_id, body.decision, body.note)
        except KeyError as ex:
            raise HTTPException(status_code=404, detail="run not found") from ex
        except DecisionNotAllowed as ex:
            raise HTTPException(status_code=409, detail=str(ex)) from ex
        return {"ok": True}

    @app.get("/api/runs/{run_id}/events")
    async def stream_events(run_id: str, request: Request) -> EventSourceResponse:
        if not manager.exists(run_id):
            raise HTTPException(status_code=404, detail="run not found")

        last = request.headers.get("last-event-id")
        after_seq = int(last) if last and last.lstrip("-").isdigit() else -1

        async def generator() -> AsyncIterator[dict[str, str]]:
            async for event in manager.bus.subscribe(run_id, after_seq):
                yield {"id": str(event["seq"]), "event": event["type"], "data": json.dumps(event)}

        return EventSourceResponse(generator())

    return app


def build_app(settings: Settings | None = None) -> FastAPI:
    import redis
    import redis.asyncio as aioredis

    settings = settings or get_settings()
    sync_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    async_client = aioredis.Redis.from_url(settings.redis_url, decode_responses=True)
    bus = EventBus(sync_client, async_client, ttl_seconds=settings.run_ttl_seconds)
    limiter = Limiter(async_client, settings)
    manager = RunManager(bus, settings, limiter)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await manager.shutdown()
        await async_client.aclose()
        sync_client.close()

    app = create_app(manager, cors_origins=settings.cors_origins)
    app.router.lifespan_context = lifespan
    return app


app = build_app()
