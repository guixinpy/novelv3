from app.core.model_call_trace import build_context_block


def build_provider_error_block(*, key: str, provider: str, exc: Exception) -> dict:
    error_type = type(exc).__name__
    block = build_context_block(
        key=key,
        kind="provider_error",
        title=f"{provider} 上下文构建失败",
        content=f"{provider} context provider failed: {error_type}: {exc}",
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
