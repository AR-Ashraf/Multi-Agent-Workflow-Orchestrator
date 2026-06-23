from cadenza_orchestrator.constants import (
    MAX_CRITIC_RETRIES,
    MAX_STEPS,
    MAX_TOKENS,
    MECHANICAL_NODES,
    SMART_NODES,
    TOTAL_STEPS,
    assign_models,
    resolve_model,
)


def test_total_steps_and_caps():
    assert TOTAL_STEPS == 8
    assert MAX_TOKENS > 0 and MAX_STEPS > 0 and MAX_CRITIC_RETRIES >= 1


def test_smart_and_mechanical_cover_seven_model_nodes():
    nodes = sorted([*SMART_NODES, *MECHANICAL_NODES])
    assert nodes == sorted(
        ["planner", "analyst", "critic", "researcher-a", "researcher-b", "researcher-c", "writer"]
    )


def test_resolve_model_defaults_to_provider_default():
    assert resolve_model("anthropic", "nope")["badge"] == "Sonnet"
    assert resolve_model("anthropic", "claude-haiku")["badge"] == "Haiku"


def test_routing_on_downgrades_mechanical_steps():
    by_id = {a["nodeId"]: a for a in assign_models("anthropic", "claude-sonnet", True)}
    assert by_id["planner"] == {"nodeId": "planner", "modelLabel": "Sonnet", "tier": "smart"}
    assert by_id["researcher-a"] == {
        "nodeId": "researcher-a",
        "modelLabel": "Haiku",
        "tier": "fast",
    }
    assert by_id["writer"]["modelLabel"] == "Haiku"


def test_routing_off_uses_selected_model_everywhere():
    assignments = assign_models("anthropic", "claude-sonnet", False)
    assert all(a["modelLabel"] == "Sonnet" for a in assignments)
    assert all(a["tier"] == "smart" for a in assignments)
