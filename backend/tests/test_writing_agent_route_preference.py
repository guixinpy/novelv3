from __future__ import annotations

from app.services.writing_agent.slash_command_route import inspect_agent_route_preference_projection


def test_route_preference_recommends_approved_chain_for_chapter_routes_without_mutating_runtime_route():
    output = inspect_agent_route_preference_projection(
        static_adapter_tool_names=_static_adapter_tools(),
        action_execution_tool_names=_action_execution_tools(),
    )
    chapter_routes = [
        route
        for route in output["routes"]
        if route["action_type"] == "preview_chapter" and route["current_tool_name"] == "generate_chapter"
    ]

    assert output["status"] == "ready"
    assert chapter_routes
    for route in chapter_routes:
        assert route["preferred_tool_chain"] == [
            "prepare_generate_chapter_execution",
            "execute_generate_chapter_with_approval",
        ]
        assert route["approval_gate_required"] is True
        assert route["runtime_route_changed"] is False
        assert route["migration_status"] == "recommended_not_applied"
        assert route["reason_code"] == "chapter_generation_should_use_approved_agent_gate"
        assert route["missing_preferred_tools"] == []


def test_route_preference_recommends_approved_chains_for_hermes_routes_without_mutating_runtime_route():
    output = inspect_agent_route_preference_projection(
        static_adapter_tool_names=_static_adapter_tools(),
        action_execution_tool_names=_action_execution_tools(),
    )
    expected = {
        "preview_setup": [
            "prepare_generate_setup_execution",
            "execute_generate_setup_with_approval",
        ],
        "preview_storyline": [
            "prepare_generate_storyline_execution",
            "execute_generate_storyline_with_approval",
        ],
        "preview_outline": [
            "prepare_generate_outline_execution",
            "execute_generate_outline_with_approval",
        ],
    }

    assert output["status"] == "ready"
    for action_type, preferred_chain in expected.items():
        route = next(
            route
            for route in output["routes"]
            if route["source"] == "slash_command" and route["action_type"] == action_type
        )
        assert route["preferred_tool_chain"] == preferred_chain
        assert route["preferred_prepare_tool_name"] == preferred_chain[0]
        assert route["preferred_execute_tool_name"] == preferred_chain[1]
        assert route["approval_gate_required"] is True
        assert route["preferred_execution_supported"] is True
        assert route["runtime_tool_name"] == route["current_tool_name"]
        assert route["runtime_route_changed"] is False
        assert route["runtime_behavior_changed"] is False
        assert route["migration_status"] == "recommended_not_applied"
        assert route["missing_preferred_tools"] == []
    assert output["trace"]["runtime_behavior_changed"] is False


def test_route_preference_can_filter_to_text_intent_source():
    output = inspect_agent_route_preference_projection(
        source="text_intent",
        static_adapter_tool_names=_static_adapter_tools(),
        action_execution_tool_names=_action_execution_tools(),
    )

    assert output["status"] == "ready"
    assert {route["source"] for route in output["routes"]} == {"text_intent"}
    assert any(route["action_type"] == "preview_chapter" for route in output["routes"])


def test_route_preference_degrades_when_preferred_approval_tools_are_missing():
    output = inspect_agent_route_preference_projection(
        static_adapter_tool_names=_static_adapter_tools()
        - {"prepare_generate_chapter_execution", "execute_generate_chapter_with_approval"},
        action_execution_tool_names=_action_execution_tools(),
    )
    chapter_route = next(route for route in output["routes"] if route["action_type"] == "preview_chapter")

    assert output["status"] == "degraded"
    assert chapter_route["preferred_execution_supported"] is False
    assert chapter_route["missing_preferred_tools"] == [
        "prepare_generate_chapter_execution",
        "execute_generate_chapter_with_approval",
    ]
    assert output["trace"]["missing_preferred_tools"] == [
        "execute_generate_chapter_with_approval",
        "prepare_generate_chapter_execution",
    ]


def test_route_preference_degrades_when_hermes_approval_tools_are_missing():
    output = inspect_agent_route_preference_projection(
        static_adapter_tool_names=_static_adapter_tools()
        - {"prepare_generate_setup_execution", "execute_generate_setup_with_approval"},
        action_execution_tool_names=_action_execution_tools(),
    )
    setup_route = next(route for route in output["routes"] if route["action_type"] == "preview_setup")

    assert output["status"] == "degraded"
    assert setup_route["preferred_execution_supported"] is False
    assert setup_route["missing_preferred_tools"] == [
        "prepare_generate_setup_execution",
        "execute_generate_setup_with_approval",
    ]
    assert output["trace"]["missing_preferred_tools"] == [
        "execute_generate_setup_with_approval",
        "prepare_generate_setup_execution",
    ]


def _static_adapter_tools() -> set[str]:
    return {
        "generate_chapter",
        "prepare_generate_setup_execution",
        "execute_generate_setup_with_approval",
        "prepare_generate_storyline_execution",
        "execute_generate_storyline_with_approval",
        "prepare_generate_outline_execution",
        "execute_generate_outline_with_approval",
        "prepare_generate_chapter_execution",
        "execute_generate_chapter_with_approval",
    }


def _action_execution_tools() -> set[str]:
    return {"generate_setup", "generate_storyline", "generate_outline"}
