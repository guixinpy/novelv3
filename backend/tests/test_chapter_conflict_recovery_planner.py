from app.models import BackgroundTask, Project
from app.services.writing_agent.chapter_conflict_recovery_planner import plan_chapter_conflict_recovery


def test_plan_chapter_conflict_recovery_recommends_generation_when_target_available(db_session):
    project = Project(name="Conflict Recovery Available")
    db_session.add(project)
    db_session.commit()

    output = plan_chapter_conflict_recovery(db_session, project.id, chapter_index=2)

    assert output["status"] == "completed"
    assert output["version"] == "phase141.chapter_conflict_recovery.v1"
    assert output["chapter_index"] == 2
    assert output["conflict"]["status"] == "available"
    assert output["recovery"] == {
        "status": "none",
        "reason_code": "chapter_target_available",
        "next_tool": "generate_chapter",
        "next_params": {"chapter_index": 2},
        "should_continue_current_run": True,
        "requires_user_input": False,
    }
    assert output["tools"][0]["tool_name"] == "generate_chapter"
    assert output["tools"][0]["params"] == {"chapter_index": 2}


def test_plan_chapter_conflict_recovery_recommends_inspection_for_reserved_running_task(db_session):
    project = Project(name="Conflict Recovery Reserved")
    db_session.add(project)
    db_session.flush()
    task = BackgroundTask(
        project_id=project.id,
        task_type="generate_chapter_range",
        status="running",
        payload={"chapter_range": {"start": 2, "end": 4}},
    )
    db_session.add(task)
    db_session.commit()

    output = plan_chapter_conflict_recovery(db_session, project.id, chapter_index=3)

    assert output["status"] == "completed"
    assert output["chapter_index"] == 3
    assert output["conflict"]["status"] == "reserved"
    assert output["conflict"]["active_task_count"] == 1
    assert output["recovery"] == {
        "status": "recommended",
        "reason_code": "chapter_target_reserved",
        "next_tool": "inspect_agent_job_projection",
        "next_params": {"task_id": task.id},
        "should_continue_current_run": False,
        "requires_user_input": False,
    }
    assert [tool["tool_name"] for tool in output["tools"]] == [
        "inspect_agent_job_projection",
        "inspect_agent_job_projection",
    ]
    assert output["tools"][0]["params"] == {"chapter_index": 3}
    assert output["tools"][1]["params"] == {"task_id": task.id}
    assert output["recovery_options"][0] == {
        "action": "inspect_occupying_task",
        "tool_name": "inspect_agent_job_projection",
        "params": {"task_id": task.id},
        "safe_auto_execute": True,
    }
    assert output["recovery_options"][1]["action"] == "wait_for_occupying_task"
