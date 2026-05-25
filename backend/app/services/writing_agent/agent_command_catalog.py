from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from app.core.chat_commands import chat_command_catalog
from app.services.writing_agent.tool_executor import static_writing_agent_tool_adapter_names
from app.services.writing_agent.tool_registry import allowed_tool_names


ToolNamesProvider = Callable[[], Iterable[str]]


def build_agent_chat_command_catalog(
    *,
    descriptor_names_provider: ToolNamesProvider = allowed_tool_names,
    adapter_names_provider: ToolNamesProvider = static_writing_agent_tool_adapter_names,
) -> dict[str, Any]:
    descriptor_names = set(descriptor_names_provider())
    adapter_names = set(adapter_names_provider())
    catalog = chat_command_catalog()

    commands: list[dict[str, Any]] = []
    public_command_names: list[str] = []
    for command in catalog["commands"]:
        enriched_command = _with_capability_availability(command, descriptor_names, adapter_names)
        commands.append(enriched_command)
        if enriched_command["public"] and enriched_command["available"]:
            public_command_names.append(str(enriched_command["name"]))

    return {
        **catalog,
        "public_command_names": public_command_names,
        "commands": commands,
    }


def find_unavailable_agent_chat_command(command_name: str | None, catalog: dict[str, Any] | None = None) -> dict[str, Any] | None:
    normalized_name = (command_name or "").strip().lower()
    if not normalized_name:
        return None
    catalog = catalog or build_agent_chat_command_catalog()
    for command in catalog.get("commands", []):
        if str(command.get("name", "")).strip().lower() != normalized_name:
            continue
        if command.get("available") is False:
            return command
        return None
    return None


def unavailable_agent_chat_command_message(command: dict[str, Any]) -> str:
    label = str(command.get("label") or f"/{command.get('name', '')}").strip() or "该命令"
    reasons = [str(reason) for reason in command.get("unavailable_reasons", []) if str(reason).strip()]
    reason_text = "；".join(reasons) if reasons else "缺少所需 Agent 能力"
    return f"{label} 暂不可用：{reason_text}。该命令未执行。"


def unavailable_agent_chat_command_meta(command: dict[str, Any]) -> dict[str, Any]:
    return {
        "command_name": str(command.get("name") or ""),
        "command_available": False,
        "unavailable_reasons": [
            str(reason) for reason in command.get("unavailable_reasons", []) if str(reason).strip()
        ],
    }


def _with_capability_availability(
    command: dict[str, Any],
    descriptor_names: set[str],
    adapter_names: set[str],
) -> dict[str, Any]:
    required_tools = [str(tool_name) for tool_name in command.get("required_agent_tools", [])]
    unavailable_reasons = _unavailable_reasons(required_tools, descriptor_names, adapter_names)
    return {
        **command,
        "required_agent_tools": required_tools,
        "available": not unavailable_reasons,
        "unavailable_reasons": unavailable_reasons,
    }


def _unavailable_reasons(
    required_tools: list[str],
    descriptor_names: set[str],
    adapter_names: set[str],
) -> list[str]:
    reasons: list[str] = []
    for tool_name in required_tools:
        if tool_name not in descriptor_names:
            reasons.append(f"缺少 Agent 工具定义：{tool_name}")
        elif tool_name not in adapter_names:
            reasons.append(f"缺少 Agent 工具适配器：{tool_name}")
    return reasons
