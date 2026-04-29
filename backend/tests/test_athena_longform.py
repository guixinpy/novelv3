from app.models import (
    ChapterContent,
    Project,
    ProjectProfileVersion,
    Setup,
    WorldArtifact,
    WorldCharacter,
    WorldFaction,
    WorldFactClaim,
    WorldLocation,
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
            "geography": "故事发生在‘旧灯塔’和‘雾港城’，旧灯塔地下藏有‘黑潮门’。",
            "society": "‘档案局’封存证词，‘守夜人联盟’负责巡查雾港。",
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
    assert payload["created"]["locations"] == 2
    assert payload["created"]["factions"] == 2
    assert payload["created"]["artifacts"] == 1
    assert payload["created"]["rules"] == 1
    assert db_session.query(ProjectProfileVersion).filter_by(project_id=project.id).count() == 1
    assert db_session.query(WorldCharacter).filter_by(project_id=project.id).count() == 2
    assert db_session.query(WorldLocation).filter_by(project_id=project.id).count() == 2
    assert db_session.query(WorldFaction).filter_by(project_id=project.id).count() == 2
    assert db_session.query(WorldArtifact).filter_by(project_id=project.id).count() == 1
    assert db_session.query(WorldRule).filter_by(project_id=project.id).count() == 1

    ontology = client.get(f"/api/v1/projects/{project.id}/athena/ontology").json()
    assert ontology["profile_version"] == 1
    assert {item["name"] for item in ontology["entities"]["characters"]} == {"林舟", "沈聆"}
    assert {item["name"] for item in ontology["entities"]["locations"]} == {"旧灯塔", "雾港城"}
    assert {item["name"] for item in ontology["entities"]["factions"]} == {"档案局", "守夜人联盟"}
    assert {item["name"] for item in ontology["entities"]["artifacts"]} == {"黑潮门"}


def test_import_setup_preview_reports_candidates_without_writing_world_model(client, db_session):
    project = _seed_project_with_setup(db_session)

    response = client.get(f"/api/v1/projects/{project.id}/athena/ontology/import-setup/preview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "preview"
    assert payload["project_profile_exists"] is False
    assert payload["would_create"]["profile"] == 1
    assert payload["would_create"]["characters"] == 2
    assert payload["would_create"]["locations"] == 2
    assert payload["would_create"]["factions"] == 2
    assert payload["would_create"]["artifacts"] == 1
    assert payload["would_create"]["rules"] == 1
    assert {item["name"] for item in payload["candidates"]["characters"]} == {"林舟", "沈聆"}
    assert db_session.query(ProjectProfileVersion).filter_by(project_id=project.id).count() == 0
    assert db_session.query(WorldCharacter).filter_by(project_id=project.id).count() == 0


def test_import_setup_extracts_unquoted_world_terms_for_preview_and_import(client, db_session):
    project = Project(name="Unquoted Setup", genre="东方奇幻悬疑")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    db_session.add(
        Setup(
            project_id=project.id,
            status="generated",
            world_building={
                "background": "雾港城旁矗立旧灯塔，黑潮门由档案局看守。",
                "geography": "秘银钥匙存放在钟塔，守夜人联盟控制港口。",
                "rules": "黑潮门开启时，旧灯塔必须保持点亮。",
            },
            characters=[],
            core_concept={"hook": "档案局隐瞒黑潮门的真实用途。"},
        )
    )
    db_session.commit()

    preview = client.get(f"/api/v1/projects/{project.id}/athena/ontology/import-setup/preview")
    imported = client.post(f"/api/v1/projects/{project.id}/athena/ontology/import-setup")

    assert preview.status_code == 200
    preview_payload = preview.json()
    assert {item["name"] for item in preview_payload["candidates"]["locations"]} >= {"雾港城", "旧灯塔", "钟塔"}
    assert {item["name"] for item in preview_payload["candidates"]["factions"]} >= {"档案局", "守夜人联盟"}
    assert {item["name"] for item in preview_payload["candidates"]["artifacts"]} >= {"黑潮门", "秘银钥匙"}
    assert imported.status_code == 200
    assert {item.name for item in db_session.query(WorldLocation).filter_by(project_id=project.id).all()} >= {
        "雾港城",
        "旧灯塔",
        "钟塔",
    }
    assert {item.name for item in db_session.query(WorldFaction).filter_by(project_id=project.id).all()} >= {
        "档案局",
        "守夜人联盟",
    }
    assert {item.name for item in db_session.query(WorldArtifact).filter_by(project_id=project.id).all()} >= {
        "黑潮门",
        "秘银钥匙",
    }


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
    assert payload["created"]["proposal_items"] == 7
    assert payload["skipped"]["duplicates"] == 0
    assert rerun.status_code == 200
    assert rerun.json()["created"]["proposal_items"] == 0
    assert rerun.json()["skipped"]["duplicates"] == 7
    assert db_session.query(WorldProposalBundle).filter_by(project_id=project.id).count() == 1
    assert db_session.query(WorldProposalItem).filter_by(project_id=project.id).count() == 7
    assert db_session.query(WorldFactClaim).filter_by(project_id=project.id).count() == 0


def test_analyze_chapter_creates_event_and_character_location_candidates(client, db_session):
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

    assert response.status_code == 200
    event_item = db_session.query(WorldProposalItem).filter_by(project_id=project.id, predicate="event_summary").one()
    assert event_item.subject_ref == "chapter.1"
    assert event_item.object_ref_or_value["title"] == "第一章 雾港"
    locations = (
        db_session.query(WorldProposalItem)
        .filter_by(project_id=project.id, predicate="present_at_location")
        .all()
    )
    assert {(item.subject_ref, item.object_ref_or_value["location_ref"]) for item in locations} == {
        ("char.林舟", "loc.雾港城"),
        ("char.沈聆", "loc.旧灯塔"),
    }


def test_analyze_chapter_creates_non_character_entity_mentions(client, db_session):
    project = _seed_project_with_setup(db_session)
    client.post(f"/api/v1/projects/{project.id}/athena/ontology/import-setup")
    db_session.add(
        ChapterContent(
            project_id=project.id,
            chapter_index=1,
            title="第一章 灯塔",
            content="雾港城入夜，旧灯塔重新点亮。档案局封锁街区，黑潮门在旧灯塔地下低鸣。",
            word_count=34,
            status="generated",
        )
    )
    db_session.commit()

    response = client.post(f"/api/v1/projects/{project.id}/athena/evolution/chapters/1/analyze")
    rerun = client.post(f"/api/v1/projects/{project.id}/athena/evolution/chapters/1/analyze")

    assert response.status_code == 200
    payload = response.json()
    assert payload["created"]["proposal_items"] == 5
    assert payload["skipped"]["duplicates"] == 0
    assert rerun.status_code == 200
    assert rerun.json()["created"]["proposal_items"] == 0
    assert rerun.json()["skipped"]["duplicates"] == 5

    items = (
        db_session.query(WorldProposalItem)
        .filter_by(project_id=project.id, predicate="mentioned_in_chapter")
        .all()
    )
    assert {item.subject_ref for item in items} == {
        "loc.雾港城",
        "loc.旧灯塔",
        "faction.档案局",
        "artifact.黑潮门",
    }
    lighthouse = next(item for item in items if item.subject_ref == "loc.旧灯塔")
    assert lighthouse.object_ref_or_value["mention_count"] == 2
    assert lighthouse.object_ref_or_value["entity_type"] == "location"
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
    item = (
        db_session.query(WorldProposalItem)
        .filter_by(project_id=project.id, subject_ref="char.林舟", predicate="presence_count")
        .one()
    )

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
    assert "旧灯塔" in payload["prompt_context"]
    assert "档案局" in payload["prompt_context"]
    assert "黑潮门" in payload["prompt_context"]
    assert "旧灯塔熄灭时" in payload["prompt_context"]
    assert "presence_count" in payload["prompt_context"]
