from app.services.writing_agent.agent_command_catalog import build_agent_chat_command_catalog


def _command_by_name(catalog: dict, name: str) -> dict:
    return next(command for command in catalog["commands"] if command["name"] == name)


def test_agent_chat_command_catalog_marks_agent_control_capabilities_available():
    required = {
        "inspect_agent_health_projection",
        "inspect_agent_command_contracts",
        "plan_recovery_tools",
        "plan_recommended_followups",
        "prepare_generate_chapter_execution",
    }

    catalog = build_agent_chat_command_catalog(
        descriptor_names_provider=lambda: required,
        adapter_names_provider=lambda: required,
    )

    assert catalog["version"] == "phase27.agent_chat_command_catalog.v1"
    assert catalog["public_command_names"] == ["continue", "status", "clear", "compact"]

    continue_command = _command_by_name(catalog, "continue")
    assert continue_command["category"] == "agent_control"
    assert continue_command["capability_id"] == "agent.continue"
    assert continue_command["control_projection_type"] == "continue_agent_control"
    assert continue_command["required_agent_tools"] == [
        "inspect_agent_health_projection",
        "inspect_agent_command_contracts",
        "plan_recovery_tools",
        "plan_recommended_followups",
        "prepare_generate_chapter_execution",
    ]
    assert continue_command["available"] is True
    assert continue_command["unavailable_reasons"] == []
    status_command = _command_by_name(catalog, "status")
    assert status_command["required_agent_tools"] == [
        "inspect_agent_health_projection",
        "inspect_agent_command_contracts",
    ]
    assert status_command["available"] is True


def test_agent_chat_command_catalog_hides_public_agent_command_when_adapter_missing():
    descriptor_names = {
        "inspect_agent_health_projection",
        "inspect_agent_command_contracts",
        "plan_recovery_tools",
        "plan_recommended_followups",
        "prepare_generate_chapter_execution",
    }
    adapter_names = descriptor_names - {"prepare_generate_chapter_execution"}

    catalog = build_agent_chat_command_catalog(
        descriptor_names_provider=lambda: descriptor_names,
        adapter_names_provider=lambda: adapter_names,
    )

    assert catalog["public_command_names"] == ["status", "clear", "compact"]
    continue_command = _command_by_name(catalog, "continue")
    assert continue_command["public"] is True
    assert continue_command["available"] is False
    assert continue_command["unavailable_reasons"] == [
        "缺少 Agent 工具适配器：prepare_generate_chapter_execution"
    ]


def test_agent_chat_command_catalog_hides_status_when_command_contract_adapter_missing():
    descriptor_names = {
        "inspect_agent_health_projection",
        "inspect_agent_command_contracts",
        "plan_recovery_tools",
        "plan_recommended_followups",
        "prepare_generate_chapter_execution",
    }
    adapter_names = descriptor_names - {"inspect_agent_command_contracts"}

    catalog = build_agent_chat_command_catalog(
        descriptor_names_provider=lambda: descriptor_names,
        adapter_names_provider=lambda: adapter_names,
    )

    assert catalog["public_command_names"] == ["clear", "compact"]
    status_command = _command_by_name(catalog, "status")
    assert status_command["public"] is True
    assert status_command["available"] is False
    assert status_command["unavailable_reasons"] == [
        "缺少 Agent 工具适配器：inspect_agent_command_contracts"
    ]
    continue_command = _command_by_name(catalog, "continue")
    assert continue_command["available"] is False
    assert continue_command["unavailable_reasons"] == [
        "缺少 Agent 工具适配器：inspect_agent_command_contracts"
    ]


def test_agent_chat_command_catalog_keeps_session_commands_available_without_tools():
    catalog = build_agent_chat_command_catalog(
        descriptor_names_provider=lambda: set(),
        adapter_names_provider=lambda: set(),
    )

    assert catalog["public_command_names"] == ["clear", "compact"]
    clear_command = _command_by_name(catalog, "clear")
    assert clear_command["category"] == "session"
    assert clear_command["control_projection_type"] == ""
    assert clear_command["required_agent_tools"] == []
    assert clear_command["available"] is True
