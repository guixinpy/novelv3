from app.models import (
    ChapterContent,
    Project,
    ProjectProfileVersion,
    Setup,
    WorldCharacter,
    WorldFactClaim,
    WorldProposalBundle,
    WorldProposalItem,
    WorldRule,
)


def _seed_project_with_setup(db_session):
    project = Project(name="Athena Longform", genre="东方奇幻悬疑")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    setup = Setup(
        project_id=project.id,
        status="generated",
        world_building={
            "background": "雾港城被潮雾和旧神契约笼罩。",
            "rules": "旧灯塔熄灭时，亡者不能被直接召回。",
        },
        characters=[
            {
                "name": "林舟",
                "personality": "谨慎",
                "background": "雾港守夜人",
                "goals": "查清旧灯塔失火真相",
                "character_status": "alive",
            },
            {
                "name": "沈聆",
                "personality": "冷静",
                "background": "档案修复师",
                "goals": "找回失踪档案",
                "character_status": "alive",
            },
        ],
        core_concept={"theme": "记忆与真相", "hook": "旧灯塔会篡改证词"},
    )
    db_session.add(setup)
    db_session.commit()
    return project


def test_import_setup_creates_formal_profile_entities_and_rules(client, db_session):
    project = _seed_project_with_setup(db_session)

    response = client.post(f"/api/v1/projects/{project.id}/athena/ontology/import-setup")

    assert response.status_code == 200
    payload = response.json()
    assert payload["profile_version"] == 1
    assert payload["created"]["characters"] == 2
    assert payload["created"]["rules"] == 1
    assert db_session.query(ProjectProfileVersion).filter_by(project_id=project.id).count() == 1
    assert db_session.query(WorldCharacter).filter_by(project_id=project.id).count() == 2
    assert db_session.query(WorldRule).filter_by(project_id=project.id).count() == 1

    ontology = client.get(f"/api/v1/projects/{project.id}/athena/ontology").json()
    assert ontology["profile_version"] == 1
    assert {item["name"] for item in ontology["entities"]["characters"]} == {"林舟", "沈聆"}


def test_analyze_chapter_creates_reviewable_candidates_without_duplicates(client, db_session):
    project = _seed_project_with_setup(db_session)
    client.post(f"/api/v1/projects/{project.id}/athena/ontology/import-setup")
    db_session.add(
        ChapterContent(
            project_id=project.id,
            chapter_index=1,
            title="第一章 雾港",
            content="林舟走进雾港城。沈聆在旧灯塔旁翻开档案。林舟再次听见潮声。",
            word_count=30,
            status="generated",
        )
    )
    db_session.commit()

    response = client.post(f"/api/v1/projects/{project.id}/athena/evolution/chapters/1/analyze")
    rerun = client.post(f"/api/v1/projects/{project.id}/athena/evolution/chapters/1/analyze")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["created"]["proposal_items"] == 2
    assert payload["skipped"]["duplicates"] == 0
    assert rerun.status_code == 200
    assert rerun.json()["created"]["proposal_items"] == 0
    assert rerun.json()["skipped"]["duplicates"] == 2
    assert db_session.query(WorldProposalBundle).filter_by(project_id=project.id).count() == 1
    assert db_session.query(WorldProposalItem).filter_by(project_id=project.id).count() == 2
    assert db_session.query(WorldFactClaim).filter_by(project_id=project.id).count() == 0


def test_approved_candidate_is_injected_into_chapter_context(client, db_session):
    project = _seed_project_with_setup(db_session)
    client.post(f"/api/v1/projects/{project.id}/athena/ontology/import-setup")
    db_session.add(
        ChapterContent(
            project_id=project.id,
            chapter_index=1,
            title="第一章 雾港",
            content="林舟走进雾港城。沈聆在旧灯塔旁翻开档案。",
            word_count=24,
            status="generated",
        )
    )
    db_session.commit()
    client.post(f"/api/v1/projects/{project.id}/athena/evolution/chapters/1/analyze")
    item = db_session.query(WorldProposalItem).filter_by(project_id=project.id, subject_ref="char.林舟").one()

    review = client.post(
        f"/api/v1/projects/{project.id}/athena/evolution/proposals/{item.id}/review",
        json={
            "reviewer_ref": "tester",
            "action": "approve",
            "reason": "确认出场事实",
            "evidence_refs": ["chapter:1"],
            "edited_fields": {},
        },
    )
    context = client.get(f"/api/v1/projects/{project.id}/athena/context/chapter/2")

    assert review.status_code == 200
    assert context.status_code == 200
    payload = context.json()
    assert payload["chapter_index"] == 2
    assert payload["profile_version"] == 1
    assert "林舟" in payload["prompt_context"]
    assert "presence_count" in payload["prompt_context"]
