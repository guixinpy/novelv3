import asyncio
from unittest.mock import AsyncMock

from sqlalchemy import event

from app.models import ChapterContent, ConsistencyCheck, Project, Setup, Storyline


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


def test_deep_check_uses_setup_character_projection_without_selecting_full_setup_json(db_session, monkeypatch):
    import app.core.background_analyzer as analyzer_module

    project = Project(name="Background Setup Projection")
    db_session.add(project)
    db_session.flush()
    project_id = project.id
    db_session.add(
        Setup(
            project_id=project_id,
            status="generated",
            world_building={"rules": "长世界规则" * 1000},
            characters=[
                {
                    "name": "林舟",
                    "character_status": "dead",
                    "bio": "超长人物背景" * 5000,
                }
            ],
            core_concept={"hook": "旧灯塔" * 1000},
        )
    )
    db_session.add(
        ChapterContent(
            project_id=project_id,
            chapter_index=1,
            title="第一章",
            content="林舟在旧灯塔下出现。",
            word_count=20,
            status="generated",
        )
    )
    db_session.commit()
    analyzer = analyzer_module.BackgroundAnalyzer()
    analyzer.l2.extract = AsyncMock(return_value=[])
    monkeypatch.setattr(analyzer_module, "SessionLocal", lambda: db_session)
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        result = asyncio.run(analyzer.run_deep_check(project_id, 1))
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert "error" not in result
    assert (
        db_session.query(ConsistencyCheck)
        .filter(ConsistencyCheck.project_id == project_id, ConsistencyCheck.subject == "林舟")
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
