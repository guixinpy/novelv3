from unittest.mock import AsyncMock, patch

from sqlalchemy import event

from app.models import (
    BackgroundTask,
    ChapterContent,
    ConsistencyCheck,
    GenreProfile,
    Project,
    ProjectProfileVersion,
    WorldEvent,
    WorldTimelineAnchor,
)


def test_consistency_check_detects_dead_character(client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    with patch("app.api.setups.load_api_key", return_value="sk-test"), \
         patch("app.api.setups.ai_service.complete", new_callable=AsyncMock) as ms, \
         patch("app.api.setups.ai_service.parse_json") as mp:
        ms.return_value.content = '{"world_building": {}, "characters": [{"name": "李明", "character_status": "dead"}], "core_concept": {}}'
        mp.return_value = {"world_building": {}, "characters": [{"name": "李明", "character_status": "dead"}], "core_concept": {}}
        client.post(f"/api/v1/projects/{pid}/setup/generate")

    with patch("app.api.chapters.load_api_key", return_value="sk-test"), \
         patch("app.api.chapters.ai_service.complete", new_callable=AsyncMock) as mc:
        mc.return_value.content = "李明冷冷地看着对方。"
        mc.return_value.model = "deepseek-chat"
        mc.return_value.prompt_tokens = 10
        mc.return_value.completion_tokens = 10
        client.post(f"/api/v1/projects/{pid}/chapters/1/generate")

    r2 = client.post(f"/api/v1/projects/{pid}/consistency/chapters/1/check")
    assert r2.status_code == 200
    issues = r2.json()["issues"]
    assert any(i["checker_name"] == "CharacterStateChecker" for i in issues)


def test_list_issues(client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    r2 = client.get(f"/api/v1/projects/{pid}/consistency/issues")
    assert r2.status_code == 200
    assert r2.json()["issues"] == []


def test_list_issues_returns_bounded_page_with_total(client, db_session):
    project = Project(name="Consistency History Scale")
    db_session.add(project)
    db_session.flush()
    db_session.add_all([
        ConsistencyCheck(
            project_id=project.id,
            chapter_index=index,
            checker_name="Checker",
            subject=f"issue-{index}",
            description=f"问题 {index}",
            status="pending",
        )
        for index in range(1, 13)
    ])
    db_session.commit()

    response = client.get(f"/api/v1/projects/{project.id}/consistency/issues?offset=5&limit=4")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 12
    assert data["offset"] == 5
    assert data["limit"] == 4
    assert data["has_more"] is True
    assert [item["chapter_index"] for item in data["issues"]] == [6, 7, 8, 9]


def test_list_issues_total_does_not_select_heavy_text_fields(client, db_session):
    project = Project(name="Consistency Heavy Text")
    db_session.add(project)
    db_session.flush()
    db_session.add_all([
        ConsistencyCheck(
            project_id=project.id,
            chapter_index=index,
            checker_name="Checker",
            subject=f"issue-{index}",
            description="长问题描述" * 300,
            evidence="长证据文本" * 300,
            suggested_fix="长修复建议" * 300,
            status="pending",
        )
        for index in range(1, 4)
    ])
    db_session.commit()
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        response = client.get(f"/api/v1/projects/{project.id}/consistency/issues?limit=1")
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert response.status_code == 200
    assert response.json()["total"] == 3
    count_statements = [
        statement for statement in statements
        if "count(" in statement and "consistency_checks" in statement
    ]
    assert count_statements
    assert all("consistency_checks.description" not in statement for statement in count_statements)
    assert all("consistency_checks.evidence" not in statement for statement in count_statements)
    assert all("consistency_checks.suggested_fix" not in statement for statement in count_statements)


def test_consistency_check_uses_current_world_model_checker_pack(client, db_session):
    project = Project(name="World Checker Consistency")
    genre_profile = GenreProfile(
        canonical_id="world-checker-consistency",
        display_name="World Checker Consistency",
        contract_version="world.contract.v1",
        checker_config={
            "pack_version": "world.contract.v1",
            "layers": {
                "L0 Schema Gate": ["schema_gate"],
                "L1 Event Ledger Gate": ["event_ledger_gate"],
                "L2 Deterministic Replay": ["deterministic_replay"],
                "L3 Cross-Entity Rules": ["entity_uniqueness"],
                "L4 Profile Rules": ["profile_event_type_guard"],
            },
        },
        event_types=["event_occurred"],
        schema_payload={
            "event_schemas": {
                "event_occurred": {
                    "required_payload_fields": ["event_ref"],
                },
            },
        },
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
    db_session.add(
        ChapterContent(
            project_id=project.id,
            chapter_index=1,
            title="第一章",
            content="事件记录缺少必要字段。",
            status="generated",
        )
    )
    db_session.commit()
    db_session.add(
        WorldTimelineAnchor(
            project_id=project.id,
            profile_version=profile.version,
            anchor_id="anchor.ch1.s1",
            chapter_index=1,
            intra_chapter_seq=1,
            ordering_key="001:001",
            contract_version=profile.contract_version,
        )
    )
    db_session.add(
        WorldEvent(
            project_id=project.id,
            project_profile_version_id=profile.id,
            profile_version=profile.version,
            event_id="evt.missing.payload",
            idempotency_key="idem.missing.payload",
            timeline_anchor_id="anchor.ch1.s1",
            chapter_index=1,
            intra_chapter_seq=1,
            event_type="event_occurred",
            primitive_payload={},
            truth_layer="truth",
            disclosure_layer="public",
            contract_version=profile.contract_version,
        )
    )
    db_session.commit()

    response = client.post(f"/api/v1/projects/{project.id}/consistency/chapters/1/check")

    assert response.status_code == 200
    issues = response.json()["issues"]
    assert any(
        issue["checker_name"] == "schema_gate"
        and issue["subject"] == "missing_payload_fields"
        and "event_ref" in issue["description"]
        for issue in issues
    )
    saved_issues = client.get(f"/api/v1/projects/{project.id}/consistency/issues").json()["issues"]
    assert any(issue["checker_name"] == "schema_gate" for issue in saved_issues)


def test_world_model_consistency_check_scopes_issues_to_requested_chapter(client, db_session):
    project = Project(name="World Checker Chapter Scope")
    genre_profile = GenreProfile(
        canonical_id="world-checker-chapter-scope",
        display_name="World Checker Chapter Scope",
        contract_version="world.contract.v1",
        checker_config={
            "pack_version": "world.contract.v1",
            "layers": {
                "L0 Schema Gate": ["schema_gate"],
                "L1 Event Ledger Gate": ["event_ledger_gate"],
                "L2 Deterministic Replay": ["deterministic_replay"],
                "L3 Cross-Entity Rules": ["entity_uniqueness"],
                "L4 Profile Rules": ["profile_event_type_guard"],
            },
        },
        event_types=["event_occurred"],
        schema_payload={
            "event_schemas": {
                "event_occurred": {
                    "required_payload_fields": ["event_ref"],
                },
            },
        },
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
    db_session.add_all([
        ChapterContent(project_id=project.id, chapter_index=1, title="第一章", content="旧问题。", status="generated"),
        ChapterContent(project_id=project.id, chapter_index=2, title="第二章", content="新章节。", status="generated"),
    ])
    db_session.commit()
    db_session.add(
        WorldTimelineAnchor(
            project_id=project.id,
            profile_version=profile.version,
            anchor_id="anchor.ch1.s1",
            chapter_index=1,
            intra_chapter_seq=1,
            ordering_key="001:001",
            contract_version=profile.contract_version,
        )
    )
    db_session.add(
        WorldEvent(
            project_id=project.id,
            project_profile_version_id=profile.id,
            profile_version=profile.version,
            event_id="evt.chapter1.missing.payload",
            idempotency_key="idem.chapter1.missing.payload",
            timeline_anchor_id="anchor.ch1.s1",
            chapter_index=1,
            intra_chapter_seq=1,
            event_type="event_occurred",
            primitive_payload={},
            truth_layer="truth",
            disclosure_layer="public",
            contract_version=profile.contract_version,
        )
    )
    db_session.commit()

    chapter_two = client.post(f"/api/v1/projects/{project.id}/consistency/chapters/2/check")
    chapter_one = client.post(f"/api/v1/projects/{project.id}/consistency/chapters/1/check")

    assert chapter_two.status_code == 200
    assert chapter_two.json()["issues"] == []
    assert chapter_one.status_code == 200
    assert any(issue["subject"] == "missing_payload_fields" for issue in chapter_one.json()["issues"])


def test_deep_check_creates_background_task(client, db_session):
    project = Project(name="Deep Check")
    db_session.add(project)
    db_session.flush()
    db_session.add(
        ChapterContent(
            project_id=project.id,
            chapter_index=1,
            title="第一章",
            content="内容",
            status="generated",
        )
    )
    db_session.commit()

    with patch("app.api.consistency.LocalTaskRunner.start") as start:
        response = client.post(f"/api/v1/projects/{project.id}/consistency/chapters/1/check?depth=l2")

    assert response.status_code == 200
    payload = response.json()
    task = db_session.query(BackgroundTask).filter(BackgroundTask.id == payload["task_id"]).one()
    assert payload == {"task_id": task.id, "status": "pending"}
    assert task.task_type == "consistency_deep_check"
    assert task.payload == {"chapter_index": 1}
    assert task.status == "pending"
    start.assert_called_once()
