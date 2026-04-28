from app.core.world_contracts import DERIVED
from app.core.embedding_service import get_embedding_provider
from app.models import ChapterContent, Outline, Project, ProjectProfileVersion, Setup, WorldFactClaim


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
    assert payload["embedding_provider"] == "local"
