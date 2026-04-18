from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedCommand:
    name: str
    args: str | None = None


SUPPORTED_COMMANDS: dict[str, str] = {
    "clear": "清空当前项目对话上下文",
    "compact": "压缩当前项目历史上下文",
}


def parse_command(command_name: str | None, text: str | None, command_args: str | None) -> ParsedCommand | None:
    normalized_name = (command_name or "").strip().lower()
    if not normalized_name:
        normalized_name = _parse_command_name_from_text(text)

    if not normalized_name or normalized_name not in SUPPORTED_COMMANDS:
        return None
    return ParsedCommand(name=normalized_name, args=(command_args or "").strip() or None)


def build_command_text(parsed: ParsedCommand, raw_text: str | None = None) -> str:
    if raw_text and raw_text.strip():
        return raw_text.strip()
    if parsed.args:
        return f"/{parsed.name} {parsed.args}"
    return f"/{parsed.name}"


def _parse_command_name_from_text(text: str | None) -> str | None:
    raw = (text or "").strip()
    if not raw.startswith("/"):
        return None
    token = raw.split(maxsplit=1)[0].lstrip("/").lower()
    return token or None
