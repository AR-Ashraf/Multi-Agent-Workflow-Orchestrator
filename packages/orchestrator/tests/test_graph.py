"""Mocked-LLM tests for the research graph — no live LLM (CLAUDE.md §7).

Asserts the topology/flow: parallel research, the injection block, the HITL
interrupt + resume, the Critic retry loop, claim verification, decision rationale,
and token/step-cap enforcement.
"""

from __future__ import annotations

from cadenza_orchestrator import run_research_brief


def _run(**kw):
    return run_research_brief(run_id="t", **kw)


def test_full_run_event_envelope_and_terminus():
    events = _run(decision="approve")["events"]
    assert events[0]["type"] == "run.started"
    assert any(e["type"] == "run.completed" for e in events)
    assert events[-1] == {**events[-1], "type": "run.state", "state": "done"}
    # seq strictly increasing from 0
    for i, e in enumerate(events):
        assert e["seq"] == i


def test_model_routing_emitted_for_all_seven_nodes():
    events = _run()["events"]
    routing = next(e for e in events if e["type"] == "model.routing")
    assert len(routing["assignments"]) == 7
    assert routing["routingEnabled"] is True


def test_injection_block_fires_once_on_researcher_b():
    inj = [e for e in _run()["events"] if e["type"] == "injection.screened"]
    assert len(inj) == 1
    assert inj[0]["nodeId"] == "researcher-b"
    assert inj[0]["status"] == "blocked"


def test_hitl_pauses_then_resolves():
    types = [e["type"] for e in _run(decision="approve")["events"]]
    assert types.index("hitl.requested") < types.index("hitl.resolved")
    events = _run(decision="approve")["events"]
    assert any(e["type"] == "run.state" and e["state"] == "paused" for e in events)


def test_hitl_adjust_decision_propagates():
    resolved = next(e for e in _run(decision="adjust")["events"] if e["type"] == "hitl.resolved")
    assert resolved["decision"] == "adjust"


def test_critic_retry_loop_and_claim_verification():
    events = _run()["events"]
    claims = [e for e in events if e["type"] == "claim.verified"]
    assert len(claims) == 4  # c1✓ c2✓ c3✗ then c3✓
    assert any(c["verdict"] == "unsupported" for c in claims)
    assert any(e["type"] == "agent.rationale" and e.get("verdict") == "retry" for e in events)
    assert any(
        e["type"] == "edge.status"
        and e["edgeId"] == "critic->writer"
        and e["status"] == "retry-flow"
        for e in events
    )


def test_planner_rationale_has_structured_subtasks():
    events = _run()["events"]
    planner = next(
        e for e in events if e["type"] == "agent.rationale" and e["agentId"] == "planner"
    )
    assert planner["items"] == ["market size", "top competitors", "pricing"]


def test_brief_released_all_claims_verified():
    released = next(e for e in _run()["events"] if e["type"] == "brief.released")
    brief = released["brief"]
    assert brief["claimsVerified"] == {"verified": 3, "total": 3}
    assert brief["permalink"].endswith("/run/t")
    assert len(brief["sources"]) == 3


def test_token_budget_cap_stops_the_run_cleanly():
    out = _run(max_tokens=50)
    events = out["events"]
    assert any(e["type"] == "error" and e["code"] == "budget_exceeded" for e in events)
    assert any(e["type"] == "run.state" and e["state"] == "error" for e in events)
    assert not any(e["type"] == "brief.released" for e in events)
