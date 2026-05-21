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

    raw_recommendations = _dedupe(raw_recommendations)
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


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
