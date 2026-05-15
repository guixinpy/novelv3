from sqlalchemy import event

from app.models import Outline, Project, Storyline


def _normalize_statement(statement: str) -> str:
    return " ".join(statement.lower().split())


def _select_clauses_for(statements: list[str], table_name: str) -> list[str]:
    return [
        statement.split(f" from {table_name}", 1)[0]
        for statement in statements
        if f" from {table_name}" in statement
    ]


def test_legacy_outline_get_defaults_to_bounded_window_without_selecting_full_json(client, db_session):
    project = Project(name="Legacy Outline Window")
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
                }
                for index in range(1, 1001)
            ],
            plotlines=[
                {
                    "name": f"大纲线{index}",
                    "type": "sub",
                    "milestones": [{"chapter_index": index, "title": f"节点{index}"}],
                }
                for index in range(1, 51)
            ],
            foreshadowing=[
                {
                    "hint": f"伏笔{index}",
                    "planted_chapter": index,
                    "resolved_chapter": index + 10,
                    "status": "pending",
                }
                for index in range(1, 301)
            ],
        )
    )
    db_session.commit()
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(_normalize_statement(statement))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        response = client.get(f"/api/v1/projects/{project.id}/outline")
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert response.status_code == 200
    data = response.json()
    assert len(data["chapters"]) == 100
    assert data["chapters_total"] == 1000
    assert data["chapters_has_more"] is True
    assert len(data["plotlines"]) == 20
    assert data["plotlines_total"] == 50
    assert data["plotlines_has_more"] is True
    assert len(data["foreshadowing"]) == 100
    assert data["foreshadowing_total"] == 300
    assert data["foreshadowing_has_more"] is True

    select_clauses = _select_clauses_for(statements, "outlines")
    assert select_clauses
    assert all("outlines.chapters as" not in clause for clause in select_clauses)
    assert all("outlines.plotlines as" not in clause for clause in select_clauses)
    assert all("outlines.foreshadowing as" not in clause for clause in select_clauses)


def test_legacy_storyline_get_defaults_to_bounded_window_without_selecting_full_json(client, db_session):
    project = Project(name="Legacy Storyline Window")
    db_session.add(project)
    db_session.flush()
    db_session.add(
        Storyline(
            project_id=project.id,
            status="generated",
            plotlines=[
                {
                    "name": f"故事线{index}",
                    "type": "sub",
                    "milestones": [
                        {"chapter_index": chapter_index, "title": f"节点{chapter_index}"}
                        for chapter_index in range(1, 1001)
                    ] if index == 1 else [],
                }
                for index in range(1, 61)
            ],
            foreshadowing=[
                {
                    "hint": f"伏笔{index}",
                    "planted_chapter": index,
                    "resolved_chapter": index + 10,
                    "status": "pending",
                }
                for index in range(1, 301)
            ],
        )
    )
    db_session.commit()
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(_normalize_statement(statement))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        response = client.get(f"/api/v1/projects/{project.id}/storyline")
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert response.status_code == 200
    data = response.json()
    assert len(data["plotlines"]) == 20
    assert data["plotlines_total"] == 60
    assert data["plotlines_has_more"] is True
    assert len(data["plotlines"][0]["milestones"]) == 80
    assert data["plotlines"][0]["milestones_total"] == 1000
    assert data["plotlines"][0]["milestones_has_more"] is True
    assert len(data["foreshadowing"]) == 100
    assert data["foreshadowing_total"] == 300
    assert data["foreshadowing_has_more"] is True

    select_clauses = _select_clauses_for(statements, "storylines")
    assert select_clauses
    assert all("storylines.plotlines as" not in clause for clause in select_clauses)
    assert all("storylines.foreshadowing as" not in clause for clause in select_clauses)
