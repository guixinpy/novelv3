import json
import time
import uuid
from collections.abc import Callable
from typing import Any


def now_ms() -> int:
    return int(time.perf_counter() * 1000)


def new_request_id() -> str:
    return str(uuid.uuid4())


def format_kv_event(event: str, **fields: Any) -> str:
    parts = [f"event={_format_value(event)}"]
    for key, value in fields.items():
        if value is None:
            continue
        parts.append(f"{key}={_format_value(value)}")
    return " ".join(parts)


def log_event(event: str, **fields: Any) -> None:
    print(format_kv_event(event, **fields), flush=True)


def duration_ms_since(start_ms: int) -> int:
    return max(0, now_ms() - start_ms)


def _format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    text = str(value)
    if text and all(ch.isalnum() or ch in "._-:/@" for ch in text):
        return text
    return json.dumps(text, ensure_ascii=False)

