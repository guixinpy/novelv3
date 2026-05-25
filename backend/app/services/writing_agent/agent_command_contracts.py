from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from app.services.writing_agent.agent_command_catalog import build_agent_chat_command_catalog
from app.services.writing_agent.tool_registry import allowed_tool_names


COMMAND_CONTRACTS_VERSION = "phase38.agent_command_contracts.v1"
ToolNamesProvider = Callable[[], Iterable[str]]


def inspect_agent_command_contracts(
    *,
    descriptor_names_provider: ToolNamesProvider = allowed_tool_names,
    adapter_names_provider: ToolNamesProvider | None = None,
) -> dict[str, Any]:
    if adapter_names_provider is None:
        from app.services.writing_agent.tool_executor import static_writing_agent_tool_adapter_names

        adapter_names_provider = static_writing_agent_tool_adapter_names

    catalog = build_agent_chat_command_catalog(
        descriptor_names_provider=descriptor_names_provider,
        adapter_names_provider=adapter_names_provider,
    )
    commands = [_command_contract(command) for command in catalog.get("commands", [])]
    gaps = [gap for command in commands for gap in command["gaps"]]

    return {
        "status": "completed",
        "version": COMMAND_CONTRACTS_VERSION,
        "summary": _summary(commands, gaps),
        "commands": commands,
        "gaps": gaps,
        "recommended_next_tools": _recommended_next_tools(gaps),
        "trace": {
            "source": "inspect_agent_command_contracts",
            "catalog_version": catalog.get("version"),
            "public_command_names": catalog.get("public_command_names", []),
            "legacy_alias_names": catalog.get("legacy_alias_names", []),
        },
    }


def _command_contract(command: dict[str, Any]) -> dict[str, Any]:
    required_tools = [str(tool_name) for tool_name in command.get("required_agent_tools", [])]
    control_projection_type = str(command.get("control_projection_type") or "")
    gaps = _command_gaps(command, required_tools, control_projection_type)

    return {
        "name": str(command.get("name") or ""),
        "label": str(command.get("label") or ""),
        "category": str(command.get("category") or ""),
        "public": bool(command.get("public")),
        "legacy": bool(command.get("legacy")),
        "capability_id": str(command.get("capability_id") or ""),
        "control_projection_type": control_projection_type,
        "required_agent_tools": required_tools,
        "required_tool_count": len(required_tools),
        "available": command.get("available") is not False,
        "unavailable_reasons": [
            str(reason) for reason in command.get("unavailable_reasons", []) if str(reason).strip()
        ],
        "contract_status": "needs_attention" if gaps else "ready",
        "gaps": gaps,
    }


def _command_gaps(
    command: dict[str, Any],
    required_tools: list[str],
    control_projection_type: str,
) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    name = str(command.get("name") or "")
    category = str(command.get("category") or "")
    capability_id = str(command.get("capability_id") or "")
    public = bool(command.get("public"))

    if public and not capability_id:
        gaps.append(_gap(name, "missing_capability_id", "public command lacks capability_id"))
    if category == "agent_control" and not control_projection_type:
        gaps.append(_gap(name, "missing_control_projection_type", "agent control command lacks projection type"))
    if category == "agent_control" and not required_tools:
        gaps.append(_gap(name, "missing_required_agent_tools", "agent control command lacks required tools"))
    if command.get("available") is False:
        gaps.append(
            _gap(
                name,
                "unavailable_command",
                "command required Agent tools that are not available",
                details={
                    "unavailable_reasons": [
                        str(reason) for reason in command.get("unavailable_reasons", []) if str(reason).strip()
                    ]
                },
            )
        )
    return gaps


def _gap(command_name: str, code: str, message: str, *, details: dict[str, Any] | None = None) -> dict[str, Any]:
    gap = {
        "command_name": command_name,
        "code": code,
        "severity": "warning",
        "message": message,
    }
    if details:
        gap["details"] = details
    return gap


def _summary(commands: list[dict[str, Any]], gaps: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "total_commands": len(commands),
        "public_commands": sum(1 for command in commands if command["public"]),
        "public_available_commands": sum(1 for command in commands if command["public"] and command["available"]),
        "agent_control_commands": sum(1 for command in commands if command["category"] == "agent_control"),
        "commands_with_control_projection": sum(1 for command in commands if command["control_projection_type"]),
        "unavailable_public_commands": sum(1 for command in commands if command["public"] and not command["available"]),
        "gap_count": len(gaps),
    }


def _recommended_next_tools(gaps: list[dict[str, Any]]) -> list[str]:
    tools = ["inspect_agent_tool_contracts", "inspect_agent_health_projection"]
    if gaps:
        tools.insert(0, "describe_agent_tools")
    return tools
