from app.models import ChapterContent, Project
from app.services.writing_agent.agent_memory_route import inspect_agent_memory_route


def test_inspect_agent_memory_route_blocks_when_longform_memory_is_missing(db_session):
    project = Project(name="Memory Route Missing Longform")
    db_session.add(project)
    db_session.commit()
    db_session.add(
        ChapterContent(
            project_id=project.id,
            chapter_index=1,
            title="第1章",
            content="雾锁灯塔。" * 100,
            word_count=500,
            status="generated",
        )
    )
    db_session.commit()

    output = inspect_agent_memory_route(
        db_session,
        project.id,
        chapter_index=2,
        query="灯塔区集体失忆",
        include_context_summary=False,
    )

    assert output["status"] == "completed"
    assert output["route"]["status"] == "blocked"
    assert output["route"]["reason"] == "longform_memory_needs_maintenance"
    assert output["route"]["recommended_tools"] == ["prepare_repair_longform_maintenance"]
    assert output["longform_maintenance"]["ready_for_writing"] is False
    assert output["longform_maintenance"]["issue_count"] > 0
    assert "longform_memory_needs_maintenance" in {item["code"] for item in output["diagnostics"]}
    provenance = output["memory_provenance"]
    _assert_memory_provenance_contract(provenance)
    assert provenance["status"] == "blocked"
    assert provenance["coverage"]["ready_for_writing"] is False
    assert provenance["coverage"]["chapter_count"] == 1
    assert provenance["coverage"]["longform_memory_count"] == 0
    assert provenance["coverage"]["retrieval_document_count"] == 0
    assert provenance["recovery"]["status"] == "recommended"
    assert provenance["recovery"]["next_tools"] == ["prepare_repair_longform_maintenance"]
    assert provenance["recovery"]["tools"] == [{"tool_name": "prepare_repair_longform_maintenance", "params": {}}]
    assert {"LongformMemory", "LongformMaintenance", "RetrievalDocument"}.issubset(
        {source["source_ref"] for source in provenance["sources"]}
    )
    assert provenance["boundaries"]["world_truth"]["canonical_source"] == "Athena/world_model"


def test_inspect_agent_memory_route_is_ready_for_empty_project(db_session):
    project = Project(name="Memory Route Empty Project")
    db_session.add(project)
    db_session.commit()

    output = inspect_agent_memory_route(
        db_session,
        project.id,
        chapter_index=1,
        include_context_summary=False,
    )

    assert output["status"] == "completed"
    assert output["route"]["status"] == "ready"
    assert output["route"]["can_use_longform_context"] is True
    assert output["route"]["recommended_tools"] == ["summarize_longform_context", "preflight_writing"]
    assert output["longform_memory"]["chapter_count"] == 0
    assert output["retrieval"]["total_documents"] == 0
    provenance = output["memory_provenance"]
    _assert_memory_provenance_contract(provenance)
    assert provenance["status"] == "sparse"
    assert provenance["coverage"] == {
        "chapter_count": 0,
        "longform_memory_count": 0,
        "retrieval_document_count": 0,
        "ready_for_writing": True,
    }
    assert provenance["recovery"]["status"] == "none"
    assert provenance["recovery"]["next_tools"] == []


def test_inspect_agent_memory_route_reports_degraded_retrieval_coverage(db_session, monkeypatch):
    project = Project(name="Memory Route Degraded Retrieval")
    db_session.add(project)
    db_session.commit()

    monkeypatch.setattr(
        "app.services.writing_agent.agent_memory_route.get_longform_memory_diagnostics",
        lambda db, project_id: {
            "project_id": project_id,
            "chapter_count": 12,
            "current_word_count": 24000,
            "counts_by_type": {"chapter": 12, "arc": 1, "global": 1},
            "total_memories": 14,
            "latest_updated_at": None,
        },
    )
    monkeypatch.setattr(
        "app.services.writing_agent.agent_memory_route.get_longform_maintenance_diagnostics",
        lambda db, project_id, limit=20: {
            "project_id": project_id,
            "ready_for_writing": True,
            "issue_count": 0,
            "recommendations": [],
        },
    )
    monkeypatch.setattr(
        "app.services.writing_agent.agent_memory_route.get_retrieval_diagnostics",
        lambda db, project_id: {
            "project_id": project_id,
            "total_documents": 0,
            "total_chunks": 0,
            "total_terms": 0,
            "total_embeddings": 0,
            "documents_by_source_type": {},
        },
    )

    output = inspect_agent_memory_route(
        db_session,
        project.id,
        chapter_index=13,
        query="检查检索覆盖",
        include_context_summary=False,
    )

    assert output["route"]["status"] == "ready"
    assert "retrieval_index_empty" in {item["code"] for item in output["diagnostics"]}
    provenance = output["memory_provenance"]
    _assert_memory_provenance_contract(provenance)
    assert provenance["status"] == "degraded"
    assert provenance["coverage"] == {
        "chapter_count": 12,
        "longform_memory_count": 14,
        "retrieval_document_count": 0,
        "ready_for_writing": True,
    }
    assert provenance["recovery"]["status"] == "optional"
    assert provenance["recovery"]["reason"] == "retrieval_index_empty"
    assert provenance["recovery"]["next_tools"] == ["inspect_agent_memory_route", "prepare_repair_longform_maintenance"]
    assert provenance["recovery"]["tools"] == [
        {
            "tool_name": "inspect_agent_memory_route",
            "params": {
                "chapter_index": 13,
                "query": "检索索引为空，诊断第13章长篇记忆与检索覆盖。",
                "include_context_summary": False,
            },
        }
    ]
    assert provenance["recovery"]["write_tools"] == [{"tool_name": "prepare_repair_longform_maintenance", "params": {}}]


def _assert_memory_provenance_contract(provenance):
    assert {
        "version",
        "status",
        "sources",
        "windows",
        "recovery",
        "trace",
    }.issubset(provenance)
    assert isinstance(provenance["sources"], list)
    assert isinstance(provenance["windows"], dict)
    assert isinstance(provenance["recovery"], dict)
    assert isinstance(provenance["trace"], dict)
