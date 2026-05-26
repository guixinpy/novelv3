from __future__ import annotations

from typing import Any

MEMORY_PROVENANCE_REQUIRED_FIELDS = (
    "version",
    "status",
    "sources",
    "windows",
    "recovery",
    "trace",
)


def ensure_memory_provenance_contract(
    payload: dict[str, Any],
    *,
    windows: dict[str, Any] | None = None,
    recovery: dict[str, Any] | None = None,
) -> dict[str, Any]:
    output = dict(payload)
    sources = output.get("sources") if isinstance(output.get("sources"), list) else []
    output["sources"] = sources
    source_count = output.get("source_count") if output.get("source_count") is not None else len(sources)
    output["source_count"] = _non_negative_int(source_count)
    output["windows"] = windows if windows is not None else _dict_or_empty(output.get("windows"))
    output["recovery"] = recovery if recovery is not None else _dict_or_empty(output.get("recovery"))
    if not output["recovery"]:
        output["recovery"] = no_recovery(reason=str(output.get("status") or "") or None)
    output["trace"] = _dict_or_empty(output.get("trace"))
    return output


def no_recovery(*, reason: str | None = None) -> dict[str, Any]:
    return {
        "status": "none",
        "reason": reason,
        "next_tools": [],
        "tools": [],
    }


def count_window(
    total: Any,
    *,
    returned: Any | None = None,
    limit: Any | None = None,
    has_more: bool = False,
) -> dict[str, Any]:
    total_count = _non_negative_int(total)
    returned_count = _non_negative_int(returned if returned is not None else total_count)
    limit_count = _non_negative_int(limit if limit is not None else returned_count)
    return {
        "total": total_count,
        "returned": returned_count,
        "limit": limit_count,
        "has_more": bool(has_more),
    }


def _dict_or_empty(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _non_negative_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(parsed, 0)
