from app.models import (
    ChapterContent,
    GenreProfile,
    Project,
    ProjectProfileVersion,
    Setup,
    WorldArtifact,
    WorldCharacter,
    WorldFaction,
    WorldFactClaim,
    WorldLocation,
    WorldEvent,
    WorldProposalBundle,
    WorldProposalItem,
    WorldRule,
    WorldTimelineAnchor,
)
from app.core.athena_longform import analyze_chapter_to_world_proposals
from app.core.athena_entity_resolver import count_entity_mentions
from app.core.l1_extractor import L1RuleExtractor
from sqlalchemy import event


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


def test_l1_and_entity_mentions_do_not_double_count_overlapping_aliases():
    chapter = ChapterContent(
        project_id="project-alias",
        chapter_index=1,
        title="第一章",
        content="林舟走进雾港城。",
        status="generated",
    )
    characters = [{"name": "林舟", "aliases": ["林"]}]

    facts = L1RuleExtractor().extract(chapter, characters)

    assert facts[0]["new_value"] == 1
    assert count_entity_mentions(text=chapter.content, names=["林舟", "林"]) == 1


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
    profile = db_session.query(ProjectProfileVersion).filter_by(project_id=project.id).one()
    genre_profile = db_session.query(GenreProfile).filter_by(id=profile.genre_profile_id).one()
    assert "event_occurred" in genre_profile.event_types
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


def test_analyze_chapter_refreshes_stale_pending_candidates_after_chapter_rewrite(client, db_session):
    project = _seed_project_with_setup(db_session)
    client.post(f"/api/v1/projects/{project.id}/athena/ontology/import-setup")
    chapter = ChapterContent(
        project_id=project.id,
        chapter_index=1,
        title="第一章 雾港",
        content="林舟走进雾港城。",
        word_count=10,
        status="generated",
    )
    db_session.add(chapter)
    db_session.commit()

    first = client.post(f"/api/v1/projects/{project.id}/athena/evolution/chapters/1/analyze")
    item = (
        db_session.query(WorldProposalItem)
        .filter_by(project_id=project.id, subject_ref="char.林舟", predicate="presence_count")
        .one()
    )
    assert first.status_code == 200
    assert item.object_ref_or_value["count"] == 1

    chapter.content = "林舟进入雾港城。林舟查看旧灯塔。林舟听见潮声。"
    chapter.word_count = 30
    db_session.commit()
    second = client.post(f"/api/v1/projects/{project.id}/athena/evolution/chapters/1/analyze")

    db_session.refresh(item)
    assert second.status_code == 200
    assert second.json()["updated"]["proposal_items"] >= 1
    assert item.id == (
        db_session.query(WorldProposalItem)
        .filter_by(project_id=project.id, subject_ref="char.林舟", predicate="presence_count")
        .one()
        .id
    )
    assert item.item_status == "needs_edit"
    assert item.object_ref_or_value["count"] == 3
    assert "出现 3 次" in item.notes


def test_analyze_chapter_uses_world_model_canonical_character_refs_over_stale_setup(client, db_session):
    project = Project(name="Canonical Analyzer", genre="东方奇幻悬疑")
    genre_profile = GenreProfile(
        canonical_id="canonical-analyzer-profile",
        display_name="Canonical Analyzer",
        contract_version="world.contract.v1",
    )
    db_session.add_all([project, genre_profile])
    db_session.commit()
    db_session.refresh(project)
    profile = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=genre_profile.id,
        version=1,
        contract_version="world.contract.v1",
        profile_payload={},
    )
    db_session.add(profile)
    db_session.commit()
    db_session.add(
        Setup(
            project_id=project.id,
            status="generated",
            world_building={},
            characters=[{"name": "旧名", "character_status": "alive"}],
            core_concept={},
        )
    )
    db_session.add(
        WorldCharacter(
            project_id=project.id,
            profile_version=profile.version,
            character_id="hero",
            canonical_id="char.hero",
            primary_alias="林舟",
            name="林舟",
            aliases=["旧名"],
            role_type="character",
            identity_anchor="林舟",
            contract_version=profile.contract_version,
        )
    )
    db_session.add(
        WorldLocation(
            project_id=project.id,
            profile_version=profile.version,
            location_id="fog-harbor",
            canonical_id="loc.fog-harbor",
            primary_alias="雾港城",
            name="雾港城",
            aliases=[],
            location_type="city",
            contract_version=profile.contract_version,
        )
    )
    db_session.add(
        ChapterContent(
            project_id=project.id,
            chapter_index=1,
            title="第一章 归港",
            content="林舟走进雾港城。旧名这个称呼已经无人再用。",
            word_count=30,
            status="generated",
        )
    )
    db_session.commit()

    response = client.post(f"/api/v1/projects/{project.id}/athena/evolution/chapters/1/analyze")

    assert response.status_code == 200
    assert (
        db_session.query(WorldProposalItem)
        .filter_by(project_id=project.id, subject_ref="char.hero", predicate="presence_count")
        .count()
        == 1
    )
    location_item = (
        db_session.query(WorldProposalItem)
        .filter_by(project_id=project.id, subject_ref="char.hero", predicate="present_at_location")
        .one()
    )
    assert location_item.object_ref_or_value["location_ref"] == "loc.fog-harbor"
    assert (
        db_session.query(WorldProposalItem)
        .filter_by(project_id=project.id, subject_ref="char.旧名")
        .count()
        == 0
    )


def test_analyze_chapter_uses_bounded_setup_character_projection_when_world_model_has_no_characters(db_session):
    project = Project(name="Analyzer Setup Projection", genre="东方奇幻悬疑")
    genre_profile = GenreProfile(
        canonical_id="analyzer-setup-projection-profile",
        display_name="Analyzer Setup Projection",
        contract_version="world.contract.v1",
    )
    db_session.add_all([project, genre_profile])
    db_session.commit()
    db_session.refresh(project)
    profile = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=genre_profile.id,
        version=1,
        contract_version="world.contract.v1",
        profile_payload={},
    )
    db_session.add(profile)
    db_session.add(
        Setup(
            project_id=project.id,
            status="generated",
            world_building={"rules": "长世界规则" * 1000},
            characters=[
                {
                    "name": "林舟",
                    "aliases": ["守夜人"],
                    "character_status": "alive",
                    "bio": "超长人物背景" * 5000,
                }
            ],
            core_concept={"hook": "旧灯塔" * 1000},
        )
    )
    db_session.add(
        ChapterContent(
            project_id=project.id,
            chapter_index=1,
            title="第一章 归港",
            content="守夜人走进雾港城。林舟再次听见潮声。",
            word_count=30,
            status="generated",
        )
    )
    db_session.commit()
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        result = analyze_chapter_to_world_proposals(db_session, project.id, 1)
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert result["status"] == "completed"
    assert (
        db_session.query(WorldProposalItem)
        .filter_by(project_id=project.id, subject_ref="char.林舟", predicate="presence_count")
        .count()
        == 1
    )
    setup_select_clauses = [
        statement.split(" from setups", 1)[0]
        for statement in statements
        if " from setups" in statement
    ]
    assert setup_select_clauses
    assert any("json_each(setups.characters)" in statement for statement in statements)
    assert all("setups.world_building as setups_world_building" not in clause for clause in setup_select_clauses)
    assert all("setups.characters as setups_characters" not in clause for clause in setup_select_clauses)
    assert all("setups.core_concept as setups_core_concept" not in clause for clause in setup_select_clauses)


def test_analyze_chapter_rolls_back_partial_bundle_when_candidate_write_fails(client, db_session, monkeypatch):
    import app.core.athena_longform as athena_longform

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

    def fail_candidate_write(*args, **kwargs):
        raise RuntimeError("candidate write failed")

    monkeypatch.setattr(athena_longform, "write_candidate_fact", fail_candidate_write)

    try:
        analyze_chapter_to_world_proposals(db_session, project.id, 1)
    except RuntimeError as exc:
        assert str(exc) == "candidate write failed"
    else:
        raise AssertionError("analysis should fail when candidate writing fails")

    assert db_session.query(WorldProposalBundle).filter_by(project_id=project.id).count() == 0
    assert db_session.query(WorldProposalItem).filter_by(project_id=project.id).count() == 0


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
    assert event_item.object_ref_or_value["evidence_span"]["ref"] == "chapter:1"
    assert event_item.object_ref_or_value["quality"]["confidence_band"] == "low"
    locations = (
        db_session.query(WorldProposalItem)
        .filter_by(project_id=project.id, predicate="present_at_location")
        .all()
    )
    assert {(item.subject_ref, item.object_ref_or_value["location_ref"]) for item in locations} == {
        ("char.林舟", "loc.雾港城"),
        ("char.沈聆", "loc.旧灯塔"),
    }
    for item in locations:
        assert item.object_ref_or_value["evidence_span"]["text"]
        assert item.object_ref_or_value["quality"]["review_priority"] == "normal"


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
    assert lighthouse.object_ref_or_value["evidence_span"]["ref"] == "chapter:1"
    assert lighthouse.object_ref_or_value["quality"]["signal"] == "entity_mention"
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


def test_approved_event_summary_materializes_world_event_ledger(client, db_session):
    project = _seed_project_with_setup(db_session)
    client.post(f"/api/v1/projects/{project.id}/athena/ontology/import-setup")
    db_session.add(
        ChapterContent(
            project_id=project.id,
            chapter_index=1,
            title="第一章 雾港",
            content="林舟走进雾港城。旧灯塔重新点亮。",
            word_count=18,
            status="generated",
        )
    )
    db_session.commit()
    client.post(f"/api/v1/projects/{project.id}/athena/evolution/chapters/1/analyze")
    item = (
        db_session.query(WorldProposalItem)
        .filter_by(project_id=project.id, subject_ref="chapter.1", predicate="event_summary")
        .one()
    )

    review = client.post(
        f"/api/v1/projects/{project.id}/athena/evolution/proposals/{item.id}/review",
        json={
            "reviewer_ref": "tester",
            "action": "approve",
            "reason": "确认章节事件",
            "evidence_refs": ["chapter:1"],
            "edited_fields": {},
        },
    )
    overview = client.get(f"/api/v1/projects/{project.id}/world-model")

    assert review.status_code == 200
    anchor = db_session.query(WorldTimelineAnchor).filter_by(project_id=project.id, anchor_id="anchor.chapter.1.summary").one()
    event = db_session.query(WorldEvent).filter_by(project_id=project.id, event_id="event.chapter.1.summary").one()
    assert anchor.chapter_index == 1
    assert event.timeline_anchor_id == anchor.anchor_id
    assert event.event_type == "event_occurred"
    assert event.primitive_payload["event_ref"] == "event.chapter.1.summary"
    assert "旧灯塔重新点亮" in event.primitive_payload["summary"]
    assert overview.status_code == 200
    assert overview.json()["projection"]["occurred_events"]["event.chapter.1.summary"]["summary"]


def test_rollback_event_summary_approval_retcons_world_event_projection(client, db_session):
    project = _seed_project_with_setup(db_session)
    client.post(f"/api/v1/projects/{project.id}/athena/ontology/import-setup")
    db_session.add(
        ChapterContent(
            project_id=project.id,
            chapter_index=1,
            title="第一章 雾港",
            content="林舟走进雾港城。旧灯塔重新点亮。",
            word_count=18,
            status="generated",
        )
    )
    db_session.commit()
    client.post(f"/api/v1/projects/{project.id}/athena/evolution/chapters/1/analyze")
    item = (
        db_session.query(WorldProposalItem)
        .filter_by(project_id=project.id, subject_ref="chapter.1", predicate="event_summary")
        .one()
    )
    approval = client.post(
        f"/api/v1/projects/{project.id}/athena/evolution/proposals/{item.id}/review",
        json={
            "reviewer_ref": "tester",
            "action": "approve",
            "reason": "确认章节事件",
            "evidence_refs": ["chapter:1"],
            "edited_fields": {},
        },
    )

    rollback = client.post(
        f"/api/v1/projects/{project.id}/world-model/reviews/{approval.json()['id']}/rollback",
        json={
            "reviewer_ref": "tester",
            "reason": "撤回章节事件",
            "evidence_refs": ["chapter:1"],
        },
    )
    overview = client.get(f"/api/v1/projects/{project.id}/world-model")

    assert approval.status_code == 200
    assert rollback.status_code == 200
    original = db_session.query(WorldEvent).filter_by(project_id=project.id, event_id="event.chapter.1.summary").one()
    retcon = (
        db_session.query(WorldEvent)
        .filter_by(project_id=project.id, supersedes_event_ref="event.chapter.1.summary")
        .one()
    )
    assert original.event_type == "event_occurred"
    assert retcon.event_type == "retcon_applied"
    assert retcon.primitive_payload["replacement_event_type"] == "fact_reviewed"
    assert overview.status_code == 200
    assert "event.chapter.1.summary" not in overview.json()["projection"]["occurred_events"]
