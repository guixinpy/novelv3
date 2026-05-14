from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, load_only

from app.core.embedding_service import (
    EmbeddingProvider,
    cosine_similarity,
    get_embedding_provider,
    tokenize_for_retrieval,
    vector_hash,
)
from app.core.outline_lookup import find_outline_chapter
from app.models import (
    ChapterContent,
    LongformMemory,
    Project,
    RetrievalChunk,
    RetrievalDocument,
    RetrievalEmbedding,
    RetrievalTerm,
    WorldFactClaim,
)


MAX_CHUNK_CHARS = 900
CHUNK_OVERLAP_CHARS = 120
INDEX_WRITE_BATCH_SOURCES = 100
RETRIEVAL_EMBEDDING_BATCH_SIZE = 64


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


@dataclass(frozen=True)
class _PendingEmbedding:
    project_id: str
    chunk_id: str
    text: str
    tokens: list[str]


@dataclass(frozen=True)
class _PreparedLexicalQuery:
    text: str
    tokens: tuple[str, ...]
    token_set: frozenset[str]
    compact_text: str


def reindex_project_retrieval(db: Session, project_id: str) -> dict[str, Any]:
    _require_project(db, project_id)
    provider = get_embedding_provider()
    existing_documents = _existing_retrieval_documents(db, project_id)
    embedding_ready_document_ids = _documents_with_current_embeddings(
        db,
        project_id=project_id,
        provider=provider.provider_name,
        model=provider.model_name,
    )
    seen_sources: set[tuple[str, str]] = set()
    stale_document_ids: list[str] = []
    sources_to_index: list[RetrievalSource] = []
    preserved_documents = 0

    for source in _project_sources(db, project_id):
        source_key = (source.source_type, source.source_id)
        seen_sources.add(source_key)
        existing = existing_documents.get(source_key)
        content_hash = _content_hash(source.text)
        if (
            existing is not None
            and source.text.strip()
            and existing.content_hash == content_hash
            and existing.id in embedding_ready_document_ids
        ):
            _refresh_retrieval_document_metadata(existing, source=source, content_hash=content_hash)
            preserved_documents += 1
            continue
        if existing is not None:
            stale_document_ids.append(existing.id)
        sources_to_index.append(source)

    stale_document_ids.extend(
        document.id
        for source_key, document in existing_documents.items()
        if source_key not in seen_sources
    )
    _delete_documents_by_ids(db, stale_document_ids)
    indexed = _index_sources(db, project_id, sources_to_index)
    db.commit()
    return {
        "status": "completed",
        "project_id": project_id,
        "chapter_index": None,
        "indexed": indexed,
        "preserved_documents": preserved_documents,
        "removed_documents": len(stale_document_ids),
    }


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
        "total_documents": db.query(func.count(RetrievalDocument.id)).filter(RetrievalDocument.project_id == project_id).scalar() or 0,
        "total_chunks": db.query(func.count(RetrievalChunk.id)).filter(RetrievalChunk.project_id == project_id).scalar() or 0,
        "total_terms": db.query(func.count(RetrievalTerm.id)).filter(RetrievalTerm.project_id == project_id).scalar() or 0,
        "total_embeddings": db.query(func.count(RetrievalEmbedding.id)).filter(RetrievalEmbedding.project_id == project_id).scalar() or 0,
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
    _delete_documents_by_source_refs(
        db,
        project_id=project_id,
        source_type="longform_memory",
        source_refs=[f"memory:{memory.scope_key}" for memory in memories],
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
    query_tokens = tokenize_for_retrieval(cleaned_query)
    prepared_query = _prepare_lexical_query(cleaned_query, query_tokens)
    query_vector = _embed_query(provider, cleaned_query, query_tokens)
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
        query_tokens=query_tokens,
        limit=limit,
        candidate_limit=candidate_limit,
        source_type=source_type,
        max_chapter_index=max_chapter_index,
    ):
        vector_score = max(0.0, cosine_similarity(query_vector, _vector_from_json(embedding.vector)))
        lexical_score = _lexical_score(prepared_query, chunk.text)
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
                "snippet": _snippet(chunk.text, prepared_query),
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
        .options(
            load_only(RetrievalChunk.id, RetrievalChunk.chunk_index, RetrievalChunk.text),
            load_only(
                RetrievalDocument.id,
                RetrievalDocument.source_type,
                RetrievalDocument.source_ref,
                RetrievalDocument.title,
                RetrievalDocument.chapter_index,
                RetrievalDocument.document_metadata,
            ),
            load_only(RetrievalEmbedding.id, RetrievalEmbedding.vector),
        )
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
    query_tokens: list[str],
    limit: int,
    candidate_limit: int | None,
    source_type: str | None,
    max_chapter_index: int | None,
) -> list[tuple[Any, Any, Any]]:
    fallback_limit = candidate_limit or max(limit * 40, 240)
    lexical_limit = candidate_limit or max(limit * 80, 480)
    tokens = _candidate_query_tokens(query_tokens)
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


def _candidate_query_tokens(query_tokens: list[str]) -> list[str]:
    tokens = {token for token in query_tokens if len(token) >= 2}
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
        if len(items) >= limit:
            return items[:limit]
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
    document_rows: list[dict[str, Any]] = []
    chunk_rows: list[dict[str, Any]] = []
    term_rows: list[dict[str, Any]] = []
    pending_embeddings: list[_PendingEmbedding] = []
    batched_sources = 0
    for source in sources:
        chunks = _chunk_text(source.text)
        if not chunks:
            continue
        document_id = str(uuid.uuid4())
        document_rows.append(
            {
                "id": document_id,
                "project_id": project_id,
                "source_type": source.source_type,
                "source_id": source.source_id,
                "source_ref": source.source_ref,
                "title": source.title,
                "chapter_index": source.chapter_index,
                "profile_version": source.profile_version,
                "content_hash": _content_hash(source.text),
                "document_metadata": source.metadata,
            }
        )
        indexed["documents"] += 1
        for chunk_data in chunks:
            chunk_id = str(uuid.uuid4())
            tokens = tokenize_for_retrieval(chunk_data["text"])
            chunk_rows.append(
                {
                    "id": chunk_id,
                    "project_id": project_id,
                    "document_id": document_id,
                    "chunk_index": chunk_data["chunk_index"],
                    "text": chunk_data["text"],
                    "token_count": len(tokens),
                    "start_offset": chunk_data["start_offset"],
                    "end_offset": chunk_data["end_offset"],
                    "chunk_metadata": {},
                }
            )
            terms = _indexable_retrieval_terms(tokens)
            term_rows.extend(
                {
                    "id": f"{chunk_id}:term:{term_index}",
                    "project_id": project_id,
                    "chunk_id": chunk_id,
                    "token": token,
                }
                for term_index, token in enumerate(terms)
            )
            pending_embeddings.append(
                _PendingEmbedding(
                    project_id=project_id,
                    chunk_id=chunk_id,
                    text=chunk_data["text"],
                    tokens=tokens,
                )
            )
            indexed["terms"] += len(terms)
            indexed["chunks"] += 1
            indexed["embeddings"] += 1
        batched_sources += 1
        if batched_sources >= INDEX_WRITE_BATCH_SOURCES:
            _flush_index_write_batch(
                db,
                provider,
                document_rows,
                chunk_rows,
                term_rows,
                pending_embeddings,
            )
            batched_sources = 0
    _flush_index_write_batch(
        db,
        provider,
        document_rows,
        chunk_rows,
        term_rows,
        pending_embeddings,
    )
    return indexed


def _indexable_retrieval_terms(tokens: list[str]) -> list[str]:
    unique_tokens = sorted(set(tokens))
    has_cjk_trigrams = any(
        _is_cjk_token(token) and len(token) >= 3
        for token in unique_tokens
    )
    if not has_cjk_trigrams:
        return unique_tokens
    return [
        token
        for token in unique_tokens
        if not (_is_cjk_token(token) and len(token) == 2)
    ]


def _is_cjk_token(token: str) -> bool:
    return bool(token) and all("\u4e00" <= char <= "\u9fff" for char in token)


def _flush_index_write_batch(
    db: Session,
    provider: EmbeddingProvider,
    documents: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    terms: list[dict[str, Any]],
    embeddings: list[_PendingEmbedding],
) -> None:
    if not documents:
        return
    embedding_rows: list[dict[str, Any]] = []
    if embeddings:
        vectors = _embed_pending_embeddings(provider, embeddings)
        embedding_rows = [
            {
                "id": str(uuid.uuid4()),
                "project_id": embedding.project_id,
                "chunk_id": embedding.chunk_id,
                "provider": provider.provider_name,
                "model": provider.model_name,
                "dimensions": len(vector),
                "vector": vector,
                "vector_hash": vector_hash(vector),
            }
            for embedding, vector in zip(embeddings, vectors, strict=True)
        ]
    _insert_retrieval_rows(db, RetrievalDocument, documents)
    _insert_retrieval_rows(db, RetrievalChunk, chunks)
    _insert_retrieval_rows(db, RetrievalTerm, terms)
    _insert_retrieval_rows(db, RetrievalEmbedding, embedding_rows)
    documents.clear()
    chunks.clear()
    terms.clear()
    embeddings.clear()


def _insert_retrieval_rows(db: Session, model: type[Any], rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    db.execute(model.__table__.insert(), rows)


def _embed_pending_embeddings(
    provider: EmbeddingProvider,
    embeddings: list[_PendingEmbedding],
) -> list[list[float]]:
    vectors: list[list[float]] = []
    batch_size = max(1, RETRIEVAL_EMBEDDING_BATCH_SIZE)
    for start in range(0, len(embeddings), batch_size):
        batch = embeddings[start : start + batch_size]
        embed_token_batches = getattr(provider, "embed_token_batches", None)
        if callable(embed_token_batches):
            vectors.extend(embed_token_batches([embedding.tokens for embedding in batch]))
        else:
            vectors.extend(provider.embed_texts([embedding.text for embedding in batch]))
    return vectors


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


def _existing_retrieval_documents(db: Session, project_id: str) -> dict[tuple[str, str], RetrievalDocument]:
    return {
        (document.source_type, document.source_id): document
        for document in db.query(RetrievalDocument).filter(RetrievalDocument.project_id == project_id).all()
    }


def _documents_with_current_embeddings(
    db: Session,
    *,
    project_id: str,
    provider: str,
    model: str,
) -> set[str]:
    chunk_counts = {
        document_id: count
        for document_id, count in (
            db.query(RetrievalChunk.document_id, func.count(RetrievalChunk.id))
            .filter(RetrievalChunk.project_id == project_id)
            .group_by(RetrievalChunk.document_id)
            .all()
        )
    }
    embedding_counts = {
        document_id: count
        for document_id, count in (
            db.query(RetrievalChunk.document_id, func.count(RetrievalEmbedding.id))
            .join(RetrievalEmbedding, RetrievalEmbedding.chunk_id == RetrievalChunk.id)
            .filter(
                RetrievalChunk.project_id == project_id,
                RetrievalEmbedding.provider == provider,
                RetrievalEmbedding.model == model,
            )
            .group_by(RetrievalChunk.document_id)
            .all()
        )
    }
    return {
        document_id
        for document_id, chunk_count in chunk_counts.items()
        if chunk_count > 0 and embedding_counts.get(document_id) == chunk_count
    }


def _refresh_retrieval_document_metadata(
    document: RetrievalDocument,
    *,
    source: RetrievalSource,
    content_hash: str,
) -> None:
    document.source_ref = source.source_ref
    document.title = source.title
    document.chapter_index = source.chapter_index
    document.profile_version = source.profile_version
    document.content_hash = content_hash
    document.document_metadata = source.metadata


def _delete_documents_by_ids(db: Session, document_ids: list[str]) -> None:
    if not document_ids:
        return
    document_id_select = select(RetrievalDocument.id).where(RetrievalDocument.id.in_(document_ids))
    _delete_documents_matching(db, document_id_select)


def _delete_documents_by_source_refs(
    db: Session,
    *,
    project_id: str,
    source_type: str,
    source_refs: list[str],
) -> None:
    unique_refs = sorted(set(source_refs))
    if not unique_refs:
        return
    document_id_select = select(RetrievalDocument.id).where(
        RetrievalDocument.project_id == project_id,
        RetrievalDocument.source_type == source_type,
        RetrievalDocument.source_ref.in_(unique_refs),
    )
    _delete_documents_matching(db, document_id_select)


def _delete_documents_matching(db: Session, document_id_select) -> None:
    chunk_ids = select(RetrievalChunk.id).where(RetrievalChunk.document_id.in_(document_id_select))
    db.query(RetrievalTerm).filter(RetrievalTerm.chunk_id.in_(chunk_ids)).delete(synchronize_session=False)
    db.query(RetrievalEmbedding).filter(RetrievalEmbedding.chunk_id.in_(chunk_ids)).delete(synchronize_session=False)
    db.query(RetrievalChunk).filter(RetrievalChunk.document_id.in_(document_id_select)).delete(synchronize_session=False)
    db.query(RetrievalDocument).filter(RetrievalDocument.id.in_(document_id_select)).delete(synchronize_session=False)
    db.flush()


def _delete_document(db: Session, *, project_id: str, source_type: str, source_id: str) -> None:
    document_id_select = select(RetrievalDocument.id).where(
        RetrievalDocument.project_id == project_id,
        RetrievalDocument.source_type == source_type,
        RetrievalDocument.source_id == source_id,
    )
    _delete_documents_matching(db, document_id_select)


def _empty_indexed() -> dict[str, int]:
    return {"documents": 0, "chunks": 0, "terms": 0, "embeddings": 0}


def _chapter_context_query(db: Session, project_id: str, chapter_index: int) -> str:
    parts: list[str] = []
    outline_chapter = find_outline_chapter(db, project_id, chapter_index)
    if outline_chapter is not None:
        _outline_id, chapter = outline_chapter
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
    if not parts:
        previous = (
            db.query(ChapterContent)
            .filter(ChapterContent.project_id == project_id, ChapterContent.chapter_index == chapter_index - 1)
            .first()
        )
        if previous:
            parts.append(previous.content[:500])
    return "\n".join(parts).strip()


def _prepare_lexical_query(query: str, tokens: list[str]) -> _PreparedLexicalQuery:
    return _PreparedLexicalQuery(
        text=query,
        tokens=tuple(tokens),
        token_set=frozenset(tokens),
        compact_text="".join(query.split()),
    )


def _embed_query(provider: EmbeddingProvider, query: str, tokens: list[str]) -> list[float]:
    embed_token_batches = getattr(provider, "embed_token_batches", None)
    if callable(embed_token_batches):
        return embed_token_batches([tokens])[0]
    return provider.embed_texts([query])[0]


def _lexical_score(query: _PreparedLexicalQuery, text: str) -> float:
    if not query.token_set:
        return 0.0
    text_tokens = set(tokenize_for_retrieval(text))
    overlap = len(query.token_set & text_tokens) / max(len(query.token_set), 1)
    compact_text = "".join(text.split())
    phrase_bonus = 0.18 if query.compact_text and query.compact_text in compact_text else 0.0
    return min(1.0, overlap + phrase_bonus)


def _snippet(text: str, query: _PreparedLexicalQuery, *, length: int = 180) -> str:
    first_hit = -1
    for token in sorted(query.tokens, key=len, reverse=True):
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
