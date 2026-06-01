import pytest

from app.models import ChapterContent, LongformMemory, Outline, Project, Storyline
from app.schemas.writing_agent import WritingAgentToolRequest
from app.services.writing_agent.memory_tree import (
    MEMORY_TREE_CHAPTER_SUMMARY_TYPE,
    MEMORY_TREE_VERSION,
    MEMORY_TREE_VOLUME_SUMMARY_TYPE,
    inspect_agent_memory_tree,
    materialize_agent_memory_tree_summaries,
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


@pytest.mark.asyncio
async def test_record_agent_memory_tree_summaries_tool_persists_summary_nodes(db_session):
    project, _refs = _seed_memory_tree_project(db_session)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-memory-tree-materialize"),
        WritingAgentToolRequest(tool_name="record_agent_memory_tree_summaries", params={}),
    )

    assert result.handled is True
    assert result.output["status"] == "completed"
    assert result.output["summary"]["volume_summary_nodes"] == 1
    assert result.output["summary"]["chapter_summary_nodes"] == 2
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
        "chapter_index": 1,
        "query": "雨巷",
    }


def test_memory_tree_tool_is_registered_with_read_metadata():
    descriptor = get_agent_tool_descriptor("inspect_agent_memory_tree")
    metadata = writing_agent_tool_adapter_metadata("inspect_agent_memory_tree")

    assert descriptor is not None
    assert descriptor.category == "longform_memory"
    assert descriptor.target_type == "agent_memory_tree"
    assert metadata == {
        "tool_name": "inspect_agent_memory_tree",
        "adapter_type": "static",
        "category": "longform_memory",
        "mutability": "read",
        "handler_name": "_inspect_agent_memory_tree",
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
        "mutability": "write",
        "handler_name": "_record_agent_memory_tree_summaries",
    }


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
