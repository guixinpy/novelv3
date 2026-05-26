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
    return build_memory_provenance(
        version=str(output.pop("version", "") or ""),
        status=str(output.pop("status", "") or ""),
        sources=output.pop("sources", []),
        windows=windows if windows is not None else output.pop("windows", {}),
        recovery=recovery if recovery is not None else output.pop("recovery", {}),
        trace=output.pop("trace", {}),
        extras=output,
    )


def build_memory_provenance(
    *,
    version: str,
    status: str,
    sources: list[dict[str, Any]] | None,
    windows: dict[str, Any] | None,
    recovery: dict[str, Any] | None,
    trace: dict[str, Any] | None,
    extras: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cleaned_version = str(version or "").strip()
    if not cleaned_version:
        raise ValueError("memory_provenance.version is required")
    cleaned_status = str(status or "").strip()
    if not cleaned_status:
        raise ValueError("memory_provenance.status is required")
    normalized_sources = _normalize_sources(sources)
    normalized_trace = _normalize_trace(trace, version=cleaned_version)
    output = {
        "version": cleaned_version,
        "status": cleaned_status,
        "source_count": len(normalized_sources),
        "sources": normalized_sources,
        "windows": _dict_or_empty(windows),
        "recovery": _normalize_recovery(recovery, reason=cleaned_status),
        "trace": normalized_trace,
    }
    for key, value in (extras or {}).items():
        if key in output:
            continue
        output[key] = value
    return output


def no_recovery(*, reason: str | None = None) -> dict[str, Any]:
    return {
        "status": "none",
        "reason": reason,
        "next_tools": [],
        "tools": [],
    }


def _normalize_sources(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    sources: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"memory_provenance.sources[{index}] must be an object")
        source_ref = str(item.get("source_ref") or "").strip()
        if not source_ref:
            raise ValueError(f"memory_provenance.sources[{index}].source_ref is required")
        source_type = str(item.get("source_type") or "").strip()
        if not source_type:
            raise ValueError(f"memory_provenance.sources[{index}].source_type is required")
        normalized = dict(item)
        normalized["source_ref"] = source_ref
        normalized["source_type"] = source_type
        sources.append(normalized)
    return sources


def _normalize_trace(value: object, *, version: str) -> dict[str, Any]:
    trace = _dict_or_empty(value)
    source = str(trace.get("source") or "").strip()
    if not source:
        raise ValueError("memory_provenance.trace.source is required")
    trace["source"] = source
    trace.setdefault("version", version)
    return trace


def _normalize_recovery(value: object, *, reason: str) -> dict[str, Any]:
    recovery = _dict_or_empty(value)
    if not recovery:
        return no_recovery(reason=reason)
    recovery.setdefault("status", "none")
    recovery.setdefault("reason", reason)
    recovery["next_tools"] = recovery.get("next_tools") if isinstance(recovery.get("next_tools"), list) else []
    recovery["tools"] = recovery.get("tools") if isinstance(recovery.get("tools"), list) else []
    return recovery


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
