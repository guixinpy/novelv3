from __future__ import annotations

from app.models import BackgroundTask, ChapterContent, Outline, Project, Setup, Storyline
from app.services.writing_agent.batch_enqueue import BATCH_TASK_TYPE
from app.services.writing_agent.batch_preflight_execution import (
    execute_longform_chapter_batch_preflight_with_approval,
    prepare_longform_chapter_batch_preflight,
)


def test_prepare_longform_chapter_batch_preflight_returns_agent_approval_contract_without_checkpoint(db_session):
    project, task = _seed_project_with_batch_task(db_session)

    output = prepare_longform_chapter_batch_preflight(
        db_session,
        project.id,
        task_id=task.id,
        max_chapters=1,
    )

    db_session.refresh(task)
    assert output["status"] == "approval_required"
    assert output["project_id"] == project.id
    assert output["target_type"] == "background_task_checkpoint"
    assert output["task"]["id"] == task.id
    assert output["required_confirmation"] == {
        "confirm_execute": True,
        "approval_contract_hash": output["agent_plan_approval_contract_hash"],
    }
    step = output["agent_plan"]["steps"][0]
    assert step["tool_name"] == "execute_longform_chapter_batch_preflight"
    assert step["approval_executor_tool_name"] == "execute_longform_chapter_batch_preflight_with_approval"
    assert step["params"] == {"task_id": task.id, "max_chapters": 1}
    assert step["mutation_fingerprint"]["status"] == "ready"
    assert step["mutation_fingerprint"]["components"]["target_type"] == "background_task_checkpoint"
    assert step["mutation_fingerprint"]["components"]["target_id"] == f"background_task_checkpoint:{task.id}:preflight"
    assert output["agent_plan_approval_contract"]["status"] == "requires_confirmation"
    assert output["agent_plan_approval_contract_hash"].startswith("approval:")
    assert output["side_effects"]["executed"] == []
    assert output["side_effects"]["skipped"] == ["background_task_result_checkpoint"]
    assert "preflight_checkpoint" not in (task.result or {})


def test_execute_longform_chapter_batch_preflight_with_approval_blocks_without_confirmation(db_session):
    project, task = _seed_project_with_batch_task(db_session)

    output = execute_longform_chapter_batch_preflight_with_approval(
        db_session,
        project.id,
        task_id=task.id,
        max_chapters=1,
        confirm_execute=False,
        approval_contract_hash=None,
        approval_contract=None,
        approval_tool_metadata_provider=lambda plan: {},
    )

    db_session.refresh(task)
    assert output["status"] == "blocked"
    assert output["reason"] == "confirmation_required"
    assert output["side_effects"]["executed"] == []
    assert output["side_effects"]["skipped"] == ["background_task_result_checkpoint"]
    assert "preflight_checkpoint" not in (task.result or {})


def test_execute_longform_chapter_batch_preflight_with_approval_persists_checkpoint_after_contract_verification(
    db_session,
):
    project, task = _seed_project_with_batch_task(db_session)
    prepared = prepare_longform_chapter_batch_preflight(
        db_session,
        project.id,
        task_id=task.id,
        max_chapters=1,
    )

    output = execute_longform_chapter_batch_preflight_with_approval(
        db_session,
        project.id,
        task_id=task.id,
        max_chapters=1,
        confirm_execute=True,
        approval_contract_hash=prepared["agent_plan_approval_contract_hash"],
        approval_contract=prepared["agent_plan_approval_contract"],
        approval_tool_metadata_provider=lambda plan: {
            "execute_longform_chapter_batch_preflight": {
                "tool_name": "execute_longform_chapter_batch_preflight",
                "tool_exists": True,
                "adapter_exists": True,
                "adapter_type": "approval_wrapper",
                "handler_name": "_execute_longform_chapter_batch_preflight_with_approval",
                "mutability": "guarded_write",
                "requires_confirmation": True,
                "required_fields": ["task_id"],
            }
        },
    )

    db_session.refresh(task)
    assert output["status"] == "ready"
    assert output["task"]["id"] == task.id
    assert output["checkpoint"]["status"] == "ready"
    assert output["agent_plan_approval_verification"]["status"] == "ready"
    assert output["execution_resource_binding"]["status"] == "ready"
    assert output["evidence"]["agent_plan_approval_verified"] is True
    assert output["side_effects"]["executed"] == ["background_task_result_checkpoint"]
    assert task.result["preflight_checkpoint"]["status"] == "ready"
    assert task.result["preflight_checkpoint"]["selected_chapter_indexes"] == [2]


def _seed_project_with_batch_task(db_session) -> tuple[Project, BackgroundTask]:
    project = Project(
        name="Approved Batch Preflight",
        genre="都市悬疑",
        target_chapter_count=600,
        target_word_count=1200000,
    )
    db_session.add(project)
    db_session.flush()
    db_session.add(
        Setup(
            project_id=project.id,
            status="generated",
            world_building={"background": "雾港存在记忆异常。"},
            characters=[{"name": "林深", "goals": "调查雾港"}],
            core_concept={"theme": "记忆与真相"},
        )
    )
    db_session.add(
        Storyline(
            project_id=project.id,
            status="generated",
            plotlines=[{"name": "主线", "summary": "追查雾港异常"}],
            foreshadowing=[],
        )
    )
    db_session.add(
        Outline(
            project_id=project.id,
            total_chapters=600,
            status="generated",
            chapters=[
                {
                    "chapter_index": 1,
                    "title": "雾港开端",
                    "summary": "林深发现雾港异常。",
                    "scenes": ["旧灯塔"],
                    "characters": ["林深"],
                },
                {
                    "chapter_index": 2,
                    "title": "雾港线索",
                    "summary": "林深继续调查记忆诊所。",
                    "scenes": ["记忆诊所"],
                    "characters": ["林深"],
                },
            ],
            plotlines=[],
            foreshadowing=[],
        )
    )
    db_session.add(
        ChapterContent(
            project_id=project.id,
            chapter_index=1,
            title="雾港开端",
            content="林深抵达雾港旧灯塔，发现雾晶实验残留。",
            word_count=50,
            status="generated",
        )
    )
    task = BackgroundTask(
        project_id=project.id,
        task_type=BATCH_TASK_TYPE,
        status="pending",
        payload={
            "plan_hash": "plan-preflight-1",
            "chapter_range": {"start": 2, "end": 2},
            "batch": {"start_chapter": 2, "end_chapter": 2, "chapter_indexes": [2]},
            "dag": {"nodes": [{"node_id": "chapter_generation"}], "edges": []},
            "queue_policy": {"resume_strategy": "background_task_chapter_range"},
        },
        result={},
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(project)
    db_session.refresh(task)
    return project, task
