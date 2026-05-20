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
        "plan_longform_chapter_batch",
        "enqueue_longform_chapter_batch",
        "inspect_longform_chapter_batch",
        "execute_longform_chapter_batch_preflight",
        "prepare_longform_chapter_batch_execution",
        "execute_longform_chapter_batch",
        "review_longform_chapter_batch_execution",
        "route_longform_chapter_batch_after_review",
        "review_chapter_quality",
        "review_chapter_continuity",
        "plan_chapter_revision",
        "repair_longform_maintenance",
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
    assert "backfill_outline_gaps" not in names
    assert "repair_longform_maintenance" not in names
    assert "review_chapter_quality" not in names
    assert "plan_writing_agent_run" not in names
    assert "plan_longform_chapter_batch" not in names
    assert "enqueue_longform_chapter_batch" not in names
    assert "inspect_longform_chapter_batch" not in names
    assert "execute_longform_chapter_batch_preflight" not in names
    assert "prepare_longform_chapter_batch_execution" not in names
    assert "execute_longform_chapter_batch" not in names
    assert "review_longform_chapter_batch_execution" not in names
    assert "route_longform_chapter_batch_after_review" not in names
    assert "preflight_writing" not in names


def test_tool_executor_exposes_backfill_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("backfill_outline_gaps")

    assert metadata == {
        "tool_name": "backfill_outline_gaps",
        "adapter_type": "static",
        "category": "maintenance",
        "mutability": "write",
        "handler_name": "_backfill_outline_gaps",
    }


def test_tool_executor_exposes_repair_longform_maintenance_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("repair_longform_maintenance")

    assert metadata == {
        "tool_name": "repair_longform_maintenance",
        "adapter_type": "static",
        "category": "maintenance",
        "mutability": "write",
        "handler_name": "_repair_longform_maintenance",
    }


def test_tool_executor_exposes_plan_longform_chapter_batch_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("plan_longform_chapter_batch")

    assert metadata == {
        "tool_name": "plan_longform_chapter_batch",
        "adapter_type": "static",
        "category": "task_queue",
        "mutability": "read",
        "handler_name": "_plan_longform_chapter_batch",
    }


def test_tool_executor_exposes_enqueue_longform_chapter_batch_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("enqueue_longform_chapter_batch")

    assert metadata == {
        "tool_name": "enqueue_longform_chapter_batch",
        "adapter_type": "static",
        "category": "task_queue",
        "mutability": "write",
        "handler_name": "_enqueue_longform_chapter_batch",
    }


def test_tool_executor_exposes_inspect_longform_chapter_batch_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("inspect_longform_chapter_batch")

    assert metadata == {
        "tool_name": "inspect_longform_chapter_batch",
        "adapter_type": "static",
        "category": "task_queue",
        "mutability": "read",
        "handler_name": "_inspect_longform_chapter_batch",
    }


def test_tool_executor_exposes_execute_longform_chapter_batch_preflight_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("execute_longform_chapter_batch_preflight")

    assert metadata == {
        "tool_name": "execute_longform_chapter_batch_preflight",
        "adapter_type": "static",
        "category": "task_queue",
        "mutability": "write",
        "handler_name": "_execute_longform_chapter_batch_preflight",
    }


def test_tool_executor_exposes_prepare_longform_chapter_batch_execution_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("prepare_longform_chapter_batch_execution")

    assert metadata == {
        "tool_name": "prepare_longform_chapter_batch_execution",
        "adapter_type": "static",
        "category": "task_queue",
        "mutability": "write",
        "handler_name": "_prepare_longform_chapter_batch_execution",
    }


def test_tool_executor_exposes_execute_longform_chapter_batch_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("execute_longform_chapter_batch")

    assert metadata == {
        "tool_name": "execute_longform_chapter_batch",
        "adapter_type": "static",
        "category": "task_queue",
        "mutability": "write",
        "handler_name": "_execute_longform_chapter_batch",
    }


def test_tool_executor_exposes_review_longform_chapter_batch_execution_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("review_longform_chapter_batch_execution")

    assert metadata == {
        "tool_name": "review_longform_chapter_batch_execution",
        "adapter_type": "static",
        "category": "task_queue",
        "mutability": "write",
        "handler_name": "_review_longform_chapter_batch_execution",
    }


def test_tool_executor_exposes_route_longform_chapter_batch_after_review_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("route_longform_chapter_batch_after_review")

    assert metadata == {
        "tool_name": "route_longform_chapter_batch_after_review",
        "adapter_type": "static",
        "category": "task_queue",
        "mutability": "write",
        "handler_name": "_route_longform_chapter_batch_after_review",
    }


@pytest.mark.asyncio
async def test_tool_executor_dispatches_plan_longform_chapter_batch_adapter(db_session, monkeypatch):
    project = Project(name="Executor Batch Plan")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, str | None, int | None, int | None]] = []

    def fake_plan(db, project_id: str, *, source_run_id: str | None, start_chapter: int | None, batch_size: int | None):
        calls.append((project_id, source_run_id, start_chapter, batch_size))
        return {"status": "completed", "batch": {"chapter_indexes": [start_chapter]}}

    monkeypatch.setattr(
        "app.services.writing_agent.batch_planner.build_longform_chapter_batch_plan",
        fake_plan,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="plan_longform_chapter_batch",
            params={"source_run_id": "run-1", "start_chapter": "7", "batch_size": "2"},
        ),
    )

    assert result.handled is True
    assert result.output == {"status": "completed", "batch": {"chapter_indexes": [7]}}
    assert calls == [(project.id, "run-1", 7, 2)]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_enqueue_longform_chapter_batch_adapter(db_session, monkeypatch):
    project = Project(name="Executor Batch Enqueue")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, str | None, int | None, int | None, bool, str | None]] = []

    def fake_enqueue(
        db,
        project_id: str,
        *,
        source_run_id: str | None,
        start_chapter: int | None,
        batch_size: int | None,
        confirm_enqueue: bool,
        plan_hash: str | None,
    ):
        calls.append((project_id, source_run_id, start_chapter, batch_size, confirm_enqueue, plan_hash))
        return {"status": "queued", "task": {"id": "task-1"}}

    monkeypatch.setattr(
        "app.services.writing_agent.batch_enqueue.build_longform_chapter_batch_enqueue",
        fake_enqueue,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="enqueue_longform_chapter_batch",
            params={
                "source_run_id": "run-1",
                "start_chapter": "7",
                "batch_size": "2",
                "confirm_enqueue": True,
                "plan_hash": "hash-1",
            },
        ),
    )

    assert result.handled is True
    assert result.output == {"status": "queued", "task": {"id": "task-1"}}
    assert calls == [(project.id, "run-1", 7, 2, True, "hash-1")]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_inspect_longform_chapter_batch_adapter(db_session, monkeypatch):
    project = Project(name="Executor Batch Inspect")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, str | None, str | None, int | None]] = []

    def fake_inspect(db, project_id: str, *, task_id: str | None, plan_hash: str | None, limit: int | None):
        calls.append((project_id, task_id, plan_hash, limit))
        return {"status": "completed", "tasks": []}

    monkeypatch.setattr(
        "app.services.writing_agent.batch_queue_inspector.inspect_longform_chapter_batch_queue",
        fake_inspect,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="inspect_longform_chapter_batch",
            params={"task_id": "task-1", "plan_hash": "hash-1", "limit": "2"},
        ),
    )

    assert result.handled is True
    assert result.output == {"status": "completed", "tasks": []}
    assert calls == [(project.id, "task-1", "hash-1", 2)]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_execute_longform_chapter_batch_preflight_adapter(db_session, monkeypatch):
    project = Project(name="Executor Batch Preflight")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, str | None, int | None]] = []

    def fake_preflight(db, project_id: str, *, task_id: str | None, max_chapters: int | None):
        calls.append((project_id, task_id, max_chapters))
        return {"status": "ready", "checkpoint": {"task_id": task_id}}

    monkeypatch.setattr(
        "app.services.writing_agent.batch_preflight.execute_longform_chapter_batch_preflight",
        fake_preflight,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="execute_longform_chapter_batch_preflight",
            params={"task_id": "task-1", "max_chapters": "2"},
        ),
    )

    assert result.handled is True
    assert result.output == {"status": "ready", "checkpoint": {"task_id": "task-1"}}
    assert calls == [(project.id, "task-1", 2)]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_prepare_longform_chapter_batch_execution_adapter(db_session, monkeypatch):
    project = Project(name="Executor Batch Prepare")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, str | None]] = []

    def fake_prepare(db, project_id: str, *, task_id: str | None):
        calls.append((project_id, task_id))
        return {"status": "approval_required", "attempt_manifest": {"task_id": task_id}}

    monkeypatch.setattr(
        "app.services.writing_agent.batch_execution_prepare.prepare_longform_chapter_batch_execution",
        fake_prepare,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="prepare_longform_chapter_batch_execution",
            params={"task_id": "task-1"},
        ),
    )

    assert result.handled is True
    assert result.output == {"status": "approval_required", "attempt_manifest": {"task_id": "task-1"}}
    assert calls == [(project.id, "task-1")]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_execute_longform_chapter_batch_adapter(db_session, monkeypatch):
    project = Project(name="Executor Batch Execute")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, str | None, bool, str | None, str | None]] = []

    async def fake_execute(
        db,
        project_id: str,
        *,
        task_id: str | None,
        confirm_execute: bool,
        attempt_manifest_hash: str | None,
        approval_contract_hash: str | None,
    ):
        calls.append((project_id, task_id, confirm_execute, attempt_manifest_hash, approval_contract_hash))
        return {"status": "completed", "chapter_index": 2}

    monkeypatch.setattr(
        "app.services.writing_agent.batch_execution.execute_longform_chapter_batch",
        fake_execute,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="execute_longform_chapter_batch",
            params={
                "task_id": "task-1",
                "confirm_execute": True,
                "attempt_manifest_hash": "attempt-hash",
                "approval_contract_hash": "contract-hash",
            },
        ),
    )

    assert result.handled is True
    assert result.output == {"status": "completed", "chapter_index": 2}
    assert calls == [(project.id, "task-1", True, "attempt-hash", "contract-hash")]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_review_longform_chapter_batch_execution_adapter(db_session, monkeypatch):
    project = Project(name="Executor Batch Review")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, str | None, int | None]] = []

    def fake_review(db, project_id: str, *, task_id: str | None, lookback: int | None):
        calls.append((project_id, task_id, lookback))
        return {"status": "completed", "chapter_index": 2}

    monkeypatch.setattr(
        "app.services.writing_agent.batch_post_generation_review.review_longform_chapter_batch_execution",
        fake_review,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="review_longform_chapter_batch_execution",
            params={"task_id": "task-1", "lookback": "12"},
        ),
    )

    assert result.handled is True
    assert result.output == {"status": "completed", "chapter_index": 2}
    assert calls == [(project.id, "task-1", 12)]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_route_longform_chapter_batch_after_review_adapter(
    db_session,
    monkeypatch,
):
    project = Project(name="Executor Batch Route")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, str | None, int | None]] = []

    def fake_route(
        db,
        project_id: str,
        *,
        task_id: str | None,
        expected_post_generation_review_hash: str | None,
        next_batch_size: int | None,
    ):
        calls.append((project_id, task_id, next_batch_size))
        return {"status": "completed", "route": {"decision": "next_batch_ready"}}

    monkeypatch.setattr(
        "app.services.writing_agent.batch_post_review_router.route_longform_chapter_batch_after_review",
        fake_route,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="route_longform_chapter_batch_after_review",
            params={
                "task_id": "task-1",
                "expected_post_generation_review_hash": "review-hash",
                "next_batch_size": "2",
            },
        ),
    )

    assert result.handled is True
    assert result.output == {"status": "completed", "route": {"decision": "next_batch_ready"}}
    assert calls == [(project.id, "task-1", 2)]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_backfill_adapter_with_normalized_params(db_session, monkeypatch):
    project = Project(name="Executor Backfill")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, int | None]] = []

    def fake_backfill(db, project_id: str, *, before_chapter: int | None):
        calls.append((project_id, before_chapter))
        return {"status": "completed", "before_chapter": before_chapter}

    monkeypatch.setattr(
        "app.core.outline_lookup.backfill_missing_outline_chapters_from_content",
        fake_backfill,
    )
    context = WritingAgentToolContext(db=db_session, project_id=project.id)

    from_before = await execute_writing_agent_tool(
        context,
        WritingAgentToolRequest(tool_name="backfill_outline_gaps", params={"before_chapter": "7"}),
    )
    from_chapter = await execute_writing_agent_tool(
        context,
        WritingAgentToolRequest(tool_name="backfill_outline_gaps", params={"chapter_index": "8"}),
    )
    without_bound = await execute_writing_agent_tool(
        context,
        WritingAgentToolRequest(tool_name="backfill_outline_gaps"),
    )

    assert from_before.handled is True
    assert from_before.output == {"status": "completed", "before_chapter": 7}
    assert from_chapter.output == {"status": "completed", "before_chapter": 8}
    assert without_bound.output == {"status": "completed", "before_chapter": None}
    assert calls == [(project.id, 7), (project.id, 8), (project.id, None)]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_repair_longform_maintenance_adapter(db_session, monkeypatch):
    project = Project(name="Executor Longform Repair")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, int, int]] = []

    def fake_repair(db, project_id: str, *, limit: int, repair_limit: int):
        calls.append((project_id, limit, repair_limit))
        return {"status": "completed", "limit": limit, "repair_limit": repair_limit}

    monkeypatch.setattr("app.core.longform_memory.repair_longform_maintenance", fake_repair)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="repair_longform_maintenance",
            params={"limit": "9", "repair_limit": "11"},
        ),
    )

    assert result.handled is True
    assert result.output == {"status": "completed", "limit": 9, "repair_limit": 11}
    assert calls == [(project.id, 9, 11)]


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
