from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import ChapterContent, LongformMemory, Outline, Storyline

MEMORY_TREE_VERSION = "phase238.memory_tree_browsing.v1"
MEMORY_TREE_SUMMARY_MATERIALIZATION_VERSION = "phase237.memory_tree_summary_materialization.v1"
MEMORY_TREE_LEVELS = ["volume", "chapter", "scene", "beat"]
MEMORY_TREE_VOLUME_SUMMARY_TYPE = "memory_tree_volume_summary"
MEMORY_TREE_CHAPTER_SUMMARY_TYPE = "memory_tree_chapter_summary"
MEMORY_TREE_SUMMARY_TYPES = (MEMORY_TREE_VOLUME_SUMMARY_TYPE, MEMORY_TREE_CHAPTER_SUMMARY_TYPE)
MIN_SEMANTIC_RELEVANCE_SCORE = 0.5


def inspect_agent_memory_tree(
    db: Session,
    project_id: str,
    *,
    level: str | None = None,
    node_id: str | None = None,
    expand_node_id: str | None = None,
    chapter_index: int | None = None,
    query: str | None = None,
    include_ancestors: bool = False,
    max_depth: int | None = None,
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
    nodes, navigation = _select_nodes(
        all_nodes,
        level=level,
        node_id=node_id,
        expand_node_id=expand_node_id,
        chapter_index=chapter_index,
        query=query,
        include_ancestors=include_ancestors,
        max_depth=max_depth,
    )
    return {
        "version": MEMORY_TREE_VERSION,
        "status": "ready",
        "project_id": project_id,
        "levels": list(MEMORY_TREE_LEVELS),
        "filters": {
            "level": level,
            "node_id": node_id,
            "expand_node_id": expand_node_id,
            "chapter_index": chapter_index,
            "query": query,
            "include_ancestors": include_ancestors,
            "max_depth": max_depth,
        },
        "navigation": navigation,
        "summary": _summary(all_nodes),
        "roots": [node["id"] for node in all_nodes if node["level"] == "volume"],
        "nodes": nodes,
        "trace": {
            "source_tables": ["chapter_contents", "outlines", "storylines", "longform_memories"],
            "projection": "in_memory",
        },
    }


def _select_nodes(
    nodes: list[dict[str, Any]],
    *,
    level: str | None,
    node_id: str | None,
    expand_node_id: str | None,
    chapter_index: int | None,
    query: str | None,
    include_ancestors: bool,
    max_depth: int | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    nodes_by_id = {node["id"]: node for node in nodes}
    normalised_max_depth = _normalise_max_depth(max_depth)
    ancestor_node_ids: list[str] = []
    descendant_node_ids: list[str] = []
    relevance_by_id: dict[str, dict[str, Any]] = {}
    recommended_drilldowns: list[dict[str, Any]] = []
    semantic_search = False

    if expand_node_id:
        matched_node_ids = [expand_node_id] if expand_node_id in nodes_by_id else []
        descendant_node_ids = _descendant_node_ids(
            nodes_by_id,
            expand_node_id,
            max_depth=normalised_max_depth,
        )
        selected_node_ids = set(matched_node_ids) | set(descendant_node_ids)
        if include_ancestors:
            ancestor_node_ids = _ancestor_node_ids(nodes_by_id, matched_node_ids)
            selected_node_ids.update(ancestor_node_ids)
        mode = "expanded_subtree"
    else:
        matched_nodes, relevance_by_id, semantic_search = _filter_nodes(
            nodes,
            level=level,
            node_id=node_id,
            chapter_index=chapter_index,
            query=query,
        )
        matched_node_ids = [node["id"] for node in matched_nodes]
        selected_node_ids = set(matched_node_ids)
        if include_ancestors:
            ancestor_node_ids = _ancestor_node_ids(nodes_by_id, matched_node_ids)
            selected_node_ids.update(ancestor_node_ids)
        mode = _navigation_mode(query=query, include_ancestors=include_ancestors, semantic_search=semantic_search)
        recommended_drilldowns = _recommended_drilldowns(matched_nodes, relevance_by_id)

    return [_navigation_node(node, relevance_by_id) for node in nodes if node["id"] in selected_node_ids], {
        "mode": mode,
        "matched_node_ids": matched_node_ids,
        "expanded_node_id": expand_node_id,
        "include_ancestors": include_ancestors,
        "max_depth": normalised_max_depth,
        "ancestor_node_ids": ancestor_node_ids,
        "descendant_node_ids": descendant_node_ids,
        "recommended_drilldowns": recommended_drilldowns,
    }


def materialize_agent_memory_tree_summaries(
    db: Session,
    project_id: str,
    *,
    chapter_index: int | None = None,
) -> dict[str, Any]:
    chapters = _chapters(db, project_id)
    if chapter_index is not None:
        chapters = [chapter for chapter in chapters if int(chapter.chapter_index) == int(chapter_index)]
    outline = _outline(db, project_id)
    storyline = _storyline(db, project_id)
    outline_by_chapter = _outline_by_chapter(outline)
    created = 0
    updated = 0
    volume_records: list[LongformMemory] = []
    chapter_records: list[LongformMemory] = []

    chapters_by_volume: dict[int, list[ChapterContent]] = {}
    for chapter in chapters:
        chapters_by_volume.setdefault(_volume_index(chapter.chapter_index), []).append(chapter)

    for volume_index, volume_chapters in sorted(chapters_by_volume.items()):
        record, was_created = _upsert_summary_memory(
            db,
            project_id=project_id,
            memory_type=MEMORY_TREE_VOLUME_SUMMARY_TYPE,
            scope_key=f"volume:{volume_index}",
            start_chapter_index=min(int(chapter.chapter_index) for chapter in volume_chapters),
            end_chapter_index=max(int(chapter.chapter_index) for chapter in volume_chapters),
            title=f"Volume {volume_index}",
            summary=_volume_summary(volume_index, chapters=volume_chapters, outline=outline, storyline=storyline),
            metadata={"level": "volume", "volume_index": volume_index},
        )
        volume_records.append(record)
        if was_created:
            created += 1
        else:
            updated += 1

    for chapter in chapters:
        chapter_index_value = int(chapter.chapter_index)
        record, was_created = _upsert_summary_memory(
            db,
            project_id=project_id,
            memory_type=MEMORY_TREE_CHAPTER_SUMMARY_TYPE,
            scope_key=f"chapter:{chapter_index_value}",
            start_chapter_index=chapter_index_value,
            end_chapter_index=chapter_index_value,
            title=chapter.title or f"Chapter {chapter_index_value}",
            summary=_chapter_summary(chapter, outline_by_chapter.get(chapter_index_value)),
            metadata={"level": "chapter", "chapter_index": chapter_index_value},
        )
        chapter_records.append(record)
        if was_created:
            created += 1
        else:
            updated += 1

    db.commit()
    return {
        "version": MEMORY_TREE_SUMMARY_MATERIALIZATION_VERSION,
        "status": "completed",
        "project_id": project_id,
        "summary": {
            "volume_summary_nodes": len(volume_records),
            "chapter_summary_nodes": len(chapter_records),
            "created_nodes": created,
            "updated_nodes": updated,
        },
        "nodes": [
            _summary_record_projection(record)
            for record in sorted(
                [*volume_records, *chapter_records],
                key=lambda item: (item.start_chapter_index or 0, item.memory_type, item.scope_key),
            )
        ],
        "trace": {
            "source": "materialize_agent_memory_tree_summaries",
            "storage": "longform_memories",
            "memory_types": list(MEMORY_TREE_SUMMARY_TYPES),
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
    summary_by_scope = _summary_memories_by_scope(memories)

    for volume_index in sorted({_volume_index(chapter.chapter_index) for chapter in chapters} or {1}):
        volume_node = _volume_node(
            volume_index,
            outline=outline,
            storyline=storyline,
            summary_memory=summary_by_scope.get((MEMORY_TREE_VOLUME_SUMMARY_TYPE, f"volume:{volume_index}")),
        )
        nodes.append(volume_node)
        nodes_by_id[volume_node["id"]] = volume_node

    for chapter in chapters:
        volume_id = f"volume:{_volume_index(chapter.chapter_index)}"
        chapter_index = int(chapter.chapter_index)
        chapter_node = _chapter_node(
            chapter,
            outline=outline,
            outline_item=outline_by_chapter.get(chapter_index),
            summary_memory=summary_by_scope.get((MEMORY_TREE_CHAPTER_SUMMARY_TYPE, f"chapter:{chapter_index}")),
        )
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


def _volume_node(
    volume_index: int,
    *,
    outline: Outline | None,
    storyline: Storyline | None,
    summary_memory: LongformMemory | None,
) -> dict[str, Any]:
    source_refs: list[dict[str, str]] = []
    if outline is not None:
        source_refs.append({"source_type": "outline", "source_id": outline.id})
    if storyline is not None:
        source_refs.append({"source_type": "storyline", "source_id": storyline.id})
    if summary_memory is not None:
        source_refs.append({"source_type": "longform_memory", "source_id": summary_memory.id})
    return {
        "id": f"volume:{volume_index}",
        "level": "volume",
        "parent_id": None,
        "chapter_index": None,
        "title": f"Volume {volume_index}",
        "summary": summary_memory.summary if summary_memory is not None else "",
        "source_refs": source_refs,
        "children": [],
    }


def _chapter_node(
    chapter: ChapterContent,
    *,
    outline: Outline | None,
    outline_item: dict[str, Any] | None,
    summary_memory: LongformMemory | None,
) -> dict[str, Any]:
    chapter_index = int(chapter.chapter_index)
    source_refs = [{"source_type": "chapter_content", "source_id": chapter.id}]
    if outline is not None and outline_item is not None:
        source_refs.append({"source_type": "outline", "source_id": outline.id})
    if summary_memory is not None:
        source_refs.append({"source_type": "longform_memory", "source_id": summary_memory.id})
    return {
        "id": f"chapter:{chapter_index}",
        "level": "chapter",
        "parent_id": f"volume:{_volume_index(chapter_index)}",
        "chapter_index": chapter_index,
        "title": chapter.title or str((outline_item or {}).get("title") or f"Chapter {chapter_index}"),
        "summary": (
            summary_memory.summary
            if summary_memory is not None
            else str((outline_item or {}).get("summary") or "")
        ),
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
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], bool]:
    query_text = str(query or "").strip().lower()
    filtered = _candidate_nodes(nodes, level=level, node_id=node_id, chapter_index=chapter_index)
    if not query_text:
        return filtered, {}, False
    exact_matches = [node for node in filtered if _exact_query_match(node, query_text)]
    if exact_matches:
        return exact_matches, {}, False
    semantic_matches = _semantic_node_matches(
        filtered,
        query_text,
        all_nodes=nodes,
        rollup_descendants=bool(level or node_id or chapter_index is not None),
    )
    return [item["node"] for item in semantic_matches], {
        str(item["node"]["id"]): item["relevance"] for item in semantic_matches
    }, bool(semantic_matches)


def _candidate_nodes(
    nodes: list[dict[str, Any]],
    *,
    level: str | None,
    node_id: str | None,
    chapter_index: int | None,
) -> list[dict[str, Any]]:
    filtered = nodes
    if level:
        filtered = [node for node in filtered if node["level"] == level]
    if node_id:
        filtered = [node for node in filtered if node["id"] == node_id]
    if chapter_index is not None:
        filtered = [node for node in filtered if node["chapter_index"] == chapter_index]
    return filtered


def _exact_query_match(node: dict[str, Any], query_text: str) -> bool:
    return query_text in str(node.get("title") or "").lower() or query_text in str(node.get("summary") or "").lower()


def _semantic_node_matches(
    nodes: list[dict[str, Any]],
    query_text: str,
    *,
    all_nodes: list[dict[str, Any]],
    rollup_descendants: bool,
) -> list[dict[str, Any]]:
    query_terms = _query_terms(query_text)
    if not query_terms:
        return []
    nodes_by_id = {str(node.get("id") or ""): node for node in all_nodes}
    matches: list[dict[str, Any]] = []
    for node in nodes:
        relevance = _node_relevance(node, query_terms=query_terms, query_text=query_text)
        descendant_relevance = (
            _descendant_relevance(
                node,
                nodes_by_id=nodes_by_id,
                query_terms=query_terms,
                query_text=query_text,
            )
            if rollup_descendants
            else _empty_relevance(query_text)
        )
        relevance = _merge_relevance(relevance, descendant_relevance, query_text=query_text)
        if float(relevance["score"]) < MIN_SEMANTIC_RELEVANCE_SCORE:
            continue
        matches.append({"node": node, "relevance": relevance})
    return sorted(
        matches,
        key=lambda item: (
            -float(item["relevance"]["score"]),
            _level_rank(str(item["node"].get("level") or "")),
            str(item["node"].get("id") or ""),
        ),
    )


def _node_relevance(
    node: dict[str, Any],
    *,
    query_terms: list[str],
    query_text: str,
) -> dict[str, Any]:
    field_values = {
        "title": str(node.get("title") or "").lower(),
        "summary": str(node.get("summary") or "").lower(),
        "scope_key": str(node.get("scope_key") or "").lower(),
    }
    matched_terms: list[str] = []
    matched_fields: list[str] = []
    for field_name, value in field_values.items():
        field_matched = [term for term in query_terms if term and term in value]
        if not field_matched:
            continue
        matched_fields.append(field_name)
        for term in field_matched:
            if term not in matched_terms:
                matched_terms.append(term)
    if not matched_terms:
        return {
            "score": 0,
            "query": query_text,
            "matched_terms": [],
            "matched_fields": [],
            "match_reasons": [],
        }
    field_bonus = 0.1 * len(matched_fields)
    title_bonus = 0.1 if "title" in matched_fields else 0
    score = round((len(matched_terms) / len(query_terms)) + field_bonus + title_bonus, 4)
    return {
        "score": score,
        "query": query_text,
        "matched_terms": matched_terms,
        "matched_fields": matched_fields,
        "match_reasons": ["semantic_token_overlap"],
    }


def _descendant_relevance(
    node: dict[str, Any],
    *,
    nodes_by_id: dict[str, dict[str, Any]],
    query_terms: list[str],
    query_text: str,
) -> dict[str, Any]:
    node_id = str(node.get("id") or "")
    descendant_matches: list[dict[str, Any]] = []
    for descendant_id in _descendant_node_ids(nodes_by_id, node_id, max_depth=None):
        descendant = nodes_by_id.get(descendant_id)
        if descendant is None:
            continue
        relevance = _node_relevance(descendant, query_terms=query_terms, query_text=query_text)
        if float(relevance["score"]) < MIN_SEMANTIC_RELEVANCE_SCORE:
            continue
        descendant_matches.append({"node_id": descendant_id, "relevance": relevance})
    if not descendant_matches:
        return _empty_relevance(query_text)
    descendant_matches = sorted(
        descendant_matches,
        key=lambda item: (
            -float(item["relevance"]["score"]),
            str(item["node_id"]),
        ),
    )
    matched_terms: list[str] = []
    matched_fields: list[str] = []
    matched_descendant_ids: list[str] = []
    for match in descendant_matches:
        relevance = match["relevance"]
        matched_descendant_ids.append(str(match["node_id"]))
        for term in relevance.get("matched_terms") or []:
            if term not in matched_terms:
                matched_terms.append(str(term))
        for field in relevance.get("matched_fields") or []:
            descendant_field = f"descendant.{field}"
            if descendant_field not in matched_fields:
                matched_fields.append(descendant_field)
    top_score = float(descendant_matches[0]["relevance"]["score"])
    return {
        "score": round(top_score * 0.95, 4),
        "query": query_text,
        "matched_terms": matched_terms,
        "matched_fields": matched_fields,
        "match_reasons": ["descendant_semantic_match"],
        "matched_descendant_ids": matched_descendant_ids,
    }


def _merge_relevance(
    direct: dict[str, Any],
    descendant: dict[str, Any],
    *,
    query_text: str,
) -> dict[str, Any]:
    if float(direct.get("score") or 0) <= 0 and float(descendant.get("score") or 0) <= 0:
        return _empty_relevance(query_text)
    if float(descendant.get("score") or 0) > float(direct.get("score") or 0):
        base = dict(descendant)
    else:
        base = dict(direct)
    return {
        "score": base.get("score") or 0,
        "query": query_text,
        "matched_terms": _dedupe([str(term) for term in base.get("matched_terms") or []]),
        "matched_fields": _dedupe([str(field) for field in base.get("matched_fields") or []]),
        "match_reasons": _dedupe([str(reason) for reason in base.get("match_reasons") or []]),
        **(
            {"matched_descendant_ids": _dedupe([str(node_id) for node_id in base.get("matched_descendant_ids") or []])}
            if base.get("matched_descendant_ids")
            else {}
        ),
    }


def _empty_relevance(query_text: str) -> dict[str, Any]:
    return {
        "score": 0,
        "query": query_text,
        "matched_terms": [],
        "matched_fields": [],
        "match_reasons": [],
    }


def _query_terms(query_text: str) -> list[str]:
    terms: list[str] = []
    word = ""
    for char in query_text:
        if _is_cjk(char):
            if word:
                terms.append(word)
                word = ""
            terms.append(char)
        elif char.isalnum():
            word += char
        elif word:
            terms.append(word)
            word = ""
    if word:
        terms.append(word)
    return _dedupe([term.lower() for term in terms if term.strip()])


def _is_cjk(char: str) -> bool:
    return "\u4e00" <= char <= "\u9fff"


def _navigation_mode(*, query: str | None, include_ancestors: bool, semantic_search: bool) -> str:
    if not query:
        return "filtered"
    if semantic_search and include_ancestors:
        return "semantic_search_with_ancestors"
    if semantic_search:
        return "semantic_search"
    return "search_with_ancestors" if include_ancestors else "filtered"


def _navigation_node(node: dict[str, Any], relevance_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    relevance = relevance_by_id.get(str(node.get("id") or ""))
    if not relevance:
        return node
    output = dict(node)
    output["relevance"] = relevance
    return output


def _recommended_drilldowns(
    matched_nodes: list[dict[str, Any]],
    relevance_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    if not relevance_by_id or not matched_nodes:
        return []
    top_node = matched_nodes[0]
    relevance = relevance_by_id.get(str(top_node.get("id") or ""))
    if not relevance:
        return []
    if relevance.get("matched_descendant_ids"):
        return [
            {
                "node_id": top_node["id"],
                "expand_node_id": top_node["id"],
                "reason": "descendant_relevance",
                "score": relevance["score"],
                "matched_descendant_ids": [str(node_id) for node_id in relevance.get("matched_descendant_ids") or []],
            }
        ]
    return [
        {
            "node_id": top_node["id"],
            "expand_node_id": top_node["id"],
            "reason": "highest_relevance",
            "score": relevance["score"],
        }
    ]


def _level_rank(level: str) -> int:
    try:
        return MEMORY_TREE_LEVELS.index(level)
    except ValueError:
        return len(MEMORY_TREE_LEVELS)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _ancestor_node_ids(nodes_by_id: dict[str, dict[str, Any]], node_ids: list[str]) -> list[str]:
    ancestor_ids: list[str] = []
    seen: set[str] = set()
    for node_id in node_ids:
        node = nodes_by_id.get(node_id)
        if node is None:
            continue
        path: list[str] = []
        parent_id = node.get("parent_id")
        while parent_id and parent_id in nodes_by_id:
            path.append(parent_id)
            parent_id = nodes_by_id[parent_id].get("parent_id")
        for ancestor_id in reversed(path):
            if ancestor_id not in seen:
                ancestor_ids.append(ancestor_id)
                seen.add(ancestor_id)
    return ancestor_ids


def _descendant_node_ids(
    nodes_by_id: dict[str, dict[str, Any]],
    node_id: str,
    *,
    max_depth: int | None,
) -> list[str]:
    if node_id not in nodes_by_id:
        return []
    descendant_ids: list[str] = []
    queue = [(child_id, 1) for child_id in nodes_by_id[node_id].get("children", [])]
    while queue:
        current_id, depth = queue.pop(0)
        if current_id not in nodes_by_id:
            continue
        if max_depth is not None and depth > max_depth:
            continue
        descendant_ids.append(current_id)
        if max_depth is None or depth < max_depth:
            queue.extend((child_id, depth + 1) for child_id in nodes_by_id[current_id].get("children", []))
    return descendant_ids


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
        .filter(LongformMemory.memory_type.in_(("scene", "beat", *MEMORY_TREE_SUMMARY_TYPES)))
        .order_by(
            LongformMemory.start_chapter_index.asc(),
            LongformMemory.memory_type.desc(),
            LongformMemory.scope_key.asc(),
        )
        .all()
    )


def _summary_memories_by_scope(memories: list[LongformMemory]) -> dict[tuple[str, str], LongformMemory]:
    return {
        (memory.memory_type, memory.scope_key): memory
        for memory in memories
        if memory.memory_type in MEMORY_TREE_SUMMARY_TYPES
    }


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


def _normalise_max_depth(value: int | None) -> int | None:
    if value is None:
        return None
    return max(0, int(value))


def _volume_summary(
    volume_index: int,
    *,
    chapters: list[ChapterContent],
    outline: Outline | None,
    storyline: Storyline | None,
) -> str:
    chapter_indexes = [int(chapter.chapter_index) for chapter in chapters]
    parts = [f"Volume {volume_index} covers chapters {min(chapter_indexes)}-{max(chapter_indexes)}."]
    plotlines = storyline.plotlines if storyline is not None and isinstance(storyline.plotlines, list) else []
    plot_titles = [
        str(item.get("title") or item.get("name") or "").strip()
        for item in plotlines
        if isinstance(item, dict)
    ]
    plot_titles = [title for title in plot_titles if title]
    if plot_titles:
        parts.append("Main plotlines: " + "; ".join(plot_titles[:3]) + ".")
    outline_items = _outline_by_chapter(outline)
    chapter_summaries = [
        str((outline_items.get(index) or {}).get("summary") or "").strip()
        for index in chapter_indexes
    ]
    chapter_summaries = [summary for summary in chapter_summaries if summary]
    if chapter_summaries:
        parts.append("Chapter summaries: " + "; ".join(chapter_summaries[:5]) + ".")
    return " ".join(parts)


def _chapter_summary(chapter: ChapterContent, outline_item: dict[str, Any] | None) -> str:
    outline_summary = str((outline_item or {}).get("summary") or "").strip()
    title = chapter.title or str((outline_item or {}).get("title") or f"Chapter {chapter.chapter_index}")
    content = str(chapter.content or "").strip().replace("\n", " ")
    content_preview = content[:160]
    if outline_summary and content_preview:
        return f"{title}: {outline_summary} Content points: {content_preview}"
    if outline_summary:
        return f"{title}: {outline_summary}"
    return f"{title}: {content_preview}" if content_preview else str(title)


def _upsert_summary_memory(
    db: Session,
    *,
    project_id: str,
    memory_type: str,
    scope_key: str,
    start_chapter_index: int,
    end_chapter_index: int,
    title: str,
    summary: str,
    metadata: dict[str, Any],
) -> tuple[LongformMemory, bool]:
    record = (
        db.query(LongformMemory)
        .filter(
            LongformMemory.project_id == project_id,
            LongformMemory.memory_type == memory_type,
            LongformMemory.scope_key == scope_key,
        )
        .first()
    )
    created = record is None
    if record is None:
        record = LongformMemory(project_id=project_id, memory_type=memory_type, scope_key=scope_key)
        db.add(record)
    record.start_chapter_index = start_chapter_index
    record.end_chapter_index = end_chapter_index
    record.title = title
    record.summary = summary
    record.status = "current"
    record.memory_metadata = metadata
    db.flush()
    return record, created


def _summary_record_projection(record: LongformMemory) -> dict[str, Any]:
    return {
        "id": record.id,
        "memory_type": record.memory_type,
        "scope_key": record.scope_key,
        "start_chapter_index": record.start_chapter_index,
        "end_chapter_index": record.end_chapter_index,
        "title": record.title,
        "summary": record.summary,
    }
