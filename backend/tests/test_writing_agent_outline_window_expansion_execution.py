import pytest

from app.models import Project


def test_prepare_expand_outline_window_execution_returns_agent_approval_contract(db_session):
    from app.services.writing_agent.outline_window_expansion_execution import (
        prepare_expand_outline_window_execution,
    )

    project = Project(name="Prepare Outline Window Expansion")
    db_session.add(project)
    db_session.commit()

    output = prepare_expand_outline_window_execution(db_session, project.id, start_chapter=3, end_chapter=5)

    assert output["status"] == "approval_required"
    assert output["project_id"] == project.id
    assert output["start_chapter"] == 3
    assert output["end_chapter"] == 5
    assert output["target_type"] == "outline"
    step = output["agent_plan"]["steps"][0]
    assert {
        key: value
        for key, value in step.items()
        if key not in {"mutation_fingerprint", "tool_call_id", "resource_binding"}
    } == {
        "step_index": 1,
        "step_id": f"direct-expand-outline-window:{project.id}:chapters:3-5",
        "tool_name": "expand_outline_window",
        "approval_executor_tool_name": "execute_expand_outline_window_with_approval",
        "params": {"start_chapter": 3, "end_chapter": 5},
        "mutability": "guarded_write",
        "requires_confirmation": True,
        "reason": "扩展指定章节窗口的大纲。",
    }
    assert step["mutation_fingerprint"]["status"] == "ready"
    assert step["mutation_fingerprint"]["components"]["target_type"] == "outline"
    assert step["mutation_fingerprint"]["components"]["target_id"] == f"outline_window:{project.id}:chapters:3-5"
    assert output["resource_binding"]["target_id"] == f"outline_window:{project.id}:chapters:3-5"
    assert output["agent_plan_approval_contract"]["status"] == "requires_confirmation"
    assert output["agent_plan_approval_contract_hash"].startswith("approval:")
    assert output["side_effects"]["executed"] == []
    assert output["side_effects"]["skipped"] == ["expand_outline_window"]
    assert output["recommended_next_tools"] == ["execute_expand_outline_window_with_approval"]


@pytest.mark.asyncio
async def test_execute_expand_outline_window_with_approval_blocks_without_confirmation(db_session, monkeypatch):
    from app.services.writing_agent.outline_window_expansion_execution import (
        execute_expand_outline_window_with_approval,
    )

    project = Project(name="Blocked Outline Window Expansion")
    db_session.add(project)
    db_session.commit()
    calls: list[str] = []

    async def fake_expand(*args, **kwargs):
        calls.append("called")
        return {"status": "completed"}

    monkeypatch.setattr(
        "app.services.writing_agent.outline_window_expansion_execution.expand_outline_window_tool",
        fake_expand,
    )

    output = await execute_expand_outline_window_with_approval(
        db_session,
        project.id,
        start_chapter=3,
        end_chapter=5,
        confirm_execute=False,
        approval_contract_hash=None,
        approval_contract=None,
        approval_tool_metadata_provider=lambda plan: {},
    )

    assert output["status"] == "blocked"
    assert output["reason"] == "confirmation_required"
    assert output["side_effects"]["executed"] == []
    assert output["side_effects"]["skipped"] == ["expand_outline_window"]
    assert output["recommended_next_tools"] == ["prepare_expand_outline_window_execution"]
    assert calls == []


@pytest.mark.asyncio
async def test_execute_expand_outline_window_with_approval_runs_after_contract_verification(db_session, monkeypatch):
    from app.services.writing_agent.outline_window_expansion_execution import (
        execute_expand_outline_window_with_approval,
        prepare_expand_outline_window_execution,
    )

    project = Project(name="Approved Outline Window Expansion")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, int, int, str | None]] = []

    async def fake_expand(db, project_id: str, *, start_chapter: int, end_chapter: int, command_args: str | None):
        calls.append((project_id, start_chapter, end_chapter, command_args))
        return {
            "status": "completed",
            "start_chapter": start_chapter,
            "end_chapter": end_chapter,
            "outline_id": "outline-1",
            "total_chapters": 600,
            "added_chapter_count": 3,
            "merge": {"added_chapter_count": 3},
            "trace_id": "trace-outline",
            "recommended_next_tools": ["preflight_writing"],
        }

    monkeypatch.setattr(
        "app.services.writing_agent.outline_window_expansion_execution.expand_outline_window_tool",
        fake_expand,
    )
    prepared = prepare_expand_outline_window_execution(db_session, project.id, start_chapter=3, end_chapter=5)

    output = await execute_expand_outline_window_with_approval(
        db_session,
        project.id,
        start_chapter=3,
        end_chapter=5,
        command_args="补齐悬疑伏笔",
        confirm_execute=True,
        approval_contract_hash=prepared["agent_plan_approval_contract_hash"],
        approval_contract=prepared["agent_plan_approval_contract"],
        approval_tool_metadata_provider=lambda plan: {
            "expand_outline_window": {
                "tool_name": "expand_outline_window",
                "tool_exists": True,
                "adapter_exists": True,
                "adapter_type": "approval_wrapper",
                "handler_name": "_execute_expand_outline_window_with_approval",
                "mutability": "write",
                "requires_confirmation": True,
                "required_fields": [],
            }
        },
    )

    assert output["status"] == "completed"
    assert output["start_chapter"] == 3
    assert output["end_chapter"] == 5
    assert output["agent_plan_approval_verification"]["status"] == "ready"
    assert output["execution_resource_binding"]["status"] == "ready"
    assert output["execution_resource_binding"]["resource_binding"]["target_id"] == (
        f"outline_window:{project.id}:chapters:3-5"
    )
    assert output["evidence"]["agent_plan_approval_verified"] is True
    assert output["side_effects"]["executed"] == ["expand_outline_window"]
    assert calls == [(project.id, 3, 5, "补齐悬疑伏笔")]
