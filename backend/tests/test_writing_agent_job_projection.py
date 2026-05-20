from app.models import BackgroundTask, Project, WritingAgentRun
from app.services.writing_agent.agent_job_projection import inspect_agent_job_projection


def test_inspect_agent_job_projection_reports_empty_queue(db_session):
    project = Project(name="Agent Job Empty")
    db_session.add(project)
    db_session.commit()

    output = inspect_agent_job_projection(db_session, project.id)

    assert output["status"] == "completed"
    assert output["queue"]["depth"] == 0
    assert output["summary"]["total"] == 0
    assert output["tasks"] == []
    assert output["selected_task"] is None
    assert output["recommended_tools"] == ["plan_longform_chapter_batch"]


def test_inspect_agent_job_projection_exposes_active_control_plane_and_progress(db_session):
    project = Project(name="Agent Job Active")
    db_session.add(project)
    db_session.flush()
    task = BackgroundTask(
        project_id=project.id,
        task_type="generate_chapter",
        status="running",
        payload={
            "chapter_index": 3,
            "chapter_range": {"start": 3, "end": 5},
            "control_plane": {
                "version": "phase71.writing_task_control_plane.v1",
                "source": "writing_start",
                "entrypoint": "continuous_writing_generate",
                "tool_name": "generate_chapter",
                "chapter_index": 3,
            },
        },
        result={
            "progress": {
                "completed_chapter_indexes": [3],
                "next_chapter_index": 4,
                "completed_count": 1,
                "total_count": 3,
                "can_resume": True,
            }
        },
    )
    db_session.add(task)
    db_session.flush()
    db_session.add(
        WritingAgentRun(
            project_id=project.id,
            goal="生成第3-5章",
            status="running",
            entrypoint="writing_start",
            background_task_id=task.id,
            input={"task_id": task.id},
        )
    )
    db_session.commit()

    output = inspect_agent_job_projection(db_session, project.id, task_id=task.id)

    selected = output["selected_task"]
    assert output["status"] == "completed"
    assert output["queue"]["active"] == 1
    assert selected["id"] == task.id
    assert selected["control_plane"]["source"] == "writing_start"
    assert selected["chapter_range"] == {"start": 3, "end": 5}
    assert selected["progress"]["next_chapter_index"] == 4
    assert selected["resume"]["can_resume"] is True
    assert selected["resume"]["pending_chapter_indexes"] == [4, 5]
    assert selected["agent_runs"][0]["entrypoint"] == "writing_start"
    assert "inspect_agent_trace_audit" in output["recommended_tools"]


def test_inspect_agent_job_projection_exposes_failed_recovery_hint(db_session):
    project = Project(name="Agent Job Failed")
    db_session.add(project)
    db_session.flush()
    task = BackgroundTask(
        project_id=project.id,
        task_type="generate_chapter",
        status="failed",
        payload={"chapter_index": 2, "chapter_range": {"start": 2, "end": 4}},
        result={"progress": {"next_chapter_index": 3, "completed_chapter_indexes": [2], "can_resume": True}},
        error="DeepSeek timeout " * 50,
    )
    db_session.add(task)
    db_session.commit()

    output = inspect_agent_job_projection(db_session, project.id, task_id=task.id)

    selected = output["selected_task"]
    assert selected["status"] == "failed"
    assert selected["error_preview"].startswith("DeepSeek timeout")
    assert len(selected["error_preview"]) <= 240
    assert selected["recovery"]["can_retry"] is True
    assert selected["recovery"]["recommended_tools"] == ["inspect_agent_trace_audit", "plan_recovery_tools"]
    assert output["recommended_tools"] == ["inspect_agent_trace_audit", "plan_recovery_tools"]
