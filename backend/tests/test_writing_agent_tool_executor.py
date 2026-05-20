import pytest

from app.models import Project
from app.schemas.writing_agent import WritingAgentToolRequest
from app.services.writing_agent.tool_executor import (
    WritingAgentToolContext,
    execute_writing_agent_tool,
    static_writing_agent_tool_adapter_names,
    unhandled_internal_writing_agent_tool_names,
    writing_agent_tool_adapter_metadata,
)


@pytest.mark.asyncio
async def test_tool_executor_handles_describe_agent_tools(db_session):
    project = Project(name="Executor Tool Plan")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-1"),
        WritingAgentToolRequest(tool_name="describe_agent_tools", params={"chapter_index": 1}),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert "visible_tools" in result.output
    assert "hidden_tools" in result.output


@pytest.mark.asyncio
async def test_tool_executor_handles_planner_tool(db_session):
    project = Project(name="Executor Planner")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="plan_writing_agent_run",
            params={"goal": "创建一个都市悬疑项目", "chapter_index": 1, "intent": "setup_project"},
        ),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert result.output["intent_class"] == "setup_project"
    assert result.output["steps"][0]["tool_name"] == "describe_agent_tools"


@pytest.mark.asyncio
async def test_tool_executor_handles_preflight_with_injected_callback(db_session):
    project = Project(name="Executor Preflight")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, dict]] = []

    def fake_preflight(project_id: str, params: dict):
        calls.append((project_id, params))
        return {"status": "ready", "chapter_index": params["chapter_index"]}

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="preflight_writing", params={"chapter_index": 3}),
        preflight_writing=fake_preflight,
    )

    assert result.handled is True
    assert result.output == {"status": "ready", "chapter_index": 3}
    assert calls == [(project.id, {"chapter_index": 3})]


@pytest.mark.asyncio
async def test_tool_executor_leaves_legacy_generation_tools_unhandled(db_session):
    project = Project(name="Executor Legacy")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="generate_setup", command_args="城市悬疑"),
    )

    assert result.handled is False
    assert result.output is None


def test_tool_executor_static_adapter_names_are_report_or_agent_native_tools():
    names = static_writing_agent_tool_adapter_names()

    assert {
        "describe_agent_tools",
        "plan_writing_agent_run",
        "review_chapter_quality",
        "review_chapter_continuity",
        "plan_chapter_revision",
        "review_world_model_proposals",
        "plan_world_model_proposal_resolution",
        "preview_world_model_proposal_resolution",
        "draft_world_model_proposal_resolution_decisions",
    }.issubset(names)
    assert "generate_setup" not in names
    assert "generate_chapter" not in names


def test_tool_executor_exposes_adapter_metadata_for_trace():
    review_metadata = writing_agent_tool_adapter_metadata("review_chapter_quality")
    preflight_metadata = writing_agent_tool_adapter_metadata("preflight_writing")

    assert review_metadata == {
        "tool_name": "review_chapter_quality",
        "adapter_type": "static",
        "category": "review",
        "mutability": "read",
        "handler_name": "_review_chapter_quality",
    }
    assert preflight_metadata == {
        "tool_name": "preflight_writing",
        "adapter_type": "injected",
        "category": "preflight",
        "mutability": "read",
        "handler_name": "preflight_writing",
    }
    assert writing_agent_tool_adapter_metadata("generate_chapter") is None


def test_tool_executor_lists_unhandled_internal_tools_for_migration_tracking():
    names = unhandled_internal_writing_agent_tool_names()

    assert "analyze_chapter_world_model" in names
    assert "apply_world_model_proposal_resolution" in names
    assert "create_revision_draft" in names
    assert "review_chapter_quality" not in names
    assert "plan_writing_agent_run" not in names
    assert "preflight_writing" not in names


@pytest.mark.asyncio
async def test_tool_executor_dispatches_chapter_report_adapters(db_session, monkeypatch):
    import app.core.chapter_revision_planner as revision_planner

    project = Project(name="Executor Chapter Reports")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, str, int, int | None]] = []

    def fake_quality(db, project_id: str, chapter_index: int):
        calls.append(("quality", project_id, chapter_index, None))
        return {"status": "quality", "chapter_index": chapter_index}

    def fake_continuity(db, project_id: str, chapter_index: int, *, lookback: int):
        calls.append(("continuity", project_id, chapter_index, lookback))
        return {"status": "continuity", "chapter_index": chapter_index, "lookback": lookback}

    def fake_revision(db, project_id: str, chapter_index: int):
        calls.append(("revision", project_id, chapter_index, None))
        return {"status": "revision", "chapter_index": chapter_index}

    monkeypatch.setattr("app.core.chapter_quality_review.review_chapter_quality", fake_quality)
    monkeypatch.setattr("app.core.chapter_continuity_review.review_chapter_continuity", fake_continuity)
    monkeypatch.setattr(revision_planner, "plan_chapter_revision", fake_revision)
    context = WritingAgentToolContext(db=db_session, project_id=project.id)

    quality = await execute_writing_agent_tool(
        context,
        WritingAgentToolRequest(tool_name="review_chapter_quality", params={"chapter_index": 4}),
    )
    continuity = await execute_writing_agent_tool(
        context,
        WritingAgentToolRequest(tool_name="review_chapter_continuity", params={"chapter_index": 5}),
    )
    revision = await execute_writing_agent_tool(
        context,
        WritingAgentToolRequest(tool_name="plan_chapter_revision", params={"chapter_index": 6}),
    )

    assert quality.handled is True
    assert quality.output == {"status": "quality", "chapter_index": 4}
    assert continuity.output == {"status": "continuity", "chapter_index": 5, "lookback": 20}
    assert revision.output == {"status": "revision", "chapter_index": 6}
    assert calls == [
        ("quality", project.id, 4, None),
        ("continuity", project.id, 5, 20),
        ("revision", project.id, 6, None),
    ]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_world_proposal_report_adapters(db_session, monkeypatch):
    import app.core.world_proposal_resolution_plan as resolution_plan

    project = Project(name="Executor World Reports")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, str, object, object]] = []

    def fake_queue_report(db, project_id: str, *, offset: int, limit: int):
        calls.append(("queue", project_id, offset, limit))
        return {"status": "queue", "offset": offset, "limit": limit}

    def fake_resolution_plan(db, project_id: str, *, offset: int, limit: int):
        calls.append(("plan", project_id, offset, limit))
        return {"status": "plan", "offset": offset, "limit": limit}

    def fake_preview(db, project_id: str, decisions: list):
        calls.append(("preview", project_id, list(decisions), None))
        return {"status": "preview", "decision_count": len(decisions)}

    def fake_draft(db, project_id: str, *, limit: int, predicate_policies, include_unclassified: bool):
        calls.append(("draft", project_id, predicate_policies, include_unclassified))
        return {"status": "draft", "limit": limit, "predicate_policies": predicate_policies}

    monkeypatch.setattr("app.core.world_proposal_agent_report.build_world_proposal_agent_report", fake_queue_report)
    monkeypatch.setattr(resolution_plan, "build_world_proposal_resolution_plan", fake_resolution_plan)
    monkeypatch.setattr("app.core.world_proposal_resolution_preview.preview_world_model_proposal_resolution", fake_preview)
    monkeypatch.setattr(
        "app.core.world_proposal_resolution_draft.draft_world_model_proposal_resolution_decisions",
        fake_draft,
    )
    context = WritingAgentToolContext(db=db_session, project_id=project.id)

    queue = await execute_writing_agent_tool(context, WritingAgentToolRequest(tool_name="review_world_model_proposals"))
    plan = await execute_writing_agent_tool(
        context,
        WritingAgentToolRequest(tool_name="plan_world_model_proposal_resolution", params={"offset": "2", "limit": "7"}),
    )
    preview = await execute_writing_agent_tool(
        context,
        WritingAgentToolRequest(tool_name="preview_world_model_proposal_resolution", params={"decisions": "bad"}),
    )
    draft = await execute_writing_agent_tool(
        context,
        WritingAgentToolRequest(
            tool_name="draft_world_model_proposal_resolution_decisions",
            params={"limit": 20, "predicate_policies": ["bad"], "include_unclassified": True},
        ),
    )

    assert queue.handled is True
    assert queue.output == {"status": "queue", "offset": 0, "limit": 50}
    assert plan.output == {"status": "plan", "offset": 2, "limit": 7}
    assert preview.output == {"status": "preview", "decision_count": 0}
    assert draft.output == {"status": "draft", "limit": 20, "predicate_policies": None}
    assert calls == [
        ("queue", project.id, 0, 50),
        ("plan", project.id, 2, 7),
        ("preview", project.id, [], None),
        ("draft", project.id, None, True),
    ]
