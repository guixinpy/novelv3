from app.services.writing_agent.agent_control_plane_readiness import inspect_agent_control_plane_readiness


def test_agent_control_plane_readiness_reports_ready_when_contracts_are_clean():
    output = inspect_agent_control_plane_readiness(
        tool_contract_snapshot_provider=lambda: {
            "status": "completed",
            "summary": {"total_tools": 3, "tools_needing_work": 0, "gap_count": 0},
            "coverage": {"adapter_coverage_ratio": 1.0},
        },
        command_contract_provider=lambda: {
            "status": "completed",
            "version": "phase38.agent_command_contracts.v1",
            "summary": {
                "total_commands": 4,
                "agent_control_commands": 2,
                "commands_with_control_projection": 2,
                "gap_count": 0,
            },
        },
    )

    assert output["status"] == "ready"
    assert output["summary"]["total_gap_count"] == 0
    assert output["summary"]["agent_control_commands"] == 2
    assert output["diagnostics"] == []
    assert output["recommended_next_tools"] == ["inspect_agent_health_projection"]


def test_agent_control_plane_readiness_reports_degraded_contract_gaps():
    output = inspect_agent_control_plane_readiness(
        tool_contract_snapshot_provider=lambda: {
            "status": "completed",
            "summary": {"total_tools": 5, "tools_needing_work": 2, "gap_count": 3},
            "coverage": {"adapter_coverage_ratio": 0.6},
        },
        command_contract_provider=lambda: {
            "status": "completed",
            "version": "phase38.agent_command_contracts.v1",
            "summary": {
                "total_commands": 4,
                "agent_control_commands": 2,
                "commands_with_control_projection": 1,
                "gap_count": 1,
            },
        },
    )

    assert output["status"] == "degraded"
    assert output["summary"]["total_gap_count"] == 4
    assert [item["code"] for item in output["diagnostics"]] == [
        "agent_tool_contract_gaps",
        "agent_command_contract_gaps",
    ]
    assert output["recommended_next_tools"] == [
        "inspect_agent_tool_contracts",
        "inspect_agent_command_contracts",
        "inspect_agent_health_projection",
    ]
