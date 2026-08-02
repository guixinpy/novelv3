"""大纲 CRUD 测试（v1 绞杀：generate/expand-window 端点已删除）。"""
from sqlalchemy import event

from app.models import Outline, Project


def test_get_outline_not_found(client):
    r = client.get("/api/v1/projects/nonexistent/outline")
    assert r.status_code == 404


def test_patch_outline_chapter_updates_json_without_selecting_full_chapters(client, db_session):
    project = Project(name="Patch Large Outline")
    db_session.add(project)
    db_session.flush()
    db_session.add(
        Outline(
            project_id=project.id,
            status="generated",
            total_chapters=1000,
            chapters=[
                {
                    "chapter_index": index,
                    "title": f"第{index}章",
                    "summary": "章节摘要" * 20,
                    "scenes": ["旧场景"],
                    "characters": ["旧角色"],
                    "purpose": "旧目的",
                }
                for index in range(1, 1001)
            ],
        )
    )
    db_session.commit()
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        response = client.patch(
            f"/api/v1/projects/{project.id}/outline/chapters/512",
            json={
                "title": "新的第512章",
                "scenes": ["新场景"],
                "characters": ["新角色"],
                "purpose": "新目的",
            },
        )
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert response.status_code == 200
    updated_outline = db_session.query(Outline).filter(Outline.project_id == project.id).one()
    updated = updated_outline.chapters[511]
    assert updated["chapter_index"] == 512
    assert updated["title"] == "新的第512章"
    assert updated["summary"] == "章节摘要" * 20
    assert updated["scenes"] == ["新场景"]
    assert updated["characters"] == ["新角色"]
    assert updated["purpose"] == "新目的"
    assert updated_outline.chapters[510]["title"] == "第511章"
    assert updated_outline.chapters[512]["title"] == "第513章"

    select_clauses = [
        statement.split(" from outlines", 1)[0]
        for statement in statements
        if " from outlines" in statement
    ]
    assert select_clauses
    assert any("json_each(outlines.chapters)" in statement for statement in statements)
    assert any("json_set" in statement for statement in statements)
    assert all("outlines.chapters as" not in clause for clause in select_clauses)
