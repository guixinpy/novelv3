from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedCommand:
    name: str
    args: str | None = None


@dataclass(frozen=True)
class ChatCommandSpec:
    description: str
    action_type: str | None = None
    mutates_history: bool = False


CHAT_COMMAND_REGISTRY: dict[str, ChatCommandSpec] = {
    "clear": ChatCommandSpec(
        description="清空当前项目对话上下文",
        mutates_history=True,
    ),
    "compact": ChatCommandSpec(
        description="压缩当前项目历史上下文",
        mutates_history=True,
    ),
    "setup": ChatCommandSpec(
        description="触发设定生成预览动作",
        action_type="preview_setup",
    ),
    "storyline": ChatCommandSpec(
        description="触发故事线生成预览动作",
        action_type="preview_storyline",
    ),
    "outline": ChatCommandSpec(
        description="触发大纲生成预览动作",
        action_type="preview_outline",
    ),
    "chapter": ChatCommandSpec(
        description="触发章节正文生成预览动作",
        action_type="preview_chapter",
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


def command_mutates_history(command_name: str | None) -> bool:
    normalized = (command_name or "").strip().lower()
    spec = CHAT_COMMAND_REGISTRY.get(normalized)
    if not spec:
        return False
    return spec.mutates_history
