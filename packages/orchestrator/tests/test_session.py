"""RunSession (start/resume split) — the primitive the FastAPI gateway drives."""

from __future__ import annotations

from cadenza_orchestrator import RunSession


def test_start_pauses_at_hitl_then_resume_completes():
    s = RunSession(run_id="s1", query="Market for AI scheduling assistants for US dental clinics")

    paused = s.start()
    assert paused is True
    assert s.paused and not s.completed
    assert "hitl.requested" in [e["type"] for e in s.events]
    assert "brief.released" not in [e["type"] for e in s.events]  # not until resumed

    s.resume("approve")
    assert s.completed and not s.paused
    assert "brief.released" in [e["type"] for e in s.events]
    assert s.events[-1]["type"] == "run.state" and s.events[-1]["state"] == "done"


def test_sink_receives_events_live_and_carries_the_decision():
    seen: list[dict] = []
    s = RunSession(run_id="s2", query="anything", sink=seen.append)
    s.start()
    assert any(e["type"] == "hitl.requested" for e in seen)
    s.resume("adjust")
    assert any(e["type"] == "hitl.resolved" and e["decision"] == "adjust" for e in seen)
