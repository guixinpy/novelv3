from app.models import ChapterContent, Dialog, DialogMessage, Outline, Project, Setup, Storyline, Version


def test_workspace_bootstrap_returns_project_session_bundle(client, db_session):
    project = Project(name="雾港二十夜", genre="都市奇幻悬疑")
    db_session.add(project)
    db_session.flush()
    chapter = ChapterContent(
        project_id=project.id,
        chapter_index=1,
        title="第一章",
        content="雾港醒来。",
        word_count=5,
        status="generated",
    )
    setup = Setup(project_id=project.id, status="generated", core_concept={"theme": "雾"})
    storyline = Storyline(project_id=project.id, status="generated", plotlines=[{"name": "主线"}])
    outline = Outline(project_id=project.id, status="generated", total_chapters=1, chapters=[{"chapter_index": 1, "title": "第一章", "summary": "开端"}])
    hermes_dialog = Dialog(project_id=project.id, dialog_type="hermes")
    athena_dialog = Dialog(project_id=project.id, dialog_type="athena")
    db_session.add_all([chapter, setup, storyline, outline, hermes_dialog, athena_dialog])
    db_session.flush()
    db_session.add_all(
        [
            DialogMessage(dialog_id=hermes_dialog.id, role="assistant", content="Hermes 历史"),
            DialogMessage(dialog_id=athena_dialog.id, role="assistant", content="Athena 历史"),
            Version(
                project_id=project.id,
                node_type="chapter",
                node_id=chapter.id,
                version_number=1,
                content=chapter.content,
                description="initial",
            ),
        ]
    )
    db_session.commit()

    response = client.get(f"/api/v1/projects/{project.id}/workspace-bootstrap")

    assert response.status_code == 200
    payload = response.json()
    assert payload["project"]["id"] == project.id
    assert payload["diagnosis"]["completed_items"] == ["setup", "storyline", "outline", "content"]
    assert payload["setup"]["core_concept"]["theme"] == "雾"
    assert payload["storyline"]["plotlines"] == [{"name": "主线"}]
    assert payload["outline"]["total_chapters"] == 1
    assert payload["chapters"] == [
        {
            "id": chapter.id,
            "chapter_index": 1,
            "title": "第一章",
            "word_count": 5,
            "status": "generated",
        }
    ]
    assert payload["versions"][0]["node_type"] == "chapter"
    assert payload["dialogs"]["hermes"]["messages"][0]["content"] == "Hermes 历史"
    assert payload["dialogs"]["athena"]["messages"][0]["content"] == "Athena 历史"


def test_workspace_bootstrap_returns_404_for_missing_project(client):
    response = client.get("/api/v1/projects/missing/workspace-bootstrap")

    assert response.status_code == 404


def test_workspace_bootstrap_bounds_chapter_summaries_for_large_projects(client, db_session):
    project = Project(name="千章冷启动", genre="都市奇幻")
    db_session.add(project)
    db_session.flush()
    db_session.add_all(
        [
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章",
                content="章节正文",
                word_count=1000,
                status="generated",
            )
            for index in range(1, 251)
        ]
    )
    db_session.commit()

    response = client.get(f"/api/v1/projects/{project.id}/workspace-bootstrap")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["chapters"]) == 200
    assert payload["chapters"][0]["chapter_index"] == 1
    assert payload["chapters"][-1]["chapter_index"] == 200
    assert payload["chapters_total"] == 250
    assert payload["chapters_offset"] == 0
    assert payload["chapters_limit"] == 200
    assert payload["chapters_has_more"] is True
    assert payload["chapters_latest_index"] == 250
