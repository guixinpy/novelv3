from __future__ import annotations

from collections.abc import Iterable, Mapping

from app.services.writing_agent.tool_policy import report_policy_for_tool
from app.services.writing_agent.tool_registry import allowed_tool_names

RECOMMENDATION_OUTPUT_FIELDS = ("recommended_next_tools", "recommended_actions")
TOOL_RECOMMENDATION_VERSION = "phase100.tool_recommendations.v1"


def normalize_tool_recommendations(
    tool_name: str,
    output: Mapping[str, object],
    *,
    allowed_tools: Iterable[str] | None = None,
) -> dict[str, object]:
    allowed = set(allowed_tools if allowed_tools is not None else allowed_tool_names())
    source_fields: list[str] = []
    raw_recommendations: list[str] = []
    for field in RECOMMENDATION_OUTPUT_FIELDS:
        if field not in output:
            continue
        source_fields.append(field)
        raw_recommendations.extend(_recommendation_values(output.get(field)))
    provenance_tools = _provenance_recovery_tools(output)
    if provenance_tools:
        source_fields.append("memory_provenance.recovery.tools")
        raw_recommendations.extend(_recommendation_value(tool) for tool in provenance_tools)
    post_approval_continuation_tools = _post_approval_continuation_tools(output)
    if post_approval_continuation_tools:
        source_fields.append("post_approval_continuation_tools")
        raw_recommendations.extend(_recommendation_value(tool) for tool in post_approval_continuation_tools)
    recommended_next_tool_calls = _recommended_next_tool_calls(output)
    if recommended_next_tool_calls:
        source_fields.append("recommended_next_tool_calls")
        raw_recommendations.extend(_recommendation_value(tool) for tool in recommended_next_tool_calls)
    provenance_write_tools = _provenance_write_tools(output)
    if provenance_write_tools:
        source_fields.append("memory_provenance.recovery.write_tools")

    raw_recommendations = _dedupe([item for item in raw_recommendations if item])
    runtime_followups = [item for item in raw_recommendations if item in allowed]
    non_tool_recommendations = [item for item in raw_recommendations if item not in allowed]
    policy = report_policy_for_tool(tool_name)
    policy_followups = [str(item) for item in policy.get("allowed_followups") or [] if str(item) in allowed]
    return {
        "version": TOOL_RECOMMENDATION_VERSION,
        "source_fields": source_fields,
        "raw_recommendations": raw_recommendations,
        "runtime_followups": runtime_followups,
        "non_tool_recommendations": non_tool_recommendations,
        "policy_followups": policy_followups,
        "canonical_followups": _dedupe(runtime_followups + policy_followups),
        "provenance_recovery_tools": provenance_tools,
        "post_approval_continuation_tools": post_approval_continuation_tools,
        "recommended_next_tool_calls": recommended_next_tool_calls,
        "provenance_write_tools": provenance_write_tools,
    }


def _recommendation_values(value: object) -> list[str]:
    if isinstance(value, str):
        normalized = value.strip()
        return [normalized] if normalized else []
    if not isinstance(value, list):
        return []
    results: list[str] = []
    for item in value:
        normalized = _recommendation_value(item)
        if not normalized:
            continue
        results.append(normalized)
    return results


def _recommendation_value(item: object) -> str | None:
    if isinstance(item, str):
        normalized = item.strip()
        return normalized or None
    if not isinstance(item, Mapping):
        return None
    for key in ("tool_name", "action"):
        value = item.get(key)
        if not isinstance(value, str):
            continue
        normalized = value.strip()
        if normalized:
            return normalized
    return None


def _provenance_recovery_tools(output: Mapping[str, object]) -> list[dict[str, object]]:
    return _provenance_tool_requests(output, field="tools")


def _provenance_write_tools(output: Mapping[str, object]) -> list[dict[str, object]]:
    return _provenance_tool_requests(output, field="write_tools")


def _post_approval_continuation_tools(output: Mapping[str, object]) -> list[dict[str, object]]:
    value = output.get("post_approval_continuation_tools")
    if not isinstance(value, list):
        return []
    results: list[dict[str, object]] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        tool_name = item.get("tool_name")
        if not isinstance(tool_name, str) or not tool_name.strip():
            continue
        params = item.get("params")
        results.append(
            {
                "tool_name": tool_name.strip(),
                "params": dict(params) if isinstance(params, Mapping) else {},
            }
        )
    return results


def _recommended_next_tool_calls(output: Mapping[str, object]) -> list[dict[str, object]]:
    value = output.get("recommended_next_tool_calls")
    if not isinstance(value, list):
        return []
    results: list[dict[str, object]] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        tool_name = item.get("tool_name")
        if not isinstance(tool_name, str) or not tool_name.strip():
            continue
        params = item.get("params")
        normalized: dict[str, object] = {
            "tool_name": tool_name.strip(),
            "params": dict(params) if isinstance(params, Mapping) else {},
        }
        visibility = item.get("visibility")
        if isinstance(visibility, str) and visibility.strip():
            normalized["visibility"] = visibility.strip()
        if "requires_confirmation" in item:
            normalized["requires_confirmation"] = item.get("requires_confirmation") is True
        results.append(normalized)
    return results


def _provenance_tool_requests(output: Mapping[str, object], *, field: str) -> list[dict[str, object]]:
    provenance = output.get("memory_provenance")
    if not isinstance(provenance, Mapping):
        return []
    recovery = provenance.get("recovery")
    if not isinstance(recovery, Mapping):
        return []
    tools = recovery.get(field)
    if not isinstance(tools, list):
        return []
    results: list[dict[str, object]] = []
    for item in tools:
        if not isinstance(item, Mapping):
            continue
        tool_name = item.get("tool_name")
        if not isinstance(tool_name, str) or not tool_name.strip():
            continue
        params = item.get("params")
        results.append(
            {
                "tool_name": tool_name.strip(),
                "params": dict(params) if isinstance(params, Mapping) else {},
            }
        )
    return results


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
