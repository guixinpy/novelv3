from __future__ import annotations

import re
from datetime import UTC, datetime
from time import perf_counter
from typing import Any

from sqlalchemy.orm import Session

from app.models import AIModelCallTrace


TRUNCATION_NOTICE = "\n\n[truncated: original content exceeded trace limit]"
BEARER_PATTERN = re.compile(r"(Authorization\s*:\s*Bearer\s+)([^\s,;]+)", re.IGNORECASE)
SK_TOKEN_PATTERN = re.compile(r"sk-[A-Za-z0-9][A-Za-z0-9_\-]{8,}")
API_KEY_PATTERN = re.compile(r"(\bapi[_-]?key\b\s*[:=]\s*)([^\s,;&]+)", re.IGNORECASE)
SENSITIVE_KEYS = {"api_key", "apikey", "authorization", "access_token", "secret_key"}


def now_ms() -> int:
    return int(perf_counter() * 1000)


def estimate_tokens(text: str | None) -> int:
    if not text:
        return 0
    ascii_chars = sum(1 for char in text if ord(char) < 128)
    non_ascii_chars = len(text) - ascii_chars
    return max(1, (ascii_chars + (non_ascii_chars * 2) + 3) // 4)


def sanitize_text(text: str) -> str:
    sanitized = BEARER_PATTERN.sub(r"\1[REDACTED]", text)
    sanitized = API_KEY_PATTERN.sub(r"\1[REDACTED]", sanitized)
    return SK_TOKEN_PATTERN.sub("[REDACTED]", sanitized)


def truncate_text(text: str | None, *, max_chars: int = 12000) -> dict[str, Any]:
    content = sanitize_text(text or "")
    original_char_count = len(content)
    if original_char_count <= max_chars:
        return {
            "content": content,
            "original_char_count": original_char_count,
            "truncated": False,
        }

    available_chars = max(0, max_chars)
    return {
        "content": content[:available_chars] + TRUNCATION_NOTICE,
        "original_char_count": original_char_count,
        "truncated": True,
    }


def sanitize_model_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_sanitize_value(message) for message in messages]


def build_context_block(
    *,
    key: str,
    kind: str,
    content: str,
    sources: list[dict[str, Any]] | None = None,
    max_chars: int = 12000,
) -> dict[str, Any]:
    truncated = truncate_text(content, max_chars=max_chars)
    block_content = truncated["content"]
    return {
        "key": key,
        "kind": kind,
        "content": block_content,
        "sources": _sanitize_value(sources or []),
        "char_count": len(block_content),
        "token_estimate": estimate_tokens(block_content),
        "original_char_count": truncated["original_char_count"],
        "truncated": truncated["truncated"],
    }


def create_trace(
    db: Session,
    *,
    project_id: str,
    trace_type: str,
    messages: list[dict[str, Any]] | None = None,
    context_blocks: list[dict[str, Any]] | None = None,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    dialog_id: str | None = None,
    request_message_id: str | None = None,
    chapter_id: str | None = None,
    chapter_index: int | None = None,
    trace_metadata: dict[str, Any] | None = None,
    status: str = "started",
) -> AIModelCallTrace:
    trace = AIModelCallTrace(
        project_id=project_id,
        trace_type=trace_type,
        status=status,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        dialog_id=dialog_id,
        request_message_id=request_message_id,
        chapter_id=chapter_id,
        chapter_index=chapter_index,
        messages=sanitize_model_messages(messages or []),
        context_blocks=_sanitize_value(context_blocks or []),
        trace_metadata=_sanitize_value(trace_metadata or {}),
    )
    db.add(trace)
    db.flush()
    return trace


def mark_trace_success(
    db: Session,
    trace: AIModelCallTrace,
    *,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    latency_ms: int | None = None,
) -> AIModelCallTrace:
    trace.status = "success"
    trace.prompt_tokens = prompt_tokens
    trace.completion_tokens = completion_tokens
    trace.latency_ms = latency_ms
    trace.error_message = None
    trace.updated_at = datetime.now(UTC)
    db.add(trace)
    db.flush()
    return trace


def mark_trace_failed(
    db: Session,
    trace: AIModelCallTrace,
    *,
    error_message: str,
    latency_ms: int | None = None,
) -> AIModelCallTrace:
    trace.status = "failed"
    trace.error_message = sanitize_text(error_message)
    trace.latency_ms = latency_ms
    trace.updated_at = datetime.now(UTC)
    db.add(trace)
    db.flush()
    return trace


def attach_trace_response(
    db: Session,
    trace: AIModelCallTrace,
    *,
    response_message_id: str,
) -> AIModelCallTrace:
    trace.response_message_id = response_message_id
    trace.updated_at = datetime.now(UTC)
    db.add(trace)
    db.flush()
    return trace


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, dict):
        sanitized = {}
        for key, item in value.items():
            normalized_key = str(key).lower().replace("-", "_")
            if normalized_key in SENSITIVE_KEYS:
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = _sanitize_value(item)
        return sanitized
    return value
