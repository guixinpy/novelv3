from __future__ import annotations

import re
from datetime import UTC, datetime
from time import perf_counter
from typing import Any

from sqlalchemy.orm import Session

from app.models import AIModelCallTrace


TRUNCATION_NOTICE = "\n\n[truncated: original content exceeded trace limit]"
MAX_TRACE_MESSAGE_CONTENT_CHARS = 12000
MAX_TRACE_ERROR_MESSAGE_CHARS = 2000
BEARER_PATTERN = re.compile(r"(Authorization\s*:\s*Bearer\s+)([^\s,;]+)", re.IGNORECASE)
SK_TOKEN_PATTERN = re.compile(r"sk-[A-Za-z0-9][A-Za-z0-9_\-]{8,}")
KEY_VALUE_PATTERN = re.compile(
    r"(?P<key_quote>['\"]?)(?P<key>[A-Za-z][A-Za-z0-9_-]*)(?P=key_quote)"
    r"(?P<separator>\s*[:=]\s*)"
    r"(?P<value_quote>['\"]?)(?P<value>[^\s,;&'\"]+)(?P=value_quote)"
)
SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "access_token",
    "refresh_token",
    "secret_key",
    "client_secret",
    "password",
    "token",
    "id_token",
    "session_token",
}
STRING_ASSIGNMENT_KEYS = SENSITIVE_KEYS - {"authorization"}


def now_ms() -> int:
    return int(perf_counter() * 1000)


def estimate_tokens(text: str | None) -> int:
    if not text:
        return 0
    ascii_chars = sum(1 for char in text if ord(char) < 128)
    non_ascii_chars = len(text) - ascii_chars
    return max(1, (ascii_chars + (non_ascii_chars * 2) + 3) // 4)


def _normalize_key(key: str) -> str:
    normalized = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", str(key))
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", normalized)
    normalized = re.sub(r"[\s-]+", "_", normalized)
    return normalized.lower()


def _is_sensitive_key(key: str, *, include_authorization: bool = True) -> bool:
    normalized_key = _normalize_key(key)
    if normalized_key in {"prompt_tokens", "completion_tokens", "max_tokens"}:
        return False
    denylist = SENSITIVE_KEYS if include_authorization else STRING_ASSIGNMENT_KEYS
    return normalized_key in denylist


def sanitize_text(text: str) -> str:
    sanitized = BEARER_PATTERN.sub(r"\1[REDACTED]", text)
    sanitized = KEY_VALUE_PATTERN.sub(
        lambda match: (
            f"{match.group('key_quote')}{match.group('key')}{match.group('key_quote')}"
            f"{match.group('separator')}{match.group('value_quote')}[REDACTED]{match.group('value_quote')}"
            if _is_sensitive_key(match.group("key"), include_authorization=False)
            else match.group(0)
        ),
        sanitized,
    )
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
    sanitized_messages: list[dict[str, Any]] = []
    for message in messages:
        if not isinstance(message, dict):
            sanitized_messages.append(_sanitize_value(message))
            continue
        sanitized_message = {}
        for key, value in message.items():
            if key == "content" and isinstance(value, str):
                sanitized_message[key] = truncate_text(value, max_chars=MAX_TRACE_MESSAGE_CONTENT_CHARS)["content"]
            else:
                sanitized_message[key] = _sanitize_value(value)
        sanitized_messages.append(sanitized_message)
    return sanitized_messages


def build_context_block(
    *,
    key: str,
    kind: str,
    title: str,
    content: str,
    sources: list[dict[str, Any]] | None = None,
    max_chars: int = 12000,
) -> dict[str, Any]:
    truncated = truncate_text(content, max_chars=max_chars)
    block_content = truncated["content"]
    return {
        "key": key,
        "kind": kind,
        "title": sanitize_text(title),
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
    status: str = "running",
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
    trace.prompt_tokens = _optional_int(prompt_tokens)
    trace.completion_tokens = _optional_int(completion_tokens)
    trace.latency_ms = latency_ms
    trace.error_message = None
    trace.updated_at = datetime.now(UTC)
    db.add(trace)
    db.flush()
    return trace


def _optional_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def mark_trace_failed(
    db: Session,
    trace: AIModelCallTrace,
    *,
    error_message: str,
    latency_ms: int | None = None,
) -> AIModelCallTrace:
    trace.status = "failed"
    trace.error_message = truncate_text(error_message, max_chars=MAX_TRACE_ERROR_MESSAGE_CHARS)["content"]
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
            if _is_sensitive_key(str(key)):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = _sanitize_value(item)
        return sanitized
    return value
