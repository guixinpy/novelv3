from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from app.core.embedding_service import cosine_similarity, get_embedding_provider, tokenize_for_retrieval, vector_hash
from app.models import (
    ChapterContent,
    LongformMemory,
    Outline,
    Project,
    RetrievalChunk,
    RetrievalDocument,
    RetrievalEmbedding,
    RetrievalTerm,
    WorldFactClaim,
)


MAX_CHUNK_CHARS = 900
CHUNK_OVERLAP_CHARS = 120


@dataclass(frozen=True)
class RetrievalSource:
    source_type: str
    source_id: str
    source_ref: str
    title: str
    text: str
    chapter_index: int | None
    profile_version: int | None
    metadata: dict[str, Any]


def reindex_project_retrieval(db: Session, project_id: str) -> dict[str, Any]:
    _require_project(db, project_id)
    _delete_project_index(db, project_id)
    indexed = _index_sources(db, project_id, _project_sources(db, project_id))
    db.commit()
    return {"status": "completed", "project_id": project_id, "chapter_index": None, "indexed": indexed}


def index_chapter_retrieval(db: Session, project_id: str, chapter_index: int) -> dict[str, Any]:
    _require_project(db, project_id)
    chapter = (
        db.query(ChapterContent)
        .filter(ChapterContent.project_id == project_id, ChapterContent.chapter_index == chapter_index)
        .first()
    )
    if chapter is None:
        raise HTTPException(status_code=404, detail="Chapter not found")
    _delete_document(db, project_id=project_id, source_type="chapter", source_id=chapter.id)
    indexed = _index_sources(db, project_id, [_chapter_source(chapter)])
    db.commit()
    return {"status": "completed", "project_id": project_id, "chapter_index": chapter_index, "indexed": indexed}


def get_retrieval_diagnostics(db: Session, project_id: str) -> dict[str, Any]:
    _require_project(db, project_id)
    provider = get_embedding_provider()
    source_rows = (
        db.query(RetrievalDocument.source_type, func.count(RetrievalDocument.id))
        .filter(RetrievalDocument.project_id == project_id)
        .group_by(RetrievalDocument.source_type)
        .all()
    )
    return {
        "project_id": project_id,
        "embedding_provider": provider.provider_name,
        "embedding_model": provider.model_name,
        "vector_dimension": provider.dimensions,
        "total_documents": db.query(RetrievalDocument).filter(RetrievalDocument.project_id == project_id).count(),
        "total_chunks": db.query(RetrievalChunk).filter(RetrievalChunk.project_id == project_id).count(),
        "total_terms": db.query(RetrievalTerm).filter(RetrievalTerm.project_id == project_id).count(),
        "total_embeddings": db.query(RetrievalEmbedding).filter(RetrievalEmbedding.project_id == project_id).count(),
        "documents_by_source_type": {source_type: count for source_type, count in source_rows},
    }


def sync_longform_memory_retrieval_documents(
    db: Session,
    project_id: str,
    memory_ids: list[str],
) -> dict[str, Any]:
    _require_project(db, project_id)
    if not memory_ids:
        return {"status": "completed", "project_id": project_id, "synced_scope_keys": [], "indexed": _empty_indexed()}
    memories = (
        db.query(LongformMemory)
        .filter(LongformMemory.project_id == project_id, LongformMemory.id.in_(memory_ids))
        .order_by(
            LongformMemory.end_chapter_index.asc().nullsfirst(),
            LongformMemory.memory_type.asc(),
            LongformMemory.scope_key.asc(),
        )
        .all()
    )
    for memory in memories:
        _delete_document_by_source_ref(
            db,
            project_id=project_id,
            source_type="longform_memory",
            source_ref=f"memory:{memory.scope_key}",
        )
    indexed = _index_sources(db, project_id, [_longform_memory_source(memory) for memory in memories])
    db.commit()
    return {
        "status": "completed",
        "project_id": project_id,
        "synced_scope_keys": [memory.scope_key for memory in memories],
        "indexed": indexed,
    }


def search_retrieval(
    db: Session,
    project_id: str,
    query: str,
    *,
    limit: int = 8,
    source_type: str | None = None,
    max_chapter_index: int | None = None,
    candidate_limit: int | None = None,
) -> dict[str, Any]:
    _require_project(db, project_id)
    cleaned_query = query.strip()
    if not cleaned_query:
        return {"query": query, "total": 0, "items": []}

    provider = get_embedding_provider()
    query_vector = provider.embed_texts([cleaned_query])[0]
    rows_query = _search_rows_query(
        db,
        project_id,
        source_type=source_type,
        max_chapter_index=max_chapter_index,
    )

    scored = []
    for chunk, document, embedding in _candidate_rows(
        db,
        rows_query,
        project_id=project_id,
        cleaned_query=cleaned_query,
        limit=limit,
        candidate_limit=candidate_limit,
        source_type=source_type,
        max_chapter_index=max_chapter_index,
    ):
        vector_score = max(0.0, cosine_similarity(query_vector, _vector_from_json(embedding.vector)))
        lexical_score = _lexical_score(cleaned_query, chunk.text)
        score = (lexical_score * 0.58) + (vector_score * 0.42)
        if document.source_type == "world_fact":
            score += 0.03
        if score <= 0.02:
            continue
        scored.append(
            {
                "chunk_id": chunk.id,
                "document_id": document.id,
                "source_type": document.source_type,
                "source_ref": document.source_ref,
                "title": document.title,
                "chapter_index": document.chapter_index,
                "score": round(score, 6),
                "lexical_score": round(lexical_score, 6),
                "vector_score": round(vector_score, 6),
                "snippet": _snippet(chunk.text, cleaned_query),
                "metadata": document.document_metadata or {},
            }
        )
    scored.sort(key=lambda item: item["score"], reverse=True)
    items = scored[:limit]
    return {"query": cleaned_query, "total": len(scored), "items": items}


def _search_rows_query(
    db: Session,
    project_id: str,
    *,
    source_type: str | None,
    max_chapter_index: int | None,
):
    rows_query = (
        db.query(RetrievalChunk, RetrievalDocument, RetrievalEmbedding)
        .join(RetrievalDocument, RetrievalChunk.document_id == RetrievalDocument.id)
        .join(RetrievalEmbedding, RetrievalEmbedding.chunk_id == RetrievalChunk.id)
        .filter(RetrievalChunk.project_id == project_id)
    )
    if source_type:
        rows_query = rows_query.filter(RetrievalDocument.source_type == source_type)
    if max_chapter_index is not None:
        rows_query = rows_query.filter(
            (RetrievalDocument.chapter_index.is_(None)) | (RetrievalDocument.chapter_index <= max_chapter_index)
        )
    return rows_query


def _stable_candidate_order(rows_query):
    return rows_query.order_by(
        RetrievalDocument.source_type.asc(),
        RetrievalDocument.chapter_index.asc().nullsfirst(),
        RetrievalChunk.chunk_index.asc(),
        RetrievalChunk.id.asc(),
    )


def _candidate_rows(
    db: Session,
    rows_query,
    *,
    project_id: str,
    cleaned_query: str,
    limit: int,
    candidate_limit: int | None,
    source_type: str | None,
    max_chapter_index: int | None,
) -> list[tuple[Any, Any, Any]]:
    fallback_limit = candidate_limit or max(limit * 80, 400)
    lexical_limit = candidate_limit or max(limit * 160, 800)
    tokens = _candidate_query_tokens(cleaned_query)
    rows: list[tuple[Any, Any, Any]] = []
    seen_chunk_ids: set[str] = set()

    if tokens:
        lexical_rows = _indexed_lexical_candidate_rows(
            db,
            rows_query,
            project_id=project_id,
            tokens=tokens,
            lexical_limit=lexical_limit,
            source_type=source_type,
            max_chapter_index=max_chapter_index,
        )
        if not lexical_rows:
            lexical_rows = _legacy_like_candidate_rows(rows_query, tokens=tokens, lexical_limit=lexical_limit)
        for row in lexical_rows:
            chunk = row[0]
            if chunk.id in seen_chunk_ids:
                continue
            seen_chunk_ids.add(chunk.id)
            rows.append(row)

    for row in _stable_candidate_order(rows_query).limit(fallback_limit).all():
        chunk = row[0]
        if chunk.id in seen_chunk_ids:
            continue
        seen_chunk_ids.add(chunk.id)
        rows.append(row)
    return rows


def _indexed_lexical_candidate_rows(
    db: Session,
    rows_query,
    *,
    project_id: str,
    tokens: list[str],
    lexical_limit: int,
    source_type: str | None,
    max_chapter_index: int | None,
) -> list[tuple[Any, Any, Any]]:
    match_count = func.count(RetrievalTerm.token)
    token_query = (
        db.query(RetrievalTerm.chunk_id, match_count.label("match_count"))
        .join(RetrievalChunk, RetrievalChunk.id == RetrievalTerm.chunk_id)
        .join(RetrievalDocument, RetrievalChunk.document_id == RetrievalDocument.id)
        .filter(
            RetrievalTerm.project_id == project_id,
            RetrievalTerm.token.in_(tokens),
        )
    )
    if source_type:
        token_query = token_query.filter(RetrievalDocument.source_type == source_type)
    if max_chapter_index is not None:
        token_query = token_query.filter(
            (RetrievalDocument.chapter_index.is_(None)) | (RetrievalDocument.chapter_index <= max_chapter_index)
        )
    token_rows = (
        token_query.group_by(RetrievalTerm.chunk_id)
        .order_by(
            match_count.desc(),
            RetrievalDocument.source_type.asc(),
            RetrievalDocument.chapter_index.asc().nullsfirst(),
            RetrievalChunk.chunk_index.asc(),
            RetrievalChunk.id.asc(),
        )
        .limit(lexical_limit)
        .all()
    )
    chunk_ids = [row[0] for row in token_rows]
    if not chunk_ids:
        return []
    rows_by_chunk_id = {row[0].id: row for row in rows_query.filter(RetrievalChunk.id.in_(chunk_ids)).all()}
    return [rows_by_chunk_id[chunk_id] for chunk_id in chunk_ids if chunk_id in rows_by_chunk_id]


def _legacy_like_candidate_rows(rows_query, *, tokens: list[str], lexical_limit: int) -> list[tuple[Any, Any, Any]]:
    match_expr = None
    conditions = []
    for token in tokens:
        condition = RetrievalChunk.text.contains(token, autoescape=True)
        conditions.append(condition)
        token_expr = case((condition, 1), else_=0)
        match_expr = token_expr if match_expr is None else match_expr + token_expr
    return (
        rows_query.filter(or_(*conditions))
        .order_by(
            match_expr.desc(),
            RetrievalDocument.source_type.asc(),
            RetrievalDocument.chapter_index.asc().nullsfirst(),
            RetrievalChunk.chunk_index.asc(),
            RetrievalChunk.id.asc(),
        )
        .limit(lexical_limit)
        .all()
    )


def _candidate_query_tokens(query: str) -> list[str]:
    tokens = {token for token in tokenize_for_retrieval(query) if len(token) >= 2}
    return sorted(tokens, key=lambda token: (-len(token), token))[:12]


def build_chapter_retrieval_context(db: Session, project_id: str, chapter_index: int, *, limit: int = 6) -> dict[str, Any] | None:
    query = _chapter_context_query(db, project_id, chapter_index)
    if not query:
        return None
    results = search_retrieval(
        db,
        project_id,
        query,
        limit=limit,
        max_chapter_index=max(chapter_index - 1, 0),
    )
    items = results["items"]
    if not items:
        return None
    lines = ["【检索证据】"]
    for item in items[:limit]:
        label = "章节" if item["source_type"] == "chapter" else "世界事实"
        chapter_label = f"第{item['chapter_index']}章 " if item.get("chapter_index") else ""
        lines.append(f"- {label} {chapter_label}{item['title']}：{item['snippet']}")
    return {
        "section": {"key": "retrieval", "title": "检索证据", "items": items},
        "prompt_lines": lines,
    }


def build_query_aware_retrieval_context(
    db: Session,
    project_id: str,
    chapter_index: int,
    *,
    user_query: str | None = None,
    limit: int = 6,
) -> dict[str, Any] | None:
    query = _query_aware_context_query(db, project_id, chapter_index, user_query=user_query)
    if not query:
        return None
    max_chapter_index = max(chapter_index - 1, 0)
    result_items = _query_aware_result_items(
        db,
        project_id=project_id,
        query=query,
        user_query=user_query,
        limit=limit,
        max_chapter_index=max_chapter_index,
    )
    if not result_items:
        return None

    items = [
        _with_retrieval_explanation(item, user_query=user_query, max_chapter_index=max_chapter_index)
        for item in result_items[:limit]
    ]
    lines = ["【检索依据】"]
    lines.append(f"- 查询范围：第{max_chapter_index}章及之前的正文、长篇记忆和世界事实。")
    if user_query:
        lines.append(f"- 用户查询：{user_query.strip()}")
    for item in items:
        explanation = item["metadata"]["explanation"]
        lines.append(
            f"- {explanation['source_label']} {explanation['chapter_range']} "
            f"{item['title']}（{explanation['reason']}）：{item['snippet']}"
        )
    return {
        "section": {"key": "query_aware_retrieval", "title": "查询感知检索依据", "items": items},
        "prompt_lines": lines,
        "query": query,
    }


def _query_aware_result_items(
    db: Session,
    *,
    project_id: str,
    query: str,
    user_query: str | None,
    limit: int,
    max_chapter_index: int,
) -> list[dict[str, Any]]:
    seen: set[str] = set()
    items: list[dict[str, Any]] = []
    cleaned_user_query = (user_query or "").strip()
    if cleaned_user_query:
        user_results = search_retrieval(
            db,
            project_id,
            cleaned_user_query,
            limit=limit,
            max_chapter_index=max_chapter_index,
        )
        for item in user_results["items"]:
            seen.add(item["chunk_id"])
            items.append(item)
    context_results = search_retrieval(
        db,
        project_id,
        query,
        limit=limit,
        max_chapter_index=max_chapter_index,
    )
    for item in context_results["items"]:
        if item["chunk_id"] in seen:
            continue
        seen.add(item["chunk_id"])
        items.append(item)
        if len(items) >= limit:
            break
    return items


def _query_aware_context_query(
    db: Session,
    project_id: str,
    chapter_index: int,
    *,
    user_query: str | None,
) -> str:
    parts = [_chapter_context_query(db, project_id, chapter_index)]
    cleaned_user_query = (user_query or "").strip()
    if cleaned_user_query:
        parts.append(cleaned_user_query)
    return "\n".join(part for part in parts if part).strip()


def _with_retrieval_explanation(
    item: dict[str, Any],
    *,
    user_query: str | None,
    max_chapter_index: int,
) -> dict[str, Any]:
    metadata = dict(item.get("metadata") or {})
    source_type = str(item.get("source_type") or "")
    explanation = {
        "source_type": source_type,
        "source_label": _source_type_label(source_type),
        "chapter_range": _source_chapter_range(item),
        "score": item.get("score", 0),
        "reason": _retrieval_reason(item, user_query=user_query, max_chapter_index=max_chapter_index),
    }
    metadata["explanation"] = explanation
    return {**item, "metadata": metadata}


def _source_type_label(source_type: str) -> str:
    return {
        "chapter": "章节正文",
        "longform_memory": "长篇记忆",
        "world_fact": "世界事实",
    }.get(source_type, source_type or "未知来源")


def _source_chapter_range(item: dict[str, Any]) -> str:
    metadata = item.get("metadata") or {}
    if item.get("source_type") == "longform_memory":
        start = metadata.get("start_chapter_index")
        end = metadata.get("end_chapter_index")
        if start and end and start != end:
            return f"第{start}-{end}章"
        if end:
            return f"第{end}章"
    chapter_index = item.get("chapter_index")
    return f"第{chapter_index}章" if chapter_index else "全局"


def _retrieval_reason(item: dict[str, Any], *, user_query: str | None, max_chapter_index: int) -> str:
    score = item.get("score", 0)
    lexical_score = item.get("lexical_score", 0)
    vector_score = item.get("vector_score", 0)
    query_reason = "用户查询" if (user_query or "").strip() else "目标章节上下文"
    if lexical_score >= vector_score:
        match_type = "关键词命中"
    else:
        match_type = "语义相似"
    return f"{query_reason}触发，{match_type}，得分 {score}，范围限制至第{max_chapter_index}章"


def _project_sources(db: Session, project_id: str) -> Iterator[RetrievalSource]:
    chapter_rows = (
        db.query(ChapterContent)
        .with_entities(
            ChapterContent.id,
            ChapterContent.chapter_index,
            ChapterContent.title,
            ChapterContent.content,
            ChapterContent.status,
        )
        .filter(ChapterContent.project_id == project_id, ChapterContent.content != "")
        .order_by(ChapterContent.chapter_index.asc())
        .yield_per(50)
    )
    for chapter in chapter_rows:
        yield _chapter_source(chapter)

    memories = (
        db.query(LongformMemory)
        .filter(LongformMemory.project_id == project_id, LongformMemory.summary != "")
        .order_by(
            LongformMemory.end_chapter_index.asc().nullsfirst(),
            LongformMemory.memory_type.asc(),
            LongformMemory.scope_key.asc(),
        )
        .yield_per(50)
    )
    for memory in memories:
        yield _longform_memory_source(memory)

    facts = (
        db.query(WorldFactClaim)
        .filter(
            WorldFactClaim.project_id == project_id,
            WorldFactClaim.claim_status == "confirmed",
            WorldFactClaim.claim_layer == "truth",
        )
        .order_by(WorldFactClaim.chapter_index.asc().nullsfirst(), WorldFactClaim.claim_id.asc())
        .yield_per(50)
    )
    for fact in facts:
        yield _fact_source(fact)


def sync_fact_retrieval_document(db: Session, *, fact: WorldFactClaim) -> dict[str, int]:
    _delete_document(db, project_id=fact.project_id, source_type="world_fact", source_id=fact.id)
    if fact.claim_layer != "truth" or fact.claim_status != "confirmed":
        return {"documents": 0, "chunks": 0, "embeddings": 0}
    return _index_sources(db, fact.project_id, [_fact_source(fact)])


def delete_fact_retrieval_document(db: Session, *, fact: WorldFactClaim) -> None:
    _delete_document(db, project_id=fact.project_id, source_type="world_fact", source_id=fact.id)


def _chapter_source(chapter: ChapterContent) -> RetrievalSource:
    return RetrievalSource(
        source_type="chapter",
        source_id=chapter.id,
        source_ref=f"chapter:{chapter.chapter_index}",
        title=chapter.title or f"第{chapter.chapter_index}章",
        text=chapter.content or "",
        chapter_index=chapter.chapter_index,
        profile_version=None,
        metadata={"chapter_index": chapter.chapter_index, "status": chapter.status},
    )


def _longform_memory_source(memory: LongformMemory) -> RetrievalSource:
    metadata = memory.memory_metadata or {}
    return RetrievalSource(
        source_type="longform_memory",
        source_id=memory.id,
        source_ref=f"memory:{memory.scope_key}",
        title=memory.title or memory.scope_key,
        text=memory.summary or "",
        chapter_index=memory.end_chapter_index,
        profile_version=None,
        metadata={
            "memory_type": memory.memory_type,
            "scope_key": memory.scope_key,
            "start_chapter_index": memory.start_chapter_index,
            "end_chapter_index": memory.end_chapter_index,
            **metadata,
        },
    )


def _fact_source(fact: WorldFactClaim) -> RetrievalSource:
    value = _json_value(fact.object_ref_or_value)
    text = f"{fact.subject_ref}.{fact.predicate} = {value}"
    if fact.notes:
        text = f"{text}\n{fact.notes}"
    return RetrievalSource(
        source_type="world_fact",
        source_id=fact.id,
        source_ref=f"claim:{fact.claim_id}",
        title=f"{fact.subject_ref}.{fact.predicate}",
        text=text,
        chapter_index=fact.chapter_index,
        profile_version=fact.profile_version,
        metadata={
            "claim_id": fact.claim_id,
            "subject_ref": fact.subject_ref,
            "predicate": fact.predicate,
            "evidence_refs": fact.evidence_refs or [],
        },
    )


def _index_sources(db: Session, project_id: str, sources: Iterable[RetrievalSource]) -> dict[str, int]:
    provider = get_embedding_provider()
    indexed = {"documents": 0, "chunks": 0, "terms": 0, "embeddings": 0}
    for source in sources:
        chunks = _chunk_text(source.text)
        if not chunks:
            continue
        document = RetrievalDocument(
            project_id=project_id,
            source_type=source.source_type,
            source_id=source.source_id,
            source_ref=source.source_ref,
            title=source.title,
            chapter_index=source.chapter_index,
            profile_version=source.profile_version,
            content_hash=_content_hash(source.text),
            document_metadata=source.metadata,
        )
        db.add(document)
        db.flush()
        vectors = provider.embed_texts([chunk["text"] for chunk in chunks])
        indexed["documents"] += 1
        for chunk_data, vector in zip(chunks, vectors, strict=True):
            chunk = RetrievalChunk(
                project_id=project_id,
                document_id=document.id,
                chunk_index=chunk_data["chunk_index"],
                text=chunk_data["text"],
                token_count=len(tokenize_for_retrieval(chunk_data["text"])),
                start_offset=chunk_data["start_offset"],
                end_offset=chunk_data["end_offset"],
                chunk_metadata={},
            )
            db.add(chunk)
            db.flush()
            terms = sorted(set(tokenize_for_retrieval(chunk_data["text"])))
            for token in terms:
                db.add(RetrievalTerm(project_id=project_id, chunk_id=chunk.id, token=token))
            indexed["terms"] += len(terms)
            db.add(
                RetrievalEmbedding(
                    project_id=project_id,
                    chunk_id=chunk.id,
                    provider=provider.provider_name,
                    model=provider.model_name,
                    dimensions=len(vector),
                    vector=vector,
                    vector_hash=vector_hash(vector),
                )
            )
            indexed["chunks"] += 1
            indexed["embeddings"] += 1
    return indexed


def _chunk_text(text: str) -> list[dict[str, Any]]:
    cleaned = (text or "").strip()
    if not cleaned:
        return []
    chunks = []
    start = 0
    index = 0
    while start < len(cleaned):
        end = min(start + MAX_CHUNK_CHARS, len(cleaned))
        chunk_text = cleaned[start:end].strip()
        if chunk_text:
            chunks.append({"chunk_index": index, "text": chunk_text, "start_offset": start, "end_offset": end})
            index += 1
        if end >= len(cleaned):
            break
        start = max(end - CHUNK_OVERLAP_CHARS, start + 1)
    return chunks


def _delete_project_index(db: Session, project_id: str) -> None:
    db.query(RetrievalTerm).filter(RetrievalTerm.project_id == project_id).delete(synchronize_session=False)
    db.query(RetrievalEmbedding).filter(RetrievalEmbedding.project_id == project_id).delete(synchronize_session=False)
    db.query(RetrievalChunk).filter(RetrievalChunk.project_id == project_id).delete(synchronize_session=False)
    db.query(RetrievalDocument).filter(RetrievalDocument.project_id == project_id).delete(synchronize_session=False)
    db.flush()


def _delete_document(db: Session, *, project_id: str, source_type: str, source_id: str) -> None:
    document = (
        db.query(RetrievalDocument)
        .filter(
            RetrievalDocument.project_id == project_id,
            RetrievalDocument.source_type == source_type,
            RetrievalDocument.source_id == source_id,
        )
        .first()
    )
    if document is None:
        return
    _delete_retrieval_document(db, document)


def _delete_document_by_source_ref(db: Session, *, project_id: str, source_type: str, source_ref: str) -> None:
    document = (
        db.query(RetrievalDocument)
        .filter(
            RetrievalDocument.project_id == project_id,
            RetrievalDocument.source_type == source_type,
            RetrievalDocument.source_ref == source_ref,
        )
        .first()
    )
    if document is None:
        return
    _delete_retrieval_document(db, document)


def _delete_retrieval_document(db: Session, document: RetrievalDocument) -> None:
    chunk_ids = [row[0] for row in db.query(RetrievalChunk.id).filter(RetrievalChunk.document_id == document.id).all()]
    if chunk_ids:
        db.query(RetrievalTerm).filter(RetrievalTerm.chunk_id.in_(chunk_ids)).delete(synchronize_session=False)
        db.query(RetrievalEmbedding).filter(RetrievalEmbedding.chunk_id.in_(chunk_ids)).delete(synchronize_session=False)
    db.query(RetrievalChunk).filter(RetrievalChunk.document_id == document.id).delete(synchronize_session=False)
    db.delete(document)
    db.flush()


def _empty_indexed() -> dict[str, int]:
    return {"documents": 0, "chunks": 0, "terms": 0, "embeddings": 0}


def _chapter_context_query(db: Session, project_id: str, chapter_index: int) -> str:
    outline = db.query(Outline).filter(Outline.project_id == project_id).first()
    parts: list[str] = []
    if outline and outline.chapters:
        for chapter in outline.chapters:
            if isinstance(chapter, dict) and chapter.get("chapter_index") == chapter_index:
                parts.extend(
                    str(value)
                    for value in [
                        chapter.get("title"),
                        chapter.get("summary"),
                        " ".join(chapter.get("characters", []) or []),
                        " ".join(chapter.get("scenes", []) or []),
                    ]
                    if value
                )
                break
    if not parts:
        previous = (
            db.query(ChapterContent)
            .filter(ChapterContent.project_id == project_id, ChapterContent.chapter_index == chapter_index - 1)
            .first()
        )
        if previous:
            parts.append(previous.content[:500])
    return "\n".join(parts).strip()


def _lexical_score(query: str, text: str) -> float:
    query_tokens = set(tokenize_for_retrieval(query))
    if not query_tokens:
        return 0.0
    text_tokens = set(tokenize_for_retrieval(text))
    overlap = len(query_tokens & text_tokens) / max(len(query_tokens), 1)
    compact_query = "".join(query.split())
    compact_text = "".join(text.split())
    phrase_bonus = 0.18 if compact_query and compact_query in compact_text else 0.0
    return min(1.0, overlap + phrase_bonus)


def _snippet(text: str, query: str, *, length: int = 180) -> str:
    compact_tokens = tokenize_for_retrieval(query)
    first_hit = -1
    for token in sorted(compact_tokens, key=len, reverse=True):
        first_hit = text.find(token)
        if first_hit >= 0:
            break
    if first_hit < 0:
        return text[:length]
    start = max(first_hit - length // 3, 0)
    end = min(start + length, len(text))
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    return f"{prefix}{text[start:end]}{suffix}"


def _content_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _vector_from_json(value: Any) -> list[float]:
    if isinstance(value, list):
        return [float(item) for item in value]
    return []


def _json_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _require_project(db: Session, project_id: str) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
