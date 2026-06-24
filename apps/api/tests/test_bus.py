"""Event bus — buffering, replay (reconnect/resume), and terminal stop."""

from __future__ import annotations

from typing import Any

from cadenza_api.bus import EventBus


def _ev(seq: int, type_: str = "log", **extra: Any) -> dict[str, Any]:
    return {"runId": "r", "seq": seq, "ts": seq, "type": type_, **extra}


async def test_publish_then_replay_preserves_order(bus: EventBus):
    for i in range(3):
        bus.publish("r", _ev(i))
    got = await bus.replay("r")
    assert [e["seq"] for e in got] == [0, 1, 2]


async def test_replay_after_seq_filters_already_seen(bus: EventBus):
    for i in range(4):
        bus.publish("r", _ev(i))
    got = await bus.replay("r", after_seq=1)
    assert [e["seq"] for e in got] == [2, 3]


async def test_subscribe_replays_then_stops_at_terminal(bus: EventBus):
    bus.publish("r", _ev(0, "log"))
    bus.publish("r", _ev(1, "run.state", state="done"))
    got = [e async for e in bus.subscribe("r")]
    assert [e["seq"] for e in got] == [0, 1]  # returns once the terminal event is seen
