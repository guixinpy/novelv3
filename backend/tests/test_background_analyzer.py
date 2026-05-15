from sqlalchemy import event

from app.models import Project, Storyline


def test_overdue_foreshadowing_candidates_do_not_select_full_storyline_json(db_session):
    import app.core.background_analyzer as analyzer_module

    loader = getattr(analyzer_module, "_load_overdue_foreshadowing_candidates", None)
    assert loader is not None

    project = Project(name="Foreshadowing Candidate Window")
    db_session.add(project)
    db_session.flush()
    db_session.add(
        Storyline(
            project_id=project.id,
            status="generated",
            plotlines=[],
            foreshadowing=[
                {
                    "hint": "逾期伏笔",
                    "planted_chapter": 1,
                    "resolved_chapter": 10,
                    "status": "planted",
                },
                {
                    "hint": "缺省状态逾期伏笔",
                    "planted_chapter": 2,
                    "resolved_chapter": 12,
                },
                {
                    "hint": "未逾期伏笔",
                    "planted_chapter": 20,
                    "resolved_chapter": 49,
                    "status": "planted",
                },
                {
                    "hint": "已解决伏笔",
                    "planted_chapter": 3,
                    "resolved_chapter": 10,
                    "status": "resolved",
                },
            ] + [
                {
                    "hint": f"未来伏笔{index}",
                    "planted_chapter": index,
                    "resolved_chapter": 100 + index,
                    "status": "planted",
                }
                for index in range(1, 501)
            ],
        )
    )
    db_session.commit()
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        candidates = loader(db_session, project.id, 50)
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert [item["hint"] for item in candidates] == ["逾期伏笔", "缺省状态逾期伏笔"]
    assert any("json_each(storylines.foreshadowing)" in statement for statement in statements)
    select_clauses = [
        statement.split(" from storylines", 1)[0]
        for statement in statements
        if " from storylines" in statement
    ]
    assert select_clauses
    assert all("storylines.foreshadowing as" not in clause for clause in select_clauses)
