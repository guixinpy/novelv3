from app.services.writing_agent.dogfood_evidence_projection import (
    DOGFOOD_EVIDENCE_VERSION,
    inspect_agent_dogfood_evidence,
)


def test_inspect_agent_dogfood_evidence_surfaces_api_loop_and_memory_activation():
    output = inspect_agent_dogfood_evidence()

    assert output["version"] == DOGFOOD_EVIDENCE_VERSION
    assert output["status"] == "ready"
    assert output["summary"]["evidence_count"] >= 2
    assert output["summary"]["missing_source_count"] == 0
    assert output["summary"]["generated_chapter_count"] >= 4
    assert output["summary"]["required_capability_count"] == len(output["capability_coverage"])
    assert output["summary"]["covered_capability_count"] == output["summary"]["required_capability_count"]
    assert {
        "api_backed_multi_chapter_loop",
        "generate_review_recover_revise_continue",
        "long_memory_activation",
        "world_model_recovery",
        "observability_snapshot",
        "trace_anomaly_threshold_calibration",
        "trace_anomaly_long_run_sample_execution",
    }.issubset({item["capability"] for item in output["capability_coverage"]})
    evidence_by_id = {item["evidence_id"]: item for item in output["evidence"]}
    full_loop = evidence_by_id["full_agent_native_loop_20260526"]
    assert full_loop["runtime_path"] == "api"
    assert full_loop["metrics"]["generated_chapter_count"] == 3
    assert full_loop["metrics"]["event_count"] == 100
    assert "inspect_agent_event_projection" in full_loop["proven_tools"]
    memory_activation = evidence_by_id["narrative_memory_activation_20260526"]
    assert memory_activation["metrics"]["retrieval_document_refresh_count"] == 6
    assert "inspect_agent_memory_activation_plan" in memory_activation["proven_tools"]
    trace_calibration = evidence_by_id["trace_anomaly_threshold_calibration_20260603"]
    assert trace_calibration["runtime_path"] == "pytest_vitest_docs"
    assert trace_calibration["metrics"] == {
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
    }
    assert trace_calibration["open_findings"] == []
    assert "inspect_agent_trace_anomaly_trends" in trace_calibration["proven_tools"]
    assert "inspect_agent_trace_anomaly_long_run_samples" in trace_calibration["proven_tools"]
    assert "inspect_agent_trace_anomaly_threshold_review" in trace_calibration["proven_tools"]
    assert "prepare_record_agent_trace_anomaly_threshold_config" in trace_calibration["proven_tools"]
    assert "execute_record_agent_trace_anomaly_threshold_config_with_approval" in trace_calibration["proven_tools"]
    assert "Long Run Samples" in trace_calibration["title"]
    calibration_coverage = {
        item["capability"]: item for item in output["capability_coverage"]
    }["trace_anomaly_threshold_calibration"]
    assert calibration_coverage["status"] == "covered"
    assert calibration_coverage["evidence_ids"] == ["trace_anomaly_threshold_calibration_20260603"]
    assert "inspect_agent_trace_anomaly_trends" in calibration_coverage["proven_tools"]
    long_run_execution = evidence_by_id["trace_anomaly_long_run_samples_20260604"]
    assert long_run_execution["runtime_path"] == "sqlite_readonly_dogfood"
    assert long_run_execution["source_exists"] is True
    assert long_run_execution["metrics"] == {
        "long_run_sample_execution_run_count": 14,
        "long_run_sample_execution_step_count": 31,
        "long_run_sample_execution_dogfood_run_count": 12,
        "long_run_sample_execution_blocked_run_count": 2,
        "long_run_sample_execution_success_run_count": 12,
        "long_run_sample_execution_chapter_count": 3,
    }
    assert long_run_execution["open_findings"] == []
    execution_coverage = {
        item["capability"]: item for item in output["capability_coverage"]
    }["trace_anomaly_long_run_sample_execution"]
    assert execution_coverage["status"] == "covered"
    assert execution_coverage["evidence_ids"] == ["trace_anomaly_long_run_samples_20260604"]
    assert "inspect_agent_trace_anomaly_long_run_samples" in execution_coverage["proven_tools"]
    assert "inspect_agent_health_projection" in output["recommended_next_tools"]
    assert output["trace"]["runtime_behavior_changed"] is False
