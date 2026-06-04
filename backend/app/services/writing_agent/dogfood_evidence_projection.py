from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DOGFOOD_EVIDENCE_VERSION = "phase243.agent_dogfood_evidence_trace_long_run_samples.v1"
DOGFOOD_EVIDENCE_RUN_SOURCE = "planner_trace.agent_health_projection.dogfood_evidence"

_FULL_AGENT_NATIVE_DOGFOOD = (
    "docs/archive/superpowers/notes/long-memory-agent/2026-05-26-full-agent-native-dogfood.md"
)
_NARRATIVE_MEMORY_DOGFOOD = (
    "docs/archive/superpowers/notes/long-memory-agent/2026-05-26-narrative-memory-activation-dogfood.md"
)
_TRACE_ANOMALY_CALIBRATION_TEST = "backend/tests/test_writing_agent_trace_audit.py"

_REQUIRED_CAPABILITIES: tuple[dict[str, Any], ...] = (
    {
        "capability": "api_backed_multi_chapter_loop",
        "label": "API-backed multi-chapter loop",
        "required_for": "Prove the Agent can run real generation through the application path.",
    },
    {
        "capability": "generate_review_recover_revise_continue",
        "label": "Generate-review-recover-revise-continue loop",
        "required_for": "Prove pressure-test findings become recoverable next actions.",
    },
    {
        "capability": "long_memory_activation",
        "label": "Long-memory activation before writing",
        "required_for": "Prove prior memory is selected and future memory is excluded before generation.",
    },
    {
        "capability": "write_after_memory_refresh",
        "label": "Write-after memory refresh",
        "required_for": "Prove generated chapter memory becomes available to the next chapter.",
    },
    {
        "capability": "world_model_recovery",
        "label": "World-model recovery loop",
        "required_for": "Prove Athena proposal queues can block, resolve, and unblock writing.",
    },
    {
        "capability": "observability_snapshot",
        "label": "Health, event, memory tree, and context snapshot",
        "required_for": "Prove longform dogfood can be audited without reading raw notes manually.",
    },
    {
        "capability": "trace_anomaly_threshold_calibration",
        "label": "Trace anomaly threshold calibration",
        "required_for": "Prove Trace anomaly trends expose baseline, configurable thresholds, calibration policy, long-run sample collection projection, safe review projection, approval-gated config maintenance, and false-positive/false-negative guard evidence before long-running dogfood sample execution.",
    },
)

_EVIDENCE_RECORDS: tuple[dict[str, Any], ...] = (
    {
        "evidence_id": "full_agent_native_loop_20260526",
        "title": "Full Agent-Native Dogfood",
        "source_ref": _FULL_AGENT_NATIVE_DOGFOOD,
        "verified_on": "2026-05-26",
        "runtime_path": "api",
        "project_id": "3f85aed4-4f6f-413f-bd1a-03fbe02ea0f4",
        "database": "data/agent_native_dogfood_20260526.db",
        "chapter_indexes": [1, 2, 3],
        "capabilities": [
            "api_backed_multi_chapter_loop",
            "generate_review_recover_revise_continue",
            "world_model_recovery",
            "observability_snapshot",
        ],
        "loop": ["generate", "review", "recover_world_model", "revise", "continue_generation"],
        "metrics": {
            "generated_chapter_count": 3,
            "review_step_count": 3,
            "repair_run_count": 2,
            "event_count": 100,
            "memory_tree_volume_nodes": 1,
            "memory_tree_chapter_nodes": 3,
            "context_usage_ratio": 0.5022,
            "world_model_actionable_items_after_recovery": 0,
        },
        "proven_tools": [
            "generate_chapter",
            "review_chapter_quality",
            "review_chapter_continuity",
            "analyze_chapter_world_model",
            "plan_world_model_proposal_resolution",
            "draft_world_model_proposal_resolution_decisions",
            "repair_longform_maintenance",
            "inspect_agent_health_projection",
            "inspect_agent_context_compression_projection",
            "inspect_agent_memory_tree",
            "inspect_agent_event_projection",
        ],
        "open_findings": [
            "default_sqlite_migration_drift",
            "world_model_profile_preflight_needed",
            "compression_forbidden_term_retry",
            "chapter3_pending_world_model_proposals",
        ],
    },
    {
        "evidence_id": "narrative_memory_activation_20260526",
        "title": "Narrative Memory Activation Dogfood",
        "source_ref": _NARRATIVE_MEMORY_DOGFOOD,
        "verified_on": "2026-05-26",
        "runtime_path": "api_testclient",
        "project_id": "37964dae-c9bf-4fa3-adfc-44cee18ca52a",
        "chapter_indexes": [3, 4],
        "capabilities": [
            "api_backed_multi_chapter_loop",
            "long_memory_activation",
            "write_after_memory_refresh",
            "observability_snapshot",
        ],
        "loop": ["preflight", "activate_memory", "generate", "review", "repair_memory", "activate_next_chapter"],
        "metrics": {
            "generated_chapter_count": 1,
            "review_step_count": 2,
            "activated_source_count": 5,
            "longform_items_selected": 3,
            "retrieval_document_refresh_count": 6,
            "future_leak_count": 0,
        },
        "proven_tools": [
            "preflight_writing",
            "inspect_agent_memory_activation_plan",
            "generate_chapter",
            "review_chapter_quality",
            "review_chapter_continuity",
            "repair_longform_maintenance",
            "inspect_agent_health_projection",
        ],
        "open_findings": ["agent_write_gate_high_risk_residue"],
    },
    {
        "evidence_id": "trace_anomaly_threshold_calibration_20260603",
        "title": "AgentRunDrawer Trace Anomaly Trends Long Run Samples",
        "source_ref": _TRACE_ANOMALY_CALIBRATION_TEST,
        "verified_on": "2026-06-03",
        "runtime_path": "pytest_vitest_docs",
        "project_id": "",
        "chapter_indexes": [],
        "capabilities": ["trace_anomaly_threshold_calibration", "observability_snapshot"],
        "loop": [
            "aggregate_recent_trace_runs",
            "compare_baseline_window",
            "apply_project_configured_thresholds",
            "emit_threshold_signals",
            "project_long_run_sample_collection",
            "project_threshold_review",
            "project_drawer_summary",
        ],
        "metrics": {
            "trace_anomaly_trend_regression_count": 2,
            "threshold_signal_count": 2,
            "threshold_config_projection_count": 1,
            "threshold_config_approval_chain_count": 1,
            "threshold_config_write_gate_count": 1,
            "threshold_config_worker_route_count": 1,
            "threshold_review_projection_count": 1,
            "threshold_review_intent_count": 1,
            "threshold_review_worker_route_count": 1,
            "long_run_sample_collection_projection_count": 1,
            "long_run_sample_collection_intent_count": 1,
            "long_run_sample_collection_worker_route_count": 1,
            "threshold_calibration_projection_count": 1,
            "threshold_policy_projection_count": 1,
            "drawer_projection_regression_count": 1,
            "drawer_threshold_config_projection_count": 1,
            "drawer_calibration_projection_count": 1,
            "drawer_policy_projection_count": 1,
            "false_positive_guard_count": 1,
            "false_negative_guard_count": 1,
        },
        "proven_tools": [
            "inspect_agent_trace_audit",
            "inspect_agent_trace_anomaly_trends",
            "inspect_agent_trace_anomaly_long_run_samples",
            "inspect_agent_trace_anomaly_threshold_review",
            "record_agent_trace_anomaly_threshold_config",
            "prepare_record_agent_trace_anomaly_threshold_config",
            "execute_record_agent_trace_anomaly_threshold_config_with_approval",
            "inspect_agent_write_gate_coverage",
            "plan_dialog_intent_agent_run",
        ],
        "supporting_source_refs": [
            "frontend/src/components/writingAgent/AgentRunDrawer.test.ts",
            "docs/codex-guide/05-progress-tracker.md",
        ],
        "open_findings": ["trace_anomaly_threshold_long_run_sample_execution"],
    },
)


def inspect_agent_dogfood_evidence() -> dict[str, Any]:
    evidence = [_evidence_with_source_status(item) for item in _EVIDENCE_RECORDS]
    ready_evidence = [item for item in evidence if item["status"] == "ready"]
    capability_coverage = _capability_coverage(ready_evidence)
    diagnostics = _diagnostics(evidence, capability_coverage)
    summary = {
        "evidence_count": len(evidence),
        "ready_evidence_count": len(ready_evidence),
        "missing_source_count": sum(1 for item in evidence if item["status"] != "ready"),
        "required_capability_count": len(capability_coverage),
        "covered_capability_count": sum(1 for item in capability_coverage if item["status"] == "covered"),
        "missing_capability_count": sum(1 for item in capability_coverage if item["status"] != "covered"),
        "generated_chapter_count": sum(_metric_int(item, "generated_chapter_count") for item in ready_evidence),
        "review_step_count": sum(_metric_int(item, "review_step_count") for item in ready_evidence),
        "open_finding_count": sum(len(item.get("open_findings") or []) for item in ready_evidence),
    }
    status = "ready" if not diagnostics else "degraded"
    return _json_safe_output(
        {
            "status": status,
            "version": DOGFOOD_EVIDENCE_VERSION,
            "source_refs": [str(item["source_ref"]) for item in evidence],
            "summary": summary,
            "capability_coverage": capability_coverage,
            "evidence": evidence,
            "diagnostics": diagnostics,
            "recommended_next_tools": _recommended_next_tools(status),
            "trace": {
                "source": "inspect_agent_dogfood_evidence",
                "version": DOGFOOD_EVIDENCE_VERSION,
                "mutability": "read",
                "runtime_behavior_changed": False,
            },
        }
    )


def dogfood_evidence_from_run_input(run_input: object) -> dict[str, Any] | None:
    if not isinstance(run_input, dict):
        return None
    planner = run_input.get("planner") if isinstance(run_input.get("planner"), dict) else {}
    trace = planner.get("trace") if isinstance(planner.get("trace"), dict) else {}
    health = trace.get("agent_health_projection") if isinstance(trace.get("agent_health_projection"), dict) else {}
    evidence = health.get("dogfood_evidence") if isinstance(health.get("dogfood_evidence"), dict) else {}
    summary = evidence.get("summary") if isinstance(evidence.get("summary"), dict) else {}
    if not summary:
        return None
    return {
        "source": DOGFOOD_EVIDENCE_RUN_SOURCE,
        "status": str(evidence.get("status") or "unknown"),
        "version": evidence.get("version"),
        "source_refs": _string_list(evidence.get("source_refs")),
        "summary": {
            "evidence_count": _non_negative_int(summary.get("evidence_count")),
            "ready_evidence_count": _non_negative_int(summary.get("ready_evidence_count")),
            "missing_source_count": _non_negative_int(summary.get("missing_source_count")),
            "required_capability_count": _non_negative_int(summary.get("required_capability_count")),
            "covered_capability_count": _non_negative_int(summary.get("covered_capability_count")),
            "missing_capability_count": _non_negative_int(summary.get("missing_capability_count")),
            "generated_chapter_count": _non_negative_int(summary.get("generated_chapter_count")),
            "review_step_count": _non_negative_int(summary.get("review_step_count")),
            "open_finding_count": _non_negative_int(summary.get("open_finding_count")),
        },
        "recommended_next_tools": _string_list(evidence.get("recommended_next_tools")),
    }


def _evidence_with_source_status(record: dict[str, Any]) -> dict[str, Any]:
    source_ref = str(record.get("source_ref") or "")
    output = dict(record)
    output["source_exists"] = _repo_path(source_ref).is_file()
    output["status"] = "ready" if output["source_exists"] else "missing_source"
    return output


def _capability_coverage(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for requirement in _REQUIRED_CAPABILITIES:
        capability = str(requirement["capability"])
        covering = [item for item in evidence if capability in set(item.get("capabilities") or [])]
        source_refs = [str(item.get("source_ref") or "") for item in covering]
        tools: list[str] = []
        for item in covering:
            tools.extend(str(tool) for tool in item.get("proven_tools") or [])
        rows.append(
            {
                **requirement,
                "status": "covered" if covering else "missing",
                "evidence_ids": [str(item.get("evidence_id") or "") for item in covering],
                "source_refs": source_refs,
                "proven_tools": _dedupe(tools),
            }
        )
    return rows


def _diagnostics(evidence: list[dict[str, Any]], coverage: list[dict[str, Any]]) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    missing_sources = [item for item in evidence if item.get("status") != "ready"]
    if missing_sources:
        diagnostics.append(
            {
                "code": "dogfood_source_missing",
                "severity": "warning",
                "message": "Dogfood evidence source files are missing from the current workspace.",
                "missing_source_count": len(missing_sources),
                "source_refs": [str(item.get("source_ref") or "") for item in missing_sources],
            }
        )
    missing_capabilities = [item for item in coverage if item.get("status") != "covered"]
    if missing_capabilities:
        diagnostics.append(
            {
                "code": "dogfood_capability_gap",
                "severity": "warning",
                "message": "Dogfood evidence does not cover every required long-memory Agent capability.",
                "missing_capability_count": len(missing_capabilities),
                "capabilities": [str(item.get("capability") or "") for item in missing_capabilities],
            }
        )
    return diagnostics


def _recommended_next_tools(status: str) -> list[str]:
    tools = ["inspect_agent_health_projection", "inspect_agent_reference_alignment"]
    if status != "ready":
        tools.insert(0, "inspect_agent_dogfood_evidence")
    return _dedupe(tools)


def _metric_int(item: dict[str, Any], key: str) -> int:
    metrics = item.get("metrics") if isinstance(item.get("metrics"), dict) else {}
    try:
        return max(0, int(metrics.get(key) or 0))
    except (TypeError, ValueError):
        return 0


def _repo_path(relative_path: str) -> Path:
    root = Path(__file__).resolve().parents[4]
    return root / relative_path


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = str(value or "").strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result


def _string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value is None:
        return []
    cleaned = str(value).strip()
    return [cleaned] if cleaned else []


def _non_negative_int(value: object) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(parsed, 0)


def _json_safe_output(output: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(output, ensure_ascii=False, default=str))
