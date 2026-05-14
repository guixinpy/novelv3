from app.models import ChapterContent, Dialog, DialogMessage, Outline, Project, Setup, Storyline, Version
from sqlalchemy import event


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
    assert payload["versions_total"] == 1
    assert payload["versions_offset"] == 0
    assert payload["versions_limit"] == 50
    assert payload["versions_has_more"] is False
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


def test_workspace_bootstrap_summaries_do_not_select_body_content(client, db_session):
    project = Project(name="轻量冷启动", genre="都市奇幻")
    db_session.add(project)
    db_session.flush()
    chapter = ChapterContent(
        project_id=project.id,
        chapter_index=1,
        title="第一章",
        content="冷启动不应读取的大段章节正文。" * 1000,
        word_count=1000,
        status="generated",
    )
    db_session.add(chapter)
    db_session.flush()
    db_session.add(
        Version(
            project_id=project.id,
            node_type="chapter",
            node_id=chapter.id,
            version_number=1,
            content="冷启动不应读取的大段版本正文。" * 1000,
            description="initial",
        )
    )
    db_session.commit()
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        response = client.get(f"/api/v1/projects/{project.id}/workspace-bootstrap")
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert response.status_code == 200
    chapter_select_clauses = [
        statement.split("from chapter_contents", 1)[0]
        for statement in statements
        if "from chapter_contents" in statement
    ]
    version_select_clauses = [
        statement.split("from versions", 1)[0]
        for statement in statements
        if "from versions" in statement
    ]
    assert chapter_select_clauses
    assert version_select_clauses
    assert all("chapter_contents.content" not in clause for clause in chapter_select_clauses)
    assert all("versions.content" not in clause for clause in version_select_clauses)
