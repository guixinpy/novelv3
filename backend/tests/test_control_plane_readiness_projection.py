from app.services.writing_agent.control_plane_readiness_projection import (
    CONTROL_PLANE_READINESS_SOURCE,
    control_plane_readiness_from_run_input,
    control_plane_readiness_needs_attention,
)


def test_control_plane_readiness_from_run_input_returns_bounded_summary():
    output = control_plane_readiness_from_run_input(
        {
            "planner": {
                "trace": {
                    "agent_health_projection": {
                        "control_plane_readiness": {
                            "status": "degraded",
                            "version": "phase46.agent_control_plane_readiness.v1",
                            "summary": {
                                "total_tools": 30,
                                "tools_needing_work": 1,
                                "tool_gap_count": 1,
                                "total_commands": 8,
                                "agent_control_commands": 2,
                                "commands_with_control_projection": 1,
                                "command_gap_count": 1,
                                "total_gap_count": 2,
                            },
                            "recommended_next_tools": [
                                "inspect_agent_control_plane_readiness",
                                "",
                                "inspect_agent_command_contracts",
                            ],
                            "control_surfaces": {"commands": [{"name": "continue"}]},
                        }
                    }
                }
            }
        }
    )

    assert output == {
        "source": CONTROL_PLANE_READINESS_SOURCE,
        "status": "degraded",
        "version": "phase46.agent_control_plane_readiness.v1",
        "summary": {
            "total_tools": 30,
            "tools_needing_work": 1,
            "tool_gap_count": 1,
            "total_commands": 8,
            "agent_control_commands": 2,
            "commands_with_control_projection": 1,
            "command_gap_count": 1,
            "total_gap_count": 2,
        },
        "recommended_next_tools": [
            "inspect_agent_control_plane_readiness",
            "inspect_agent_command_contracts",
        ],
    }


def test_control_plane_readiness_needs_attention_uses_status_or_gap_count():
    assert control_plane_readiness_needs_attention(
        {"status": "ready", "summary": {"total_gap_count": 0}}
    ) is False
    assert control_plane_readiness_needs_attention(
        {"status": "ready", "summary": {"total_gap_count": 1}}
    ) is True
    assert control_plane_readiness_needs_attention(
        {"status": "degraded", "summary": {"total_gap_count": 0}}
    ) is True
    assert control_plane_readiness_needs_attention(None) is False
