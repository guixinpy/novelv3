import pytest

from app.models import ChapterContent, Project
from app.schemas.writing_agent import WritingAgentToolRequest
from app.services.writing_agent.chapter_generation_tool import execute_generate_chapter_tool
from app.services.writing_agent.tool_registry import internal_tool_names
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
async def test_generate_chapter_tool_appends_context_without_run_service(db_session, monkeypatch):
    project = Project(name="Direct Chapter Tool")
    db_session.add(project)
    db_session.flush()
    db_session.add(
        ChapterContent(
            project_id=project.id,
            chapter_index=1,
            title="空白信的秘密",
            content="林深和苏晚晴在灯塔下发现空白信，信纸显出雾晶是钥匙。两人决定前往下城黑市。",
            word_count=2000,
            status="generated",
        )
    )
    db_session.commit()
    captured: dict[str, object] = {}

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        captured["action_type"] = action_type
        captured["command_args"] = command_args
        captured["action_params"] = action_params
        return {"status": "success", "chapter_index": action_params["chapter_index"]}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    result = await execute_generate_chapter_tool(
        db_session,
        project.id,
        chapter_index=2,
        command_args="保持紧张感",
    )

    command_args = str(captured["command_args"])
    assert result["status"] == "success"
    assert captured["action_type"] == "generate_chapter"
    assert captured["action_params"] == {"chapter_index": 2}
    assert "保持紧张感" in command_args
    assert "上一章状态卡" in command_args
    assert "空白信" in command_args
    assert result["agent_continuity_feedback"]["status"] == "active"
    assert result["recommended_next_tools"] == [
        "review_chapter_quality",
        "review_chapter_continuity",
        "analyze_chapter_world_model",
    ]


@pytest.mark.asyncio
async def test_tool_executor_does_not_coerce_invalid_generate_chapter_index(db_session, monkeypatch):
    project = Project(name="Invalid Chapter Index")
    db_session.add(project)
    db_session.commit()
    calls: list[str] = []

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append(action_type)
        return {"status": "success"}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    with pytest.raises(ValueError):
        await execute_writing_agent_tool(
            WritingAgentToolContext(db=db_session, project_id=project.id),
            WritingAgentToolRequest(tool_name="generate_chapter", params={"chapter_index": "not-a-number"}),
        )

    assert calls == []


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
        "generate_chapter",
        "plan_writing_agent_run",
        "plan_longform_chapter_batch",
        "enqueue_longform_chapter_batch",
        "inspect_longform_chapter_batch",
        "inspect_agent_job_projection",
        "inspect_agent_tool_contracts",
        "inspect_agent_knowledge_base_route",
        "record_agent_knowledge_base_candidate",
        "analyze_chapter_world_model",
        "execute_longform_chapter_batch_preflight",
        "prepare_longform_chapter_batch_execution",
        "execute_longform_chapter_batch",
        "review_longform_chapter_batch_execution",
        "route_longform_chapter_batch_after_review",
        "inspect_agent_trace_audit",
        "inspect_agent_memory_route",
        "inspect_agent_world_model_route",
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
    assert writing_agent_tool_adapter_metadata("generate_chapter") == {
        "tool_name": "generate_chapter",
        "adapter_type": "static",
        "category": "generation",
        "mutability": "write",
        "handler_name": "_generate_chapter",
    }


def test_tool_executor_lists_unhandled_internal_tools_for_migration_tracking():
    names = unhandled_internal_writing_agent_tool_names()

    assert "apply_world_model_proposal_resolution" in names
    assert "create_revision_draft" in names
    assert "backfill_outline_gaps" not in names
    assert "repair_longform_maintenance" not in names
    assert "inspect_agent_trace_audit" not in names
    assert "inspect_agent_memory_route" not in names
    assert "inspect_agent_world_model_route" not in names
    assert "review_chapter_quality" not in names
    assert "plan_writing_agent_run" not in names
    assert "analyze_chapter_world_model" not in names
    assert "plan_longform_chapter_batch" not in names
    assert "enqueue_longform_chapter_batch" not in names
    assert "inspect_longform_chapter_batch" not in names
    assert "inspect_agent_job_projection" not in names
    assert "inspect_agent_tool_contracts" not in names
    assert "inspect_agent_knowledge_base_route" not in names
    assert "record_agent_knowledge_base_candidate" not in names
    assert "execute_longform_chapter_batch_preflight" not in names
    assert "prepare_longform_chapter_batch_execution" not in names
    assert "execute_longform_chapter_batch" not in names
    assert "review_longform_chapter_batch_execution" not in names
    assert "route_longform_chapter_batch_after_review" not in names
    assert "preflight_writing" not in names


def test_tool_executor_exposes_inspect_agent_memory_route_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("inspect_agent_memory_route")

    assert metadata == {
        "tool_name": "inspect_agent_memory_route",
        "adapter_type": "static",
        "category": "longform_memory",
        "mutability": "read",
        "handler_name": "_inspect_agent_memory_route",
    }


def test_tool_executor_exposes_inspect_agent_tool_contracts_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("inspect_agent_tool_contracts")

    assert metadata == {
        "tool_name": "inspect_agent_tool_contracts",
        "adapter_type": "static",
        "category": "preflight",
        "mutability": "read",
        "handler_name": "_inspect_agent_tool_contracts",
    }


def test_tool_executor_exposes_analyze_chapter_world_model_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("analyze_chapter_world_model")

    assert metadata == {
        "tool_name": "analyze_chapter_world_model",
        "adapter_type": "static",
        "category": "athena_world_model",
        "mutability": "write",
        "handler_name": "_analyze_chapter_world_model",
    }


@pytest.mark.asyncio
async def test_tool_executor_handles_inspect_agent_tool_contracts(db_session):
    project = Project(name="Tool Contract Snapshot")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-contract"),
        WritingAgentToolRequest(
            tool_name="inspect_agent_tool_contracts",
            params={"chapter_index": 1, "include_gap_details": True},
        ),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert result.output["summary"]["total_tools"] >= 1
    assert result.output["summary"]["internal_tools"] >= 1
    assert result.output["coverage"]["schema_coverage_ratio"] == 1.0
    assert result.output["coverage"]["adapter_coverage_ratio"] < 1.0
    assert "confirmation_contract_ratio" in result.output["coverage"]
    assert "tool_visibility_projection" in result.output["reference_alignment"]["patterns"]
    assert "permission_scope_category" in result.output["reference_alignment"]["patterns"]
    assert "references/agent-projects/openclaw" in result.output["reference_alignment"]["source_refs"]
    tools_by_name = {tool["name"]: tool for tool in result.output["tools"]}
    assert tools_by_name["describe_agent_tools"]["mutability"] == "read"
    assert tools_by_name["describe_agent_tools"]["parallel_safe"] is True
    assert tools_by_name["inspect_agent_knowledge_base_route"]["memory_boundary"] == "knowledge_base"
    assert tools_by_name["inspect_agent_tool_contracts"]["contract_status"] == "ready"
    assert tools_by_name["enqueue_longform_chapter_batch"]["mutability"] == "guarded_write"
    assert tools_by_name["enqueue_longform_chapter_batch"]["permission_level"] == "confirm_required"
    assert "requires_confirmation" in tools_by_name["enqueue_longform_chapter_batch"]["side_effects"]
    assert tools_by_name["route_longform_chapter_batch_after_review"]["mutability"] == "guarded_write"
    assert tools_by_name["execute_longform_chapter_batch"]["requires_confirmation"] is True
    assert tools_by_name["execute_longform_chapter_batch"]["mutability"] == "guarded_write"
    assert tools_by_name["execute_longform_chapter_batch"]["permission_level"] == "confirm_required"
    assert tools_by_name["execute_longform_chapter_batch"]["parallel_safe"] is False
    assert tools_by_name["execute_longform_chapter_batch"]["recovery_tools"] == [
        "inspect_agent_job_projection",
        "plan_recovery_tools",
    ]
    assert tools_by_name["generate_chapter"]["resource_scope"] == "manuscript"
    assert tools_by_name["generate_chapter"]["adapter_type"] == "static"
    assert "missing_agent_native_adapter" not in tools_by_name["generate_chapter"]["gap_codes"]
    assert "output_schema_too_generic" not in tools_by_name["generate_chapter"]["gap_codes"]
    assert tools_by_name["analyze_chapter_world_model"]["adapter_type"] == "static"
    assert "missing_agent_native_adapter" not in tools_by_name["analyze_chapter_world_model"]["gap_codes"]
    assert internal_tool_names().issubset(set(tools_by_name))


@pytest.mark.asyncio
async def test_tool_executor_hides_contract_gap_details_when_requested(db_session):
    project = Project(name="Tool Contract Snapshot Compact")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-contract-compact"),
        WritingAgentToolRequest(
            tool_name="inspect_agent_tool_contracts",
            params={"chapter_index": 1, "include_gap_details": False},
        ),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["gaps"] == []
    assert all("gaps" not in tool for tool in result.output["tools"])


def test_tool_executor_exposes_inspect_agent_trace_audit_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("inspect_agent_trace_audit")

    assert metadata == {
        "tool_name": "inspect_agent_trace_audit",
        "adapter_type": "static",
        "category": "trace",
        "mutability": "read",
        "handler_name": "_inspect_agent_trace_audit",
    }


def test_tool_executor_exposes_inspect_agent_world_model_route_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("inspect_agent_world_model_route")

    assert metadata == {
        "tool_name": "inspect_agent_world_model_route",
        "adapter_type": "static",
        "category": "athena_world_model",
        "mutability": "read",
        "handler_name": "_inspect_agent_world_model_route",
    }


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


def test_tool_executor_exposes_inspect_agent_job_projection_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("inspect_agent_job_projection")

    assert metadata == {
        "tool_name": "inspect_agent_job_projection",
        "adapter_type": "static",
        "category": "task_queue",
        "mutability": "read",
        "handler_name": "_inspect_agent_job_projection",
    }


def test_tool_executor_exposes_inspect_agent_knowledge_base_route_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("inspect_agent_knowledge_base_route")

    assert metadata == {
        "tool_name": "inspect_agent_knowledge_base_route",
        "adapter_type": "static",
        "category": "knowledge_base",
        "mutability": "read",
        "handler_name": "_inspect_agent_knowledge_base_route",
    }


def test_tool_executor_exposes_record_agent_knowledge_base_candidate_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("record_agent_knowledge_base_candidate")

    assert metadata == {
        "tool_name": "record_agent_knowledge_base_candidate",
        "adapter_type": "static",
        "category": "knowledge_base",
        "mutability": "write",
        "handler_name": "_record_agent_knowledge_base_candidate",
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
async def test_tool_executor_dispatches_inspect_agent_job_projection_adapter(db_session, monkeypatch):
    project = Project(name="Executor Agent Job Projection")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, str | None, str | None, str | None, int | None]] = []

    def fake_projection(
        db,
        project_id: str,
        *,
        task_id: str | None,
        task_type: str | None,
        status: str | None,
        limit: int | None,
    ):
        calls.append((project_id, task_id, task_type, status, limit))
        return {"status": "completed", "queue": {"depth": 0}}

    monkeypatch.setattr(
        "app.services.writing_agent.agent_job_projection.inspect_agent_job_projection",
        fake_projection,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="inspect_agent_job_projection",
            params={"task_id": "task-1", "task_type": "generate_chapter", "status": "failed", "limit": "9"},
        ),
    )

    assert result.handled is True
    assert result.output == {"status": "completed", "queue": {"depth": 0}}
    assert calls == [(project.id, "task-1", "generate_chapter", "failed", 9)]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_inspect_agent_knowledge_base_route_adapter(db_session, monkeypatch):
    project = Project(name="Executor Knowledge Base Route")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, int | None, str | None, int | None]] = []

    def fake_route(db, project_id: str, *, chapter_index: int | None, query: str | None, limit: int | None):
        calls.append((project_id, chapter_index, query, limit))
        return {"status": "completed", "route": {"status": "ready"}}

    monkeypatch.setattr(
        "app.services.writing_agent.agent_knowledge_base_route.inspect_agent_knowledge_base_route",
        fake_route,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="inspect_agent_knowledge_base_route",
            params={"chapter_index": "8", "query": "雾港节奏", "limit": "5"},
        ),
    )

    assert result.handled is True
    assert result.output == {"status": "completed", "route": {"status": "ready"}}
    assert calls == [(project.id, 8, "雾港节奏", 5)]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_record_agent_knowledge_base_candidate_adapter(db_session, monkeypatch):
    project = Project(name="Executor Knowledge Base Candidate")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, str, str, str, list[str], float | None, str | None, list[str]]] = []

    def fake_record(
        db,
        project_id: str,
        *,
        memory_type: str,
        title: str,
        summary: str,
        source_refs: list[str],
        confidence: float | None,
        status: str | None,
        tags: list[str],
    ):
        calls.append((project_id, memory_type, title, summary, source_refs, confidence, status, tags))
        return {"status": "completed", "action": "created"}

    monkeypatch.setattr(
        "app.services.writing_agent.agent_knowledge_base_candidates.record_agent_knowledge_base_candidate",
        fake_record,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="record_agent_knowledge_base_candidate",
            params={
                "memory_type": "self_optimization_lesson",
                "title": "低细节续写可行",
                "summary": "Agent route 可以支撑续写。",
                "source_refs": ["phase77", "chapter:24"],
                "confidence": "0.8",
                "status": "candidate",
                "tags": ["dogfood"],
            },
        ),
    )

    assert result.handled is True
    assert result.output == {"status": "completed", "action": "created"}
    assert calls == [
        (
            project.id,
            "self_optimization_lesson",
            "低细节续写可行",
            "Agent route 可以支撑续写。",
            ["phase77", "chapter:24"],
            0.8,
            "candidate",
            ["dogfood"],
        )
    ]


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
async def test_tool_executor_dispatches_inspect_agent_memory_route_adapter(db_session, monkeypatch):
    project = Project(name="Executor Memory Route")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, int | None, str | None, bool]] = []

    def fake_route(db, project_id: str, *, chapter_index: int | None, query: str | None, include_context_summary: bool):
        calls.append((project_id, chapter_index, query, include_context_summary))
        return {"status": "completed", "route": {"status": "ready"}}

    monkeypatch.setattr("app.services.writing_agent.agent_memory_route.inspect_agent_memory_route", fake_route)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="inspect_agent_memory_route",
            params={"chapter_index": "12", "query": "父亲失踪", "include_context_summary": True},
        ),
    )

    assert result.handled is True
    assert result.output == {"status": "completed", "route": {"status": "ready"}}
    assert calls == [(project.id, 12, "父亲失踪", True)]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_inspect_agent_trace_audit_adapter(db_session, monkeypatch):
    project = Project(name="Executor Trace Audit")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, str | None, int | None, str | None, int | None]] = []

    def fake_audit(
        db,
        project_id: str,
        *,
        run_id: str | None,
        chapter_index: int | None,
        task_id: str | None,
        limit: int | None,
    ):
        calls.append((project_id, run_id, chapter_index, task_id, limit))
        return {"status": "completed", "audit": {"status": "completed"}}

    monkeypatch.setattr("app.services.writing_agent.agent_trace_audit.inspect_agent_trace_audit", fake_audit)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="inspect_agent_trace_audit",
            params={"run_id": "run-1", "chapter_index": "12", "task_id": "task-1", "limit": "7"},
        ),
    )

    assert result.handled is True
    assert result.output == {"status": "completed", "audit": {"status": "completed"}}
    assert calls == [(project.id, "run-1", 12, "task-1", 7)]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_inspect_agent_world_model_route_adapter(db_session, monkeypatch):
    project = Project(name="Executor World Model Route")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, int | None, str | None, int | None]] = []

    def fake_route(db, project_id: str, *, chapter_index: int | None, subject_ref: str | None, limit: int | None):
        calls.append((project_id, chapter_index, subject_ref, limit))
        return {"status": "completed", "route": {"status": "ready"}}

    monkeypatch.setattr("app.services.writing_agent.agent_world_model_route.inspect_agent_world_model_route", fake_route)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="inspect_agent_world_model_route",
            params={"chapter_index": "12", "subject_ref": "char.hero", "limit": "9"},
        ),
    )

    assert result.handled is True
    assert result.output == {"status": "completed", "route": {"status": "ready"}}
    assert calls == [(project.id, 12, "char.hero", 9)]


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
