from app.models import ChapterContent, ChapterRevision, RevisionAnnotation, RevisionCorrection
from test_support.writing_agent_run_helpers import (
    approved_create_revision_draft_tool,
    seed_longform_project,
)


def test_agent_create_revision_draft_from_plan_is_non_destructive(client, db_session):
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    chapter.title = "第2章"
    chapter.word_count = 3400
    original_content = chapter.content
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "为第2章创建修订草稿",
            "tools": [approved_create_revision_draft_tool(db_session, project.id, chapter_index=2)],
        },
    )

    output = response.json()["steps"][0]["output"]
    chapter_after = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    revision = db_session.query(ChapterRevision).filter_by(id=output["revision_id"]).one()
    annotations = db_session.query(RevisionAnnotation).filter_by(revision_id=revision.id).all()
    corrections = db_session.query(RevisionCorrection).filter_by(revision_id=revision.id).all()
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "drafted"
    assert output["annotation_count"] >= 2
    assert output["correction_count"] == 0
    assert revision.status == "draft"
    assert revision.result_version_id is None
    assert corrections == []
    assert any("[PLAN_ACTION:retitle_chapter]" in item.comment for item in annotations)
    assert any("[PLAN_ACTION:compress_chapter]" in item.comment for item in annotations)
    assert chapter_after.content == original_content
    assert chapter_after.title == "第2章"


def test_agent_create_revision_draft_anchors_drift_actions(client, db_session):
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "黑市雾晶"
    chapter.content = "苏晚晴低声说，她以前是雾安局研究员。随后她制造幻觉骗过守卫。"
    chapter.word_count = 2000
    original_content = chapter.content
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "创建第1章漂移修订草稿",
            "tools": [approved_create_revision_draft_tool(db_session, project.id, chapter_index=1)],
        },
    )

    output = response.json()["steps"][0]["output"]
    annotations = db_session.query(RevisionAnnotation).filter_by(revision_id=output["revision_id"]).all()
    comments = [annotation.comment or "" for annotation in annotations]
    selected = [annotation.selected_text or "" for annotation in annotations]
    assert response.status_code == 200
    assert output["status"] == "drafted"
    assert output["annotation_count"] == 2
    assert any("[PLAN_ACTION:fix_character_profile_drift]" in comment for comment in comments)
    assert any("[PLAN_ACTION:respect_ability_boundary]" in comment for comment in comments)
    assert any("雾安局研究员" in text for text in selected)
    assert any("制造幻觉" in text for text in selected)
    assert db_session.query(ChapterContent).filter_by(id=chapter.id).one().content == original_content


def test_agent_create_revision_draft_reuses_existing_draft(client, db_session):
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    chapter.title = "第2章"
    chapter.word_count = 3400
    db_session.commit()

    first = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "为第2章创建修订草稿",
            "tools": [approved_create_revision_draft_tool(db_session, project.id, chapter_index=2)],
        },
    )
    second = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "再次为第2章创建修订草稿",
            "tools": [approved_create_revision_draft_tool(db_session, project.id, chapter_index=2)],
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200
    first_output = first.json()["steps"][0]["output"]
    second_output = second.json()["steps"][0]["output"]
    assert first_output["revision_id"] == second_output["revision_id"]
    assert db_session.query(ChapterRevision).filter_by(project_id=project.id, chapter_index=2).count() == 1
    assert second_output["revision_index"] == 1


def test_agent_create_revision_draft_does_not_modify_manual_draft(client, db_session):
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    chapter.title = "第2章"
    chapter.word_count = 3400
    revision = ChapterRevision(
        project_id=project.id,
        chapter_id=chapter.id,
        chapter_index=2,
        revision_index=1,
        status="draft",
    )
    db_session.add(revision)
    db_session.flush()
    db_session.add(
        RevisionAnnotation(
            revision_id=revision.id,
            paragraph_index=0,
            start_offset=0,
            end_offset=2,
            selected_text="林深",
            comment="用户手写批注",
        )
    )
    db_session.add(
        RevisionCorrection(
            revision_id=revision.id,
            paragraph_index=0,
            original_text="旧句",
            corrected_text="新句",
        )
    )
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "不要覆盖用户手写草稿",
            "tools": [approved_create_revision_draft_tool(db_session, project.id, chapter_index=2)],
        },
    )

    annotations = db_session.query(RevisionAnnotation).filter_by(revision_id=revision.id).all()
    corrections = db_session.query(RevisionCorrection).filter_by(revision_id=revision.id).all()
    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert response.json()["steps"][0]["output"]["reason"] == "existing_manual_draft"
    assert db_session.query(ChapterRevision).filter_by(project_id=project.id, chapter_index=2).count() == 1
    assert [item.comment for item in annotations] == ["用户手写批注"]
    assert corrections[0].corrected_text == "新句"


def test_agent_create_revision_draft_does_not_compete_with_submitted_revision(client, db_session):
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    chapter.title = "第2章"
    chapter.word_count = 3400
    submitted = ChapterRevision(
        project_id=project.id,
        chapter_id=chapter.id,
        chapter_index=2,
        revision_index=1,
        status="submitted",
    )
    db_session.add(submitted)
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "不要创建竞争修订",
            "tools": [approved_create_revision_draft_tool(db_session, project.id, chapter_index=2)],
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert response.json()["steps"][0]["output"]["reason"] == "existing_active_revision"
    revisions = db_session.query(ChapterRevision).filter_by(project_id=project.id, chapter_index=2).all()
    assert len(revisions) == 1
    assert revisions[0].id == submitted.id
    assert revisions[0].status == "submitted"


def test_agent_create_revision_draft_skips_ready_chapter(client, db_session):
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第1章是否需要修订草稿",
            "tools": [approved_create_revision_draft_tool(db_session, project.id, chapter_index=1)],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "skipped"
    assert output["reason"] == "no_revision_actions"
    assert output["revision_id"] is None
    assert db_session.query(ChapterRevision).filter_by(project_id=project.id).count() == 0


def test_agent_create_revision_draft_blocks_followup_generation(client, db_session, monkeypatch):
    project = seed_longform_project(db_session, outline_chapters=[1, 2, 3], generated_chapters=[1, 2])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    chapter.title = "第2章"
    chapter.word_count = 3400
    db_session.commit()
    calls = []

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append(action_type)
        return {"status": "success", "chapter_index": 3}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "创建第2章修订草稿后尝试生成第3章",
            "tools": [
                approved_create_revision_draft_tool(db_session, project.id, chapter_index=2),
                {"tool_name": "generate_chapter", "params": {"chapter_index": 3}},
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert payload["steps"][0]["tool_name"] == "execute_create_revision_draft_with_approval"
    assert payload["steps"][0]["output"]["should_generate_next_chapter"] is False
    assert len(payload["steps"]) == 1
    assert calls == []
