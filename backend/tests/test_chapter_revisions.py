from unittest.mock import AsyncMock, patch

from app.models import ChapterRevision, Dialog, DialogMessage, PromptRule, RevisionAnnotation, RevisionCorrection, Setup, Version
from app.models import ChapterContent, Project


def test_revision_feedback_formats_annotations_and_corrections():
    from app.core.revision_feedback import format_revision_feedback

    text = format_revision_feedback(
        annotations=[{"paragraph_index": 0, "selected_text": "开头", "comment": "节奏太慢"}],
        corrections=[{"paragraph_index": 1, "original_text": "寒风凛冽", "corrected_text": "夜风微凉"}],
    )

    assert "批注" in text
    assert "节奏太慢" in text
    assert "寒风凛冽 -> 夜风微凉" in text


def test_revision_models_are_importable():
    assert ChapterRevision.__tablename__ == "chapter_revisions"
    assert RevisionAnnotation.__tablename__ == "revision_annotations"
    assert RevisionCorrection.__tablename__ == "revision_corrections"


def test_submit_revision_persists_annotations_and_corrections(client, db_session):
    project = Project(name="Test")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    chapter = ChapterContent(
        project_id=project.id,
        chapter_index=1,
        title="第一章",
        content="开头寒风凛冽。",
        status="generated",
    )
    db_session.add(chapter)
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/revisions",
        json={
            "chapter_index": 1,
            "annotations": [
                {
                    "paragraph_index": 0,
                    "start_offset": 0,
                    "end_offset": 2,
                    "selected_text": "开头",
                    "comment": "节奏太慢",
                }
            ],
            "corrections": [
                {
                    "paragraph_index": 0,
                    "original_text": "寒风凛冽",
                    "corrected_text": "夜风微凉",
                }
            ],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["revision_index"] == 1
    assert len(data["annotations"]) == 1
    assert data["annotations"][0]["comment"] == "节奏太慢"
    assert len(data["corrections"]) == 1
    assert data["corrections"][0]["corrected_text"] == "夜风微凉"
    learned_rule = db_session.query(PromptRule).filter(PromptRule.project_id == project.id, PromptRule.rule_type == "learned").first()
    assert learned_rule is not None
    assert "节奏" in learned_rule.condition

    list_response = client.get(f"/api/v1/projects/{project.id}/revisions")
    assert list_response.status_code == 200
    assert list_response.json()[0]["id"] == data["id"]

    detail_response = client.get(f"/api/v1/projects/{project.id}/revisions/{data['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["annotations"][0]["selected_text"] == "开头"


def test_submit_revision_rejects_empty_feedback(client, db_session):
    project = Project(name="Test")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    chapter = ChapterContent(project_id=project.id, chapter_index=1, title="第一章", content="正文", status="generated")
    db_session.add(chapter)
    db_session.commit()

    response = client.post(f"/api/v1/projects/{project.id}/revisions", json={"chapter_index": 1})

    assert response.status_code == 422


def test_revision_draft_persists_and_can_be_reloaded(client, db_session):
    project = Project(name="Test")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    chapter = ChapterContent(project_id=project.id, chapter_index=1, title="第一章", content="原正文", status="generated")
    db_session.add(chapter)
    db_session.commit()

    save_response = client.put(
        f"/api/v1/projects/{project.id}/revisions/chapters/1/draft",
        json={
            "annotations": [
                {"paragraph_index": 0, "start_offset": 0, "end_offset": 1, "selected_text": "原", "comment": "重写"}
            ],
            "corrections": [
                {"paragraph_index": 0, "original_text": "原正文", "corrected_text": "新正文"}
            ],
        },
    )

    assert save_response.status_code == 200
    data = save_response.json()
    assert data["status"] == "draft"
    assert data["revision_index"] == 1
    assert data["annotations"][0]["comment"] == "重写"
    assert data["corrections"][0]["corrected_text"] == "新正文"

    reload_response = client.get(f"/api/v1/projects/{project.id}/revisions/chapters/1/active")
    assert reload_response.status_code == 200
    assert reload_response.json()["id"] == data["id"]
    assert reload_response.json()["annotations"][0]["selected_text"] == "原"


def test_submit_draft_links_base_version_and_keeps_revision_active(client, db_session):
    project = Project(name="Test")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    chapter = ChapterContent(project_id=project.id, chapter_index=1, title="第一章", content="原正文", status="generated")
    db_session.add(chapter)
    db_session.commit()
    draft_response = client.put(
        f"/api/v1/projects/{project.id}/revisions/chapters/1/draft",
        json={
            "annotations": [
                {"paragraph_index": 0, "start_offset": 0, "end_offset": 1, "selected_text": "原", "comment": "重写"}
            ],
            "corrections": [],
        },
    )

    submit_response = client.post(f"/api/v1/projects/{project.id}/revisions/{draft_response.json()['id']}/submit")

    assert submit_response.status_code == 200
    data = submit_response.json()
    assert data["status"] == "submitted"
    assert data["base_version_id"]
    base_version = db_session.query(Version).filter(Version.id == data["base_version_id"]).first()
    assert base_version.node_type == "chapter"
    assert base_version.node_id == chapter.id
    assert base_version.content == "原正文"
    active_response = client.get(f"/api/v1/projects/{project.id}/revisions/chapters/1/active")
    assert active_response.status_code == 200
    assert active_response.json()["id"] == data["id"]


def test_submit_draft_applies_revision_optimization(client, db_session):
    project = Project(name="Test")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    chapter = ChapterContent(project_id=project.id, chapter_index=1, title="第一章", content="原正文", status="generated")
    db_session.add(chapter)
    db_session.commit()
    draft_response = client.put(
        f"/api/v1/projects/{project.id}/revisions/chapters/1/draft",
        json={
            "annotations": [
                {"paragraph_index": 0, "start_offset": 0, "end_offset": 1, "selected_text": "原", "comment": "节奏太慢"}
            ],
            "corrections": [],
        },
    )

    submit_response = client.post(f"/api/v1/projects/{project.id}/revisions/{draft_response.json()['id']}/submit")

    assert submit_response.status_code == 200
    learned_rule = db_session.query(PromptRule).filter(PromptRule.project_id == project.id, PromptRule.rule_type == "learned").first()
    assert learned_rule is not None
    assert learned_rule.condition == "用户反馈节奏太慢"


def test_empty_draft_update_removes_submitted_revision_feedback(client, db_session):
    project = Project(name="Test")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    chapter = ChapterContent(project_id=project.id, chapter_index=1, title="第一章", content="原正文", status="generated")
    db_session.add(chapter)
    db_session.commit()
    draft_response = client.put(
        f"/api/v1/projects/{project.id}/revisions/chapters/1/draft",
        json={
            "annotations": [
                {"paragraph_index": 0, "start_offset": 0, "end_offset": 1, "selected_text": "原", "comment": "重写"}
            ],
            "corrections": [],
        },
    )
    submit_response = client.post(f"/api/v1/projects/{project.id}/revisions/{draft_response.json()['id']}/submit")
    revision_id = submit_response.json()["id"]

    clear_response = client.put(
        f"/api/v1/projects/{project.id}/revisions/chapters/1/draft",
        json={"annotations": [], "corrections": []},
    )

    assert clear_response.status_code == 200
    assert clear_response.json() is None
    active_response = client.get(f"/api/v1/projects/{project.id}/revisions/chapters/1/active")
    assert active_response.status_code == 200
    assert active_response.json() is None
    assert db_session.query(ChapterRevision).filter(ChapterRevision.id == revision_id).first() is None


@patch("app.api.chapters.load_api_key", return_value="sk-test")
@patch("app.api.chapters.ai_service.complete", new_callable=AsyncMock)
def test_regenerate_revision_updates_chapter_and_status(mock_complete, mock_key, client, db_session):
    project = Project(name="Test")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    setup = Setup(project_id=project.id, world_building={}, characters=[], core_concept={}, status="generated")
    chapter = ChapterContent(
        project_id=project.id,
        chapter_index=1,
        title="第一章",
        content="开头寒风凛冽。",
        status="generated",
    )
    db_session.add_all([setup, chapter])
    db_session.commit()

    submit_response = client.post(
        f"/api/v1/projects/{project.id}/revisions",
        json={
            "chapter_index": 1,
            "annotations": [
                {
                    "paragraph_index": 0,
                    "start_offset": 0,
                    "end_offset": 2,
                    "selected_text": "开头",
                    "comment": "节奏太慢",
                }
            ],
            "corrections": [],
        },
    )
    revision_id = submit_response.json()["id"]
    mock_complete.return_value.content = "重写后的正文"
    mock_complete.return_value.model = "deepseek-chat"
    mock_complete.return_value.prompt_tokens = 100
    mock_complete.return_value.completion_tokens = 200

    response = client.post(f"/api/v1/projects/{project.id}/revisions/{revision_id}/regenerate")

    assert response.status_code == 200
    assert response.json()["content"] == "重写后的正文"
    detail_response = client.get(f"/api/v1/projects/{project.id}/revisions/{revision_id}")
    assert detail_response.json()["status"] == "completed"
    prompt = mock_complete.call_args.args[0][0]["content"]
    assert "用户批注" in prompt
    assert "节奏太慢" in prompt


@patch("app.api.chapters.load_api_key", return_value="sk-test")
@patch("app.api.chapters.ai_service.complete", new_callable=AsyncMock)
def test_regenerate_revision_links_result_version_and_closes_active_revision(mock_complete, mock_key, client, db_session):
    project = Project(name="Test")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    setup = Setup(project_id=project.id, world_building={}, characters=[], core_concept={}, status="generated")
    chapter = ChapterContent(project_id=project.id, chapter_index=1, title="第一章", content="原正文", status="generated")
    db_session.add_all([setup, chapter])
    db_session.commit()
    draft_response = client.put(
        f"/api/v1/projects/{project.id}/revisions/chapters/1/draft",
        json={
            "annotations": [
                {"paragraph_index": 0, "start_offset": 0, "end_offset": 1, "selected_text": "原", "comment": "重写"}
            ],
            "corrections": [],
        },
    )
    submit_response = client.post(f"/api/v1/projects/{project.id}/revisions/{draft_response.json()['id']}/submit")
    mock_complete.return_value.content = "重写后的正文"
    mock_complete.return_value.model = "deepseek-chat"
    mock_complete.return_value.prompt_tokens = 100
    mock_complete.return_value.completion_tokens = 200

    response = client.post(f"/api/v1/projects/{project.id}/revisions/{submit_response.json()['id']}/regenerate")

    assert response.status_code == 200
    detail_response = client.get(f"/api/v1/projects/{project.id}/revisions/{submit_response.json()['id']}")
    detail = detail_response.json()
    assert detail["status"] == "completed"
    assert detail["base_version_id"]
    assert detail["result_version_id"]
    active_response = client.get(f"/api/v1/projects/{project.id}/revisions/chapters/1/active")
    assert active_response.status_code == 200
    assert active_response.json() is None
    versions = (
        db_session.query(Version)
        .filter(Version.project_id == project.id, Version.node_type == "chapter")
        .order_by(Version.version_number.asc())
        .all()
    )
    assert [version.content for version in versions] == ["原正文", "重写后的正文"]


@patch("app.api.chapters.load_api_key", return_value="sk-test")
@patch("app.api.chapters.ai_service.complete", new_callable=AsyncMock)
def test_regenerate_revision_persists_hermes_messages(mock_complete, mock_key, client, db_session):
    project = Project(name="Test")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    setup = Setup(project_id=project.id, world_building={}, characters=[], core_concept={}, status="generated")
    chapter = ChapterContent(project_id=project.id, chapter_index=1, title="第一章", content="原正文", status="generated")
    db_session.add_all([setup, chapter])
    db_session.commit()

    submit_response = client.post(
        f"/api/v1/projects/{project.id}/revisions",
        json={
            "chapter_index": 1,
            "annotations": [
                {"paragraph_index": 0, "start_offset": 0, "end_offset": 1, "selected_text": "原", "comment": "重写"}
            ],
            "corrections": [],
        },
    )
    mock_complete.return_value.content = "重写后的正文"
    mock_complete.return_value.model = "deepseek-chat"
    mock_complete.return_value.prompt_tokens = 100
    mock_complete.return_value.completion_tokens = 200

    response = client.post(f"/api/v1/projects/{project.id}/revisions/{submit_response.json()['id']}/regenerate")

    assert response.status_code == 200
    dialog = db_session.query(Dialog).filter(Dialog.project_id == project.id, Dialog.dialog_type == "hermes").first()
    messages = db_session.query(DialogMessage).filter(DialogMessage.dialog_id == dialog.id).order_by(DialogMessage.created_at).all()
    assert [message.role for message in messages] == ["user", "assistant"]
    assert "提交修订" in messages[0].content
    assert "重新生成第 1 章" in messages[1].content


@patch("app.api.chapters.load_api_key", return_value="sk-test")
@patch("app.api.chapters.ai_service.complete", new_callable=AsyncMock)
def test_regenerate_revision_marks_failed_when_generation_fails(mock_complete, mock_key, client, db_session):
    project = Project(name="Test")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    setup = Setup(project_id=project.id, world_building={}, characters=[], core_concept={}, status="generated")
    chapter = ChapterContent(project_id=project.id, chapter_index=1, title="第一章", content="原正文", status="generated")
    db_session.add_all([setup, chapter])
    db_session.commit()
    submit_response = client.post(
        f"/api/v1/projects/{project.id}/revisions",
        json={
            "chapter_index": 1,
            "annotations": [
                {"paragraph_index": 0, "start_offset": 0, "end_offset": 1, "selected_text": "原", "comment": "重写"}
            ],
            "corrections": [],
        },
    )
    revision_id = submit_response.json()["id"]
    mock_complete.side_effect = RuntimeError("LLM unavailable")

    response = client.post(f"/api/v1/projects/{project.id}/revisions/{revision_id}/regenerate")

    assert response.status_code == 500
    revision = db_session.query(ChapterRevision).filter(ChapterRevision.id == revision_id).first()
    assert revision.status == "failed"


@patch("app.api.chapters.load_api_key", return_value="sk-test")
@patch("app.api.chapters.ai_service.complete", new_callable=AsyncMock)
def test_regenerate_revision_is_idempotent_after_completed(mock_complete, mock_key, client, db_session):
    project = Project(name="Test")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    setup = Setup(project_id=project.id, world_building={}, characters=[], core_concept={}, status="generated")
    chapter = ChapterContent(project_id=project.id, chapter_index=1, title="第一章", content="原正文", status="generated")
    db_session.add_all([setup, chapter])
    db_session.commit()
    submit_response = client.post(
        f"/api/v1/projects/{project.id}/revisions",
        json={
            "chapter_index": 1,
            "annotations": [
                {"paragraph_index": 0, "start_offset": 0, "end_offset": 1, "selected_text": "原", "comment": "重写"}
            ],
            "corrections": [],
        },
    )
    revision_id = submit_response.json()["id"]
    mock_complete.return_value.content = "第一次重写"
    mock_complete.return_value.model = "deepseek-chat"
    mock_complete.return_value.prompt_tokens = 100
    mock_complete.return_value.completion_tokens = 200
    first_response = client.post(f"/api/v1/projects/{project.id}/revisions/{revision_id}/regenerate")
    assert first_response.status_code == 200
    mock_complete.reset_mock()

    second_response = client.post(f"/api/v1/projects/{project.id}/revisions/{revision_id}/regenerate")

    assert second_response.status_code == 200
    assert second_response.json()["content"] == "第一次重写"
    mock_complete.assert_not_called()
