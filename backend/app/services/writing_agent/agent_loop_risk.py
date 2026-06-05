from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from typing import Any, Iterable, Mapping

LOOP_RISK_WARNING_THRESHOLD = 3
LOOP_RISK_CRITICAL_THRESHOLD = 5
PING_PONG_WARNING_THRESHOLD = 2
PING_PONG_CRITICAL_THRESHOLD = 3
GLOBAL_CIRCUIT_BREAKER_THRESHOLD = 30

KNOWN_POLL_TOOLS = {
    "inspect_agent_health_projection",
    "inspect_agent_job_projection",
    "inspect_agent_memory_route",
    "inspect_agent_retrieval_strategy",
    "inspect_agent_trace_audit",
    "inspect_agent_world_model_semantic_check",
    "inspect_longform_chapter_batch",
}

_STATUS_RANK = {"clear": 0, "warning": 1, "critical": 2}
_DETECTOR_PRIORITY = {
    "global_circuit_breaker": 50,
    "unknown_tool_repeat": 40,
    "ping_pong": 30,
    "known_poll_no_progress": 20,
    "generic_repeat": 10,
}


def build_agent_loop_risk(
    steps: Iterable[Any],
    *,
    planned_tools: Iterable[Mapping[str, Any]] | None = None,
    known_tool_names: set[str] | None = None,
) -> dict[str, Any]:
    markers = [_step_marker(step) for step in steps]
    planned_markers = [_planned_tool_marker(tool) for tool in planned_tools or []]
    detectors = [
        detector
        for detector in [
            _generic_repeat(markers),
            _ping_pong(markers),
            _known_poll_no_progress(markers),
            _unknown_tool_repeat(planned_markers, known_tool_names),
            _global_circuit_breaker(markers),
        ]
        if detector is not None
    ]
    detectors.sort(key=lambda item: (_STATUS_RANK.get(item["status"], 0), _DETECTOR_PRIORITY[item["detector"]]), reverse=True)
    primary = detectors[0] if detectors else None
    max_repeat_count = max([_signature_count(markers), *(int(item.get("repeat_count") or 0) for item in detectors)] or [0])
    return {
        "status": primary["status"] if primary else "clear",
        "detector": primary["detector"] if primary else None,
        "max_repeat_count": max_repeat_count,
        "tool_name": primary.get("tool_name") if primary else None,
        "signature": primary.get("signature") if primary else None,
        "thresholds": {
            "warning": LOOP_RISK_WARNING_THRESHOLD,
            "critical": LOOP_RISK_CRITICAL_THRESHOLD,
            "global_circuit_breaker": GLOBAL_CIRCUIT_BREAKER_THRESHOLD,
        },
        "detectors": detectors,
        "recommended_next_action": primary["recommended_next_action"] if primary else _no_action(),
    }


def _generic_repeat(markers: list[dict[str, Any]]) -> dict[str, Any] | None:
    counts = Counter(marker["signature"] for marker in markers)
    if not counts:
        return None
    signature, repeat_count = counts.most_common(1)[0]
    if repeat_count < LOOP_RISK_WARNING_THRESHOLD:
        return None
    marker = next(item for item in markers if item["signature"] == signature)
    status = "critical" if repeat_count >= LOOP_RISK_CRITICAL_THRESHOLD else "warning"
    return {
        "detector": "generic_repeat",
        "status": status,
        "tool_name": marker["tool_name"],
        "signature": signature,
        "repeat_count": repeat_count,
        "thresholds": {"warning": LOOP_RISK_WARNING_THRESHOLD, "critical": LOOP_RISK_CRITICAL_THRESHOLD},
        "evidence": _evidence([item for item in markers if item["signature"] == signature]),
        "recommended_next_action": _action("generic_repeat", status),
    }


def _ping_pong(markers: list[dict[str, Any]]) -> dict[str, Any] | None:
    best: tuple[int, int] | None = None
    for start in range(0, max(0, len(markers) - 3)):
        first = markers[start]["signature"]
        second = markers[start + 1]["signature"]
        if first == second:
            continue
        length = 2
        while start + length < len(markers) and markers[start + length]["signature"] == (first if length % 2 == 0 else second):
            length += 1
        if length >= 4 and (best is None or length > best[1]):
            best = (start, length)
    if best is None:
        return None
    start, length = best
    repeat_count = length // 2
    status = "critical" if repeat_count >= PING_PONG_CRITICAL_THRESHOLD else "warning"
    first = markers[start]
    second = markers[start + 1]
    return {
        "detector": "ping_pong",
        "status": status,
        "tool_name": first["tool_name"],
        "signature": first["signature"],
        "pattern": [first["tool_name"], second["tool_name"]],
        "repeat_count": repeat_count,
        "thresholds": {"warning": PING_PONG_WARNING_THRESHOLD, "critical": PING_PONG_CRITICAL_THRESHOLD},
        "evidence": _evidence(markers[start : start + length]),
        "recommended_next_action": _action("ping_pong", status),
    }


def _known_poll_no_progress(markers: list[dict[str, Any]]) -> dict[str, Any] | None:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for marker in markers:
        if marker["tool_name"] in KNOWN_POLL_TOOLS:
            groups[(marker["tool_name"], marker["signature"], marker["output_signature"])].append(marker)
    if not groups:
        return None
    (_, signature, output_signature), group = max(groups.items(), key=lambda item: len(item[1]))
    repeat_count = len(group)
    if repeat_count < LOOP_RISK_WARNING_THRESHOLD:
        return None
    status = "critical" if repeat_count >= LOOP_RISK_CRITICAL_THRESHOLD else "warning"
    return {
        "detector": "known_poll_no_progress",
        "status": status,
        "tool_name": group[0]["tool_name"],
        "signature": signature,
        "output_signature": output_signature,
        "repeat_count": repeat_count,
        "thresholds": {"warning": LOOP_RISK_WARNING_THRESHOLD, "critical": LOOP_RISK_CRITICAL_THRESHOLD},
        "evidence": _evidence(group),
        "recommended_next_action": _action("known_poll_no_progress", status),
    }


def _unknown_tool_repeat(
    planned_markers: list[dict[str, Any]],
    known_tool_names: set[str] | None,
) -> dict[str, Any] | None:
    if known_tool_names is None:
        return None
    unknown = [marker for marker in planned_markers if marker["tool_name"] not in known_tool_names]
    if not unknown:
        return None
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for marker in unknown:
        groups[marker["signature"]].append(marker)
    signature, group = max(groups.items(), key=lambda item: len(item[1]))
    repeat_count = len(group)
    if repeat_count < LOOP_RISK_WARNING_THRESHOLD:
        return None
    status = "critical" if repeat_count >= LOOP_RISK_CRITICAL_THRESHOLD else "warning"
    return {
        "detector": "unknown_tool_repeat",
        "status": status,
        "tool_name": group[0]["tool_name"],
        "signature": signature,
        "repeat_count": repeat_count,
        "thresholds": {"warning": LOOP_RISK_WARNING_THRESHOLD, "critical": LOOP_RISK_CRITICAL_THRESHOLD},
        "evidence": _evidence(group),
        "recommended_next_action": _action("unknown_tool_repeat", status),
    }


def _global_circuit_breaker(markers: list[dict[str, Any]]) -> dict[str, Any] | None:
    if len(markers) < GLOBAL_CIRCUIT_BREAKER_THRESHOLD:
        return None
    return {
        "detector": "global_circuit_breaker",
        "status": "critical",
        "tool_name": markers[-1]["tool_name"],
        "signature": markers[-1]["signature"],
        "call_count": len(markers),
        "thresholds": {"critical": GLOBAL_CIRCUIT_BREAKER_THRESHOLD},
        "evidence": _evidence(markers[-5:]),
        "recommended_next_action": _action("global_circuit_breaker", "critical"),
    }


def _step_marker(step: Any) -> dict[str, Any]:
    params = _params_from_input(getattr(step, "input", None))
    output = getattr(step, "output", None)
    return {
        "step_index": getattr(step, "step_index", None),
        "tool_name": str(getattr(step, "tool_name", "") or ""),
        "status": str(getattr(step, "status", "") or ""),
        "signature": _signature(str(getattr(step, "tool_name", "") or ""), params),
        "output_signature": _digest(output),
        "params": params,
    }


def _planned_tool_marker(tool: Mapping[str, Any]) -> dict[str, Any]:
    tool_name = str(tool.get("tool_name") or "")
    params = tool.get("params") if isinstance(tool.get("params"), Mapping) else {}
    return {
        "step_index": None,
        "tool_name": tool_name,
        "status": "planned",
        "signature": _signature(tool_name, params),
        "output_signature": "",
        "params": dict(params),
    }


def _params_from_input(value: object) -> dict[str, Any]:
    if isinstance(value, Mapping):
        params = value.get("params")
        if isinstance(params, Mapping):
            return dict(params)
    return {}


def _signature(tool_name: str, params: Mapping[str, Any]) -> str:
    return f"{tool_name}:{_digest(params)}"


def _digest(value: object) -> str:
    try:
        serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    except (TypeError, ValueError):
        serialized = str(value)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


def _signature_count(markers: list[dict[str, Any]]) -> int:
    counts = Counter(marker["signature"] for marker in markers)
    return counts.most_common(1)[0][1] if counts else 0


def _evidence(markers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "step_index": marker["step_index"],
            "tool_name": marker["tool_name"],
            "status": marker["status"],
            "signature": marker["signature"],
        }
        for marker in markers[:5]
    ]


def _action(detector: str, status: str) -> dict[str, Any]:
    if status == "critical":
        tools = ["inspect_agent_health_projection"]
        if detector == "unknown_tool_repeat":
            tools.append("describe_agent_tools")
        return {
            "status": "blocked",
            "reason": f"loop_risk_{detector}",
            "next_tool": tools[0],
            "recommended_tools": tools,
            "requires_user_input": False,
            "allow_continue": False,
        }
    return {
        "status": "recommended",
        "reason": f"loop_risk_{detector}",
        "next_tool": "inspect_agent_health_projection",
        "recommended_tools": ["inspect_agent_health_projection"],
        "requires_user_input": False,
        "allow_continue": True,
    }


def _no_action() -> dict[str, Any]:
    return {
        "status": "none",
        "reason": "loop_risk_clear",
        "next_tool": None,
        "recommended_tools": [],
        "requires_user_input": False,
        "allow_continue": True,
    }
