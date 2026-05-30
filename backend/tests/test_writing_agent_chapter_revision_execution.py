from __future__ import annotations

import pytest

from app.models import Project
from app.services.writing_agent.chapter_revision_execution import (
    execute_compress_chapter_to_target_with_approval,
    execute_expand_chapter_to_target_with_approval,
    prepare_compress_chapter_to_target_execution,
    prepare_expand_chapter_to_target_execution,
)


def test_prepare_expand_chapter_to_target_execution_returns_agent_approval_contract(db_session):
    project = Project(name="Prepare Chapter Expansion")
    db_session.add(project)
    db_session.commit()

    output = prepare_expand_chapter_to_target_execution(
        db_session,
        project.id,
        chapter_index=3,
        min_word_count=2100,
        extra_instruction="补足动作细节",
    )

    assert output["status"] == "approval_required"
    assert output["project_id"] == project.id
    assert output["chapter_index"] == 3
    step = output["agent_plan"]["steps"][0]
    assert {
        key: value
        for key, value in step.items()
        if key not in {"mutation_fingerprint", "tool_call_id", "resource_binding"}
    } == {
        "step_index": 1,
        "step_id": f"direct-expand-chapter-to-target:{project.id}:chapter:3",
        "tool_name": "expand_chapter_to_target",
        "approval_executor_tool_name": "execute_expand_chapter_to_target_with_approval",
        "params": {"chapter_index": 3, "min_word_count": 2100, "extra_instruction": "补足动作细节"},
        "mutability": "guarded_write",
        "requires_confirmation": True,
        "reason": "扩写章节正文并写入新章节版本。",
    }
    assert step["mutation_fingerprint"]["status"] == "ready"
    assert step["mutation_fingerprint"]["components"]["target_type"] == "chapter_revision_adjustment"
    assert step["mutation_fingerprint"]["components"]["target_id"] == (
        "chapter_revision_adjustment:expand_chapter_to_target:3"
    )
    assert output["agent_plan_approval_contract"]["status"] == "requires_confirmation"
    assert output["agent_plan_approval_contract_hash"].startswith("approval:")
    assert output["side_effects"]["executed"] == []
    assert output["side_effects"]["skipped"] == ["expand_chapter_to_target"]


@pytest.mark.asyncio
async def test_execute_expand_chapter_to_target_with_approval_blocks_without_confirmation(db_session, monkeypatch):
    project = Project(name="Blocked Chapter Expansion")
    db_session.add(project)
    db_session.commit()
    calls: list[int] = []

    async def fake_expand_chapter_to_target_tool(db, project_id: str, *, chapter_index: int, **kwargs):
        calls.append(chapter_index)
        return {"status": "completed", "chapter_index": chapter_index}

    monkeypatch.setattr(
        "app.services.writing_agent.chapter_revision_execution.expand_chapter_to_target_tool",
        fake_expand_chapter_to_target_tool,
    )

    output = await execute_expand_chapter_to_target_with_approval(
        db_session,
        project.id,
        chapter_index=3,
        min_word_count=2100,
        extra_instruction="补足动作细节",
        confirm_execute=False,
        approval_contract_hash=None,
        approval_contract=None,
        approval_tool_metadata_provider=lambda plan: {},
    )

    assert output["status"] == "blocked"
    assert output["reason"] == "confirmation_required"
    assert output["side_effects"]["executed"] == []
    assert output["side_effects"]["skipped"] == ["expand_chapter_to_target"]
    assert calls == []


@pytest.mark.asyncio
async def test_execute_expand_chapter_to_target_with_approval_runs_after_contract_verification(
    db_session,
    monkeypatch,
):
    project = Project(name="Approved Chapter Expansion")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, int, int | None, str]] = []

    async def fake_expand_chapter_to_target_tool(
        db,
        project_id: str,
        *,
        chapter_index: int,
        min_word_count: int | None,
        extra_instruction: str,
    ):
        calls.append((project_id, chapter_index, min_word_count, extra_instruction))
        return {
            "status": "completed",
            "chapter_index": chapter_index,
            "revision_id": "rev-expand",
            "result_version_id": "chapter-version-expanded",
        }

    monkeypatch.setattr(
        "app.services.writing_agent.chapter_revision_execution.expand_chapter_to_target_tool",
        fake_expand_chapter_to_target_tool,
    )
    prepared = prepare_expand_chapter_to_target_execution(
        db_session,
        project.id,
        chapter_index=3,
        min_word_count=2100,
        extra_instruction="补足动作细节",
    )

    output = await execute_expand_chapter_to_target_with_approval(
        db_session,
        project.id,
        chapter_index=3,
        min_word_count=2100,
        extra_instruction="补足动作细节",
        confirm_execute=True,
        approval_contract_hash=prepared["agent_plan_approval_contract_hash"],
        approval_contract=prepared["agent_plan_approval_contract"],
        approval_tool_metadata_provider=lambda plan: _approval_metadata("expand_chapter_to_target"),
    )

    assert output["status"] == "completed"
    assert output["chapter_index"] == 3
    assert output["revision_id"] == "rev-expand"
    assert output["agent_plan_approval_verification"]["status"] == "ready"
    assert output["execution_resource_binding"]["status"] == "ready"
    assert output["evidence"]["agent_plan_approval_verified"] is True
    assert output["side_effects"]["executed"] == ["expand_chapter_to_target"]
    assert calls == [(project.id, 3, 2100, "补足动作细节")]


def test_prepare_compress_chapter_to_target_execution_returns_agent_approval_contract(db_session):
    project = Project(name="Prepare Chapter Compression")
    db_session.add(project)
    db_session.commit()

    output = prepare_compress_chapter_to_target_execution(
        db_session,
        project.id,
        chapter_index=4,
        target_max_word_count=2300,
        extra_instruction="保留悬念",
        forbidden_terms=["  啰嗦  ", "", "重复"],
    )

    assert output["status"] == "approval_required"
    step = output["agent_plan"]["steps"][0]
    assert {
        key: value
        for key, value in step.items()
        if key not in {"mutation_fingerprint", "tool_call_id", "resource_binding"}
    } == {
        "step_index": 1,
        "step_id": f"direct-compress-chapter-to-target:{project.id}:chapter:4",
        "tool_name": "compress_chapter_to_target",
        "approval_executor_tool_name": "execute_compress_chapter_to_target_with_approval",
        "params": {
            "chapter_index": 4,
            "target_max_word_count": 2300,
            "extra_instruction": "保留悬念",
            "forbidden_terms": ["啰嗦", "重复"],
        },
        "mutability": "guarded_write",
        "requires_confirmation": True,
        "reason": "压缩章节正文并写入新章节版本。",
    }
    assert step["mutation_fingerprint"]["status"] == "ready"
    assert step["mutation_fingerprint"]["components"]["target_id"] == (
        "chapter_revision_adjustment:compress_chapter_to_target:4"
    )
    assert output["side_effects"]["executed"] == []
    assert output["side_effects"]["skipped"] == ["compress_chapter_to_target"]


@pytest.mark.asyncio
async def test_execute_compress_chapter_to_target_with_approval_runs_after_contract_verification(
    db_session,
    monkeypatch,
):
    project = Project(name="Approved Chapter Compression")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, int, int | None, str, list[str]]] = []

    async def fake_compress_chapter_to_target_tool(
        db,
        project_id: str,
        *,
        chapter_index: int,
        target_max_word_count: int | None,
        extra_instruction: str,
        forbidden_terms: list[str],
    ):
        calls.append((project_id, chapter_index, target_max_word_count, extra_instruction, forbidden_terms))
        return {
            "status": "completed",
            "chapter_index": chapter_index,
            "revision_id": "rev-compress",
            "result_version_id": "chapter-version-compressed",
        }

    monkeypatch.setattr(
        "app.services.writing_agent.chapter_revision_execution.compress_chapter_to_target_tool",
        fake_compress_chapter_to_target_tool,
    )
    prepared = prepare_compress_chapter_to_target_execution(
        db_session,
        project.id,
        chapter_index=4,
        target_max_word_count=2300,
        extra_instruction="保留悬念",
        forbidden_terms=["啰嗦", "重复"],
    )

    output = await execute_compress_chapter_to_target_with_approval(
        db_session,
        project.id,
        chapter_index=4,
        target_max_word_count=2300,
        extra_instruction="保留悬念",
        forbidden_terms=["啰嗦", "重复"],
        confirm_execute=True,
        approval_contract_hash=prepared["agent_plan_approval_contract_hash"],
        approval_contract=prepared["agent_plan_approval_contract"],
        approval_tool_metadata_provider=lambda plan: _approval_metadata("compress_chapter_to_target"),
    )

    assert output["status"] == "completed"
    assert output["chapter_index"] == 4
    assert output["revision_id"] == "rev-compress"
    assert output["agent_plan_approval_verification"]["status"] == "ready"
    assert output["execution_resource_binding"]["status"] == "ready"
    assert output["evidence"]["agent_plan_approval_verified"] is True
    assert output["side_effects"]["executed"] == ["compress_chapter_to_target"]
    assert calls == [(project.id, 4, 2300, "保留悬念", ["啰嗦", "重复"])]


def _approval_metadata(tool_name: str) -> dict[str, dict[str, object]]:
    return {
        tool_name: {
            "tool_name": tool_name,
            "tool_exists": True,
            "adapter_exists": True,
            "adapter_type": "approval_wrapper",
            "handler_name": f"_execute_{tool_name}_with_approval",
            "mutability": "guarded_write",
            "requires_confirmation": True,
            "required_fields": [],
        }
    }
