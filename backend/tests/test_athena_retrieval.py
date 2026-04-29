from app.core.world_contracts import DERIVED
from app.core.embedding_service import get_embedding_provider
from app.core.athena_retrieval import search_retrieval
from app.core.world_proposal_service import create_bundle, review_proposal_item, rollback_review, write_candidate_fact
from app.models import (
    ChapterContent,
    Outline,
    Project,
    ProjectProfileVersion,
    RetrievalDocument,
    RetrievalTerm,
    Setup,
    WorldFactClaim,
)
from app.schemas.world_proposals import ProposalCandidateFactCreate


def test_embedding_provider_defaults_to_local_without_explicit_remote_mode(monkeypatch):
    monkeypatch.setenv("EMBEDDING_API_KEY", "test-key")
    monkeypatch.setenv("EMBEDDING_MODEL", "remote-model")
    monkeypatch.delenv("EMBEDDING_PROVIDER", raising=False)

    provider = get_embedding_provider()

    assert provider.provider_name == "local"


def _seed_retrieval_project(db_session):
    project = Project(name="Athena Retrieval", genre="东方奇幻悬疑")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    db_session.add(
        Setup(
            project_id=project.id,
            status="generated",
            world_building={
                "background": "雾港城被潮雾笼罩。",
                "rules": "旧灯塔熄灭时，亡者不能被直接召回。",
            },
            characters=[
                {
                    "name": "林舟",
                    "personality": "谨慎",
                    "background": "雾港守夜人",
                    "goals": "查清旧灯塔失火真相",
                    "character_status": "alive",
                }
            ],
            core_concept={"theme": "记忆与真相"},
        )
    )
    db_session.add(
        Outline(
            project_id=project.id,
            total_chapters=3,
            status="generated",
            chapters=[
                {"chapter_index": 1, "title": "雾港来信", "summary": "林舟发现旧灯塔失火的证词互相矛盾。"},
                {"chapter_index": 2, "title": "亡者契约", "summary": "沈聆发现旧灯塔熄灭会阻断亡者召回。"},
                {"chapter_index": 3, "title": "灯塔再燃", "summary": "林舟准备利用旧灯塔和亡者契约反查真相。"},
            ],
        )
    )
    db_session.add_all(
        [
            ChapterContent(
                project_id=project.id,
                chapter_index=1,
                title="雾港来信",
                content="林舟在潮雾里走近旧灯塔。墙上的证词说，旧灯塔失火那夜有人听见亡者敲门。",
                word_count=40,
                status="generated",
            ),
            ChapterContent(
                project_id=project.id,
                chapter_index=2,
                title="亡者契约",
                content="沈聆翻出档案：旧灯塔熄灭时，亡者不能被直接召回，守夜人只能等待潮声停下。",
                word_count=42,
                status="generated",
            ),
        ]
    )
    db_session.commit()
    return project


def _seed_confirmed_fact(db_session, project_id: str):
    profile = db_session.query(ProjectProfileVersion).filter_by(project_id=project_id).one()
    claim = WorldFactClaim(
        project_id=project_id,
        project_profile_version_id=profile.id,
        profile_version=profile.version,
        claim_id="claim.old_lighthouse.recall_ban",
        chapter_index=2,
        intra_chapter_seq=1,
        subject_ref="rule.old_lighthouse",
        predicate="recall_constraint",
        object_ref_or_value="旧灯塔熄灭时，亡者不能被直接召回。",
        claim_layer="truth",
        claim_status="confirmed",
        evidence_refs=["chapter:2"],
        authority_type=DERIVED,
        confidence=0.92,
        contract_version=profile.contract_version,
    )
    db_session.add(claim)
    db_session.commit()
    return claim


def _write_reviewable_fact_candidate(db_session, project_id: str):
    profile = db_session.query(ProjectProfileVersion).filter_by(project_id=project_id).one()
    bundle = create_bundle(
        db=db_session,
        project_id=project_id,
        project_profile_version_id=profile.id,
        profile_version=profile.version,
        created_by="athena.test",
        title="增量检索候选",
    )
    return write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="athena.test",
        candidate=ProposalCandidateFactCreate(
            project_id=project_id,
            project_profile_version_id=profile.id,
            profile_version=profile.version,
            claim_id="claim.linzhou.role.incremental",
            chapter_index=2,
            subject_ref="char.林舟",
            predicate="role",
            object_ref_or_value="雾港城守夜人",
            claim_layer="truth",
            evidence_refs=["chapter:2"],
            authority_type=DERIVED,
            confidence=0.93,
            notes="林舟在雾港城承担守夜职责。",
            contract_version=profile.contract_version,
        ),
    )


def test_reindex_builds_searchable_chunks_for_chapters_and_confirmed_facts(client, db_session):
    project = _seed_retrieval_project(db_session)
    client.post(f"/api/v1/projects/{project.id}/athena/ontology/import-setup")
    _seed_confirmed_fact(db_session, project.id)

    response = client.post(f"/api/v1/projects/{project.id}/athena/retrieval/reindex")
    search = client.get(f"/api/v1/projects/{project.id}/athena/retrieval/search?q=旧灯塔亡者召回&limit=5")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["indexed"]["documents"] >= 3
    assert payload["indexed"]["chunks"] >= 3

    assert search.status_code == 200
    results = search.json()
    assert results["total"] >= 2
    assert results["items"][0]["score"] >= results["items"][-1]["score"]
    assert {item["source_type"] for item in results["items"]} >= {"chapter", "world_fact"}
    assert any("亡者不能被直接召回" in item["snippet"] for item in results["items"])


def test_reindex_builds_indexed_lexical_terms_for_local_search(client, db_session):
    project = _seed_retrieval_project(db_session)
    client.post(f"/api/v1/projects/{project.id}/athena/ontology/import-setup")
    _seed_confirmed_fact(db_session, project.id)

    response = client.post(f"/api/v1/projects/{project.id}/athena/retrieval/reindex")
    diagnostics = client.get(f"/api/v1/projects/{project.id}/athena/retrieval/diagnostics")

    term_count = db_session.query(RetrievalTerm).filter_by(project_id=project.id).count()
    assert response.status_code == 200
    assert term_count > 0
    assert diagnostics.status_code == 200
    assert diagnostics.json()["total_terms"] == term_count


def test_search_retrieval_uses_lexical_shortlist_for_late_relevant_chunks(client, db_session):
    project = Project(name="Late Retrieval", genre="东方奇幻悬疑")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    db_session.add_all(
        [
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"无关章节 {index}",
                content=f"第{index}章只有普通街巷和潮声，没有目标线索。",
                word_count=20,
                status="generated",
            )
            for index in range(1, 421)
        ]
        + [
            ChapterContent(
                project_id=project.id,
                chapter_index=421,
                title="迟到的钥匙",
                content="档案最深处写着：秘银钥匙沉睡在旧灯塔底层，只有潮汐归零时才会苏醒。",
                word_count=32,
                status="generated",
            )
        ]
    )
    db_session.commit()

    response = client.post(f"/api/v1/projects/{project.id}/athena/retrieval/reindex")
    results = search_retrieval(db_session, project.id, "秘银钥匙沉睡旧灯塔", limit=3)

    assert response.status_code == 200
    assert response.json()["indexed"]["documents"] == 421
    assert any("秘银钥匙沉睡" in item["snippet"] for item in results["items"])


def test_chapter_context_includes_retrieved_evidence(client, db_session):
    project = _seed_retrieval_project(db_session)
    client.post(f"/api/v1/projects/{project.id}/athena/ontology/import-setup")
    _seed_confirmed_fact(db_session, project.id)
    client.post(f"/api/v1/projects/{project.id}/athena/retrieval/reindex")

    response = client.get(f"/api/v1/projects/{project.id}/athena/context/chapter/3")

    assert response.status_code == 200
    payload = response.json()
    retrieval_sections = [section for section in payload["sections"] if section["key"] == "retrieval"]
    assert retrieval_sections
    assert "【检索证据】" in payload["prompt_context"]
    assert "旧灯塔" in payload["prompt_context"]
    assert "亡者" in payload["prompt_context"]


def test_retrieval_diagnostics_and_single_chapter_index_endpoint(client, db_session):
    project = _seed_retrieval_project(db_session)

    response = client.post(f"/api/v1/projects/{project.id}/athena/retrieval/chapters/2/index")
    diagnostics = client.get(f"/api/v1/projects/{project.id}/athena/retrieval/diagnostics")

    assert response.status_code == 200
    assert response.json()["chapter_index"] == 2
    assert response.json()["indexed"]["documents"] == 1
    assert diagnostics.status_code == 200
    payload = diagnostics.json()
    assert payload["total_documents"] == 1
    assert payload["total_chunks"] >= 1
    assert payload["total_terms"] >= payload["total_chunks"]
    assert payload["embedding_provider"] == "local"


def test_approval_incrementally_indexes_world_fact_without_full_reindex(client, db_session):
    project = _seed_retrieval_project(db_session)
    client.post(f"/api/v1/projects/{project.id}/athena/ontology/import-setup")
    item = _write_reviewable_fact_candidate(db_session, project.id)

    review = review_proposal_item(
        db=db_session,
        proposal_item_id=item.id,
        reviewer_ref="tester",
        action="approve",
        reason="确认进入世界模型",
        evidence_refs=["chapter:2"],
    )

    documents = db_session.query(RetrievalDocument).filter_by(project_id=project.id, source_type="world_fact").all()
    search = search_retrieval(db_session, project.id, "雾港城守夜人", source_type="world_fact")

    assert review.created_truth_claim_id == "claim.linzhou.role.incremental"
    assert [document.source_ref for document in documents] == ["claim:claim.linzhou.role.incremental"]
    assert search["items"]
    assert "雾港城守夜人" in search["items"][0]["snippet"]


def test_rollback_removes_incremental_world_fact_retrieval_document(client, db_session):
    project = _seed_retrieval_project(db_session)
    client.post(f"/api/v1/projects/{project.id}/athena/ontology/import-setup")
    item = _write_reviewable_fact_candidate(db_session, project.id)
    approval = review_proposal_item(
        db=db_session,
        proposal_item_id=item.id,
        reviewer_ref="tester",
        action="approve",
        reason="先并入世界模型",
        evidence_refs=["chapter:2"],
    )
    assert db_session.query(RetrievalDocument).filter_by(project_id=project.id, source_type="world_fact").count() == 1

    rollback_review(
        db=db_session,
        review_id=approval.id,
        reviewer_ref="tester",
        reason="证据撤回",
        evidence_refs=["chapter:3"],
    )

    assert db_session.query(RetrievalDocument).filter_by(project_id=project.id, source_type="world_fact").count() == 0
