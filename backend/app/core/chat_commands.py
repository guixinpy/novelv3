from dataclasses import dataclass
import re

from app.core.dialog_agent_routes import (
    build_dialog_agent_route,
    dialog_action_to_agent_tool_name,
)

CHAT_COMMAND_CATALOG_VERSION = "phase27.agent_chat_command_catalog.v1"

CONTINUE_REQUIRED_AGENT_TOOLS = (
    "inspect_agent_health_projection",
    "inspect_agent_command_contracts",
    "plan_recovery_tools",
    "plan_recommended_followups",
    "prepare_generate_chapter_execution",
)
STATUS_REQUIRED_AGENT_TOOLS = (
    "inspect_agent_health_projection",
    "inspect_agent_command_contracts",
)


@dataclass(frozen=True)
class ParsedCommand:
    name: str
    args: str | None = None


@dataclass(frozen=True)
class ChatCommandSpec:
    description: str
    action_type: str | None = None
    mutates_history: bool = False
    public: bool = True
    legacy: bool = False
    agent_intent_text: str | None = None
    example: str = ""
    supports_args: bool = False
    category: str = "agent_control"
    capability_id: str = ""
    required_agent_tools: tuple[str, ...] = ()
    control_projection_type: str = ""


CHAT_COMMAND_REGISTRY: dict[str, ChatCommandSpec] = {
    "continue": ChatCommandSpec(
        description="让写作 Agent 根据当前项目状态继续推进",
        agent_intent_text="继续",
        example="/continue",
        capability_id="agent.continue",
        required_agent_tools=CONTINUE_REQUIRED_AGENT_TOOLS,
        control_projection_type="continue_agent_control",
    ),
    "status": ChatCommandSpec(
        description="查看写作 Agent 对当前项目状态的判断",
        agent_intent_text="接下来做什么",
        example="/status",
        capability_id="agent.status",
        required_agent_tools=STATUS_REQUIRED_AGENT_TOOLS,
        control_projection_type="agent_health_projection",
    ),
    "clear": ChatCommandSpec(
        description="清空当前项目对话上下文",
        mutates_history=True,
        example="/clear",
        category="session",
        capability_id="session.clear",
    ),
    "compact": ChatCommandSpec(
        description="压缩当前项目历史上下文",
        mutates_history=True,
        example="/compact",
        category="session",
        capability_id="session.compact",
    ),
    "setup": ChatCommandSpec(
        description="旧命令：转译为 Agent 设定意图",
        public=False,
        legacy=True,
        example="/setup 主角是植物学家",
        supports_args=True,
        category="legacy_alias",
        capability_id="legacy.setup",
    ),
    "storyline": ChatCommandSpec(
        description="旧命令：转译为 Agent 故事线意图",
        public=False,
        legacy=True,
        example="/storyline 主线走悬疑反转",
        supports_args=True,
        category="legacy_alias",
        capability_id="legacy.storyline",
    ),
    "outline": ChatCommandSpec(
        description="旧命令：转译为 Agent 大纲意图",
        public=False,
        legacy=True,
        example="/outline 第 1 章结尾必须反转",
        supports_args=True,
        category="legacy_alias",
        capability_id="legacy.outline",
    ),
    "chapter": ChatCommandSpec(
        description="旧命令：转译为 Agent 章节生成意图",
        public=False,
        legacy=True,
        example="/chapter 1 强化灯塔悬疑",
        supports_args=True,
        category="legacy_alias",
        capability_id="legacy.chapter",
    ),
}


def parse_command(command_name: str | None, text: str | None, command_args: str | None) -> ParsedCommand | None:
    parsed_from_text = _parse_command_from_text(text)
    if parsed_from_text:
        normalized_name, normalized_args = parsed_from_text
    else:
        normalized_name = (command_name or "").strip().lower()
        normalized_args = (command_args or "").strip() or None

    if not normalized_name or not is_supported_chat_command(normalized_name):
        return None
    return ParsedCommand(name=normalized_name, args=normalized_args)


def build_command_text(parsed: ParsedCommand) -> str:
    if parsed.args:
        return f"/{parsed.name} {parsed.args}"
    return f"/{parsed.name}"


def _parse_command_from_text(text: str | None) -> tuple[str, str | None] | None:
    raw = (text or "").strip()
    if not raw.startswith("/"):
        return None
    command_part, _, args_part = raw.partition(" ")
    name = command_part.lstrip("/").lower()
    args = args_part.strip() or None
    if not name:
        return None
    return name, args


def is_supported_chat_command(command_name: str | None) -> bool:
    return (command_name or "").strip().lower() in CHAT_COMMAND_REGISTRY


def command_to_action_type(command_name: str | None) -> str | None:
    normalized = (command_name or "").strip().lower()
    spec = CHAT_COMMAND_REGISTRY.get(normalized)
    if not spec:
        return None
    return spec.action_type


def command_to_agent_tool_name(command_name: str | None) -> str | None:
    normalized = (command_name or "").strip().lower()
    spec = CHAT_COMMAND_REGISTRY.get(normalized)
    if not spec:
        return None
    return dialog_action_to_agent_tool_name(spec.action_type)


def command_control_projection_type(command_name: str | None) -> str:
    normalized = (command_name or "").strip().lower()
    spec = CHAT_COMMAND_REGISTRY.get(normalized)
    if not spec:
        return ""
    return spec.control_projection_type


def public_chat_command_names() -> list[str]:
    return [name for name, spec in CHAT_COMMAND_REGISTRY.items() if spec.public]


def chat_command_catalog() -> dict:
    return {
        "version": CHAT_COMMAND_CATALOG_VERSION,
        "public_command_names": public_chat_command_names(),
        "legacy_alias_names": [name for name, spec in CHAT_COMMAND_REGISTRY.items() if spec.legacy],
        "commands": [_chat_command_catalog_item(name, spec) for name, spec in CHAT_COMMAND_REGISTRY.items()],
    }


def _chat_command_catalog_item(name: str, spec: ChatCommandSpec) -> dict[str, object]:
    item: dict[str, object] = {
        "name": name,
        "label": f"/{name}",
        "description": spec.description,
        "example": spec.example or f"/{name}",
        "supports_args": spec.supports_args,
        "public": spec.public,
        "legacy": spec.legacy,
        "mutates_history": spec.mutates_history,
        "category": spec.category,
        "capability_id": spec.capability_id,
        "required_agent_tools": list(spec.required_agent_tools),
        "control_projection_type": spec.control_projection_type,
    }
    if spec.action_type:
        item["action_type"] = spec.action_type
    if spec.agent_intent_text:
        item["agent_intent_text"] = spec.agent_intent_text
    return item


def is_legacy_chat_command(command_name: str | None) -> bool:
    normalized = (command_name or "").strip().lower()
    spec = CHAT_COMMAND_REGISTRY.get(normalized)
    return bool(spec and spec.legacy)


def command_to_agent_intent_text(command_name: str | None, args: str | None = None) -> str | None:
    normalized = (command_name or "").strip().lower()
    spec = CHAT_COMMAND_REGISTRY.get(normalized)
    if not spec:
        return None
    if spec.agent_intent_text:
        return spec.agent_intent_text
    if spec.legacy:
        return legacy_command_to_agent_intent_text(normalized, args)
    return None


def legacy_command_to_agent_intent_text(command_name: str, args: str | None = None) -> str:
    normalized_args = (args or "").strip()
    if command_name == "setup":
        return _with_optional_detail("请生成项目设定", normalized_args)
    if command_name == "storyline":
        return _with_optional_detail("请生成故事线", normalized_args)
    if command_name == "outline":
        return _with_optional_detail("请生成章节大纲", normalized_args)
    if command_name == "chapter":
        return _legacy_chapter_intent_text(normalized_args)
    return _with_optional_detail("请让写作 Agent 继续推进项目", normalized_args)


def _with_optional_detail(prefix: str, detail: str) -> str:
    if not detail:
        return prefix
    return f"{prefix}，{detail}"


def _legacy_chapter_intent_text(args: str) -> str:
    if not args:
        return "请继续生成下一章正文"
    match = re.match(r"^(?:第\s*)?(\d+)(?:\s*章)?(?:[\s,，:：-]+)?(.*)$", args)
    if not match:
        return f"请生成下一章正文，{args}"
    chapter_index = int(match.group(1))
    detail = match.group(2).strip()
    if detail:
        return f"请生成第{chapter_index}章正文，{detail}"
    return f"请生成第{chapter_index}章正文"


def command_agent_route(command_name: str | None) -> dict[str, str | bool] | None:
    normalized = (command_name or "").strip().lower()
    spec = CHAT_COMMAND_REGISTRY.get(normalized)
    if not spec or not spec.action_type:
        return None
    return build_dialog_agent_route(spec.action_type, source="slash_command", command_name=normalized)


def agent_slash_command_routes() -> list[dict[str, str | bool]]:
    routes: list[dict[str, str | bool]] = []
    for command_name in CHAT_COMMAND_REGISTRY:
        route = command_agent_route(command_name)
        if route is not None:
            routes.append(route)
    return routes


def command_mutates_history(command_name: str | None) -> bool:
    normalized = (command_name or "").strip().lower()
    spec = CHAT_COMMAND_REGISTRY.get(normalized)
    if not spec:
        return False
    return spec.mutates_history
