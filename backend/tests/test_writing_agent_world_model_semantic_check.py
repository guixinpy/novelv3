import pytest

from app.core.world_contracts import DERIVED
from app.models import AIModelCallTrace, ChapterContent, GenreProfile, Project, ProjectProfileVersion, WorldFactClaim


@pytest.mark.asyncio
async def test_world_model_semantic_check_records_l5_trace_without_world_writes(db_session):
    from app.services.writing_agent.world_model_semantic_check import inspect_agent_world_model_semantic_check

    project, profile = _seed_profiled_project(db_session, "World Semantic Check")
    db_session.add(
        ChapterContent(
            project_id=project.id,
            chapter_index=3,
            title="旧塔回声",
            content="顾衍在旧塔底层倒下，众人确认他已经死亡。蓝焰证词却说他稍后仍会出现。",
            status="generated",
        )
    )
    db_session.add(
        WorldFactClaim(
            project_id=project.id,
            project_profile_version_id=profile.id,
            profile_version=profile.version,
            claim_id="claim.hero.status",
            chapter_index=1,
            subject_ref="char.hero",
            predicate="status",
            object_ref_or_value="alive",
            claim_layer="truth",
            claim_status="confirmed",
            evidence_refs=["chapter:1"],
            authority_type=DERIVED,
            confidence=0.93,
            contract_version=profile.contract_version,
        )
    )
    db_session.commit()
    before_fact_count = db_session.query(WorldFactClaim).filter(WorldFactClaim.project_id == project.id).count()
    ai_service = _FakeWorldSemanticAIService(
        '{"overall_status":"issues_found","summary":"章节死亡叙述和确认事实冲突。",'
        '"issues":[{"code":"fact_semantic_conflict","severity":"warning",'
        '"message":"章节声称顾衍死亡，但世界模型确认其状态为存活。",'
        '"subject_ref":"char.hero","predicate":"status","claim_id":"claim.hero.status",'
        '"evidence_excerpt":"众人确认他已经死亡"}]}'
    )

    output = await inspect_agent_world_model_semantic_check(
        db_session,
        project.id,
        chapter_index=3,
        subject_ref="char.hero",
        max_facts=5,
        ai_service=ai_service,
    )

    assert output["status"] == "completed"
    assert output["semantic_check"] == {
        "layer": "L5 Semantic Checks",
        "checker_name": "semantic_consistency_llm",
        "status": "issues_found",
        "issue_count": 1,
        "summary": "章节死亡叙述和确认事实冲突。",
    }
    assert output["issues"] == [
        {
            "code": "fact_semantic_conflict",
            "severity": "warning",
            "message": "章节声称顾衍死亡，但世界模型确认其状态为存活。",
            "subject_ref": "char.hero",
            "predicate": "status",
            "claim_id": "claim.hero.status",
            "evidence_excerpt": "众人确认他已经死亡",
        }
    ]
    assert output["fact_window"]["returned_facts"] == 1
    assert output["llm_prompt_contract"]["trace_type"] == "world_model_semantic_check"
    assert output["side_effects"] == {
        "executed": ["world_model_semantic_check_trace"],
        "skipped": ["world_fact_write", "world_model_proposal_write"],
    }
    assert output["recommended_next_tools"] == [
        "prepare_analyze_chapter_world_model_execution",
        "review_world_model_proposals",
        "inspect_agent_world_model_route",
    ]
    assert output["trace"]["llm_call_executed"] is True
    assert output["trace"]["trace_type"] == "world_model_semantic_check"
    assert ai_service.calls[0]["kwargs"]["response_format"] == {"type": "json_object"}
    assert db_session.query(WorldFactClaim).filter(WorldFactClaim.project_id == project.id).count() == before_fact_count

    trace = db_session.query(AIModelCallTrace).filter_by(id=output["trace"]["trace_id"]).one()
    assert trace.status == "success"
    assert trace.trace_type == "world_model_semantic_check"
    assert trace.chapter_index == 3
    assert trace.prompt_tokens == 17
    assert trace.completion_tokens == 9
    assert trace.context_blocks[0]["kind"] == "chapter_content"
    assert trace.context_blocks[1]["kind"] == "world_model_fact_window"
    assert trace.trace_metadata["world_model_semantic_check"]["checker_name"] == "semantic_consistency_llm"
    assert trace.trace_metadata["world_model_semantic_check"]["issue_count"] == 1


@pytest.mark.asyncio
async def test_world_model_semantic_check_blocks_without_profile_before_model_call(db_session):
    from app.services.writing_agent.world_model_semantic_check import inspect_agent_world_model_semantic_check

    project = Project(name="World Semantic Missing Profile")
    db_session.add(project)
    db_session.commit()
    ai_service = _FakeWorldSemanticAIService('{"overall_status":"passed","issues":[]}')

    output = await inspect_agent_world_model_semantic_check(
        db_session,
        project.id,
        chapter_index=1,
        ai_service=ai_service,
    )

    assert output["status"] == "blocked"
    assert output["reason"] == "missing_world_model_profile"
    assert output["semantic_check"]["checker_name"] == "semantic_consistency_llm"
    assert output["side_effects"] == {"executed": [], "skipped": ["world_model_semantic_check_trace"]}
    assert ai_service.calls == []


def _seed_profiled_project(db_session, name: str) -> tuple[Project, ProjectProfileVersion]:
    project = Project(name=name, ai_model="fake-world-semantic-model")
    genre_profile = GenreProfile(
        canonical_id=f"{name.lower().replace(' ', '-')}-profile",
        display_name=name,
        contract_version="world.contract.v1",
    )
    db_session.add_all([project, genre_profile])
    db_session.commit()
    profile = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=genre_profile.id,
        version=1,
        contract_version="world.contract.v1",
        profile_payload={},
    )
    db_session.add(profile)
    db_session.commit()
    return project, profile


class _FakeWorldSemanticAIService:
    def __init__(self, content: str):
        self.content = content
        self.calls: list[dict[str, object]] = []

    async def complete(self, messages, **kwargs):
        self.calls.append({"messages": messages, "kwargs": kwargs})
        return _FakeWorldSemanticResult(self.content)


class _FakeWorldSemanticResult:
    def __init__(self, content: str):
        self.content = content
        self.prompt_tokens = 17
        self.completion_tokens = 9
