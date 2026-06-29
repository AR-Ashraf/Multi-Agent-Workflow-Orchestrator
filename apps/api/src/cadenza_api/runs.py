"""Run manager — owns the per-run lifecycle, the HITL pause/resume bridge, and
admission control (the cost & safety guardrails in CLAUDE.md §8).

A run is driven by a background asyncio task: it runs the orchestrator's
`RunSession.start()` (offloaded to a thread, since the graph is sync) to the HITL
interrupt, then awaits a human decision, then resumes. Events reach the browser
purely through the bus (the session's sink publishes each one).

`admit()` is the gate in front of all of this: per-IP rate limit, BYOK vs
house-funded vs demo decision, and the daily spend cap. A run is only created
when admission resolves to a real (`live`) run; otherwise the caller serves the
free cached replay (`demo`).

BYOK (CLAUDE.md §6, §10): the visitor's key is format-checked and used to decide
admission, then discarded — it is never stored on the record, in Redis, or in
logs. Per-run token/step ceilings (§8.3) are fed into the orchestrator.
"""

from __future__ import annotations

import asyncio
import secrets
from dataclasses import dataclass, field

from cadenza_orchestrator import RunSession

from .bus import EventBus
from .byok import validate_key
from .config import Settings
from .limits import Limiter
from .schemas import StartRunRequest


class DecisionNotAllowed(Exception):
    pass


@dataclass
class Admission:
    """Outcome of the §8 gate. `mode="live"` → start a backend run; `mode="demo"`
    → the client replays the cached example (run_id stays null)."""

    mode: str  # "live" | "demo"
    funded_by: str  # "visitor" | "house" | "none"
    reason: str | None = None  # "no_key" | "rate_limited" | "daily_cap"
    reservation: float = 0.0  # house USD reserved against the daily cap


@dataclass
class RunRecord:
    run_id: str
    session: RunSession
    mode: str
    funded_by: str = "visitor"
    reservation: float = 0.0
    status: str = "starting"  # starting | paused | completed | error
    decision_event: asyncio.Event = field(default_factory=asyncio.Event)
    decision: tuple[str, str | None] | None = None
    task: asyncio.Task[None] | None = None


class RunManager:
    def __init__(self, bus: EventBus, settings: Settings, limiter: Limiter) -> None:
        self.bus = bus
        self.settings = settings
        self.limiter = limiter
        self._runs: dict[str, RunRecord] = {}

    def exists(self, run_id: str) -> bool:
        return run_id in self._runs

    def get(self, run_id: str) -> RunRecord | None:
        return self._runs.get(run_id)

    async def admit(self, req: StartRunRequest, ip: str) -> Admission:
        """Apply the §8 guardrails and decide how (or whether) this run executes.

        Raises ValueError only for a malformed BYOK key (→ 400). Everything else
        degrades gracefully to a cached demo rather than erroring.
        """
        if not await self.limiter.allow_ip(ip):
            return Admission("demo", "none", reason="rate_limited")

        if req.api_key:
            ok, why = validate_key(req.provider, req.api_key)
            if not ok:
                raise ValueError(why)
            return Admission("live", "visitor")  # billed to the visitor's key

        # No key: optionally fund from the house key, bounded by the daily cap.
        estimate = self.settings.estimated_run_cost_usd
        if await self.limiter.reserve_house_budget(estimate):
            return Admission("live", "house", reservation=estimate)

        reason = "daily_cap" if self.settings.house_api_key else "no_key"
        return Admission("demo", "none", reason=reason)

    async def start_run(self, req: StartRunRequest, admission: Admission) -> RunRecord:
        """Create + drive a backend run. Only valid for a `live` admission."""
        run_id = secrets.token_urlsafe(8)
        session = RunSession(
            run_id=run_id,
            query=req.query,
            provider=req.provider,
            model_id=req.model,
            routing=req.routing,
            mode="live",
            sink=lambda event: self.bus.publish(run_id, event),
            max_tokens=self.settings.per_run_max_tokens,
            max_steps=self.settings.per_run_max_steps,
        )
        rec = RunRecord(
            run_id=run_id,
            session=session,
            mode="live",
            funded_by=admission.funded_by,
            reservation=admission.reservation,
        )
        self._runs[run_id] = rec
        rec.task = asyncio.create_task(self._drive(rec))
        return rec

    async def _drive(self, rec: RunRecord) -> None:
        try:
            paused = await asyncio.to_thread(rec.session.start)
            if paused:
                rec.status = "paused"
                if not await self._await_decision(rec):
                    # Abandoned at the HITL checkpoint — cancel to free resources.
                    rec.session.cancel(
                        "no approval received before the timeout",
                        code="hitl_timeout",
                        label="Stopped · approval timed out",
                    )
                    rec.status = "error"
                    return
                decision, note = rec.decision or ("approve", None)
                await asyncio.to_thread(rec.session.resume, decision, note)
            rec.status = "error" if rec.session.errored else "completed"
        except asyncio.CancelledError:
            raise
        except Exception:
            rec.status = "error"
        finally:
            await self._settle(rec)

    async def _await_decision(self, rec: RunRecord) -> bool:
        """Wait for the human decision; return False if the approval window lapses."""
        timeout = self.settings.hitl_timeout_seconds
        if not timeout or timeout <= 0:
            await rec.decision_event.wait()
            return True
        try:
            await asyncio.wait_for(rec.decision_event.wait(), timeout)
            return True
        except TimeoutError:
            return False

    async def _settle(self, rec: RunRecord) -> None:
        """Reconcile a house-funded run's reservation to its actual cost (§8.1)."""
        if rec.funded_by != "house":
            return
        actual = _run_cost(rec.session)
        try:
            await self.limiter.settle_house_spend(rec.reservation, actual)
        except Exception:
            pass  # accounting must never crash a run

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


def _run_cost(session: RunSession) -> float:
    """Pull the run's final estimated cost from its terminal meters/completed event."""
    for event in reversed(session.events):
        if event.get("type") in ("run.completed", "meters") and "costUsd" in event:
            return float(event["costUsd"])
    return 0.0
