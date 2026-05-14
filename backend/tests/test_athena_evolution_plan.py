from sqlalchemy import event

from app.models import Outline, Project, Storyline


def test_evolution_plan_window_mode_does_not_select_full_plan_json(client, db_session):
    project = Project(name="Windowed Narrative Plan")
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
        )
    )
    db_session.add(
        Storyline(
            project_id=project.id,
            status="generated",
            plotlines=[
                {
                    "name": f"故事线{index}",
                    "type": "sub",
                    "milestones": [{"chapter_index": index, "title": f"节点{index}"}],
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
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        response = client.get(
            f"/api/v1/projects/{project.id}/athena/evolution/plan"
            "?mode=window&chapter_offset=100&chapter_limit=3"
            "&plotline_offset=10&plotline_limit=2"
            "&foreshadowing_offset=20&foreshadowing_limit=4"
        )
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert response.status_code == 200
    data = response.json()
    assert [item["chapter_index"] for item in data["outline"]["chapters"]] == [101, 102, 103]
    assert data["outline"]["chapters_total"] == 1000
    assert data["outline"]["chapters_has_more"] is True
    assert [item["name"] for item in data["storyline"]["plotlines"]] == ["故事线11", "故事线12"]
    assert data["storyline"]["plotlines_total"] == 60
    assert [item["hint"] for item in data["storyline"]["foreshadowing"]] == ["伏笔21", "伏笔22", "伏笔23", "伏笔24"]
    assert data["storyline"]["foreshadowing_total"] == 300

    select_clauses = [
        statement.split(" from ", 1)[0]
        for statement in statements
        if " from outlines" in statement or " from storylines" in statement
    ]
    assert select_clauses
    assert all("outlines.chapters as" not in clause for clause in select_clauses)
    assert all("outlines.plotlines as" not in clause for clause in select_clauses)
    assert all("storylines.plotlines as" not in clause for clause in select_clauses)
    assert all("storylines.foreshadowing as" not in clause for clause in select_clauses)
