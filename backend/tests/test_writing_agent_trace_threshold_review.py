from datetime import datetime, timedelta, timezone

from app.models import AIModelCallTrace, Project, WritingAgentRun, WritingAgentStep
from app.services.writing_agent import agent_trace_audit


def test_inspect_agent_trace_anomaly_threshold_review_builds_prepare_payload_from_run_windows(db_session):
    project = Project(name="Trace Threshold Review")
    db_session.add(project)
    db_session.flush()
    base_time = datetime(2026, 6, 4, 10, 0, tzinfo=timezone.utc)
    recent_runs = [
        WritingAgentRun(
            id=f"run-review-secret-recent-{index}",
            project_id=project.id,
            goal=f"预检第{index}章",
            status="success",
            entrypoint="dialog_auto_plan",
            created_at=base_time + timedelta(minutes=10 + index),
        )
        for index in (1, 2)
    ]
    baseline_runs = [
        WritingAgentRun(
            id=f"run-review-secret-baseline-{index}",
            project_id=project.id,
            goal=f"历史预检第{index}章",
            status="success",
            entrypoint="dialog_auto_plan",
            created_at=base_time + timedelta(minutes=index),
        )
        for index in (1, 2)
    ]
    db_session.add_all(recent_runs + baseline_runs)
    db_session.flush()
    baseline_traces = [
        AIModelCallTrace(
            id=f"trace-review-secret-clear-{index}",
            project_id=project.id,
            trace_type="preflight",
            status="success",
            model="local",
            chapter_index=index,
            context_blocks=[],
        )
        for index in (1, 2)
    ]
    db_session.add_all(baseline_traces)
    db_session.flush()
    db_session.add_all(
        [
            WritingAgentStep(
                id=f"step-review-secret-recent-{index}",
                run_id=run.id,
                project_id=project.id,
                step_index=1,
                tool_name="preflight_writing",
                status="success",
                output={"status": "ready"},
                chapter_index=index,
            )
            for index, run in enumerate(recent_runs, start=1)
        ]
        + [
            WritingAgentStep(
                id=f"step-review-secret-baseline-{index}",
                run_id=run.id,
                project_id=project.id,
                step_index=1,
                tool_name="preflight_writing",
                status="success",
                output={"status": "ready", "trace_id": trace.id},
                trace_id=trace.id,
                chapter_index=index,
            )
            for index, (run, trace) in enumerate(zip(baseline_runs, baseline_traces, strict=True), start=1)
        ]
    )
    db_session.commit()

    output = agent_trace_audit.inspect_agent_trace_anomaly_threshold_review(
        db_session,
        project.id,
        limit=2,
        baseline_limit=2,
    )

    assert output["status"] == "completed"
    assert output["review"]["status"] == "ready_for_manual_review"
    assert output["review"]["policy_decision"] == "keep_current_thresholds"
    assert output["review"]["sample"] == {
        "recent_run_count": 2,
        "baseline_run_count": 2,
        "reviewed_run_count": 4,
        "minimum_review_run_count": 4,
    }
    assert output["review"]["signal_count"] == 1
    assert output["threshold_candidate"] == {
        "affected_run_rate_delta": 0.5,
        "critical_issue_rate_delta": 0.25,
    }
    assert output["recommended_next_tools"] == [
        "prepare_record_agent_trace_anomaly_threshold_config",
        "inspect_agent_dogfood_evidence",
    ]
    assert output["recommended_next_tool_calls"] == [
        {
            "tool_name": "prepare_record_agent_trace_anomaly_threshold_config",
            "params": {
                "affected_run_rate_delta": 0.5,
                "critical_issue_rate_delta": 0.25,
                "source": "trace_anomaly_threshold_review",
                "reviewed_run_count": 4,
                "reason": "manual_review_from_trace_anomaly_threshold_review",
            },
        }
    ]
    assert output["side_effects"] == {"executed": [], "skipped": ["record_agent_trace_anomaly_threshold_config"]}
    assert output["trace"] == {
        "source": "inspect_agent_trace_anomaly_threshold_review",
        "version": "phase242.agent_trace_anomaly_threshold_review.v1",
        "mutability": "read",
    }
    assert "run-review-secret" not in str(output)
    assert "trace-review-secret" not in str(output)
    assert "step-review-secret" not in str(output)


def test_inspect_agent_trace_anomaly_threshold_review_collects_more_samples_when_windows_are_small(db_session):
    project = Project(name="Trace Threshold Review Empty")
    db_session.add(project)
    db_session.commit()

    output = agent_trace_audit.inspect_agent_trace_anomaly_threshold_review(
        db_session,
        project.id,
        limit=2,
        baseline_limit=2,
    )

    assert output["status"] == "completed"
    assert output["review"]["status"] == "collecting_samples"
    assert output["review"]["sample"]["reviewed_run_count"] == 0
    assert output["recommended_next_tools"] == ["inspect_agent_trace_anomaly_trends", "inspect_agent_dogfood_evidence"]
    assert output["recommended_next_tool_calls"] == []
    assert output["side_effects"] == {"executed": [], "skipped": []}
