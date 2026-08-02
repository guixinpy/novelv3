from app.core.model_call_trace import build_context_block, sanitize_text

MAX_PROVIDER_ERROR_MESSAGE_CHARS = 300


def build_provider_error_block(*, key: str, provider: str, exc: Exception) -> dict:
    error_type = type(exc).__name__
    brief_message = _brief_exception_message(exc)
    block = build_context_block(
        key=key,
        kind="provider_error",
        title=f"{provider} 上下文构建失败",
        content=f"{provider} context provider failed: {error_type}: {brief_message}",
        sources=[
            {
                "source_type": "PromptContextProvider",
                "source_id": provider,
                "label": f"{provider} provider failure",
                "source_ref": provider,
                "metadata": {"provider": provider, "error_type": error_type},
            }
        ],
    )
    block["metadata"] = {
        "provider": provider,
        "error_type": error_type,
        "trace_only": True,
    }
    return block


def _brief_exception_message(exc: Exception) -> str:
    one_line = " ".join(str(exc).split())
    sanitized = sanitize_text(one_line)
    if len(sanitized) <= MAX_PROVIDER_ERROR_MESSAGE_CHARS:
        return sanitized
    return sanitized[: MAX_PROVIDER_ERROR_MESSAGE_CHARS - 3].rstrip() + "..."
