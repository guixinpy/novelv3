from types import SimpleNamespace

import pytest

from app.models import AIModelCallTrace, ChapterContent, LongformMemory, Outline, Project, Storyline
from app.schemas.writing_agent import WritingAgentToolRequest
from app.services.writing_agent.memory_tree import (
    MEMORY_TREE_CHAPTER_SUMMARY_TYPE,
    MEMORY_TREE_VERSION,
    MEMORY_TREE_VOLUME_SUMMARY_TYPE,
    build_agent_memory_tree_llm_summary_plan,
    inspect_agent_memory_tree,
    inspect_agent_memory_tree_quality,
    materialize_agent_memory_tree_summaries,
    summarize_agent_memory_tree_llm_candidate,
)
from app.services.writing_agent.memory_tree_summary_execution import (
    prepare_record_agent_memory_tree_summaries,
)
from app.services.writing_agent.tool_adapter_types import WritingAgentToolContext
from app.services.writing_agent.tool_executor import execute_writing_agent_tool, writing_agent_tool_adapter_metadata
from app.services.writing_agent.tool_registry import get_agent_tool_descriptor


def test_memory_tree_projects_volume_chapter_scene_and_beat_nodes(db_session):
    project, refs = _seed_memory_tree_project(db_session)

    tree = inspect_agent_memory_tree(db_session, project.id)
    nodes = {node["id"]: node for node in tree["nodes"]}

    assert tree["version"] == MEMORY_TREE_VERSION
    assert tree["status"] == "ready"
    assert tree["levels"] == ["volume", "chapter", "scene", "beat"]
    assert tree["summary"] == {
        "volume_nodes": 1,
        "chapter_nodes": 2,
        "scene_nodes": 1,
        "beat_nodes": 1,
    }
    assert nodes["volume:1"]["children"] == ["chapter:1", "chapter:2"]
    assert nodes["chapter:1"]["source_refs"] == [
        {"source_type": "chapter_content", "source_id": refs["chapter_1_id"]},
        {"source_type": "outline", "source_id": refs["outline_id"]},
    ]
    assert nodes[f"scene:{refs['scene_memory_id']}"]["parent_id"] == "chapter:1"
    assert nodes[f"scene:{refs['scene_memory_id']}"]["source_refs"] == [
        {"source_type": "longform_memory", "source_id": refs["scene_memory_id"]},
        {"source_type": "chapter_content", "source_id": refs["chapter_1_id"]},
    ]
    assert nodes[f"beat:{refs['beat_memory_id']}"]["parent_id"] == f"scene:{refs['scene_memory_id']}"
    assert nodes[f"beat:{refs['beat_memory_id']}"]["source_refs"] == [
        {"source_type": "longform_memory", "source_id": refs["beat_memory_id"]},
        {"source_type": "chapter_content", "source_id": refs["chapter_1_id"]},
    ]
    assert tree["trace"]["source_tables"] == ["chapter_contents", "outlines", "storylines", "longform_memories"]


def test_memory_tree_materializes_volume_and_chapter_summary_nodes(db_session):
    project, refs = _seed_memory_tree_project(db_session)

    result = materialize_agent_memory_tree_summaries(db_session, project.id)

    assert result["status"] == "completed"
    assert result["summary"] == {
        "volume_summary_nodes": 1,
        "chapter_summary_nodes": 2,
        "created_nodes": 3,
        "updated_nodes": 0,
    }
    records = {
        (memory.memory_type, memory.scope_key): memory
        for memory in db_session.query(LongformMemory).filter(LongformMemory.project_id == project.id).all()
    }
    volume_record = records[(MEMORY_TREE_VOLUME_SUMMARY_TYPE, "volume:1")]
    chapter_record = records[(MEMORY_TREE_CHAPTER_SUMMARY_TYPE, "chapter:1")]

    assert volume_record.start_chapter_index == 1
    assert volume_record.end_chapter_index == 2
    assert "空白信主线" in volume_record.summary
    assert chapter_record.start_chapter_index == 1
    assert chapter_record.end_chapter_index == 1
    assert "收到空白信" in chapter_record.summary

    tree = inspect_agent_memory_tree(db_session, project.id)
    nodes = {node["id"]: node for node in tree["nodes"]}

    assert nodes["volume:1"]["summary"] == volume_record.summary
    assert {"source_type": "longform_memory", "source_id": volume_record.id} in nodes["volume:1"]["source_refs"]
    assert nodes["chapter:1"]["summary"] == chapter_record.summary
    assert {"source_type": "longform_memory", "source_id": chapter_record.id} in nodes["chapter:1"]["source_refs"]
    assert {"source_type": "chapter_content", "source_id": refs["chapter_1_id"]} in nodes["chapter:1"]["source_refs"]


def test_memory_tree_expands_node_with_depth_and_ancestors(db_session):
    project, refs = _seed_memory_tree_project(db_session)

    tree = inspect_agent_memory_tree(
        db_session,
        project.id,
        expand_node_id="chapter:1",
        max_depth=1,
        include_ancestors=True,
    )

    assert [node["id"] for node in tree["nodes"]] == [
        "volume:1",
        "chapter:1",
        f"scene:{refs['scene_memory_id']}",
    ]
    assert tree["navigation"]["mode"] == "expanded_subtree"
    assert tree["navigation"]["expanded_node_id"] == "chapter:1"
    assert tree["navigation"]["max_depth"] == 1
    assert tree["navigation"]["ancestor_node_ids"] == ["volume:1"]
    assert tree["navigation"]["descendant_node_ids"] == [f"scene:{refs['scene_memory_id']}"]


def test_memory_tree_semantic_search_scores_cross_field_matches_and_recommends_drilldown(db_session):
    project, _refs = _seed_memory_tree_project(db_session)

    tree = inspect_agent_memory_tree(
        db_session,
        project.id,
        query="灯塔旧回声",
        include_ancestors=True,
    )

    assert [node["id"] for node in tree["nodes"]] == ["volume:1", "chapter:2"]
    chapter_node = next(node for node in tree["nodes"] if node["id"] == "chapter:2")
    assert chapter_node["relevance"]["score"] > 0
    assert chapter_node["relevance"]["matched_fields"] == ["title", "summary"]
    assert set(chapter_node["relevance"]["matched_terms"]) >= {"灯", "塔", "旧", "回", "声"}
    assert "semantic_token_overlap" in chapter_node["relevance"]["match_reasons"]
    assert tree["navigation"]["mode"] == "semantic_search_with_ancestors"
    assert tree["navigation"]["matched_node_ids"] == ["chapter:2"]
    assert tree["navigation"]["ancestor_node_ids"] == ["volume:1"]
    assert tree["navigation"]["recommended_drilldowns"] == [
        {
            "node_id": "chapter:2",
            "expand_node_id": "chapter:2",
            "reason": "highest_relevance",
            "score": chapter_node["relevance"]["score"],
        }
    ]


def test_memory_tree_semantic_search_rolls_up_descendant_matches_to_filtered_level(db_session):
    project, refs = _seed_memory_tree_project(db_session)
    beat_node_id = f"beat:{refs['beat_memory_id']}"

    tree = inspect_agent_memory_tree(
        db_session,
        project.id,
        level="chapter",
        query="后续调查",
    )

    assert [node["id"] for node in tree["nodes"]] == ["chapter:1"]
    chapter_node = tree["nodes"][0]
    assert chapter_node["relevance"]["score"] > 0
    assert "descendant_semantic_match" in chapter_node["relevance"]["match_reasons"]
    assert chapter_node["relevance"]["matched_descendant_ids"] == [beat_node_id]
    assert "descendant.summary" in chapter_node["relevance"]["matched_fields"]
    assert set(chapter_node["relevance"]["matched_terms"]) >= {"后", "续", "调", "查"}
    assert tree["navigation"]["mode"] == "semantic_search"
    assert tree["navigation"]["matched_node_ids"] == ["chapter:1"]
    assert tree["navigation"]["recommended_drilldowns"] == [
        {
            "node_id": "chapter:1",
            "expand_node_id": "chapter:1",
            "reason": "descendant_relevance",
            "score": chapter_node["relevance"]["score"],
            "matched_descendant_ids": [beat_node_id],
        }
    ]


def test_memory_tree_quality_projection_reports_summary_and_semantic_coverage(db_session):
    project, _refs = _seed_memory_tree_project(db_session)
    materialize_agent_memory_tree_summaries(db_session, project.id)

    output = inspect_agent_memory_tree_quality(
        db_session,
        project.id,
        chapter_index=1,
        query="后续调查",
    )

    assert output["status"] == "ready"
    assert output["coverage"] == {
        "volume_nodes": 1,
        "chapter_nodes": 2,
        "scene_nodes": 1,
        "beat_nodes": 1,
        "summary_backed_volume_nodes": 1,
        "summary_backed_chapter_nodes": 2,
        "chapter_nodes_with_children": 1,
        "chapter_node_coverage_ratio": 1.0,
        "summary_backed_chapter_ratio": 1.0,
    }
    assert output["semantic_probe"] == {
        "status": "matched",
        "query": "后续调查",
        "chapter_index": 1,
        "matched_node_count": 1,
        "matched_levels": ["chapter"],
        "recommended_drilldown_count": 1,
        "top_match": {
            "level": "chapter",
            "chapter_index": 1,
            "title": "第一章 雨巷来信",
            "score": 1.235,
            "matched_fields": ["descendant.title", "descendant.summary"],
            "match_reasons": ["descendant_semantic_match"],
            "matched_descendant_count": 1,
        },
    }
    assert output["diagnostics"] == []
    assert output["recommended_next_tools"] == ["inspect_agent_memory_tree", "inspect_agent_dogfood_evidence"]
    assert output["trace"] == {
        "source": "inspect_agent_memory_tree_quality",
        "version": "phase245.memory_tree_quality.v1",
        "mutability": "read",
        "runtime_behavior_changed": False,
    }


def test_memory_tree_llm_summary_plan_builds_trace_ready_evidence_window_without_writes(db_session):
    project, _refs = _seed_memory_tree_project(db_session)

    output = build_agent_memory_tree_llm_summary_plan(
        db_session,
        project.id,
        chapter_index=2,
        query="蓝焰证词",
        max_source_chars=180,
    )

    assert output["status"] == "ready"
    assert output["summary_target"] == {
        "level": "chapter",
        "chapter_index": 2,
        "scope_key": "chapter:2",
        "memory_type": MEMORY_TREE_CHAPTER_SUMMARY_TYPE,
    }
    assert output["evidence_window"]["source_count"] >= 2
    assert output["evidence_window"]["source_chars"] <= 180
    assert output["evidence_window"]["sources"][0]["source_type"] == "chapter_content"
    assert output["llm_prompt_contract"]["trace_required"] is True
    assert output["llm_prompt_contract"]["trace_type"] == "memory_tree_summary_generation"
    assert "蓝焰证词" in output["llm_prompt_contract"]["user_prompt"]
    assert output["quality_gate"]["precheck"]["semantic_probe"]["status"] == "missing_match"
    assert output["quality_gate"]["expected_postcheck"] == {
        "tool_name": "inspect_agent_memory_tree_quality",
        "params": {"chapter_index": 2, "query": "蓝焰证词"},
    }
    assert output["side_effects"] == {"executed": [], "skipped": ["record_agent_memory_tree_summaries"]}
    assert output["recommended_next_tools"] == [
        "prepare_record_agent_memory_tree_summaries",
        "execute_record_agent_memory_tree_summaries_with_approval",
        "inspect_agent_memory_tree_quality",
    ]
    assert output["trace"]["mutability"] == "read"
    assert (
        db_session.query(LongformMemory)
        .filter(
            LongformMemory.project_id == project.id,
            LongformMemory.memory_type == MEMORY_TREE_CHAPTER_SUMMARY_TYPE,
        )
        .count()
        == 0
    )


@pytest.mark.asyncio
async def test_memory_tree_llm_summary_candidate_records_trace_without_memory_write(db_session):
    project, _refs = _seed_memory_tree_project(db_session)
    ai_service = _FakeMemoryTreeAIService(
        '{"summary":"顾衍追查灯塔旧回声，蓝焰证词指向空白信来源仍未解。",'
        '"salient_terms":["顾衍","灯塔","蓝焰证词"],'
        '"open_questions":["空白信来源是否与灯塔有关？"],'
        '"source_coverage":["chapter_content","outline"]}'
    )

    output = await summarize_agent_memory_tree_llm_candidate(
        db_session,
        project.id,
        chapter_index=2,
        query="蓝焰证词",
        max_source_chars=220,
        ai_service=ai_service,
    )

    assert output["status"] == "ready"
    assert output["summary_target"]["scope_key"] == "chapter:2"
    assert output["candidate"] == {
        "summary": "顾衍追查灯塔旧回声，蓝焰证词指向空白信来源仍未解。",
        "salient_terms": ["顾衍", "灯塔", "蓝焰证词"],
        "open_questions": ["空白信来源是否与灯塔有关？"],
        "source_coverage": ["chapter_content", "outline"],
    }
    assert output["side_effects"] == {
        "executed": ["memory_tree_summary_generation_trace"],
        "skipped": ["record_agent_memory_tree_summaries"],
    }
    assert output["recommended_next_tools"] == [
        "prepare_record_agent_memory_tree_summaries",
        "execute_record_agent_memory_tree_summaries_with_approval",
        "inspect_agent_memory_tree_quality",
    ]
    assert output["trace"]["llm_call_executed"] is True
    assert output["trace"]["trace_type"] == "memory_tree_summary_generation"
    assert output["trace"]["trace_id"]
    assert ai_service.calls[0]["kwargs"]["response_format"] == {"type": "json_object"}

    trace = db_session.query(AIModelCallTrace).filter_by(id=output["trace"]["trace_id"]).one()
    assert trace.status == "success"
    assert trace.trace_type == "memory_tree_summary_generation"
    assert trace.chapter_index == 2
    assert trace.prompt_tokens == 11
    assert trace.completion_tokens == 7
    assert trace.messages[0]["role"] == "system"
    assert trace.messages[1]["role"] == "user"
    assert trace.context_blocks[0]["kind"] == "chapter_content"
    assert trace.trace_metadata["memory_tree_llm_summary_candidate"]["source_count"] >= 2
    assert (
        db_session.query(LongformMemory)
        .filter(
            LongformMemory.project_id == project.id,
            LongformMemory.memory_type == MEMORY_TREE_CHAPTER_SUMMARY_TYPE,
        )
        .count()
        == 0
    )


@pytest.mark.asyncio
async def test_record_agent_memory_tree_summaries_tool_requires_approval(db_session):
    project, _refs = _seed_memory_tree_project(db_session)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-memory-tree-materialize"),
        WritingAgentToolRequest(tool_name="record_agent_memory_tree_summaries", params={}),
    )

    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["reason"] == "approval_required_before_write"
    assert result.output["required_approval"] == {
        "prepare_tool": "prepare_record_agent_memory_tree_summaries",
        "execute_tool": "execute_record_agent_memory_tree_summaries_with_approval",
        "approval_scope": "agent_plan_approval",
    }
    assert result.output["side_effects"] == {"executed": [], "skipped": ["record_agent_memory_tree_summaries"]}
    assert (
        db_session.query(LongformMemory)
        .filter(
            LongformMemory.project_id == project.id,
            LongformMemory.memory_type == MEMORY_TREE_CHAPTER_SUMMARY_TYPE,
        )
        .count()
        == 0
    )


@pytest.mark.asyncio
async def test_prepare_record_agent_memory_tree_summaries_tool_builds_approval_contract(db_session):
    project, _refs = _seed_memory_tree_project(db_session)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-memory-tree-prepare"),
        WritingAgentToolRequest(
            tool_name="prepare_record_agent_memory_tree_summaries",
            params={"quality_query": "后续调查", "quality_chapter_index": 1},
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "approval_required"
    assert result.output["target_type"] == "agent_memory_tree_summary"
    assert result.output["summary_plan"] == {
        "chapter_index": None,
        "quality_chapter_index": 1,
        "quality_query": "后续调查",
    }
    plan_step = result.output["agent_plan"]["steps"][0]
    assert plan_step["tool_name"] == "record_agent_memory_tree_summaries"
    assert plan_step["approval_executor_tool_name"] == "execute_record_agent_memory_tree_summaries_with_approval"
    assert plan_step["requires_confirmation"] is True
    assert result.output["side_effects"] == {"executed": [], "skipped": ["record_agent_memory_tree_summaries"]}
    assert result.output["recommended_next_tools"] == ["execute_record_agent_memory_tree_summaries_with_approval"]


@pytest.mark.asyncio
async def test_execute_record_agent_memory_tree_summaries_with_approval_persists_and_reports_quality(db_session):
    project, _refs = _seed_memory_tree_project(db_session)
    prepared = prepare_record_agent_memory_tree_summaries(
        db_session,
        project.id,
        action_params={"quality_query": "后续调查", "quality_chapter_index": 1},
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-memory-tree-approved"),
        WritingAgentToolRequest(
            tool_name="execute_record_agent_memory_tree_summaries_with_approval",
            params={
                "quality_query": "后续调查",
                "quality_chapter_index": 1,
                "confirm_execute": True,
                "approval_contract_hash": prepared["agent_plan_approval_contract_hash"],
                "approval_contract": prepared["agent_plan_approval_contract"],
            },
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "success"
    assert result.output["materialization"]["summary"]["chapter_summary_nodes"] == 2
    assert result.output["post_materialization_quality"]["status"] == "ready"
    assert result.output["post_materialization_quality"]["coverage"]["summary_backed_chapter_nodes"] == 2
    assert result.output["post_materialization_quality"]["diagnostics"] == []
    assert result.output["agent_plan_approval_verification"]["status"] == "ready"
    assert result.output["side_effects"] == {"executed": ["record_agent_memory_tree_summaries"], "skipped": []}
    assert result.output["recommended_next_tools"] == ["inspect_agent_memory_tree_quality"]
    assert (
        db_session.query(LongformMemory)
        .filter(
            LongformMemory.project_id == project.id,
            LongformMemory.memory_type == MEMORY_TREE_CHAPTER_SUMMARY_TYPE,
        )
        .count()
        == 2
    )


@pytest.mark.asyncio
async def test_inspect_agent_memory_tree_tool_supports_drilldown_filters(db_session):
    project, refs = _seed_memory_tree_project(db_session)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-memory-tree"),
        WritingAgentToolRequest(
            tool_name="inspect_agent_memory_tree",
            params={"level": "scene", "chapter_index": 1, "query": "雨巷"},
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "ready"
    assert [node["id"] for node in result.output["nodes"]] == [f"scene:{refs['scene_memory_id']}"]
    assert result.output["filters"] == {
        "level": "scene",
        "node_id": None,
        "expand_node_id": None,
        "chapter_index": 1,
        "query": "雨巷",
        "include_ancestors": False,
        "max_depth": None,
    }


@pytest.mark.asyncio
async def test_inspect_agent_memory_tree_tool_search_can_include_ancestor_context(db_session):
    project, refs = _seed_memory_tree_project(db_session)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-memory-tree-search"),
        WritingAgentToolRequest(
            tool_name="inspect_agent_memory_tree",
            params={"query": "后续调查", "include_ancestors": True},
        ),
    )

    assert result.handled is True
    assert [node["id"] for node in result.output["nodes"]] == [
        "volume:1",
        "chapter:1",
        f"scene:{refs['scene_memory_id']}",
        f"beat:{refs['beat_memory_id']}",
    ]
    assert result.output["navigation"]["mode"] == "search_with_ancestors"
    assert result.output["navigation"]["matched_node_ids"] == [f"beat:{refs['beat_memory_id']}"]
    assert result.output["navigation"]["ancestor_node_ids"] == [
        "volume:1",
        "chapter:1",
        f"scene:{refs['scene_memory_id']}",
    ]


@pytest.mark.asyncio
async def test_inspect_agent_memory_tree_quality_tool_reports_projection(db_session):
    project, _refs = _seed_memory_tree_project(db_session)
    materialize_agent_memory_tree_summaries(db_session, project.id)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-memory-tree-quality"),
        WritingAgentToolRequest(
            tool_name="inspect_agent_memory_tree_quality",
            params={"chapter_index": 1, "query": "后续调查"},
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "ready"
    assert result.output["semantic_probe"]["status"] == "matched"
    assert result.output["coverage"]["summary_backed_chapter_nodes"] == 2


@pytest.mark.asyncio
async def test_build_memory_tree_llm_summary_plan_tool_reports_readonly_contract(db_session):
    project, _refs = _seed_memory_tree_project(db_session)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-memory-tree-llm-summary-plan"),
        WritingAgentToolRequest(
            tool_name="build_agent_memory_tree_llm_summary_plan",
            params={"chapter_index": 2, "query": "灯塔旧回声", "max_source_chars": 180},
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "ready"
    assert result.output["llm_prompt_contract"]["trace_required"] is True
    assert result.output["quality_gate"]["expected_postcheck"]["tool_name"] == "inspect_agent_memory_tree_quality"
    assert result.output["side_effects"] == {"executed": [], "skipped": ["record_agent_memory_tree_summaries"]}


@pytest.mark.asyncio
async def test_summarize_memory_tree_llm_candidate_tool_reports_traced_candidate(db_session, monkeypatch):
    project, _refs = _seed_memory_tree_project(db_session)
    fake_ai_service = _FakeMemoryTreeAIService('{"summary":"灯塔旧回声仍指向空白信。"}')
    monkeypatch.setattr("app.services.writing_agent.memory_tree.AIService", lambda: fake_ai_service)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-memory-tree-llm-candidate"),
        WritingAgentToolRequest(
            tool_name="summarize_agent_memory_tree_llm_candidate",
            params={"chapter_index": 2, "query": "灯塔旧回声", "max_source_chars": 180},
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "ready"
    assert result.output["candidate"]["summary"] == "灯塔旧回声仍指向空白信。"
    assert result.output["trace"]["trace_type"] == "memory_tree_summary_generation"
    assert result.output["trace"]["llm_call_executed"] is True
    assert fake_ai_service.closed is True


def test_memory_tree_tool_is_registered_with_read_metadata():
    descriptor = get_agent_tool_descriptor("inspect_agent_memory_tree")
    metadata = writing_agent_tool_adapter_metadata("inspect_agent_memory_tree")

    assert descriptor is not None
    assert descriptor.category == "longform_memory"
    assert descriptor.target_type == "agent_memory_tree"
    assert descriptor.input_schema["properties"]["expand_node_id"]["type"] == "string"
    assert descriptor.input_schema["properties"]["include_ancestors"]["type"] == "boolean"
    assert descriptor.input_schema["properties"]["max_depth"]["type"] == "integer"
    assert metadata == {
        "tool_name": "inspect_agent_memory_tree",
        "adapter_type": "static",
        "category": "longform_memory",
        "mutability": "read",
        "handler_name": "_inspect_agent_memory_tree",
    }


def test_memory_tree_quality_tool_is_registered_with_read_metadata():
    descriptor = get_agent_tool_descriptor("inspect_agent_memory_tree_quality")
    metadata = writing_agent_tool_adapter_metadata("inspect_agent_memory_tree_quality")

    assert descriptor is not None
    assert descriptor.category == "longform_memory"
    assert descriptor.target_type == "agent_memory_tree_quality"
    assert descriptor.input_schema["properties"]["query"]["type"] == "string"
    assert descriptor.input_schema["properties"]["chapter_index"]["minimum"] == 1
    assert descriptor.output_schema["properties"]["coverage"]["type"] == "object"
    assert metadata == {
        "tool_name": "inspect_agent_memory_tree_quality",
        "adapter_type": "static",
        "category": "longform_memory",
        "mutability": "read",
        "handler_name": "_inspect_agent_memory_tree_quality",
    }


def test_memory_tree_llm_summary_plan_tool_is_registered_with_read_metadata():
    descriptor = get_agent_tool_descriptor("build_agent_memory_tree_llm_summary_plan")
    metadata = writing_agent_tool_adapter_metadata("build_agent_memory_tree_llm_summary_plan")

    assert descriptor is not None
    assert descriptor.category == "longform_memory"
    assert descriptor.target_type == "agent_memory_tree_llm_summary_plan"
    assert descriptor.non_blocking_report is True
    assert descriptor.input_schema["properties"]["max_source_chars"]["minimum"] == 120
    assert descriptor.output_schema["properties"]["llm_prompt_contract"]["type"] == "object"
    assert metadata == {
        "tool_name": "build_agent_memory_tree_llm_summary_plan",
        "adapter_type": "static",
        "category": "longform_memory",
        "mutability": "read",
        "handler_name": "_build_agent_memory_tree_llm_summary_plan",
    }


def test_memory_tree_llm_summary_candidate_tool_is_registered_with_read_metadata():
    descriptor = get_agent_tool_descriptor("summarize_agent_memory_tree_llm_candidate")
    metadata = writing_agent_tool_adapter_metadata("summarize_agent_memory_tree_llm_candidate")

    assert descriptor is not None
    assert descriptor.category == "longform_memory"
    assert descriptor.target_type == "agent_memory_tree_llm_summary_candidate"
    assert descriptor.non_blocking_report is True
    assert descriptor.input_schema["properties"]["max_source_chars"]["minimum"] == 120
    assert descriptor.output_schema["properties"]["candidate"]["type"] == "object"
    assert metadata == {
        "tool_name": "summarize_agent_memory_tree_llm_candidate",
        "adapter_type": "static",
        "category": "longform_memory",
        "mutability": "read",
        "handler_name": "_summarize_agent_memory_tree_llm_candidate",
    }


def test_memory_tree_summary_tool_is_registered_with_write_metadata():
    descriptor = get_agent_tool_descriptor("record_agent_memory_tree_summaries")
    metadata = writing_agent_tool_adapter_metadata("record_agent_memory_tree_summaries")

    assert descriptor is not None
    assert descriptor.category == "longform_memory"
    assert descriptor.target_type == "agent_memory_tree_summary"
    assert descriptor.output_schema["properties"]["summary"]["type"] == "object"
    assert metadata == {
        "tool_name": "record_agent_memory_tree_summaries",
        "adapter_type": "static",
        "category": "longform_memory",
        "mutability": "guarded_write",
        "handler_name": "_record_agent_memory_tree_summaries",
        "write_policy": "approval_required_redirect",
    }

    prepare_descriptor = get_agent_tool_descriptor("prepare_record_agent_memory_tree_summaries")
    execute_descriptor = get_agent_tool_descriptor("execute_record_agent_memory_tree_summaries_with_approval")
    prepare_metadata = writing_agent_tool_adapter_metadata("prepare_record_agent_memory_tree_summaries")
    execute_metadata = writing_agent_tool_adapter_metadata("execute_record_agent_memory_tree_summaries_with_approval")

    assert prepare_descriptor is not None
    assert prepare_descriptor.non_blocking_report is True
    assert prepare_descriptor.target_type == "agent_memory_tree_summary_approval"
    assert prepare_descriptor.output_schema["properties"]["agent_plan_approval_contract_hash"]["type"] == "string"
    assert execute_descriptor is not None
    assert execute_descriptor.target_type == "agent_memory_tree_summary"
    assert execute_descriptor.input_schema["properties"]["confirm_execute"]["type"] == "boolean"
    assert execute_descriptor.output_schema["properties"]["post_materialization_quality"]["type"] == "object"
    assert prepare_metadata["mutability"] == "read"
    assert prepare_metadata["handler_name"] == "_prepare_record_agent_memory_tree_summaries"
    assert execute_metadata["mutability"] == "write"
    assert execute_metadata["handler_name"] == "_execute_record_agent_memory_tree_summaries_with_approval"


class _FakeMemoryTreeAIService:
    def __init__(self, content: str):
        self.content = content
        self.calls = []
        self.closed = False

    async def complete(self, messages, **kwargs):
        self.calls.append({"messages": messages, "kwargs": kwargs})
        return SimpleNamespace(
            content=self.content,
            prompt_tokens=11,
            completion_tokens=7,
            model=kwargs.get("model") or "deepseek-chat",
        )

    async def close(self):
        self.closed = True


def _seed_memory_tree_project(db_session):
    project = Project(name="Memory Tree Projection")
    db_session.add(project)
    db_session.flush()
    chapter_1 = ChapterContent(
        project_id=project.id,
        chapter_index=1,
        title="第一章 雨巷来信",
        content="林深在雨巷收到空白信。",
        word_count=18,
        status="completed",
    )
    chapter_2 = ChapterContent(
        project_id=project.id,
        chapter_index=2,
        title="第二章 灯塔回声",
        content="顾衍追查灯塔里的旧回声。",
        word_count=18,
        status="completed",
    )
    outline = Outline(
        project_id=project.id,
        total_chapters=2,
        chapters=[
            {"chapter_index": 1, "title": "雨巷来信", "summary": "收到空白信。"},
            {"chapter_index": 2, "title": "灯塔回声", "summary": "追查旧回声。"},
        ],
        status="completed",
    )
    storyline = Storyline(
        project_id=project.id,
        plotlines=[{"title": "空白信主线", "chapters": [1, 2]}],
        foreshadowing=[{"title": "空白信来源", "introduced_chapter": 1, "status": "open"}],
        status="completed",
    )
    db_session.add_all([chapter_1, chapter_2, outline, storyline])
    db_session.flush()
    scene_memory = LongformMemory(
        project_id=project.id,
        memory_type="scene",
        scope_key="scene:1:rain-alley",
        start_chapter_index=1,
        end_chapter_index=1,
        title="雨巷收到空白信",
        summary="林深在雨巷收到没有署名的空白信。",
        status="current",
    )
    beat_memory = LongformMemory(
        project_id=project.id,
        memory_type="beat",
        scope_key="beat:1:blank-letter",
        start_chapter_index=1,
        end_chapter_index=1,
        title="空白信触发调查",
        summary="空白信成为后续调查的触发点。",
        status="current",
        memory_metadata={"scene_scope_key": "scene:1:rain-alley"},
    )
    db_session.add_all([scene_memory, beat_memory])
    db_session.commit()
    return project, {
        "chapter_1_id": chapter_1.id,
        "outline_id": outline.id,
        "scene_memory_id": scene_memory.id,
        "beat_memory_id": beat_memory.id,
    }
