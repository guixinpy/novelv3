from datetime import UTC, datetime

from app.models import BackgroundTask, Project, WritingAgentRun, WritingAgentStep
from app.services.writing_agent.agent_event_projection import inspect_agent_event_projection
from app.services.writing_agent.agent_job_projection import inspect_agent_job_projection


def test_inspect_agent_event_projection_projects_tool_events_from_steps_and_tasks(db_session):
    now = datetime(2026, 5, 26, 12, 0, tzinfo=UTC)
    project = Project(name="Agent Event Projection")
    db_session.add(project)
    db_session.flush()
    task = BackgroundTask(
        project_id=project.id,
        task_type="generate_chapter_range",
        status="running",
        payload={"chapter_range": {"start": 1, "end": 2}},
        started_at=now,
    )
    db_session.add(task)
    db_session.flush()
    run = WritingAgentRun(
        project_id=project.id,
        goal="generate 1-2",
        status="blocked",
        entrypoint="writing_start",
        background_task_id=task.id,
        started_at=now,
        input={"task_id": task.id},
    )
    db_session.add(run)
    db_session.flush()
    db_session.add_all(
        [
            WritingAgentStep(
                project_id=project.id,
                run_id=run.id,
                step_index=1,
                tool_name="generate_chapter",
                status="success",
                background_task_id=task.id,
                chapter_index=1,
                started_at=now,
                finished_at=now,
                output={"status": "completed", "chapter_index": 1},
            ),
            WritingAgentStep(
                project_id=project.id,
                run_id=run.id,
                step_index=2,
                tool_name="review_chapter_quality",
                status="failed",
                background_task_id=task.id,
                chapter_index=1,
                started_at=now,
                finished_at=now,
                output={"status": "failed", "error": "quality model timeout"},
                error="quality model timeout",
            ),
        ]
    )
    db_session.commit()

    output = inspect_agent_event_projection(db_session, project.id, task_id=task.id, run_id=run.id)

    event_types = {event["event_type"] for event in output["events"]}
    assert output["status"] == "completed"
    assert output["boundary"]["decision"] == "projection_only"
    assert {"task_created", "task_started", "run_started", "tool_started", "tool_completed", "tool_error"}.issubset(
        event_types
    )
    assert output["summary"]["by_event_type"]["tool_started"] == 2
    assert output["summary"]["by_event_type"]["tool_completed"] == 1
    assert output["summary"]["by_event_type"]["tool_error"] == 1
    assert output["trace"]["selected_sources"] == ["background_tasks", "writing_agent_runs", "writing_agent_steps"]

    tool_error = next(event for event in output["events"] if event["event_type"] == "tool_error")
    assert tool_error["tool_name"] == "review_chapter_quality"
    assert tool_error["status"] == "failed"
    assert tool_error["task_id"] == task.id
    assert tool_error["run_id"] == run.id
    assert tool_error["error_preview"] == "quality model timeout"


def test_agent_job_projection_includes_event_projection_summary(db_session):
    project = Project(name="Agent Job Event Summary")
    db_session.add(project)
    db_session.flush()
    task = BackgroundTask(
        project_id=project.id,
        task_type="generate_chapter",
        status="completed",
        payload={"chapter_index": 3},
    )
    db_session.add(task)
    db_session.flush()
    run = WritingAgentRun(
        project_id=project.id,
        goal="generate 3",
        status="success",
        background_task_id=task.id,
        input={"task_id": task.id},
    )
    db_session.add(run)
    db_session.flush()
    db_session.add(
        WritingAgentStep(
            project_id=project.id,
            run_id=run.id,
            step_index=1,
            tool_name="generate_chapter",
            status="success",
            background_task_id=task.id,
            chapter_index=3,
            output={"status": "completed"},
        )
    )
    db_session.commit()

    output = inspect_agent_job_projection(db_session, project.id, task_id=task.id)

    event_projection = output["selected_task"]["event_projection"]
    assert event_projection["status"] == "completed"
    assert event_projection["summary"]["by_event_type"]["tool_completed"] == 1
    assert event_projection["recommended_tools"] == ["inspect_agent_event_projection"]
