"""Run manager — owns the per-run lifecycle and the HITL pause/resume bridge.

A run is driven by a background asyncio task: it runs the orchestrator's
`RunSession.start()` (offloaded to a thread, since the graph is sync) to the HITL
interrupt, then awaits a human decision, then resumes. Events reach the browser
purely through the bus (the session's sink publishes each one).

BYOK (CLAUDE.md §6, §10): the visitor's key is format-checked and used to decide
live vs demo mode, then discarded — it is never stored on the record, in Redis,
or in logs.
"""

from __future__ import annotations

import asyncio
import secrets
from dataclasses import dataclass, field

from cadenza_orchestrator import RunSession

from .bus import EventBus
from .byok import validate_key
from .schemas import StartRunRequest


class DecisionNotAllowed(Exception):
    pass


@dataclass
class RunRecord:
    run_id: str
    session: RunSession
    mode: str
    status: str = "starting"  # starting | paused | completed | error
    decision_event: asyncio.Event = field(default_factory=asyncio.Event)
    decision: tuple[str, str | None] | None = None
    task: asyncio.Task[None] | None = None


class RunManager:
    def __init__(self, bus: EventBus) -> None:
        self.bus = bus
        self._runs: dict[str, RunRecord] = {}

    def exists(self, run_id: str) -> bool:
        return run_id in self._runs

    def get(self, run_id: str) -> RunRecord | None:
        return self._runs.get(run_id)

    async def start_run(self, req: StartRunRequest) -> RunRecord:
        mode = "demo"
        if req.api_key:
            ok, reason = validate_key(req.provider, req.api_key)
            if not ok:
                raise ValueError(reason)
            mode = "live"
        # NB: the key is intentionally NOT stored. Real provider adapters land in
        # a later unit; for now the offline mock keeps demo + live free and
        # deterministic. mode just records whether a (valid) key was supplied.

        run_id = secrets.token_urlsafe(8)
        session = RunSession(
            run_id=run_id,
            query=req.query,
            provider=req.provider,
            model_id=req.model,
            routing=req.routing,
            mode=mode,
            sink=lambda event: self.bus.publish(run_id, event),
        )
        rec = RunRecord(run_id=run_id, session=session, mode=mode)
        self._runs[run_id] = rec
        rec.task = asyncio.create_task(self._drive(rec))
        return rec

    async def _drive(self, rec: RunRecord) -> None:
        try:
            paused = await asyncio.to_thread(rec.session.start)
            if paused:
                rec.status = "paused"
                await rec.decision_event.wait()
                decision, note = rec.decision or ("approve", None)
                await asyncio.to_thread(rec.session.resume, decision, note)
            rec.status = "error" if rec.session.errored else "completed"
        except asyncio.CancelledError:
            raise
        except Exception:
            rec.status = "error"

    async def submit_decision(self, run_id: str, decision: str, note: str | None = None) -> None:
        rec = self._runs.get(run_id)
        if rec is None:
            raise KeyError(run_id)
        if rec.status != "paused":
            raise DecisionNotAllowed(f"run is '{rec.status}', not awaiting a decision")
        rec.decision = (decision, note)
        rec.decision_event.set()

    async def shutdown(self) -> None:
        tasks = [rec.task for rec in self._runs.values() if rec.task and not rec.task.done()]
        for task in tasks:
            task.cancel()
        for task in tasks:
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
