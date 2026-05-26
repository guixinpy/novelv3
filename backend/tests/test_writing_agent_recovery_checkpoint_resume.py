from app.models import BackgroundTask, ChapterContent, Project, WritingAgentRun, WritingAgentStep
from app.services.writing_agent.batch_enqueue import BATCH_TASK_TYPE
from app.services.writing_agent.recovery_planner import build_checkpoint_resume_preview
from app.services.writing_agent.recovery_policy import CHECKPOINT_RESUME_PREVIEW_VERSION


def test_checkpoint_resume_preview_skips_completed_and_resumes_blocked_chapter(db_session):
    project = Project(name="Checkpoint Resume")
    db_session.add(project)
    db_session.flush()

    task = BackgroundTask(
        project_id=project.id,
        task_type=BATCH_TASK_TYPE,
        status="pending",
        payload={
            "chapter_range": {"start": 1, "end": 5},
            "batch": {"chapter_indexes": [1, 2, 3, 4, 5]},
        },
        result={
            "progress": {
                "chapter_range": {"start": 1, "end": 5},
                "completed_chapter_indexes": [1, 2, 3],
                "next_chapter_index": 4,
                "completed_count": 3,
                "total_count": 5,
                "can_resume": True,
            },
            "execution_checkpoints": [
                {"checkpoint_type": "chapter_generation", "status": "completed", "chapter_index": 1},
                {"checkpoint_type": "chapter_generation", "status": "completed", "chapter_index": 2},
                {"checkpoint_type": "chapter_generation", "status": "completed", "chapter_index": 3},
                {
                    "checkpoint_type": "chapter_generation",
                    "status": "failed",
                    "chapter_index": 4,
                    "error": "generate_chapter_failed",
                },
            ],
        },
    )
    db_session.add(task)
    db_session.flush()

    for chapter_index in (1, 2, 3):
        db_session.add(
            ChapterContent(
                project_id=project.id,
                chapter_index=chapter_index,
                title=f"Chapter {chapter_index}",
                content=f"Generated content {chapter_index}",
                status="completed",
            )
        )

    run = WritingAgentRun(
        project_id=project.id,
        goal="generate 1-5",
        status="blocked",
        entrypoint="writing_start",
        background_task_id=task.id,
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
                tool_name="execute_longform_chapter_batch",
                status="success",
                background_task_id=task.id,
                chapter_index=1,
                output={"status": "completed", "chapter_index": 1, "task": {"id": task.id}},
            ),
            WritingAgentStep(
                project_id=project.id,
                run_id=run.id,
                step_index=2,
                tool_name="execute_longform_chapter_batch",
                status="success",
                background_task_id=task.id,
                chapter_index=2,
                output={"status": "completed", "chapter_index": 2, "task": {"id": task.id}},
            ),
            WritingAgentStep(
                project_id=project.id,
                run_id=run.id,
                step_index=3,
                tool_name="execute_longform_chapter_batch",
                status="success",
                background_task_id=task.id,
                chapter_index=3,
                output={"status": "completed", "chapter_index": 3, "task": {"id": task.id}},
            ),
            WritingAgentStep(
                project_id=project.id,
                run_id=run.id,
                step_index=4,
                tool_name="execute_longform_chapter_batch",
                status="blocked",
                background_task_id=task.id,
                chapter_index=4,
                output={
                    "status": "blocked",
                    "chapter_index": 4,
                    "reason": "generate_chapter_failed",
                    "task": {"id": task.id},
                },
            ),
        ]
    )
    db_session.commit()

    preview = build_checkpoint_resume_preview(db_session, project.id, task_id=task.id, run_id=run.id)

    assert preview["status"] == "ready"
    assert preview["preview_version"] == CHECKPOINT_RESUME_PREVIEW_VERSION
    assert preview["chapter_range"] == {"start": 1, "end": 5}
    assert preview["completed_chapter_indexes"] == [1, 2, 3]
    assert preview["skipped_chapter_indexes"] == [1, 2, 3]
    assert preview["blocked_chapter_indexes"] == [4]
    assert preview["pending_chapter_indexes"] == [4, 5]
    assert preview["resume"]["next_chapter_index"] == 4
    assert preview["resume"]["resume_range"] == {"start": 4, "end": 5}
    assert preview["resume"]["skip_completed"] is True
    assert preview["checkpoint_evidence"]["chapter_records"] == [1, 2, 3]
    assert preview["checkpoint_evidence"]["background_task_progress"]["next_chapter_index"] == 4
    assert preview["checkpoint_evidence"]["writing_agent_steps"][-1]["status"] == "blocked"
