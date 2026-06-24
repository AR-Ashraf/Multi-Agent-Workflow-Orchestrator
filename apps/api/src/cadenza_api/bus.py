"""Redis event bus — fan-out of orchestrator events to SSE subscribers
(CLAUDE.md §4).

Each event is both buffered (a capped, TTL'd Redis list) and published on a
per-run channel. Publishing is synchronous (called from the orchestrator worker
thread via the run's sink); subscribing is async (the SSE endpoint). A subscriber
replays the buffer first — so a client that connects late or reconnects with a
`Last-Event-ID` resumes cleanly without missing events — then streams live.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

Event = dict[str, Any]


def _channel(run_id: str) -> str:
    return f"cadenza:run:{run_id}:events"


def _buffer(run_id: str) -> str:
    return f"cadenza:run:{run_id}:buffer"


def _is_terminal(event: Event) -> bool:
    return event.get("type") == "run.state" and event.get("state") in ("done", "error")


class EventBus:
    def __init__(self, sync_client: Any, async_client: Any, *, ttl_seconds: int = 1800) -> None:
        self._sync = sync_client
        self._async = async_client
        self._ttl = ttl_seconds

    # -- publish side (sync; runs in the orchestrator worker thread) --------
    def publish(self, run_id: str, event: Event) -> None:
        data = json.dumps(event)
        pipe = self._sync.pipeline()
        pipe.rpush(_buffer(run_id), data)
        pipe.expire(_buffer(run_id), self._ttl)
        pipe.publish(_channel(run_id), data)
        pipe.execute()

    # -- read side (async; the SSE endpoint) --------------------------------
    async def replay(self, run_id: str, after_seq: int = -1) -> list[Event]:
        raw = await self._async.lrange(_buffer(run_id), 0, -1)
        events: list[Event] = []
        for item in raw:
            event = json.loads(item)
            if event.get("seq", -1) > after_seq:
                events.append(event)
        return events

    async def subscribe(self, run_id: str, after_seq: int = -1) -> AsyncIterator[Event]:
        """Yield buffered-then-live events until the run reaches a terminal state.

        Subscribes BEFORE replaying the buffer so nothing emitted in between is
        lost; live events are de-duplicated against what was already replayed.
        """
        pubsub = self._async.pubsub()
        await pubsub.subscribe(_channel(run_id))
        seen: set[int] = set()
        try:
            for event in await self.replay(run_id, after_seq):
                seq = event.get("seq", -1)
                if seq in seen:
                    continue
                seen.add(seq)
                yield event
                if _is_terminal(event):
                    return

            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                event = json.loads(message["data"])
                seq = event.get("seq", -1)
                if seq in seen or seq <= after_seq:
                    continue
                seen.add(seq)
                yield event
                if _is_terminal(event):
                    return
        finally:
            await pubsub.unsubscribe(_channel(run_id))
            await pubsub.aclose()
