from app.models import Project
from app.services.writing_agent.agent_retrieval_strategy import inspect_agent_retrieval_strategy


def test_inspect_agent_retrieval_strategy_selects_query_aware_search(db_session, monkeypatch):
    project = Project(name="Retrieval Strategy Query")
    db_session.add(project)
    db_session.commit()

    monkeypatch.setattr(
        "app.services.writing_agent.agent_retrieval_strategy.get_retrieval_diagnostics",
        lambda db, project_id: {
            "project_id": project_id,
            "total_documents": 8,
            "total_chunks": 32,
            "total_terms": 180,
            "total_embeddings": 8,
            "documents_by_source_type": {"chapter": 6, "longform_memory": 2},
        },
    )
    monkeypatch.setattr(
        "app.services.writing_agent.agent_retrieval_strategy.get_longform_maintenance_diagnostics",
        lambda db, project_id, limit=20: {
            "project_id": project_id,
            "ready_for_writing": True,
            "issue_count": 0,
            "recommendations": [],
        },
    )

    output = inspect_agent_retrieval_strategy(
        db_session,
        project.id,
        chapter_index=5,
        query="旧灯塔回声",
        limit=6,
        candidate_limit=50,
    )

    assert output["status"] == "completed"
    assert output["strategy"]["name"] == "query_aware_retrieval"
    assert output["strategy"]["filters"] == {
        "query": "旧灯塔回声",
        "limit": 6,
        "candidate_limit": 50,
        "max_chapter_index": 4,
    }
    assert output["recommended_next_tools"] == ["search_agent_retrieval_context", "summarize_longform_context"]
    assert output["recommended_next_tool_calls"] == [
        {
            "tool_name": "search_agent_retrieval_context",
            "params": {
                "query": "旧灯塔回声",
                "limit": 6,
                "candidate_limit": 50,
                "max_chapter_index": 4,
            },
        },
        {
            "tool_name": "summarize_longform_context",
            "params": {"chapter_index": 5, "query": "旧灯塔回声"},
        },
    ]
    assert output["side_effects"] == {"writes": 0, "mutability": "read"}
    assert output["trace"]["source"] == "inspect_agent_retrieval_strategy"


def test_inspect_agent_retrieval_strategy_selects_chapter_window_without_query(db_session, monkeypatch):
    project = Project(name="Retrieval Strategy Chapter")
    db_session.add(project)
    db_session.commit()

    monkeypatch.setattr(
        "app.services.writing_agent.agent_retrieval_strategy.get_retrieval_diagnostics",
        lambda db, project_id: {
            "project_id": project_id,
            "total_documents": 3,
            "total_chunks": 12,
            "total_terms": 90,
            "total_embeddings": 3,
            "documents_by_source_type": {"chapter": 3},
        },
    )
    monkeypatch.setattr(
        "app.services.writing_agent.agent_retrieval_strategy.get_longform_maintenance_diagnostics",
        lambda db, project_id, limit=20: {
            "project_id": project_id,
            "ready_for_writing": True,
            "issue_count": 0,
            "recommendations": [],
        },
    )

    output = inspect_agent_retrieval_strategy(db_session, project.id, chapter_index=4)

    assert output["strategy"]["name"] == "chapter_context_summary"
    assert output["recommended_next_tools"] == ["summarize_longform_context"]
    assert output["recommended_next_tool_calls"] == [
        {"tool_name": "summarize_longform_context", "params": {"chapter_index": 4}}
    ]


def test_inspect_agent_retrieval_strategy_blocks_for_maintenance(db_session, monkeypatch):
    project = Project(name="Retrieval Strategy Maintenance")
    db_session.add(project)
    db_session.commit()

    monkeypatch.setattr(
        "app.services.writing_agent.agent_retrieval_strategy.get_retrieval_diagnostics",
        lambda db, project_id: {
            "project_id": project_id,
            "total_documents": 0,
            "total_chunks": 0,
            "total_terms": 0,
            "total_embeddings": 0,
            "documents_by_source_type": {},
        },
    )
    monkeypatch.setattr(
        "app.services.writing_agent.agent_retrieval_strategy.get_longform_maintenance_diagnostics",
        lambda db, project_id, limit=20: {
            "project_id": project_id,
            "ready_for_writing": False,
            "issue_count": 2,
            "recommendations": [{"code": "missing_retrieval_index"}],
        },
    )

    output = inspect_agent_retrieval_strategy(
        db_session,
        project.id,
        chapter_index=3,
        query="旧灯塔",
    )

    assert output["status"] == "blocked"
    assert output["strategy"]["name"] == "repair_retrieval_maintenance"
    assert output["recommended_next_tools"] == ["inspect_agent_memory_route", "prepare_repair_longform_maintenance"]
    assert output["recommended_next_tool_calls"] == [
        {
            "tool_name": "inspect_agent_memory_route",
            "params": {"chapter_index": 3, "query": "旧灯塔", "include_context_summary": False},
        },
        {"tool_name": "prepare_repair_longform_maintenance", "params": {}},
    ]
    assert {diagnostic["code"] for diagnostic in output["diagnostics"]} == {
        "longform_memory_needs_maintenance",
        "retrieval_index_empty",
    }
