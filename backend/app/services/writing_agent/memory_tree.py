from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import ChapterContent, LongformMemory, Outline, Storyline

MEMORY_TREE_VERSION = "phase231.memory_tree.v1"
MEMORY_TREE_LEVELS = ["volume", "chapter", "scene", "beat"]


def inspect_agent_memory_tree(
    db: Session,
    project_id: str,
    *,
    level: str | None = None,
    node_id: str | None = None,
    chapter_index: int | None = None,
    query: str | None = None,
) -> dict[str, Any]:
    chapters = _chapters(db, project_id)
    outline = _outline(db, project_id)
    storyline = _storyline(db, project_id)
    memories = _memories(db, project_id)
    all_nodes = _build_nodes(
        chapters=chapters,
        outline=outline,
        storyline=storyline,
        memories=memories,
    )
    nodes = _filter_nodes(
        all_nodes,
        level=level,
        node_id=node_id,
        chapter_index=chapter_index,
        query=query,
    )
    return {
        "version": MEMORY_TREE_VERSION,
        "status": "ready",
        "project_id": project_id,
        "levels": list(MEMORY_TREE_LEVELS),
        "filters": {
            "level": level,
            "node_id": node_id,
            "chapter_index": chapter_index,
            "query": query,
        },
        "summary": _summary(all_nodes),
        "roots": [node["id"] for node in all_nodes if node["level"] == "volume"],
        "nodes": nodes,
        "trace": {
            "source_tables": ["chapter_contents", "outlines", "storylines", "longform_memories"],
            "projection": "in_memory",
        },
    }


def _build_nodes(
    *,
    chapters: list[ChapterContent],
    outline: Outline | None,
    storyline: Storyline | None,
    memories: list[LongformMemory],
) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    nodes_by_id: dict[str, dict[str, Any]] = {}
    outline_by_chapter = _outline_by_chapter(outline)
    chapter_by_index = {int(chapter.chapter_index): chapter for chapter in chapters}

    for volume_index in sorted({_volume_index(chapter.chapter_index) for chapter in chapters} or {1}):
        volume_node = _volume_node(volume_index, outline=outline, storyline=storyline)
        nodes.append(volume_node)
        nodes_by_id[volume_node["id"]] = volume_node

    for chapter in chapters:
        volume_id = f"volume:{_volume_index(chapter.chapter_index)}"
        chapter_node = _chapter_node(chapter, outline=outline, outline_item=outline_by_chapter.get(chapter.chapter_index))
        nodes.append(chapter_node)
        nodes_by_id[chapter_node["id"]] = chapter_node
        _append_child(nodes_by_id, volume_id, chapter_node["id"])

    scene_memories = [memory for memory in memories if memory.memory_type == "scene"]
    beat_memories = [memory for memory in memories if memory.memory_type == "beat"]
    scenes_by_scope = {memory.scope_key: memory for memory in scene_memories}

    for memory in scene_memories:
        scene_node = _memory_node("scene", memory, chapter_by_index)
        nodes.append(scene_node)
        nodes_by_id[scene_node["id"]] = scene_node
        _append_child(nodes_by_id, scene_node["parent_id"], scene_node["id"])

    for memory in beat_memories:
        beat_node = _memory_node("beat", memory, chapter_by_index, scenes_by_scope=scenes_by_scope)
        nodes.append(beat_node)
        nodes_by_id[beat_node["id"]] = beat_node
        _append_child(nodes_by_id, beat_node["parent_id"], beat_node["id"])

    return nodes


def _volume_node(volume_index: int, *, outline: Outline | None, storyline: Storyline | None) -> dict[str, Any]:
    source_refs: list[dict[str, str]] = []
    if outline is not None:
        source_refs.append({"source_type": "outline", "source_id": outline.id})
    if storyline is not None:
        source_refs.append({"source_type": "storyline", "source_id": storyline.id})
    return {
        "id": f"volume:{volume_index}",
        "level": "volume",
        "parent_id": None,
        "chapter_index": None,
        "title": f"Volume {volume_index}",
        "summary": "",
        "source_refs": source_refs,
        "children": [],
    }


def _chapter_node(chapter: ChapterContent, *, outline: Outline | None, outline_item: dict[str, Any] | None) -> dict[str, Any]:
    chapter_index = int(chapter.chapter_index)
    source_refs = [{"source_type": "chapter_content", "source_id": chapter.id}]
    if outline is not None and outline_item is not None:
        source_refs.append({"source_type": "outline", "source_id": outline.id})
    return {
        "id": f"chapter:{chapter_index}",
        "level": "chapter",
        "parent_id": f"volume:{_volume_index(chapter_index)}",
        "chapter_index": chapter_index,
        "title": chapter.title or str((outline_item or {}).get("title") or f"Chapter {chapter_index}"),
        "summary": str((outline_item or {}).get("summary") or ""),
        "source_refs": source_refs,
        "children": [],
    }


def _memory_node(
    level: str,
    memory: LongformMemory,
    chapter_by_index: dict[int, ChapterContent],
    *,
    scenes_by_scope: dict[str, LongformMemory] | None = None,
) -> dict[str, Any]:
    chapter_index = _memory_chapter_index(memory)
    parent_id = f"chapter:{chapter_index}" if chapter_index is not None else "volume:1"
    if level == "beat" and scenes_by_scope:
        scene_scope = _metadata_value(memory, "scene_scope_key")
        scene_memory = scenes_by_scope.get(scene_scope)
        if scene_memory is not None:
            parent_id = f"scene:{scene_memory.id}"
    source_refs = [{"source_type": "longform_memory", "source_id": memory.id}]
    chapter = chapter_by_index.get(chapter_index) if chapter_index is not None else None
    if chapter is not None:
        source_refs.append({"source_type": "chapter_content", "source_id": chapter.id})
    return {
        "id": f"{level}:{memory.id}",
        "level": level,
        "parent_id": parent_id,
        "chapter_index": chapter_index,
        "title": memory.title or memory.scope_key,
        "summary": memory.summary or "",
        "scope_key": memory.scope_key,
        "source_refs": source_refs,
        "children": [],
    }


def _filter_nodes(
    nodes: list[dict[str, Any]],
    *,
    level: str | None,
    node_id: str | None,
    chapter_index: int | None,
    query: str | None,
) -> list[dict[str, Any]]:
    query_text = str(query or "").strip().lower()
    filtered = nodes
    if level:
        filtered = [node for node in filtered if node["level"] == level]
    if node_id:
        filtered = [node for node in filtered if node["id"] == node_id]
    if chapter_index is not None:
        filtered = [node for node in filtered if node["chapter_index"] == chapter_index]
    if query_text:
        filtered = [
            node
            for node in filtered
            if query_text in str(node.get("title") or "").lower()
            or query_text in str(node.get("summary") or "").lower()
        ]
    return filtered


def _summary(nodes: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "volume_nodes": sum(1 for node in nodes if node["level"] == "volume"),
        "chapter_nodes": sum(1 for node in nodes if node["level"] == "chapter"),
        "scene_nodes": sum(1 for node in nodes if node["level"] == "scene"),
        "beat_nodes": sum(1 for node in nodes if node["level"] == "beat"),
    }


def _outline_by_chapter(outline: Outline | None) -> dict[int, dict[str, Any]]:
    if outline is None or not isinstance(outline.chapters, list):
        return {}
    items: dict[int, dict[str, Any]] = {}
    for item in outline.chapters:
        if not isinstance(item, dict):
            continue
        chapter_index = _optional_int(item.get("chapter_index") or item.get("index"))
        if chapter_index is not None:
            items[chapter_index] = item
    return items


def _chapters(db: Session, project_id: str) -> list[ChapterContent]:
    return (
        db.query(ChapterContent)
        .filter(ChapterContent.project_id == project_id)
        .order_by(ChapterContent.chapter_index.asc(), ChapterContent.id.asc())
        .all()
    )


def _outline(db: Session, project_id: str) -> Outline | None:
    return db.query(Outline).filter(Outline.project_id == project_id).order_by(Outline.created_at.desc()).first()


def _storyline(db: Session, project_id: str) -> Storyline | None:
    return db.query(Storyline).filter(Storyline.project_id == project_id).order_by(Storyline.created_at.desc()).first()


def _memories(db: Session, project_id: str) -> list[LongformMemory]:
    return (
        db.query(LongformMemory)
        .filter(LongformMemory.project_id == project_id)
        .filter(LongformMemory.memory_type.in_(("scene", "beat")))
        .order_by(
            LongformMemory.start_chapter_index.asc(),
            LongformMemory.memory_type.desc(),
            LongformMemory.scope_key.asc(),
        )
        .all()
    )


def _memory_chapter_index(memory: LongformMemory) -> int | None:
    return memory.start_chapter_index or memory.end_chapter_index


def _volume_index(chapter_index: int) -> int:
    return ((int(chapter_index) - 1) // 100) + 1


def _append_child(nodes_by_id: dict[str, dict[str, Any]], parent_id: str | None, child_id: str) -> None:
    if parent_id and parent_id in nodes_by_id:
        nodes_by_id[parent_id]["children"].append(child_id)


def _metadata_value(memory: LongformMemory, key: str) -> str:
    metadata = memory.memory_metadata if isinstance(memory.memory_metadata, dict) else {}
    return str(metadata.get(key) or "").strip()


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
