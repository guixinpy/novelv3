from datetime import datetime, timedelta, timezone

from app.models import Project, WritingAgentRun, WritingAgentStep
from app.services.writing_agent import agent_trace_audit


def test_inspect_agent_trace_anomaly_long_run_samples_recommends_review_when_window_is_ready(db_session):
    project = Project(name="Trace Long Run Samples")
    db_session.add(project)
    db_session.flush()
    base_time = datetime(2026, 6, 4, 13, 0, tzinfo=timezone.utc)
    statuses = ["success", "blocked", "failed", "success"]
    runs = [
        WritingAgentRun(
            id=f"run-long-secret-{index}",
            project_id=project.id,
            goal=f"长跑第{index}轮",
            status=status,
            entrypoint="dialog_auto_plan",
            created_at=base_time + timedelta(minutes=index),
        )
        for index, status in enumerate(statuses, start=1)
    ]
    db_session.add_all(runs)
    db_session.flush()
    db_session.add_all(
        [
            WritingAgentStep(
                id=f"step-long-secret-{index}",
                run_id=run.id,
                project_id=project.id,
                step_index=1,
                tool_name="preflight_writing",
                status="success",
                output={"status": "ready"},
                chapter_index=4,
            )
            for index, run in enumerate(runs, start=1)
        ]
    )
    db_session.commit()

    output = agent_trace_audit.inspect_agent_trace_anomaly_long_run_samples(
        db_session,
        project.id,
        limit=6,
        chapter_index=4,
    )

    assert output["status"] == "completed"
    assert output["filters"] == {
        "limit": 6,
        "chapter_index": 4,
        "minimum_review_run_count": 4,
    }
    assert output["sample_collection"] == {
        "status": "ready_for_threshold_review",
        "candidate_run_count": 4,
        "minimum_review_run_count": 4,
        "missing_run_count": 0,
        "step_count": 4,
        "status_counts": {"blocked": 1, "failed": 1, "success": 2},
        "entrypoint_counts": {"dialog_auto_plan": 4},
        "chapter_indexes": [4],
    }
    assert output["review_window"] == {"limit": 2, "baseline_limit": 2, "chapter_index": 4}
    assert output["recommended_next_tools"] == [
        "inspect_agent_trace_anomaly_threshold_review",
        "inspect_agent_dogfood_evidence",
    ]
    assert output["recommended_next_tool_calls"] == [
        {
            "tool_name": "inspect_agent_trace_anomaly_threshold_review",
            "params": {"limit": 2, "baseline_limit": 2, "chapter_index": 4},
        }
    ]
    assert output["side_effects"] == {"executed": [], "skipped": []}
    assert output["trace"] == {
        "source": "inspect_agent_trace_anomaly_long_run_samples",
        "version": "phase243.agent_trace_anomaly_long_run_samples.v1",
        "mutability": "read",
    }
    assert "run-long-secret" not in str(output)
    assert "step-long-secret" not in str(output)


def test_inspect_agent_trace_anomaly_long_run_samples_reports_collection_gap(db_session):
    project = Project(name="Trace Long Run Samples Empty")
    db_session.add(project)
    db_session.commit()

    output = agent_trace_audit.inspect_agent_trace_anomaly_long_run_samples(db_session, project.id, limit=6)

    assert output["status"] == "completed"
    assert output["sample_collection"]["status"] == "collecting_samples"
    assert output["sample_collection"]["candidate_run_count"] == 0
    assert output["sample_collection"]["missing_run_count"] == 4
    assert output["review_window"] == {}
    assert output["recommended_next_tools"] == ["plan_writing_agent_run", "inspect_agent_dogfood_evidence"]
    assert output["recommended_next_tool_calls"] == []
    assert output["side_effects"] == {"executed": [], "skipped": []}
