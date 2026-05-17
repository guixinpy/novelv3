from sqlalchemy import event

from app.core.world_contracts import DERIVED
from app.core.embedding_service import LocalHashEmbeddingProvider, get_embedding_provider
from app.core.athena_retrieval import (
    RetrievalSource,
    _index_sources,
    _chapter_context_query,
    _project_sources,
    index_chapter_retrieval,
    reindex_project_retrieval,
    search_retrieval,
)
from app.core.world_proposal_service import create_bundle, review_proposal_item, rollback_review, write_candidate_fact
from app.models import (
    ChapterContent,
    LongformMemory,
    Outline,
    Project,
    ProjectProfileVersion,
    RetrievalDocument,
    RetrievalTerm,
    Setup,
    WorldFactClaim,
)
from app.schemas.world_proposals import ProposalCandidateFactCreate


def test_retrieval_chapter_index_rejects_non_positive_chapter_index(client):
    project_response = client.post("/api/v1/projects", json={"name": "Invalid Retrieval Index"})
    project_id = project_response.json()["id"]

    response = client.post(f"/api/v1/projects/{project_id}/athena/retrieval/chapters/0/index")

    assert response.status_code == 422


def test_embedding_provider_defaults_to_local_without_explicit_remote_mode(monkeypatch):
    monkeypatch.setenv("EMBEDDING_API_KEY", "test-key")
    monkeypatch.setenv("EMBEDDING_MODEL", "remote-model")
    monkeypatch.delenv("EMBEDDING_PROVIDER", raising=False)

    provider = get_embedding_provider()

    assert provider.provider_name == "local"


def test_chapter_context_fallback_projects_previous_chapter_preview(db_session):
    project = Project(name="Retrieval fallback")
    db_session.add(project)
    db_session.flush()
    previous_content = "上一章正文" * 200
    db_session.add(
        ChapterContent(
            project_id=project.id,
            chapter_index=4,
            title="上一章",
            content=previous_content,
            word_count=len(previous_content),
            status="generated",
        )
    )
    db_session.commit()
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        query = _chapter_context_query(db_session, project.id, 5)
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert query == previous_content[:500]
    chapter_selects = [
        statement.split(" from chapter_contents", 1)[0]
        for statement in statements
        if " from chapter_contents" in statement
    ]
    assert chapter_selects
    assert any("substr(chapter_contents.content" in statement for statement in statements)
    assert all("chapter_contents.content as" not in clause for clause in chapter_selects)


def test_local_hash_embedding_hashes_repeated_tokens_once(monkeypatch):
    import app.core.embedding_service as embedding_service

    embedding_service._local_hash_token_features.cache_clear()
    original_sha256 = embedding_service.hashlib.sha256
    calls: list[bytes] = []

    def count_sha256(data: bytes):
        calls.append(data)
        return original_sha256(data)

    monkeypatch.setattr(embedding_service.hashlib, "sha256", count_sha256)

    provider = LocalHashEmbeddingProvider(dimensions=8)
    vector = provider.embed_token_batches([["星环钥"] * 20 + ["灯塔区"] * 10])[0]

    assert calls == ["星环钥".encode("utf-8"), "灯塔区".encode("utf-8")]
    assert any(value != 0 for value in vector)


def test_local_hash_embedding_reuses_token_hashes_across_batches(monkeypatch):
    import app.core.embedding_service as embedding_service

    embedding_service._local_hash_token_features.cache_clear()
    original_sha256 = embedding_service.hashlib.sha256
    calls: list[bytes] = []

    def count_sha256(data: bytes):
        calls.append(data)
        return original_sha256(data)

    monkeypatch.setattr(embedding_service.hashlib, "sha256", count_sha256)

    provider = LocalHashEmbeddingProvider(dimensions=8)
    provider.embed_token_batches([
        ["星环钥", "灯塔区"],
        ["星环钥", "潮汐钟"],
        ["灯塔区", "星环钥"],
    ])

    assert calls == [
        "星环钥".encode("utf-8"),
        "灯塔区".encode("utf-8"),
        "潮汐钟".encode("utf-8"),
    ]


def _seed_retrieval_project(db_session):
    project = Project(name="Athena Retrieval", genre="东方奇幻悬疑")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    db_session.add(
        Setup(
            project_id=project.id,
            status="generated",
            world_building={
                "background": "雾港城被潮雾笼罩。",
                "rules": "旧灯塔熄灭时，亡者不能被直接召回。",
            },
            characters=[
                {
                    "name": "林舟",
                    "personality": "谨慎",
                    "background": "雾港守夜人",
                    "goals": "查清旧灯塔失火真相",
                    "character_status": "alive",
                }
            ],
            core_concept={"theme": "记忆与真相"},
        )
    )
    db_session.add(
        Outline(
            project_id=project.id,
            total_chapters=3,
            status="generated",
            chapters=[
                {"chapter_index": 1, "title": "雾港来信", "summary": "林舟发现旧灯塔失火的证词互相矛盾。"},
                {"chapter_index": 2, "title": "亡者契约", "summary": "沈聆发现旧灯塔熄灭会阻断亡者召回。"},
                {"chapter_index": 3, "title": "灯塔再燃", "summary": "林舟准备利用旧灯塔和亡者契约反查真相。"},
            ],
        )
    )
    db_session.add_all(
        [
            ChapterContent(
                project_id=project.id,
                chapter_index=1,
                title="雾港来信",
                content="林舟在潮雾里走近旧灯塔。墙上的证词说，旧灯塔失火那夜有人听见亡者敲门。",
                word_count=40,
                status="generated",
            ),
            ChapterContent(
                project_id=project.id,
                chapter_index=2,
                title="亡者契约",
                content="沈聆翻出档案：旧灯塔熄灭时，亡者不能被直接召回，守夜人只能等待潮声停下。",
                word_count=42,
                status="generated",
            ),
        ]
    )
    db_session.commit()
    return project


def _seed_confirmed_fact(db_session, project_id: str):
    profile = db_session.query(ProjectProfileVersion).filter_by(project_id=project_id).one()
    claim = WorldFactClaim(
        project_id=project_id,
        project_profile_version_id=profile.id,
        profile_version=profile.version,
        claim_id="claim.old_lighthouse.recall_ban",
        chapter_index=2,
        intra_chapter_seq=1,
        subject_ref="rule.old_lighthouse",
        predicate="recall_constraint",
        object_ref_or_value="旧灯塔熄灭时，亡者不能被直接召回。",
        claim_layer="truth",
        claim_status="confirmed",
        evidence_refs=["chapter:2"],
        authority_type=DERIVED,
        confidence=0.92,
        contract_version=profile.contract_version,
    )
    db_session.add(claim)
    db_session.commit()
    return claim


def _write_reviewable_fact_candidate(db_session, project_id: str):
    profile = db_session.query(ProjectProfileVersion).filter_by(project_id=project_id).one()
    bundle = create_bundle(
        db=db_session,
        project_id=project_id,
        project_profile_version_id=profile.id,
        profile_version=profile.version,
        created_by="athena.test",
        title="增量检索候选",
    )
    return write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="athena.test",
        candidate=ProposalCandidateFactCreate(
            project_id=project_id,
            project_profile_version_id=profile.id,
            profile_version=profile.version,
            claim_id="claim.linzhou.role.incremental",
            chapter_index=2,
            subject_ref="char.林舟",
            predicate="role",
            object_ref_or_value="雾港城守夜人",
            claim_layer="truth",
            evidence_refs=["chapter:2"],
            authority_type=DERIVED,
            confidence=0.93,
            notes="林舟在雾港城承担守夜职责。",
            contract_version=profile.contract_version,
        ),
    )


def test_reindex_builds_searchable_chunks_for_chapters_and_confirmed_facts(client, db_session):
    project = _seed_retrieval_project(db_session)
    client.post(f"/api/v1/projects/{project.id}/athena/ontology/import-setup")
    _seed_confirmed_fact(db_session, project.id)

    response = client.post(f"/api/v1/projects/{project.id}/athena/retrieval/reindex")
    search = client.get(f"/api/v1/projects/{project.id}/athena/retrieval/search?q=旧灯塔亡者召回&limit=5")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["indexed"]["documents"] >= 3
    assert payload["indexed"]["chunks"] >= 3

    assert search.status_code == 200
    results = search.json()
    assert results["total"] >= 2
    assert results["items"][0]["score"] >= results["items"][-1]["score"]
    assert {item["source_type"] for item in results["items"]} >= {"chapter", "world_fact"}
    assert any("亡者不能被直接召回" in item["snippet"] for item in results["items"])


def test_project_sources_streams_chapters_in_order(db_session):
    project = Project(name="Streaming Retrieval Sources")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    for index in range(1, 4):
        db_session.add(
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章",
                content=f"第{index}章正文。",
                word_count=1000,
                status="generated",
            )
        )
    db_session.commit()

    sources = _project_sources(db_session, project.id)

    assert not isinstance(sources, list)
    assert [source.source_ref for source in sources] == ["chapter:1", "chapter:2", "chapter:3"]


def test_reindex_chapter_source_query_projects_only_index_fields(db_session):
    project = Project(name="Projected Retrieval Reindex")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    for index in range(1, 6):
        db_session.add(
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章",
                content="需要索引的正文。" * 30,
                word_count=1000,
                status="generated",
                model="deepseek",
                prompt_tokens=100,
                completion_tokens=200,
                generation_time=3,
                temperature=0.7,
            )
        )
    db_session.commit()
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement.lower())

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        result = reindex_project_retrieval(db_session, project.id)
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert result["indexed"]["documents"] == 5
    chapter_selects = [
        statement for statement in statements
        if "from chapter_contents" in statement
    ]
    assert chapter_selects
    select_clause = chapter_selects[0].split("from chapter_contents", 1)[0]
    for column in [
        "word_count",
        "model",
        "prompt_tokens",
        "completion_tokens",
        "generation_time",
        "temperature",
        "created_at",
        "updated_at",
    ]:
        assert f"chapter_contents.{column}" not in select_clause


def test_reindex_preserves_unchanged_documents_without_loading_chunk_ids(db_session):
    project = Project(name="Stable Retrieval Reindex")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    for index in range(1, 11):
        db_session.add(
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章",
                content="旧索引清理压力测试正文。" * 40,
                word_count=1000,
                status="generated",
            )
        )
    db_session.commit()
    first_result = reindex_project_retrieval(db_session, project.id)
    assert first_result["indexed"]["documents"] == 10
    before_doc_ids = {
        document.source_ref: document.id
        for document in db_session.query(RetrievalDocument)
        .filter(RetrievalDocument.project_id == project.id)
        .all()
    }
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement.lower())

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        second_result = reindex_project_retrieval(db_session, project.id)
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    after_doc_ids = {
        document.source_ref: document.id
        for document in db_session.query(RetrievalDocument)
        .filter(RetrievalDocument.project_id == project.id)
        .all()
    }
    assert second_result["indexed"]["documents"] == 0
    assert second_result["preserved_documents"] == 10
    assert after_doc_ids == before_doc_ids
    chunk_id_selects = [
        statement for statement in statements
        if "select retrieval_chunks.id" in statement and "from retrieval_chunks" in statement
    ]
    assert not chunk_id_selects


def test_reindex_preserves_memory_documents_after_memory_rebuild(db_session):
    from app.core.longform_memory import rebuild_longform_memory

    project = Project(name="Stable Memory Retrieval Reindex")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    for index in range(1, 4):
        db_session.add(
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章",
                content=f"第{index}章正文。星环钥匙线索保持不变。",
                word_count=1000,
                status="generated",
            )
        )
    db_session.commit()
    rebuild_longform_memory(db_session, project.id)
    first_result = reindex_project_retrieval(db_session, project.id)
    assert first_result["indexed"]["documents"] == 9
    before_doc_ids = {
        document.source_ref: document.id
        for document in db_session.query(RetrievalDocument)
        .filter(RetrievalDocument.project_id == project.id)
        .all()
    }

    rebuild_longform_memory(db_session, project.id)
    current_memory_ids = {
        f"memory:{memory.scope_key}": memory.id
        for memory in db_session.query(LongformMemory)
        .filter(LongformMemory.project_id == project.id)
        .all()
    }
    second_result = reindex_project_retrieval(db_session, project.id)
    after_documents = {
        document.source_ref: document
        for document in db_session.query(RetrievalDocument)
        .filter(RetrievalDocument.project_id == project.id)
        .all()
    }

    assert second_result["indexed"]["documents"] == 0
    assert second_result["preserved_documents"] == 9
    assert second_result["removed_documents"] == 0
    assert {source_ref: document.id for source_ref, document in after_documents.items()} == before_doc_ids
    for source_ref, memory_id in current_memory_ids.items():
        assert after_documents[source_ref].source_id == memory_id


def test_reindex_existing_document_scan_projects_only_preservation_fields(db_session):
    project = Project(name="Existing Retrieval Projection")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    db_session.add_all(
        [
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章",
                content=("已有索引投影测试正文。" * 50),
                word_count=1000,
                status="generated",
            )
            for index in range(1, 6)
        ]
    )
    db_session.commit()
    reindex_project_retrieval(db_session, project.id)
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        second_result = reindex_project_retrieval(db_session, project.id)
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert second_result["indexed"]["documents"] == 0
    document_selects = [
        statement.split("from retrieval_documents", 1)[0]
        for statement in statements
        if statement.startswith("select")
        and "from retrieval_documents" in statement
        and "retrieval_documents.project_id" in statement
    ]
    assert document_selects
    assert any("retrieval_documents.content_hash" in statement for statement in document_selects)
    assert any("retrieval_documents.source_ref" in statement for statement in document_selects)
    excluded_columns = [
        "retrieval_documents.title",
        "retrieval_documents.chapter_index",
        "retrieval_documents.profile_version",
        "retrieval_documents.document_metadata",
        "retrieval_documents.created_at",
        "retrieval_documents.updated_at",
    ]
    for column in excluded_columns:
        assert all(column not in select_clause for select_clause in document_selects)


def test_reindex_preserves_unchanged_documents_without_update_statements(db_session):
    project = Project(name="Stable Retrieval No-op")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    db_session.add_all(
        [
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章",
                content=("重复维护不应写回已有检索文档。" * 40),
                word_count=1000,
                status="generated",
            )
            for index in range(1, 4)
        ]
    )
    db_session.commit()
    reindex_project_retrieval(db_session, project.id)
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        second_result = reindex_project_retrieval(db_session, project.id)
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert second_result["indexed"]["documents"] == 0
    document_updates = [
        statement
        for statement in statements
        if statement.startswith("update retrieval_documents")
    ]
    assert document_updates == []


def test_reindex_rebuilds_chapter_document_when_source_metadata_changes(db_session):
    project = Project(name="Changed Metadata Retrieval Reindex")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    db_session.add(
        ChapterContent(
            project_id=project.id,
            chapter_index=1,
            title="旧标题",
            content="正文没有变化，只有标题发生变化。",
            word_count=1000,
            status="generated",
        )
    )
    db_session.commit()
    reindex_project_retrieval(db_session, project.id)
    before_document = db_session.query(RetrievalDocument).filter_by(project_id=project.id).one()
    before_document_id = before_document.id

    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "新标题"
    db_session.commit()
    result = reindex_project_retrieval(db_session, project.id)
    after_document = db_session.query(RetrievalDocument).filter_by(project_id=project.id).one()

    assert result["indexed"]["documents"] == 1
    assert result["preserved_documents"] == 0
    assert after_document.id != before_document_id
    assert after_document.title == "新标题"


def test_reindex_fetches_changed_chapter_sources_by_id(db_session):
    project = Project(name="Targeted Changed Retrieval Reindex")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    db_session.add_all(
        [
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章",
                content=f"第{index}章正文。定向重建检索索引。" * 30,
                word_count=1000,
                status="generated",
            )
            for index in range(1, 26)
        ]
    )
    db_session.commit()
    reindex_project_retrieval(db_session, project.id)

    changed = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=17).one()
    changed.content = "第17章正文发生变化。只应定向重建这一章检索索引。" * 30
    db_session.commit()
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        result = reindex_project_retrieval(db_session, project.id)
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert result["indexed"]["documents"] == 1
    assert result["preserved_documents"] == 24
    chapter_content_selects = [
        statement
        for statement in statements
        if statement.startswith("select")
        and "from chapter_contents" in statement
        and "chapter_contents.content" in statement.split(" from chapter_contents", 1)[0]
    ]
    broad_content_selects = [
        statement
        for statement in chapter_content_selects
        if "chapter_contents.project_id = ?" in statement and "chapter_contents.id in" not in statement
    ]
    targeted_content_selects = [
        statement
        for statement in chapter_content_selects
        if "chapter_contents.id in" in statement
    ]
    assert len(broad_content_selects) == 1
    assert targeted_content_selects


def test_source_hash_does_not_json_serialize_full_text(monkeypatch):
    import hashlib
    import app.core.athena_retrieval as athena_retrieval

    captured_payloads: list[dict] = []
    original_dumps = athena_retrieval.json.dumps

    def capture_dumps(payload, *args, **kwargs):
        captured_payloads.append(payload)
        return original_dumps(payload, *args, **kwargs)

    monkeypatch.setattr(athena_retrieval.json, "dumps", capture_dumps)
    source = athena_retrieval.RetrievalSource(
        source_type="chapter",
        source_id="chapter-1",
        source_ref="chapter:1",
        title="第一章",
        text="很长的正文" * 1000,
        chapter_index=1,
        profile_version=None,
        metadata={"status": "generated"},
    )

    value = athena_retrieval._source_hash(source)

    assert value
    assert captured_payloads
    payload = captured_payloads[0]
    assert "text" not in payload
    assert payload["text_sha256"] == hashlib.sha256(source.text.encode("utf-8")).hexdigest()


def test_reindex_skips_embedding_readiness_scan_without_existing_documents(db_session):
    project = Project(name="First Retrieval Reindex")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    db_session.add_all(
        [
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章",
                content=("首次索引无需检查旧 embedding。" * 40),
                word_count=1000,
                status="generated",
            )
            for index in range(1, 4)
        ]
    )
    db_session.commit()
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        result = reindex_project_retrieval(db_session, project.id)
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert result["indexed"]["documents"] == 3
    readiness_selects = [
        statement
        for statement in statements
        if statement.startswith("select")
        and "from retrieval_chunks" in statement
        and "count(" in statement
    ]
    assert readiness_selects == []


def test_reindex_rebuilds_only_changed_chapter_document(db_session):
    project = Project(name="Changed Chapter Retrieval Reindex")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    for index in range(1, 4):
        db_session.add(
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章",
                content=f"第{index}章原始正文。",
                word_count=1000,
                status="generated",
            )
        )
    db_session.commit()
    reindex_project_retrieval(db_session, project.id)
    before_doc_ids = {
        document.source_ref: document.id
        for document in db_session.query(RetrievalDocument)
        .filter(RetrievalDocument.project_id == project.id)
        .all()
    }

    chapter = (
        db_session.query(ChapterContent)
        .filter(ChapterContent.project_id == project.id, ChapterContent.chapter_index == 2)
        .one()
    )
    chapter.content = "第2章更新正文，新增秘银钥匙线索。"
    db_session.commit()
    result = reindex_project_retrieval(db_session, project.id)
    after_doc_ids = {
        document.source_ref: document.id
        for document in db_session.query(RetrievalDocument)
        .filter(RetrievalDocument.project_id == project.id)
        .all()
    }

    assert result["indexed"]["documents"] == 1
    assert result["preserved_documents"] == 2
    assert after_doc_ids["chapter:1"] == before_doc_ids["chapter:1"]
    assert after_doc_ids["chapter:2"] != before_doc_ids["chapter:2"]
    assert after_doc_ids["chapter:3"] == before_doc_ids["chapter:3"]


def test_index_chapter_retrieval_deletes_old_chunks_without_materializing_chunk_ids(db_session):
    project = Project(name="Incremental Chapter Retrieval Cleanup")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    chapter = ChapterContent(
        project_id=project.id,
        chapter_index=1,
        title="第一章",
        content=("星环钥匙推进。旧灯塔记录持续增长。" * 80),
        word_count=2000,
        status="generated",
    )
    db_session.add(chapter)
    db_session.commit()

    first = index_chapter_retrieval(db_session, project.id, 1)
    assert first["indexed"]["chunks"] > 1
    chapter.content = ("秘银钥匙替换旧线索。灯塔区记录重新归档。" * 80)
    db_session.commit()
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        second = index_chapter_retrieval(db_session, project.id, 1)
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert second["indexed"]["chunks"] > 1
    chunk_id_selects = [
        statement
        for statement in statements
        if statement.startswith("select retrieval_chunks.id")
        and "from retrieval_chunks" in statement
        and "retrieval_chunks.document_id" in statement
    ]
    assert chunk_id_selects == []


def test_reindex_builds_indexed_lexical_terms_for_local_search(client, db_session):
    project = _seed_retrieval_project(db_session)
    client.post(f"/api/v1/projects/{project.id}/athena/ontology/import-setup")
    _seed_confirmed_fact(db_session, project.id)

    response = client.post(f"/api/v1/projects/{project.id}/athena/retrieval/reindex")
    diagnostics = client.get(f"/api/v1/projects/{project.id}/athena/retrieval/diagnostics")

    term_count = db_session.query(RetrievalTerm).filter_by(project_id=project.id).count()
    assert response.status_code == 200
    assert term_count > 0
    assert diagnostics.status_code == 200
    assert diagnostics.json()["total_terms"] == term_count


def test_retrieval_diagnostics_counts_do_not_select_large_payload_columns(client, db_session):
    project = _seed_retrieval_project(db_session)
    reindex_project_retrieval(db_session, project.id)
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        response = client.get(f"/api/v1/projects/{project.id}/athena/retrieval/diagnostics")
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert response.status_code == 200
    count_statements = [
        statement
        for statement in statements
        if "count(" in statement and "retrieval_" in statement
    ]
    assert count_statements
    assert all("retrieval_documents.document_metadata" not in statement for statement in count_statements)
    assert all("retrieval_chunks.text" not in statement for statement in count_statements)
    assert all("retrieval_chunks.chunk_metadata" not in statement for statement in count_statements)
    assert all("retrieval_embeddings.vector" not in statement for statement in count_statements)


def test_reindex_prefers_cjk_trigrams_over_bigrams_for_lexical_terms(db_session):
    project = Project(name="Retrieval Term Compaction")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    db_session.add(
        ChapterContent(
            project_id=project.id,
            chapter_index=1,
            title="星环钥匙",
            content="星环钥匙沉睡旧灯塔，潮汐归零时才会苏醒。",
            word_count=24,
            status="generated",
        )
    )
    db_session.commit()

    reindex_project_retrieval(db_session, project.id)

    indexed_terms = {
        row[0]
        for row in db_session.query(RetrievalTerm.token)
        .filter(RetrievalTerm.project_id == project.id)
        .all()
    }
    assert "星环钥" in indexed_terms
    assert "环钥匙" in indexed_terms
    assert "旧灯塔" in indexed_terms
    assert "星环" not in indexed_terms
    assert "钥匙" not in indexed_terms
    assert "灯塔" not in indexed_terms
    result = search_retrieval(db_session, project.id, "星环钥匙", limit=1)
    assert result["items"][0]["source_ref"] == "chapter:1"
    short_query_result = search_retrieval(db_session, project.id, "灯塔", limit=1)
    assert short_query_result["items"][0]["source_ref"] == "chapter:1"


def test_indexable_retrieval_terms_avoid_repeated_full_cjk_token_checks(monkeypatch):
    import app.core.athena_retrieval as athena_retrieval

    check_count = {"value": 0}
    original_is_cjk_token = athena_retrieval._is_cjk_token

    def count_is_cjk_token(token: str) -> bool:
        check_count["value"] += 1
        return original_is_cjk_token(token)

    tokens: list[str] = []
    for index in range(200):
        tokens.extend(
            [
                f"latin_{index}",
                f"灯塔{index}",
                "灯塔",
                "塔影",
                "灯塔影",
                "塔影像",
            ]
        )

    monkeypatch.setattr(athena_retrieval, "_is_cjk_token", count_is_cjk_token)

    terms = athena_retrieval._indexable_retrieval_terms(tokens)

    assert "灯塔影" in terms
    assert "塔影像" in terms
    assert "灯塔" not in terms
    assert "塔影" not in terms
    assert check_count["value"] <= 4


def test_reindex_bulk_inserts_lexical_terms(db_session, monkeypatch):
    project = _seed_retrieval_project(db_session)
    add_counts = {"terms": 0}
    original_add = db_session.add

    def count_add(instance, *args, **kwargs):
        if isinstance(instance, RetrievalTerm):
            add_counts["terms"] += 1
        return original_add(instance, *args, **kwargs)

    monkeypatch.setattr(db_session, "add", count_add)

    result = reindex_project_retrieval(db_session, project.id)

    assert result["indexed"]["terms"] > 0
    assert db_session.query(RetrievalTerm).filter_by(project_id=project.id).count() == result["indexed"]["terms"]
    assert add_counts["terms"] == 0


def test_reindex_uses_core_insert_path_for_retrieval_rows(db_session, monkeypatch):
    project = _seed_retrieval_project(db_session)

    def reject_bulk_insert_mappings(*_args, **_kwargs):
        raise AssertionError("retrieval reindex should use Core executemany inserts")

    monkeypatch.setattr(db_session, "bulk_insert_mappings", reject_bulk_insert_mappings)

    result = reindex_project_retrieval(db_session, project.id)

    assert result["indexed"]["documents"] == 2
    assert db_session.query(RetrievalTerm).filter_by(project_id=project.id).count() == result["indexed"]["terms"]


def test_reindex_core_inserts_lexical_term_rows(db_session, monkeypatch):
    import app.core.athena_retrieval as athena_retrieval

    project = _seed_retrieval_project(db_session)
    inserted_term_batches: list[list[dict]] = []
    original_insert_rows = athena_retrieval._insert_retrieval_rows

    def count_insert_rows(db, model, rows):
        mapping_list = list(rows)
        if model is RetrievalTerm:
            inserted_term_batches.append(mapping_list)
        return original_insert_rows(db, model, mapping_list)

    monkeypatch.setattr(athena_retrieval, "_insert_retrieval_rows", count_insert_rows)

    result = reindex_project_retrieval(db_session, project.id)

    assert result["indexed"]["terms"] > 0
    assert len(inserted_term_batches) == 1
    first_mapping = inserted_term_batches[0][0]
    assert {"id", "project_id", "chunk_id", "token"} <= set(first_mapping)
    assert db_session.query(RetrievalTerm).filter_by(project_id=project.id).count() == result["indexed"]["terms"]


def test_reindex_tokenizes_each_chunk_once_for_lexical_index(db_session, monkeypatch):
    import app.core.athena_retrieval as athena_retrieval

    project = _seed_retrieval_project(db_session)
    tokenize_count = {"calls": 0}
    original_tokenize = athena_retrieval.tokenize_for_retrieval

    def count_tokenize(text: str):
        tokenize_count["calls"] += 1
        return original_tokenize(text)

    monkeypatch.setattr(athena_retrieval, "tokenize_for_retrieval", count_tokenize)

    result = reindex_project_retrieval(db_session, project.id)

    assert result["indexed"]["chunks"] > 0
    assert tokenize_count["calls"] == result["indexed"]["chunks"]


def test_reindex_avoids_flush_per_new_document_and_chunk(db_session, monkeypatch):
    project = _seed_retrieval_project(db_session)
    flush_count = {"calls": 0}
    original_flush = db_session.flush

    def count_flush(*args, **kwargs):
        flush_count["calls"] += 1
        return original_flush(*args, **kwargs)

    monkeypatch.setattr(db_session, "flush", count_flush)

    result = reindex_project_retrieval(db_session, project.id)

    assert result["indexed"]["documents"] > 0
    assert result["indexed"]["chunks"] > 0
    assert flush_count["calls"] == 0


def test_reindex_batches_retrieval_rows_as_core_inserts(db_session, monkeypatch):
    import app.core.athena_retrieval as athena_retrieval

    project = _seed_retrieval_project(db_session)
    bulk_save_calls: list[tuple[str, int]] = []
    insert_calls: list[tuple[str, int]] = []
    original_bulk_save = db_session.bulk_save_objects
    original_insert_rows = athena_retrieval._insert_retrieval_rows

    def count_bulk_save(objects, *args, **kwargs):
        object_list = list(objects)
        if object_list:
            bulk_save_calls.append((type(object_list[0]).__name__, len(object_list)))
        return original_bulk_save(object_list, *args, **kwargs)

    def count_insert_rows(db, model, rows):
        mapping_list = list(rows)
        if mapping_list:
            insert_calls.append((model.__name__, len(mapping_list)))
        return original_insert_rows(db, model, mapping_list)

    monkeypatch.setattr(db_session, "bulk_save_objects", count_bulk_save)
    monkeypatch.setattr(athena_retrieval, "_insert_retrieval_rows", count_insert_rows)

    result = reindex_project_retrieval(db_session, project.id)

    assert result["indexed"]["documents"] == 2
    assert ("RetrievalDocument", 2) in insert_calls
    assert ("RetrievalChunk", 2) in insert_calls
    assert ("RetrievalEmbedding", 2) in insert_calls
    assert sum(1 for class_name, _count in insert_calls if class_name == "RetrievalDocument") == 1
    assert sum(1 for class_name, _count in insert_calls if class_name == "RetrievalChunk") == 1
    assert sum(1 for class_name, _count in insert_calls if class_name == "RetrievalTerm") == 1
    assert sum(1 for class_name, _count in insert_calls if class_name == "RetrievalEmbedding") == 1
    assert not any(
        class_name in {"RetrievalDocument", "RetrievalChunk", "RetrievalEmbedding", "RetrievalTerm"}
        for class_name, _count in bulk_save_calls
    )


def test_reindex_uses_configured_write_batches_for_many_sources(db_session, monkeypatch):
    import app.core.athena_retrieval as athena_retrieval

    project = Project(name="Retrieval Batch Throughput")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    db_session.add_all(
        [
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章",
                content=f"第{index}章，星环钥匙线索推进。",
                word_count=20,
                status="generated",
            )
            for index in range(1, 251)
        ]
    )
    db_session.commit()
    document_insert_calls: list[int] = []
    original_insert_rows = athena_retrieval._insert_retrieval_rows

    def count_insert_rows(db, model, rows):
        mapping_list = list(rows)
        if model.__name__ == "RetrievalDocument":
            document_insert_calls.append(len(mapping_list))
        return original_insert_rows(db, model, mapping_list)

    monkeypatch.setattr(athena_retrieval, "_insert_retrieval_rows", count_insert_rows)

    result = reindex_project_retrieval(db_session, project.id)

    assert result["indexed"]["documents"] == 250
    expected_batches: list[int] = []
    remaining = 250
    while remaining > 0:
        batch_size = min(athena_retrieval.INDEX_WRITE_BATCH_SOURCES, remaining)
        expected_batches.append(batch_size)
        remaining -= batch_size
    assert document_insert_calls == expected_batches
    assert len(document_insert_calls) < 250
    assert sum(document_insert_calls) == 250


def test_reindex_streams_pending_sources_to_indexer(db_session, monkeypatch):
    import app.core.athena_retrieval as athena_retrieval

    project = Project(name="Retrieval Streaming")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    db_session.add_all(
        [
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章",
                content=f"第{index}章，星环钥匙线索推进。" * 200,
                word_count=2000,
                status="generated",
            )
            for index in range(1, 4)
        ]
    )
    db_session.commit()
    original_index_sources = athena_retrieval._index_sources
    received_is_list: list[bool] = []

    def assert_streaming_sources(db, project_id, sources):
        received_is_list.append(isinstance(sources, list))
        return original_index_sources(db, project_id, sources)

    monkeypatch.setattr(athena_retrieval, "_index_sources", assert_streaming_sources)

    result = reindex_project_retrieval(db_session, project.id)

    assert received_is_list == [False]
    assert result["indexed"]["documents"] == 3


def test_reindex_flushes_write_batch_when_term_rows_reach_guard(db_session, monkeypatch):
    import app.core.athena_retrieval as athena_retrieval

    project = Project(name="Retrieval Term Guard")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    sources = [
        RetrievalSource(
            source_type="chapter",
            source_id=f"chapter-{index}",
            source_ref=f"chapter:{index}",
            title=f"第{index}章",
            text=f"第{index}章 星环钥匙 潮汐灯塔 黑匣档案 记忆回潮。",
            chapter_index=index,
            profile_version=None,
            metadata={},
        )
        for index in range(1, 4)
    ]
    flush_document_counts: list[int] = []

    def capture_flush(_db, _provider, documents, chunks, terms, embeddings):
        if documents:
            flush_document_counts.append(len(documents))
        documents.clear()
        chunks.clear()
        terms.clear()
        embeddings.clear()

    monkeypatch.setattr(athena_retrieval, "INDEX_WRITE_BATCH_SOURCES", 999)
    monkeypatch.setattr(athena_retrieval, "INDEX_WRITE_BATCH_MAX_TERMS", 1)
    monkeypatch.setattr(athena_retrieval, "_flush_index_write_batch", capture_flush)

    result = _index_sources(db_session, project.id, sources)

    assert result["documents"] == 3
    assert result["terms"] > 0
    assert flush_document_counts == [1, 1, 1]


def test_reindex_does_not_generate_uuid_per_retrieval_term(db_session, monkeypatch):
    import app.core.athena_retrieval as athena_retrieval

    project = _seed_retrieval_project(db_session)
    original_uuid4 = athena_retrieval.uuid.uuid4
    uuid_call_count = {"value": 0}

    def count_uuid4():
        uuid_call_count["value"] += 1
        return original_uuid4()

    monkeypatch.setattr(athena_retrieval.uuid, "uuid4", count_uuid4)

    result = reindex_project_retrieval(db_session, project.id)

    expected_non_term_ids = (
        result["indexed"]["documents"]
        + result["indexed"]["chunks"]
        + result["indexed"]["embeddings"]
    )
    assert result["indexed"]["terms"] > 0
    assert uuid_call_count["value"] <= expected_non_term_ids


def test_search_retrieval_tokenizes_query_once(db_session, monkeypatch):
    import app.core.athena_retrieval as athena_retrieval

    project = Project(name="Search Query Token Reuse")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    db_session.add_all(
        [
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章",
                content=f"第{index}章，星环钥匙线索在旧灯塔推进。",
                word_count=40,
                status="generated",
            )
            for index in range(1, 16)
        ]
    )
    db_session.commit()
    reindex_project_retrieval(db_session, project.id)

    original_tokenize = athena_retrieval.tokenize_for_retrieval
    query_tokenize_count = {"value": 0}

    def count_query_tokenize(text: str):
        if text == "星环钥匙":
            query_tokenize_count["value"] += 1
        return original_tokenize(text)

    monkeypatch.setattr(athena_retrieval, "tokenize_for_retrieval", count_query_tokenize)

    result = search_retrieval(db_session, project.id, "星环钥匙", limit=6)

    assert result["items"]
    assert query_tokenize_count["value"] == 1


def test_search_candidate_rows_project_only_scoring_fields(db_session):
    project = _seed_retrieval_project(db_session)
    reindex_project_retrieval(db_session, project.id)
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        result = search_retrieval(db_session, project.id, "旧灯塔亡者召回", limit=3)
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert result["items"]
    candidate_selects = [
        statement.split("from retrieval_chunks", 1)[0]
        for statement in statements
        if statement.startswith("select")
        and "from retrieval_chunks" in statement
        and "join retrieval_documents" in statement
        and "join retrieval_embeddings" in statement
    ]
    assert candidate_selects
    excluded_columns = [
        "retrieval_chunks.token_count",
        "retrieval_chunks.start_offset",
        "retrieval_chunks.end_offset",
        "retrieval_chunks.chunk_metadata",
        "retrieval_chunks.created_at",
        "retrieval_documents.content_hash",
        "retrieval_documents.created_at",
        "retrieval_documents.updated_at",
        "retrieval_embeddings.provider",
        "retrieval_embeddings.model",
        "retrieval_embeddings.dimensions",
        "retrieval_embeddings.vector_hash",
        "retrieval_embeddings.created_at",
        "retrieval_embeddings.updated_at",
    ]
    for column in excluded_columns:
        assert all(column not in select_clause for select_clause in candidate_selects)


def test_search_retrieval_bounds_default_candidate_scoring_pool(db_session, monkeypatch):
    import app.core.athena_retrieval as athena_retrieval

    project = Project(name="Search Candidate Bound")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    db_session.add_all(
        [
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章",
                content=f"第{index}章，星环钥匙线索重复出现。",
                word_count=40,
                status="generated",
            )
            for index in range(1, 502)
        ]
    )
    db_session.commit()
    reindex_project_retrieval(db_session, project.id)
    score_calls = {"value": 0}
    original_lexical_score = athena_retrieval._lexical_score

    def count_lexical_score(*args, **kwargs):
        score_calls["value"] += 1
        return original_lexical_score(*args, **kwargs)

    monkeypatch.setattr(athena_retrieval, "_lexical_score", count_lexical_score)

    result = search_retrieval(db_session, project.id, "星环钥匙", limit=6)

    assert result["items"]
    assert score_calls["value"] <= 480


def test_reindex_batches_embedding_provider_calls_across_sources(db_session, monkeypatch):
    import app.core.athena_retrieval as athena_retrieval

    project = _seed_retrieval_project(db_session)
    base_provider = athena_retrieval.get_embedding_provider()

    class CountingEmbeddingProvider:
        provider_name = base_provider.provider_name
        model_name = base_provider.model_name
        dimensions = base_provider.dimensions

        def __init__(self):
            self.batch_sizes: list[int] = []

        def embed_texts(self, texts: list[str]) -> list[list[float]]:
            self.batch_sizes.append(len(texts))
            return base_provider.embed_texts(texts)

    provider = CountingEmbeddingProvider()
    monkeypatch.setattr(athena_retrieval, "get_embedding_provider", lambda: provider)

    result = reindex_project_retrieval(db_session, project.id)

    assert result["indexed"]["chunks"] == 2
    assert provider.batch_sizes == [2]


def test_reindex_caps_embedding_provider_batch_size(db_session, monkeypatch):
    import app.core.athena_retrieval as athena_retrieval

    project = Project(name="Embedding Batch Cap")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    db_session.add_all(
        [
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章",
                content=f"第{index}章，星环钥匙线索推进。",
                word_count=20,
                status="generated",
            )
            for index in range(1, 4)
        ]
    )
    db_session.commit()
    base_provider = athena_retrieval.get_embedding_provider()

    class CountingEmbeddingProvider:
        provider_name = base_provider.provider_name
        model_name = base_provider.model_name
        dimensions = base_provider.dimensions

        def __init__(self):
            self.batch_sizes: list[int] = []

        def embed_texts(self, texts: list[str]) -> list[list[float]]:
            self.batch_sizes.append(len(texts))
            return base_provider.embed_texts(texts)

    provider = CountingEmbeddingProvider()
    monkeypatch.setattr(athena_retrieval, "RETRIEVAL_EMBEDDING_BATCH_SIZE", 2)
    monkeypatch.setattr(athena_retrieval, "get_embedding_provider", lambda: provider)

    result = reindex_project_retrieval(db_session, project.id)

    assert result["indexed"]["chunks"] == 3
    assert provider.batch_sizes == [2, 1]


def test_reindex_reuses_token_batches_for_local_embedding_provider(db_session, monkeypatch):
    import app.core.athena_retrieval as athena_retrieval

    project = _seed_retrieval_project(db_session)

    class TokenBatchEmbeddingProvider:
        provider_name = "local"
        model_name = "token-batch-test"
        dimensions = 3

        def __init__(self):
            self.token_batch_sizes: list[int] = []

        def embed_texts(self, _texts: list[str]) -> list[list[float]]:
            raise AssertionError("local provider should receive token batches")

        def embed_token_batches(self, token_batches: list[list[str]]) -> list[list[float]]:
            self.token_batch_sizes.extend(len(tokens) for tokens in token_batches)
            return [[1.0, 0.0, 0.0] for _tokens in token_batches]

    provider = TokenBatchEmbeddingProvider()
    monkeypatch.setattr(athena_retrieval, "get_embedding_provider", lambda: provider)

    result = reindex_project_retrieval(db_session, project.id)

    assert result["indexed"]["chunks"] == 2
    assert len(provider.token_batch_sizes) == 2
    assert all(size > 0 for size in provider.token_batch_sizes)


def test_query_aware_results_skip_context_search_when_user_query_fills_limit(db_session, monkeypatch):
    import app.core.athena_retrieval as athena_retrieval

    queries: list[str] = []

    def fake_search_retrieval(_db, _project_id, query, *, limit, **_kwargs):
        queries.append(query)
        return {
            "items": [
                {"chunk_id": f"user:{index}", "snippet": f"用户查询结果 {index}"}
                for index in range(limit)
            ]
        }

    monkeypatch.setattr(athena_retrieval, "search_retrieval", fake_search_retrieval)

    items = athena_retrieval._query_aware_result_items(
        db_session,
        project_id="project-1",
        query="自动上下文查询",
        user_query="用户查询",
        limit=3,
        max_chapter_index=100,
    )

    assert queries == ["用户查询"]
    assert [item["chunk_id"] for item in items] == ["user:0", "user:1", "user:2"]


def test_search_retrieval_uses_lexical_shortlist_for_late_relevant_chunks(client, db_session):
    project = Project(name="Late Retrieval", genre="东方奇幻悬疑")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    db_session.add_all(
        [
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"无关章节 {index}",
                content=f"第{index}章只有普通街巷和潮声，没有目标线索。",
                word_count=20,
                status="generated",
            )
            for index in range(1, 421)
        ]
        + [
            ChapterContent(
                project_id=project.id,
                chapter_index=421,
                title="迟到的钥匙",
                content="档案最深处写着：秘银钥匙沉睡在旧灯塔底层，只有潮汐归零时才会苏醒。",
                word_count=32,
                status="generated",
            )
        ]
    )
    db_session.commit()

    response = client.post(f"/api/v1/projects/{project.id}/athena/retrieval/reindex")
    results = search_retrieval(db_session, project.id, "秘银钥匙沉睡旧灯塔", limit=3)

    assert response.status_code == 200
    assert response.json()["indexed"]["documents"] == 421
    assert any("秘银钥匙沉睡" in item["snippet"] for item in results["items"])


def test_chapter_context_includes_retrieved_evidence(client, db_session):
    project = _seed_retrieval_project(db_session)
    client.post(f"/api/v1/projects/{project.id}/athena/ontology/import-setup")
    _seed_confirmed_fact(db_session, project.id)
    client.post(f"/api/v1/projects/{project.id}/athena/retrieval/reindex")

    response = client.get(f"/api/v1/projects/{project.id}/athena/context/chapter/3")

    assert response.status_code == 200
    payload = response.json()
    retrieval_sections = [section for section in payload["sections"] if section["key"] == "retrieval"]
    assert retrieval_sections
    assert "【检索证据】" in payload["prompt_context"]
    assert "旧灯塔" in payload["prompt_context"]
    assert "亡者" in payload["prompt_context"]


def test_retrieval_diagnostics_and_single_chapter_index_endpoint(client, db_session):
    project = _seed_retrieval_project(db_session)

    response = client.post(f"/api/v1/projects/{project.id}/athena/retrieval/chapters/2/index")
    diagnostics = client.get(f"/api/v1/projects/{project.id}/athena/retrieval/diagnostics")

    assert response.status_code == 200
    assert response.json()["chapter_index"] == 2
    assert response.json()["indexed"]["documents"] == 1
    assert diagnostics.status_code == 200
    payload = diagnostics.json()
    assert payload["total_documents"] == 1
    assert payload["total_chunks"] >= 1
    assert payload["total_terms"] >= payload["total_chunks"]
    assert payload["embedding_provider"] == "local"


def test_approval_incrementally_indexes_world_fact_without_full_reindex(client, db_session):
    project = _seed_retrieval_project(db_session)
    client.post(f"/api/v1/projects/{project.id}/athena/ontology/import-setup")
    item = _write_reviewable_fact_candidate(db_session, project.id)

    review = review_proposal_item(
        db=db_session,
        proposal_item_id=item.id,
        reviewer_ref="tester",
        action="approve",
        reason="确认进入世界模型",
        evidence_refs=["chapter:2"],
    )

    documents = db_session.query(RetrievalDocument).filter_by(project_id=project.id, source_type="world_fact").all()
    search = search_retrieval(db_session, project.id, "雾港城守夜人", source_type="world_fact")

    assert review.created_truth_claim_id == "claim.linzhou.role.incremental"
    assert [document.source_ref for document in documents] == ["claim:claim.linzhou.role.incremental"]
    assert search["items"]
    assert "雾港城守夜人" in search["items"][0]["snippet"]


def test_rollback_removes_incremental_world_fact_retrieval_document(client, db_session):
    project = _seed_retrieval_project(db_session)
    client.post(f"/api/v1/projects/{project.id}/athena/ontology/import-setup")
    item = _write_reviewable_fact_candidate(db_session, project.id)
    approval = review_proposal_item(
        db=db_session,
        proposal_item_id=item.id,
        reviewer_ref="tester",
        action="approve",
        reason="先并入世界模型",
        evidence_refs=["chapter:2"],
    )
    assert db_session.query(RetrievalDocument).filter_by(project_id=project.id, source_type="world_fact").count() == 1

    rollback_review(
        db=db_session,
        review_id=approval.id,
        reviewer_ref="tester",
        reason="证据撤回",
        evidence_refs=["chapter:3"],
    )

    assert db_session.query(RetrievalDocument).filter_by(project_id=project.id, source_type="world_fact").count() == 0
