from app.services.writing_agent.agent_command_contracts import inspect_agent_command_contracts


def test_agent_command_contracts_report_ready_agent_control_surface():
    required = {
        "inspect_agent_health_projection",
        "inspect_agent_command_contracts",
        "plan_recovery_tools",
        "plan_recommended_followups",
        "prepare_generate_chapter_execution",
    }

    output = inspect_agent_command_contracts(
        descriptor_names_provider=lambda: required,
        adapter_names_provider=lambda: required,
    )

    assert output["status"] == "completed"
    assert output["version"] == "phase38.agent_command_contracts.v1"
    assert output["summary"]["agent_control_commands"] == 2
    assert output["summary"]["commands_with_control_projection"] == 2
    assert output["summary"]["gap_count"] == 0
    commands = {command["name"]: command for command in output["commands"]}
    assert commands["continue"]["contract_status"] == "ready"
    assert commands["continue"]["capability_id"] == "agent.continue"
    assert commands["continue"]["control_projection_type"] == "continue_agent_control"
    assert commands["continue"]["required_agent_tools"] == [
        "inspect_agent_health_projection",
        "inspect_agent_command_contracts",
        "plan_recovery_tools",
        "plan_recommended_followups",
        "prepare_generate_chapter_execution",
    ]
    assert commands["status"]["required_agent_tools"] == [
        "inspect_agent_health_projection",
        "inspect_agent_command_contracts",
    ]
    assert commands["status"]["control_projection_type"] == "agent_health_projection"
    assert commands["clear"]["contract_status"] == "ready"
    assert commands["clear"]["control_projection_type"] == ""
    assert output["gaps"] == []


def test_agent_command_contracts_report_unavailable_public_command_gap():
    descriptor_names = {
        "inspect_agent_health_projection",
        "inspect_agent_command_contracts",
        "plan_recovery_tools",
        "plan_recommended_followups",
        "prepare_generate_chapter_execution",
    }
    adapter_names = descriptor_names - {"prepare_generate_chapter_execution"}

    output = inspect_agent_command_contracts(
        descriptor_names_provider=lambda: descriptor_names,
        adapter_names_provider=lambda: adapter_names,
    )

    commands = {command["name"]: command for command in output["commands"]}
    assert commands["continue"]["contract_status"] == "needs_attention"
    assert commands["continue"]["available"] is False
    assert commands["continue"]["gaps"][0]["code"] == "unavailable_command"
    assert output["summary"]["unavailable_public_commands"] == 1
    assert output["summary"]["gap_count"] == 1
    assert output["gaps"][0]["details"]["unavailable_reasons"] == [
        "缺少 Agent 工具适配器：prepare_generate_chapter_execution"
    ]
    assert output["recommended_next_tools"][0] == "describe_agent_tools"
    assert "inspect_agent_tool_contracts" in output["recommended_next_tools"]
