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
