from app.models import ChapterContent, Project
from app.services.writing_agent.agent_memory_route import inspect_agent_memory_route


def test_inspect_agent_memory_route_blocks_when_longform_memory_is_missing(db_session):
    project = Project(name="Memory Route Missing Longform")
    db_session.add(project)
    db_session.commit()
    db_session.add(
        ChapterContent(
            project_id=project.id,
            chapter_index=1,
            title="第1章",
            content="雾锁灯塔。" * 100,
            word_count=500,
            status="generated",
        )
    )
    db_session.commit()

    output = inspect_agent_memory_route(
        db_session,
        project.id,
        chapter_index=2,
        query="灯塔区集体失忆",
        include_context_summary=False,
    )

    assert output["status"] == "completed"
    assert output["route"]["status"] == "blocked"
    assert output["route"]["reason"] == "longform_memory_needs_maintenance"
    assert output["route"]["recommended_tools"] == ["repair_longform_maintenance"]
    assert output["longform_maintenance"]["ready_for_writing"] is False
    assert output["longform_maintenance"]["issue_count"] > 0
    assert "longform_memory_needs_maintenance" in {item["code"] for item in output["diagnostics"]}


def test_inspect_agent_memory_route_is_ready_for_empty_project(db_session):
    project = Project(name="Memory Route Empty Project")
    db_session.add(project)
    db_session.commit()

    output = inspect_agent_memory_route(
        db_session,
        project.id,
        chapter_index=1,
        include_context_summary=False,
    )

    assert output["status"] == "completed"
    assert output["route"]["status"] == "ready"
    assert output["route"]["can_use_longform_context"] is True
    assert output["route"]["recommended_tools"] == ["summarize_longform_context", "preflight_writing"]
    assert output["longform_memory"]["chapter_count"] == 0
    assert output["retrieval"]["total_documents"] == 0
