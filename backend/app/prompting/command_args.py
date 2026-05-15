COMMAND_ARGS_CHAR_LIMIT = 3000


def compact_command_args(command_args: str | None) -> str:
    cleaned = (command_args or "").strip()
    if len(cleaned) <= COMMAND_ARGS_CHAR_LIMIT:
        return cleaned
    return (
        cleaned[:COMMAND_ARGS_CHAR_LIMIT].rstrip()
        + "\n\n[已截断超长附加要求，后续内容未进入本次生成上下文]"
    )
