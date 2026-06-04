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
        "memory_tree_quality_real_longform_validation",
        "memory_tree_summary_approval_recheck",
        "memory_tree_llm_summary_plan",
        "memory_tree_llm_summary_candidate",
        "memory_tree_llm_candidate_materialization",
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
    memory_tree_quality = evidence_by_id["memory_tree_quality_projection_20260604"]
    assert memory_tree_quality["runtime_path"] == "sqlite_readonly_dogfood"
    assert memory_tree_quality["metrics"] == {
        "memory_tree_quality_chapter_nodes": 3,
        "memory_tree_quality_summary_backed_chapter_nodes": 0,
        "memory_tree_quality_summary_backed_chapter_ratio": 0.0,
        "memory_tree_quality_semantic_probe_matched_count": 0,
        "memory_tree_quality_diagnostic_count": 2,
    }
    assert memory_tree_quality["open_findings"] == [
        "memory_tree_summary_gap",
        "memory_tree_semantic_probe_miss",
    ]
    quality_coverage = {
        item["capability"]: item for item in output["capability_coverage"]
    }["memory_tree_quality_real_longform_validation"]
    assert quality_coverage["status"] == "covered"
    assert quality_coverage["evidence_ids"] == [
        "memory_tree_quality_projection_20260604",
        "memory_tree_summary_approval_recheck_20260604",
        "memory_tree_llm_summary_plan_20260604",
        "memory_tree_llm_summary_candidate_20260604",
        "memory_tree_llm_candidate_materialization_20260604",
    ]
    assert "inspect_agent_memory_tree_quality" in quality_coverage["proven_tools"]
    memory_tree_summary = evidence_by_id["memory_tree_summary_approval_recheck_20260604"]
    assert memory_tree_summary["runtime_path"] == "sqlite_temp_copy_dogfood"
    assert memory_tree_summary["metrics"] == {
        "memory_tree_summary_before_summary_backed_chapter_nodes": 0,
        "memory_tree_summary_before_summary_backed_chapter_ratio": 0.0,
        "memory_tree_summary_before_semantic_probe_matched_count": 0,
        "memory_tree_summary_materialization_created_nodes": 4,
        "memory_tree_summary_materialization_updated_nodes": 0,
        "memory_tree_summary_materialization_volume_nodes": 1,
        "memory_tree_summary_materialization_chapter_nodes": 3,
        "memory_tree_summary_approval_verified_count": 1,
        "memory_tree_summary_after_summary_backed_chapter_nodes": 3,
        "memory_tree_summary_after_summary_backed_chapter_ratio": 1.0,
        "memory_tree_summary_after_semantic_probe_matched_count": 1,
        "memory_tree_summary_after_diagnostic_count": 0,
    }
    assert memory_tree_summary["open_findings"] == []
    summary_coverage = {
        item["capability"]: item for item in output["capability_coverage"]
    }["memory_tree_summary_approval_recheck"]
    assert summary_coverage["status"] == "covered"
    assert summary_coverage["evidence_ids"] == ["memory_tree_summary_approval_recheck_20260604"]
    assert "execute_record_agent_memory_tree_summaries_with_approval" in summary_coverage["proven_tools"]
    llm_summary_plan = evidence_by_id["memory_tree_llm_summary_plan_20260604"]
    assert llm_summary_plan["runtime_path"] == "sqlite_readonly_dogfood"
    assert llm_summary_plan["metrics"] == {
        "memory_tree_llm_summary_plan_source_count": 3,
        "memory_tree_llm_summary_plan_source_chars": 848,
        "memory_tree_llm_summary_plan_trace_required_count": 1,
        "memory_tree_llm_summary_plan_precheck_diagnostic_count": 2,
        "memory_tree_llm_summary_plan_semantic_probe_matched_count": 0,
        "memory_tree_llm_summary_plan_side_effect_count": 0,
    }
    assert llm_summary_plan["open_findings"] == []
    llm_summary_plan_coverage = {
        item["capability"]: item for item in output["capability_coverage"]
    }["memory_tree_llm_summary_plan"]
    assert llm_summary_plan_coverage["status"] == "covered"
    assert llm_summary_plan_coverage["evidence_ids"] == ["memory_tree_llm_summary_plan_20260604"]
    assert "build_agent_memory_tree_llm_summary_plan" in llm_summary_plan_coverage["proven_tools"]
    llm_summary_candidate = evidence_by_id["memory_tree_llm_summary_candidate_20260604"]
    assert llm_summary_candidate["runtime_path"] == "sqlite_temp_copy_fake_model_trace"
    assert llm_summary_candidate["metrics"] == {
        "memory_tree_llm_summary_candidate_source_count": 3,
        "memory_tree_llm_summary_candidate_source_chars": 848,
        "memory_tree_llm_summary_candidate_trace_success_count": 1,
        "memory_tree_llm_summary_candidate_context_block_count": 3,
        "memory_tree_llm_summary_candidate_inspection_count": 1,
        "memory_tree_llm_summary_candidate_trace_match_count": 1,
        "memory_tree_llm_summary_candidate_summary_chars": 49,
        "memory_tree_llm_summary_candidate_open_question_count": 1,
        "memory_tree_llm_summary_candidate_side_effect_count": 1,
        "memory_tree_llm_summary_candidate_memory_write_count": 0,
    }
    assert llm_summary_candidate["open_findings"] == ["fake_model_response_not_external_model_quality"]
    llm_summary_candidate_coverage = {
        item["capability"]: item for item in output["capability_coverage"]
    }["memory_tree_llm_summary_candidate"]
    assert llm_summary_candidate_coverage["status"] == "covered"
    assert llm_summary_candidate_coverage["evidence_ids"] == [
        "memory_tree_llm_summary_candidate_20260604",
        "memory_tree_llm_candidate_materialization_20260604",
    ]
    assert "summarize_agent_memory_tree_llm_candidate" in llm_summary_candidate_coverage["proven_tools"]
    assert "inspect_agent_memory_tree_llm_candidates" in llm_summary_candidate_coverage["proven_tools"]
    llm_candidate_materialization = evidence_by_id["memory_tree_llm_candidate_materialization_20260604"]
    assert llm_candidate_materialization["runtime_path"] == "sqlite_temp_copy_fake_model_approval_execute"
    assert llm_candidate_materialization["metrics"] == {
        "memory_tree_llm_candidate_materialization_source_count": 3,
        "memory_tree_llm_candidate_materialization_source_chars": 848,
        "memory_tree_llm_candidate_materialization_trace_success_count": 1,
        "memory_tree_llm_candidate_materialization_prepare_count": 1,
        "memory_tree_llm_candidate_materialization_execute_success_count": 1,
        "memory_tree_llm_candidate_materialization_approval_verified_count": 1,
        "memory_tree_llm_candidate_materialization_created_nodes": 1,
        "memory_tree_llm_candidate_materialization_updated_nodes": 0,
        "memory_tree_llm_candidate_materialization_before_memory_count": 0,
        "memory_tree_llm_candidate_materialization_after_memory_count": 1,
        "memory_tree_llm_candidate_materialization_after_summary_backed_chapter_nodes": 1,
        "memory_tree_llm_candidate_materialization_after_summary_backed_chapter_ratio": 0.3333,
        "memory_tree_llm_candidate_materialization_semantic_probe_matched_count": 1,
        "memory_tree_llm_candidate_materialization_after_diagnostic_count": 1,
    }
    assert llm_candidate_materialization["open_findings"] == [
        "fake_model_response_not_external_model_quality",
        "remaining_chapter_summary_gap_after_single_candidate_materialization",
    ]
    llm_candidate_materialization_coverage = {
        item["capability"]: item for item in output["capability_coverage"]
    }["memory_tree_llm_candidate_materialization"]
    assert llm_candidate_materialization_coverage["status"] == "covered"
    assert llm_candidate_materialization_coverage["evidence_ids"] == [
        "memory_tree_llm_candidate_materialization_20260604"
    ]
    assert (
        "execute_record_agent_memory_tree_llm_candidate_summary_with_approval"
        in llm_candidate_materialization_coverage["proven_tools"]
    )
    assert "inspect_agent_health_projection" in output["recommended_next_tools"]
    assert output["trace"]["runtime_behavior_changed"] is False
