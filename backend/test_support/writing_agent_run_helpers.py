from app.core.world_contracts import DERIVED
from app.core.world_proposal_service import create_bundle, write_candidate_fact
from app.models import ChapterContent, Outline, Project, ProjectProfileVersion, Setup, Storyline, WorldProposalItem
from app.schemas.world_proposals import ProposalCandidateFactCreate


def approved_create_revision_draft_tool(db_session, project_id: str, *, chapter_index: int) -> dict:
    from app.services.writing_agent.revision_draft_execution import prepare_create_revision_draft_execution

    prepared = prepare_create_revision_draft_execution(db_session, project_id, chapter_index=chapter_index)
    return {
        "tool_name": "execute_create_revision_draft_with_approval",
        "params": {
            "chapter_index": chapter_index,
            "confirm_execute": True,
            "approval_contract_hash": prepared["agent_plan_approval_contract_hash"],
            "approval_contract": prepared["agent_plan_approval_contract"],
        },
    }


def approved_apply_planner_revision_patch_tool(
    db_session,
    project_id: str,
    *,
    chapter_index: int,
    revision_id: str,
) -> dict:
    from app.services.writing_agent.revision_patch_execution import prepare_apply_planner_revision_patch_execution

    prepared = prepare_apply_planner_revision_patch_execution(
        db_session,
        project_id,
        chapter_index=chapter_index,
        revision_id=revision_id,
    )
    return {
        "tool_name": "execute_apply_planner_revision_patch_with_approval",
        "params": {
            "chapter_index": chapter_index,
            "revision_id": revision_id,
            "confirm_execute": True,
            "approval_contract_hash": prepared["agent_plan_approval_contract_hash"],
            "approval_contract": prepared["agent_plan_approval_contract"],
        },
    }


def approved_expand_chapter_to_target_tool(
    db_session,
    project_id: str,
    *,
    chapter_index: int,
    min_word_count: int | None = None,
    extra_instruction: str = "",
) -> dict:
    from app.services.writing_agent.chapter_revision_execution import prepare_expand_chapter_to_target_execution

    prepared = prepare_expand_chapter_to_target_execution(
        db_session,
        project_id,
        chapter_index=chapter_index,
        min_word_count=min_word_count,
        extra_instruction=extra_instruction,
    )
    params = {
        "chapter_index": chapter_index,
        "confirm_execute": True,
        "approval_contract_hash": prepared["agent_plan_approval_contract_hash"],
        "approval_contract": prepared["agent_plan_approval_contract"],
    }
    if min_word_count is not None:
        params["min_word_count"] = min_word_count
    if extra_instruction:
        params["extra_instruction"] = extra_instruction
    return {
        "tool_name": "execute_expand_chapter_to_target_with_approval",
        "params": params,
    }


def approved_compress_chapter_to_target_tool(
    db_session,
    project_id: str,
    *,
    chapter_index: int,
    target_max_word_count: int | None = None,
    extra_instruction: str = "",
    forbidden_terms: list[str] | None = None,
) -> dict:
    from app.services.writing_agent.chapter_revision_execution import prepare_compress_chapter_to_target_execution

    prepared = prepare_compress_chapter_to_target_execution(
        db_session,
        project_id,
        chapter_index=chapter_index,
        target_max_word_count=target_max_word_count,
        extra_instruction=extra_instruction,
        forbidden_terms=forbidden_terms,
    )
    params = {
        "chapter_index": chapter_index,
        "confirm_execute": True,
        "approval_contract_hash": prepared["agent_plan_approval_contract_hash"],
        "approval_contract": prepared["agent_plan_approval_contract"],
    }
    if target_max_word_count is not None:
        params["target_max_word_count"] = target_max_word_count
    if extra_instruction:
        params["extra_instruction"] = extra_instruction
    if forbidden_terms is not None:
        params["forbidden_terms"] = forbidden_terms
    return {
        "tool_name": "execute_compress_chapter_to_target_with_approval",
        "params": params,
    }


def approved_generate_chapter_tool(
    db_session,
    project_id: str,
    *,
    chapter_index: int,
    command_args: str | None = None,
) -> dict:
    from app.services.writing_agent.chapter_generation_execution import prepare_generate_chapter_execution

    prepared = prepare_generate_chapter_execution(db_session, project_id, chapter_index=chapter_index)
    tool = {
        "tool_name": "execute_generate_chapter_with_approval",
        "params": {
            "chapter_index": chapter_index,
            "confirm_execute": True,
            "approval_contract_hash": prepared["agent_plan_approval_contract_hash"],
            "approval_contract": prepared["agent_plan_approval_contract"],
        },
    }
    if command_args is not None:
        tool["command_args"] = command_args
    return tool


def approved_seed_continuity_anchor_proposals_tool(db_session, project_id: str) -> dict:
    from app.services.writing_agent.continuity_anchor_seed_execution import (
        prepare_seed_continuity_anchor_proposals_execution,
    )

    prepared = prepare_seed_continuity_anchor_proposals_execution(db_session, project_id)
    return {
        "tool_name": "execute_seed_continuity_anchor_proposals_with_approval",
        "params": {
            "confirm_execute": True,
            "approval_contract_hash": prepared["agent_plan_approval_contract_hash"],
            "approval_contract": prepared["agent_plan_approval_contract"],
        },
    }


def prepare_apply_world_model_resolution(client, project_id: str, decisions: list[dict]) -> dict:
    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "准备应用世界模型提案决策",
            "tools": [
                {
                    "tool_name": "prepare_apply_world_model_proposal_resolution",
                    "params": {"decisions": decisions},
                }
            ],
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    return response.json()["steps"][0]["output"]


def approved_apply_world_model_resolution_tool(client, project_id: str, decisions: list[dict]) -> dict:
    prepared = prepare_apply_world_model_resolution(client, project_id, decisions)
    assert prepared["status"] == "approval_required"
    return {
        "tool_name": "execute_apply_world_model_proposal_resolution_with_approval",
        "params": {
            "decisions": decisions,
            "confirm_execute": True,
            "approval_contract_hash": prepared["agent_plan_approval_contract_hash"],
            "approval_contract": prepared["agent_plan_approval_contract"],
        },
    }


def apply_world_model_resolution_with_approval(client, project_id: str, decisions: list[dict]):
    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "确认应用世界模型提案决策",
            "tools": [approved_apply_world_model_resolution_tool(client, project_id, decisions)],
        },
    )
    assert response.status_code == 200
    return response


def planner_generate_chapter_plan(db_session, project_id: str, *, chapter_index: int) -> dict:
    from app.services.writing_agent.approval_contract import build_agent_plan_approval_contract
    from app.services.writing_agent.chapter_generation_execution import prepare_generate_chapter_execution

    prepared = prepare_generate_chapter_execution(db_session, project_id, chapter_index=chapter_index)
    plan_id = f"plan:generate-chapter-{chapter_index}"
    params = {
        "chapter_index": chapter_index,
        "confirm_execute": True,
        "approval_contract_hash": prepared["agent_plan_approval_contract_hash"],
        "approval_contract": prepared["agent_plan_approval_contract"],
    }
    step = {
        "step_index": 1,
        "step_id": f"step:execute-generate-chapter-{chapter_index}",
        "tool_name": "execute_generate_chapter_with_approval",
        "params": params,
        "mutability": "write",
        "requires_confirmation": True,
        "reason": f"生成第{chapter_index}章正文。",
    }
    tool = {
        "tool_name": "execute_generate_chapter_with_approval",
        "params": params,
        "planner": {
            "step_index": 1,
            "step_id": step["step_id"],
            "plan_id": plan_id,
            "source_projection_id": f"projection:generate-chapter-{chapter_index}",
            "mutability": "write",
            "requires_confirmation": True,
            "reason": step["reason"],
            "planner_version": "phase53.context_gate.v1",
        },
    }
    plan = {
        "status": "completed",
        "planner_version": "phase53.context_gate.v1",
        "project_id": project_id,
        "intent_class": "continue_next_chapter",
        "goal": f"生成第{chapter_index}章",
        "chapter_index": chapter_index,
        "steps": [step],
        "tools": [tool],
        "trace": {
            "plan_id": plan_id,
            "source_projection_id": f"projection:generate-chapter-{chapter_index}",
            "planner_version": "phase53.context_gate.v1",
            "selected_tools": ["execute_generate_chapter_with_approval"],
        },
    }
    plan["approval_contract"] = build_agent_plan_approval_contract(plan)
    return plan


def planner_revision_patch_plan(db_session, project_id: str, *, chapter_index: int, revision_id: str) -> dict:
    from app.services.writing_agent.approval_contract import build_agent_plan_approval_contract
    from app.services.writing_agent.revision_patch_execution import prepare_apply_planner_revision_patch_execution

    prepared = prepare_apply_planner_revision_patch_execution(
        db_session,
        project_id,
        chapter_index=chapter_index,
        revision_id=revision_id,
    )
    plan_id = f"plan:revision-patch-{chapter_index}"
    params = {
        "chapter_index": chapter_index,
        "revision_id": revision_id,
        "confirm_execute": True,
        "approval_contract_hash": prepared["agent_plan_approval_contract_hash"],
        "approval_contract": prepared["agent_plan_approval_contract"],
    }
    step = {
        "step_index": 1,
        "step_id": f"step:revision-patch-{chapter_index}",
        "tool_name": "execute_apply_planner_revision_patch_with_approval",
        "params": params,
        "mutability": "write",
        "requires_confirmation": True,
        "reason": f"应用第{chapter_index}章修订补丁。",
    }
    tool = {
        "tool_name": "execute_apply_planner_revision_patch_with_approval",
        "params": params,
        "planner": {
            "step_index": 1,
            "step_id": step["step_id"],
            "plan_id": plan_id,
            "source_projection_id": f"projection:revision-patch-{chapter_index}",
            "mutability": "write",
            "requires_confirmation": True,
            "reason": step["reason"],
            "planner_version": "phase53.context_gate.v1",
        },
    }
    plan = {
        "status": "completed",
        "planner_version": "phase53.context_gate.v1",
        "project_id": project_id,
        "intent_class": "apply_revision_patch",
        "goal": f"应用第{chapter_index}章修订补丁",
        "chapter_index": chapter_index,
        "steps": [step],
        "tools": [tool],
        "trace": {
            "plan_id": plan_id,
            "source_projection_id": f"projection:revision-patch-{chapter_index}",
            "planner_version": "phase53.context_gate.v1",
            "selected_tools": ["execute_apply_planner_revision_patch_with_approval"],
        },
    }
    plan["approval_contract"] = build_agent_plan_approval_contract(plan)
    return plan


def planner_world_model_resolution_plan(
    project_id: str,
    *,
    decisions: list[dict],
    apply_approval: dict | None = None,
) -> dict:
    from app.services.writing_agent.approval_contract import build_agent_plan_approval_contract

    plan_id = f"plan:world-model-resolution:{project_id}"
    if apply_approval is None:
        tool_name = "apply_world_model_proposal_resolution"
        params = {"confirm_apply": True, "decisions": decisions}
        intent_class = "apply_world_model_proposal_resolution"
    else:
        tool_name = "execute_apply_world_model_proposal_resolution_with_approval"
        params = {
            "decisions": decisions,
            "confirm_execute": True,
            "approval_contract_hash": apply_approval["agent_plan_approval_contract_hash"],
            "approval_contract": apply_approval["agent_plan_approval_contract"],
        }
        intent_class = "execute_apply_world_model_proposal_resolution_with_approval"
    step = {
        "step_index": 1,
        "step_id": f"step:world-model-resolution:{project_id}",
        "tool_name": tool_name,
        "params": params,
        "mutability": "guarded_write",
        "requires_confirmation": True,
        "reason": "应用世界模型提案处理决策。",
    }
    tool = {
        "tool_name": tool_name,
        "params": params,
        "planner": {
            "step_index": 1,
            "step_id": step["step_id"],
            "plan_id": plan_id,
            "source_projection_id": f"projection:world-model-resolution:{project_id}",
            "mutability": "guarded_write",
            "requires_confirmation": True,
            "reason": step["reason"],
            "planner_version": "phase53.context_gate.v1",
        },
    }
    plan = {
        "status": "completed",
        "planner_version": "phase53.context_gate.v1",
        "project_id": project_id,
        "intent_class": intent_class,
        "goal": "应用世界模型提案处理决策",
        "steps": [step],
        "tools": [tool],
        "trace": {
            "plan_id": plan_id,
            "source_projection_id": f"projection:world-model-resolution:{project_id}",
            "planner_version": "phase53.context_gate.v1",
            "selected_tools": [tool_name],
        },
    }
    plan["approval_contract"] = build_agent_plan_approval_contract(plan)
    return plan


def seed_pending_world_proposal(
    db_session,
    *,
    project_id: str,
    claim_id: str,
    predicate: str,
    subject_ref: str,
) -> WorldProposalItem:
    profile = db_session.query(ProjectProfileVersion).filter_by(project_id=project_id).one()
    bundle = create_bundle(
        db=db_session,
        project_id=project_id,
        project_profile_version_id=profile.id,
        profile_version=profile.version,
        created_by="athena.test",
        title="待审事实",
    )
    item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="athena.test",
        candidate=ProposalCandidateFactCreate(
            project_id=project_id,
            project_profile_version_id=profile.id,
            profile_version=profile.version,
            claim_id=claim_id,
            chapter_index=1,
            subject_ref=subject_ref,
            predicate=predicate,
            object_ref_or_value="雾港调查者",
            claim_layer="truth",
            evidence_refs=["chapter:1"],
            authority_type=DERIVED,
            confidence=0.9,
            contract_version=profile.contract_version,
        ),
    )
    db_session.commit()
    return item


def seed_longform_project(db_session, *, outline_chapters: list[int], generated_chapters: list[int]) -> Project:
    project = Project(
        name="Preflight Novel",
        genre="都市悬疑",
        target_chapter_count=600,
        target_word_count=1200000,
    )
    db_session.add(project)
    db_session.flush()
    setup = Setup(
        project_id=project.id,
        status="generated",
        world_building={
            "background": "雾港被记忆异常和雾晶实验影响。",
            "geography": "故事发生在‘雾港’和‘旧灯塔’，地下实验室藏有‘雾晶核心’。",
            "society": "‘雾安局’控制异常档案，‘记忆诊所’收容失忆者。",
            "rules": "雾晶只能放大记忆回声，不能凭空创造真实记忆。",
        },
        characters=[
            {
                "name": "林深",
                "personality": "冷静",
                "background": "私家侦探",
                "goals": "查清十年前雾灾真相",
                "character_status": "alive",
            },
            {
                "name": "苏晚晴",
                "personality": "敏锐",
                "background": "失踪者家属",
                "goals": "找到父亲",
                "character_status": "alive",
            },
        ],
        core_concept={"theme": "记忆与真相", "hook": "雾港会回放被删除的记忆"},
    )
    db_session.add(setup)
    db_session.add(
        Storyline(
            project_id=project.id,
            status="generated",
            plotlines=[{"name": "主线", "type": "main", "summary": "追查雾港记忆异常", "milestones": []}],
            foreshadowing=[],
        )
    )
    outline = Outline(
        project_id=project.id,
        total_chapters=600,
        status="generated",
        chapters=[
            {
                "chapter_index": index,
                "title": f"雾港线索{index}",
                "summary": f"第{index}章推进雾港记忆异常调查。",
                "scenes": ["调查现场", "冲突升级"],
                "characters": ["林深", "苏晚晴"],
                "purpose": "推进主线",
            }
            for index in outline_chapters
        ],
        plotlines=[],
        foreshadowing=[],
    )
    db_session.add(outline)
    for index in generated_chapters:
        db_session.add(
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"雾港线索{index}",
                content=f"林深和苏晚晴在雾港旧灯塔调查雾晶核心。第{index}章里，雾安局巡逻队逼近，记忆诊所留下新的证词。",
                word_count=80,
                status="generated",
            )
        )
    db_session.commit()
    db_session.refresh(project)
    return project


def prepare_longform_batch_execution_contract(client, project_id: str) -> dict:
    enqueue_output = enqueue_longform_batch_with_approval(client, project_id, start_chapter=2, batch_size=1)
    task_id = enqueue_output["task"]["id"]
    preflight_longform_batch_with_approval(client, project_id, task_id, max_chapters=1)
    prepare_response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "准备长篇批次执行准备审批契约",
            "tools": [
                {
                    "tool_name": "prepare_longform_chapter_batch_execution_prepare",
                    "params": {"task_id": task_id},
                }
            ],
        },
    )
    prepare_output = prepare_response.json()["steps"][0]["output"]
    execute_response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "确认后写入长篇批次执行契约",
            "tools": [
                {
                    "tool_name": "execute_longform_chapter_batch_execution_prepare_with_approval",
                    "params": {
                        "task_id": task_id,
                        "confirm_execute": True,
                        "approval_contract_hash": prepare_output["agent_plan_approval_contract_hash"],
                        "approval_contract": prepare_output["agent_plan_approval_contract"],
                    },
                }
            ],
        },
    )
    output = execute_response.json()["steps"][0]["output"]
    return {
        "task_id": task_id,
        "attempt_manifest_hash": output["attempt_manifest_hash"],
        "approval_contract_hash": output["approval_contract_hash"],
        "attempt_manifest": output["attempt_manifest"],
        "approval_contract": output["approval_contract"],
        "agent_plan": output["agent_plan"],
        "agent_plan_approval_contract": output["agent_plan_approval_contract"],
        "agent_plan_approval_contract_hash": output["agent_plan_approval_contract_hash"],
    }


def prepare_enqueue_longform_batch(
    client,
    project_id: str,
    *,
    start_chapter: int,
    batch_size: int,
    source_run_id: str | None = None,
) -> dict:
    params = {"start_chapter": start_chapter, "batch_size": batch_size}
    if source_run_id is not None:
        params["source_run_id"] = source_run_id
    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "准备把章节加入批次队列",
            "tools": [{"tool_name": "prepare_enqueue_longform_chapter_batch", "params": params}],
        },
    )
    assert response.status_code == 200
    return response.json()["steps"][0]["output"]


def enqueue_longform_batch_with_approval(
    client,
    project_id: str,
    *,
    start_chapter: int,
    batch_size: int,
    source_run_id: str | None = None,
) -> dict:
    prepared = prepare_enqueue_longform_batch(
        client,
        project_id,
        start_chapter=start_chapter,
        batch_size=batch_size,
        source_run_id=source_run_id,
    )
    params = {
        "start_chapter": start_chapter,
        "batch_size": batch_size,
        "plan_hash": prepared["plan_hash"],
        "confirm_execute": True,
        "approval_contract_hash": prepared["agent_plan_approval_contract_hash"],
        "approval_contract": prepared["agent_plan_approval_contract"],
    }
    if source_run_id is not None:
        params["source_run_id"] = source_run_id
    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "确认加入批次队列",
            "tools": [{"tool_name": "execute_enqueue_longform_chapter_batch_with_approval", "params": params}],
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    return response.json()["steps"][0]["output"]


def preflight_longform_batch_with_approval(
    client,
    project_id: str,
    task_id: str,
    *,
    max_chapters: int,
) -> dict:
    prepared_response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "准备预检长篇批次任务",
            "tools": [
                {
                    "tool_name": "prepare_longform_chapter_batch_preflight",
                    "params": {"task_id": task_id, "max_chapters": max_chapters},
                }
            ],
        },
    )
    assert prepared_response.status_code == 200
    prepared = prepared_response.json()["steps"][0]["output"]
    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "确认预检长篇批次任务",
            "tools": [
                {
                    "tool_name": "execute_longform_chapter_batch_preflight_with_approval",
                    "params": {
                        "task_id": task_id,
                        "max_chapters": max_chapters,
                        "confirm_execute": True,
                        "approval_contract_hash": prepared["agent_plan_approval_contract_hash"],
                        "approval_contract": prepared["agent_plan_approval_contract"],
                    },
                }
            ],
        },
    )
    assert response.status_code == 200
    return response.json()


def execute_approved_longform_batch_chapter(client, project_id: str, prepared: dict, monkeypatch) -> dict:
    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        assert action_type == "generate_chapter"
        assert action_params == {"chapter_index": 2}
        self.db.add(
            ChapterContent(
                project_id=project_id,
                chapter_index=2,
                title="雾港线索2",
                content="林深和苏晚晴追入记忆诊所后巷，发现雾晶核心的回声正在扩大。",
                word_count=2200,
                status="generated",
            )
        )
        self.db.commit()
        return {"status": "success", "chapter_index": 2, "trace_id": "trace-batch-chapter-2"}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)
    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "执行已批准的长篇批次",
            "tools": [
                {
                    "tool_name": "execute_longform_chapter_batch",
                    "params": {
                        "task_id": prepared["task_id"],
                        "confirm_execute": True,
                        "attempt_manifest_hash": prepared["attempt_manifest_hash"],
                        "approval_contract_hash": prepared["approval_contract_hash"],
                    },
                }
            ],
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    return response.json()["steps"][0]["output"]


def review_executed_longform_batch_chapter(
    client,
    project_id: str,
    task_id: str,
    monkeypatch,
    *,
    status: str,
    calls: list[str] | None = None,
) -> dict:
    def fake_quality(db, project_id: str, chapter_index: int):
        if calls is not None:
            calls.append("quality")
        if status == "needs_revision":
            return {
                "status": "blocked",
                "chapter_index": chapter_index,
                "finding_count": 1,
                "blocker_count": 1,
                "findings": [
                    {
                        "code": "generic_chapter_title",
                        "severity": "blocker",
                        "message": "标题仍是占位标题。",
                        "evidence": {},
                    }
                ],
                "recommended_actions": ["revise_chapter"],
            }
        return {
            "status": "ready",
            "chapter_index": chapter_index,
            "finding_count": 0,
            "blocker_count": 0,
            "findings": [],
            "recommended_actions": [],
        }

    def fake_continuity(db, project_id: str, chapter_index: int, *, lookback: int):
        if calls is not None:
            calls.append("continuity")
        return {
            "status": "ready",
            "chapter_index": chapter_index,
            "finding_count": 0,
            "blocker_count": 0,
            "findings": [],
            "recommended_actions": [],
        }

    def fake_world_model(db, project_id: str, chapter_index: int):
        if calls is not None:
            calls.append("world_model")
        return {"status": "skipped", "reason": "missing_world_model_profile", "chapter_index": chapter_index}

    monkeypatch.setattr("app.core.chapter_quality_review.review_chapter_quality", fake_quality)
    monkeypatch.setattr("app.core.chapter_continuity_review.review_chapter_continuity", fake_continuity)
    monkeypatch.setattr("app.core.athena_longform.analyze_chapter_to_world_proposals", fake_world_model)
    prepare_response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "准备审查已执行的长篇批次",
            "tools": [
                {
                    "tool_name": "prepare_longform_chapter_batch_execution_review",
                    "params": {"task_id": task_id},
                }
            ],
        },
    )
    assert prepare_response.status_code == 200
    assert prepare_response.json()["status"] == "success"
    prepare_output = prepare_response.json()["steps"][0]["output"]
    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "确认后审查已执行的长篇批次",
            "tools": [
                {
                    "tool_name": "execute_longform_chapter_batch_execution_review_with_approval",
                    "params": {
                        "task_id": task_id,
                        "confirm_execute": True,
                        "approval_contract_hash": prepare_output["agent_plan_approval_contract_hash"],
                        "approval_contract": prepare_output["agent_plan_approval_contract"],
                    },
                }
            ],
        },
    )
    assert response.status_code == 200
    expected_status = "blocked" if status == "needs_revision" else "success"
    assert response.json()["status"] == expected_status
    return response.json()["steps"][0]["output"]


def route_reviewed_longform_batch_after_review(
    client,
    project_id: str,
    *,
    task_id: str,
    next_batch_size: int | None = None,
    expected_post_generation_review_hash: str | None = None,
) -> dict:
    params: dict[str, object] = {"task_id": task_id}
    if next_batch_size is not None:
        params["next_batch_size"] = next_batch_size
    if expected_post_generation_review_hash is not None:
        params["expected_post_generation_review_hash"] = expected_post_generation_review_hash
    prepare_response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "准备路由长篇批次生成后审查结果",
            "tools": [{"tool_name": "prepare_longform_chapter_batch_after_review_route", "params": params}],
        },
    )
    assert prepare_response.status_code == 200
    prepare_payload = prepare_response.json()
    assert prepare_payload["status"] == "success"
    prepare_output = prepare_payload["steps"][0]["output"]
    if prepare_output["status"] == "skipped":
        return prepare_payload
    assert prepare_output["status"] == "approval_required"

    execute_params = {
        **params,
        "confirm_execute": True,
        "approval_contract_hash": prepare_output["agent_plan_approval_contract_hash"],
        "approval_contract": prepare_output["agent_plan_approval_contract"],
    }
    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "确认后路由长篇批次生成后审查结果",
            "tools": [
                {
                    "tool_name": "execute_longform_chapter_batch_after_review_route_with_approval",
                    "params": execute_params,
                }
            ],
        },
    )
    assert response.status_code == 200
    return response.json()
