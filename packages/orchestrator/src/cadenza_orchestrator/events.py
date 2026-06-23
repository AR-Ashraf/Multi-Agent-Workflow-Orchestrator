"""The emitter — the orchestrator's side of the FE/BE event contract.

Every method builds a plain dict that conforms to the canonical event schema
(@cadenza/shared events.ts, exported as JSON Schema). The contract test validates
everything this emits against that schema, so field names here MUST match the
schema exactly (costUsd, nodeId, edgeId, modelLabel, proposedDirection, ...).

The emitter assigns the `runId/seq/ts` envelope and keeps the cumulative
token/cost meters. A `sink` callback lets the FastAPI layer (Unit 6) forward
each event to Redis pub/sub as it is produced; in tests the sink is omitted and
events are read from `.events`.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from typing import Any

Event = dict[str, Any]


class Emitter:
    def __init__(self, run_id: str, sink: Callable[[Event], None] | None = None) -> None:
        self.run_id = run_id
        self._sink = sink
        self.events: list[Event] = []
        self._seq = 0
        self._start = time.monotonic()
        self.tokens = 0
        self.cost = 0.0

    # -- envelope ---------------------------------------------------------
    def _elapsed_ms(self) -> int:
        return int((time.monotonic() - self._start) * 1000)

    def _emit(self, payload: Event) -> Event:
        event = {"runId": self.run_id, "seq": self._seq, "ts": self._elapsed_ms(), **payload}
        self._seq += 1
        self.events.append(event)
        if self._sink is not None:
            self._sink(event)
        return event

    # -- run lifecycle ----------------------------------------------------
    def run_started(
        self,
        *,
        query: str,
        provider: str,
        model_id: str,
        model_label: str,
        routing: bool,
        mode: str,
        total_steps: int,
    ) -> Event:
        return self._emit(
            {
                "type": "run.started",
                "query": query,
                "provider": provider,
                "modelId": model_id,
                "modelLabel": model_label,
                "routingEnabled": routing,
                "mode": mode,
                "totalSteps": total_steps,
            }
        )

    def run_state(self, state: str, label: str) -> Event:
        return self._emit({"type": "run.state", "state": state, "label": label})

    def step_changed(self, step: int, total_steps: int) -> Event:
        return self._emit({"type": "step.changed", "step": step, "totalSteps": total_steps})

    def run_completed(self, claims_verified: dict[str, int]) -> Event:
        return self._emit(
            {
                "type": "run.completed",
                "tokens": self.tokens,
                "costUsd": round(self.cost, 3),
                "elapsedMs": self._elapsed_ms(),
                "claimsVerified": claims_verified,
            }
        )

    def error(self, code: str, message: str, recoverable: bool = False) -> Event:
        return self._emit(
            {"type": "error", "code": code, "message": message, "recoverable": recoverable}
        )

    # -- graph visuals ----------------------------------------------------
    def node_status(self, node_id: str, status: str) -> Event:
        return self._emit({"type": "node.status", "nodeId": node_id, "status": status})

    def edge_status(self, edge_id: str, status: str) -> Event:
        return self._emit({"type": "edge.status", "edgeId": edge_id, "status": status})

    def model_routing(self, routing: bool, assignments: Sequence[dict]) -> Event:
        return self._emit(
            {"type": "model.routing", "routingEnabled": routing, "assignments": list(assignments)}
        )

    def meters(self, d_tokens: int, d_cost: float) -> Event:
        self.tokens += d_tokens
        self.cost = round(self.cost + d_cost, 6)
        return self._emit(
            {
                "type": "meters",
                "tokens": self.tokens,
                "costUsd": round(self.cost, 3),
                "elapsedMs": self._elapsed_ms(),
            }
        )

    # -- semantic events --------------------------------------------------
    def log(self, kind: str, who: str, text: str, node_id: str | None = None) -> Event:
        payload: Event = {"type": "log", "kind": kind, "who": who, "text": text}
        if node_id is not None:
            payload["nodeId"] = node_id
        return self._emit(payload)

    def agent_rationale(
        self,
        agent_id: str,
        summary: str,
        items: list[str] | None = None,
        verdict: str | None = None,
    ) -> Event:
        payload: Event = {"type": "agent.rationale", "agentId": agent_id, "summary": summary}
        if items is not None:
            payload["items"] = items
        if verdict is not None:
            payload["verdict"] = verdict
        return self._emit(payload)

    def injection_screened(
        self, node_id: str, status: str, detail: str, source_url: str | None = None
    ) -> Event:
        payload: Event = {
            "type": "injection.screened",
            "nodeId": node_id,
            "status": status,
            "detail": detail,
        }
        if source_url is not None:
            payload["sourceUrl"] = source_url
        return self._emit(payload)

    def claim_verified(
        self,
        claim_id: str,
        claim_text: str,
        source_id: str,
        verdict: str,
        detail: str | None = None,
    ) -> Event:
        payload: Event = {
            "type": "claim.verified",
            "claimId": claim_id,
            "claimText": claim_text,
            "sourceId": source_id,
            "verdict": verdict,
        }
        if detail is not None:
            payload["detail"] = detail
        return self._emit(payload)

    def hitl_requested(
        self, prompt: str, proposed_direction: list[str], options: list[str] | None = None
    ) -> Event:
        return self._emit(
            {
                "type": "hitl.requested",
                "prompt": prompt,
                "proposedDirection": proposed_direction,
                "options": options or ["approve", "adjust"],
            }
        )

    def hitl_resolved(self, decision: str, note: str | None = None) -> Event:
        payload: Event = {"type": "hitl.resolved", "decision": decision}
        if note is not None:
            payload["note"] = note
        return self._emit(payload)

    def brief_released(self, brief: dict) -> Event:
        return self._emit({"type": "brief.released", "brief": brief})
