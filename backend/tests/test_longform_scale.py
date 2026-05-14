import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import event, text

from app.api import dialogs
from app.models import ChapterContent, Dialog, LongformMemory, Outline, Project, RetrievalDocument


def test_longform_hot_tables_have_query_indexes(db_session):
    expected_indexes = {
        "chapter_contents": {
            "ix_chapter_contents_project_chapter",
            "ix_chapter_contents_project_status",
        },
        "dialog_messages": {
            "ix_dialog_messages_dialog_type_created",
            "ix_dialog_messages_dialog_action_created",
        },
        "versions": {
            "ix_versions_project_node_created",
            "ix_versions_project_node_version",
        },
        "background_tasks": {
            "ix_background_tasks_project_created",
            "ix_background_tasks_status",
        },
        "consistency_checks": {
            "ix_consistency_checks_project_chapter",
            "ix_consistency_checks_project_status",
        },
    }
    for table_name, index_names in expected_indexes.items():
        rows = db_session.execute(text(f"PRAGMA index_list('{table_name}')")).fetchall()
        actual_names = {row[1] for row in rows}
        assert index_names <= actual_names

    partial_index_sql = db_session.execute(
        text(
            "SELECT sql FROM sqlite_master "
            "WHERE type = 'index' AND name = 'ix_dialog_messages_dialog_action_created'"
        )
    ).scalar_one()
    assert "where action_result is not null" in partial_index_sql.lower()


def test_get_project_reconciles_current_word_count_from_chapters(client, db_session):
    project = Project(name="Longform Stats", current_word_count=1)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    db_session.add_all(
        [
            ChapterContent(
                project_id=project.id,
                chapter_index=1,
                title="一",
                content="正文一",
                word_count=1200,
                status="generated",
            ),
            ChapterContent(
                project_id=project.id,
                chapter_index=2,
                title="二",
                content="正文二",
                word_count=1300,
                status="generated",
            ),
        ]
    )
    db_session.commit()

    response = client.get(f"/api/v1/projects/{project.id}")

    assert response.status_code == 200
    assert response.json()["current_word_count"] == 2500
    db_session.refresh(project)
    assert project.current_word_count == 2500


def test_longform_memory_model_supports_scope_layers(db_session):
    project = Project(name="Memory Model")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    memory = LongformMemory(
        project_id=project.id,
        memory_type="arc",
        scope_key="arc:1-20",
        start_chapter_index=1,
        end_chapter_index=20,
        title="第一剧情弧",
        summary="主角进入核心冲突。",
        status="current",
        memory_metadata={"chapter_count": 20},
    )
    db_session.add(memory)
    db_session.commit()

    row = db_session.query(LongformMemory).filter_by(project_id=project.id, scope_key="arc:1-20").one()
    assert row.memory_type == "arc"
    assert row.memory_metadata["chapter_count"] == 20


def test_rebuild_longform_memory_creates_chapter_arc_volume_and_global_layers(client, db_session):
    project = Project(name="Hundred Chapter Memory")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    for index in range(1, 101):
        db_session.add(
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章",
                content=f"第{index}章正文。主角推进第{(index - 1) // 20 + 1}段剧情。" * 8,
                word_count=1000 + index,
                status="generated",
            )
        )
    db_session.commit()

    response = client.post(f"/api/v1/projects/{project.id}/athena/longform/memory/rebuild")
    diagnostics = client.get(f"/api/v1/projects/{project.id}/athena/longform/memory/diagnostics")

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["counts_by_type"] == {"chapter": 100, "arc": 5, "volume": 1, "global": 1}
    assert diagnostics.status_code == 200
    assert diagnostics.json()["counts_by_type"]["chapter"] == 100
    assert diagnostics.json()["current_word_count"] == sum(1000 + index for index in range(1, 101))


def test_chapter_memory_prefers_generated_content_over_stale_outline_summary(db_session):
    from app.core.longform_memory import rebuild_longform_memory

    project = Project(name="Memory Source Priority")
    db_session.add(project)
    db_session.flush()
    outline = Outline(
        project_id=project.id,
        status="generated",
        total_chapters=1,
        chapters=[
            {
                "chapter_index": 1,
                "title": "第一章",
                "summary": "旧大纲只提到普通线索。",
            }
        ],
    )
    chapter = ChapterContent(
        project_id=project.id,
        chapter_index=1,
        title="第一章",
        content="真实正文。星环钥匙第八形态在灯塔底层启动。",
        word_count=1000,
        status="generated",
    )
    db_session.add_all([outline, chapter])
    db_session.commit()

    rebuild_longform_memory(db_session, project.id)

    memory = (
        db_session.query(LongformMemory)
        .filter(LongformMemory.project_id == project.id, LongformMemory.scope_key == "chapter:1")
        .one()
    )
    assert "星环钥匙第八形态" in memory.summary
    assert "旧大纲" not in memory.summary
    assert memory.memory_metadata["source"] == "chapter_content"


def test_rebuild_longform_memory_projects_only_memory_fields(db_session):
    from app.core.longform_memory import rebuild_longform_memory

    project = Project(name="Memory Projection")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    for index in range(1, 26):
        db_session.add(
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章",
                content="记忆重建需要正文，但不需要生成元数据。",
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
        result = rebuild_longform_memory(db_session, project.id)
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert result["counts_by_type"] == {"chapter": 25, "arc": 2, "volume": 1, "global": 1}
    chapter_select_clauses = [
        statement.split("from chapter_contents", 1)[0]
        for statement in statements
        if "from chapter_contents" in statement
    ]
    assert chapter_select_clauses
    for column in [
        "model",
        "prompt_tokens",
        "completion_tokens",
        "generation_time",
        "temperature",
        "created_at",
        "updated_at",
    ]:
        assert all(f"chapter_contents.{column}" not in clause for clause in chapter_select_clauses)


def test_longform_context_for_chapter_excludes_future_chapters(client, db_session):
    project = Project(name="Future Boundary")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    for index in range(1, 8):
        db_session.add(
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章",
                content=f"第{index}章正文。{'未来秘密只在第7章揭露。' if index == 7 else '普通线索。'}",
                word_count=1000,
                status="generated",
            )
        )
    db_session.commit()
    client.post(f"/api/v1/projects/{project.id}/athena/longform/memory/rebuild")

    response = client.get(f"/api/v1/projects/{project.id}/athena/longform/context/chapters/5")

    assert response.status_code == 200
    payload = response.json()
    assert payload["chapter_index"] == 5
    assert "第4章" in payload["prompt_context"]
    assert "第7章" not in payload["prompt_context"]
    assert "未来秘密" not in payload["prompt_context"]
    assert all(
        item.get("end_chapter_index") is None or item["end_chapter_index"] <= 5
        for section in payload["sections"]
        for item in section["items"]
    )


def test_longform_context_package_rollups_do_not_load_all_memory_rows(db_session):
    from app.core.longform_memory import build_longform_context_package, rebuild_longform_memory

    project = Project(name="Context Rollup Projection")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    for index in range(1, 121):
        db_session.add(
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章",
                content=f"第{index}章正文。星环钥匙推进。",
                word_count=1000 + index,
                status="generated",
            )
        )
    db_session.commit()
    rebuild_longform_memory(db_session, project.id)
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        payload = build_longform_context_package(db_session, project.id, 120)
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    section_keys = [section["key"] for section in payload["sections"]]
    assert "global" in section_keys
    assert "volume" in section_keys
    assert "arc" in section_keys
    full_memory_selects = [
        statement
        for statement in statements
        if "select longform_memories.id" in statement
        and "from longform_memories" in statement
        and "order by longform_memories.start_chapter_index asc" in statement
        and "limit" not in statement
    ]
    assert full_memory_selects == []


def test_longform_context_rollups_include_recent_memory_summaries(db_session):
    from app.core.longform_memory import build_longform_context_package, rebuild_longform_memory

    project = Project(name="Context Rollup Summary")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    for index in range(1, 121):
        detail = "普通推进。"
        if index == 120:
            detail = "星环钥匙第九形态在塔底亮起，陆辞确认记忆潮汐进入终局。"
        db_session.add(
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章",
                content=f"第{index}章正文。{detail}",
                word_count=1000,
                status="generated",
            )
        )
    db_session.commit()
    rebuild_longform_memory(db_session, project.id)

    payload = build_longform_context_package(db_session, project.id, 120)

    rollup_summaries = {
        section["key"]: section["items"][0]["summary"]
        for section in payload["sections"]
        if section["key"] in {"global", "volume", "arc"}
    }
    assert rollup_summaries.keys() == {"global", "volume", "arc"}
    assert all("星环钥匙第九形态" in summary for summary in rollup_summaries.values())


def test_reindex_includes_longform_memory_sources(client, db_session):
    project = Project(name="Longform Retrieval Sources")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    for index in range(1, 41):
        db_session.add(
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章",
                content=f"第{index}章正文。记忆索引线索。",
                word_count=1000,
                status="generated",
            )
        )
    db_session.commit()
    client.post(f"/api/v1/projects/{project.id}/athena/longform/memory/rebuild")

    response = client.post(f"/api/v1/projects/{project.id}/athena/retrieval/reindex")
    diagnostics = client.get(f"/api/v1/projects/{project.id}/athena/retrieval/diagnostics")

    assert response.status_code == 200
    assert diagnostics.status_code == 200
    assert diagnostics.json()["documents_by_source_type"]["longform_memory"] > 0


def test_query_aware_context_uses_user_query_and_explains_sources(client, db_session):
    project = Project(name="Query Aware Context")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    for index in range(1, 36):
        content = "普通支线。"
        if index == 4:
            content = "秘银钥匙第一次出现，被林舟藏进旧灯塔底层。"
        if index == 35:
            content = "第35章目标章节，主角将调查钥匙后果。"
        db_session.add(
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章",
                content=content,
                word_count=1000,
                status="generated",
            )
        )
    db_session.commit()
    client.post(f"/api/v1/projects/{project.id}/athena/longform/memory/rebuild")
    client.post(f"/api/v1/projects/{project.id}/athena/retrieval/reindex")

    response = client.get(f"/api/v1/projects/{project.id}/athena/longform/context/chapters/35?q=秘银钥匙")

    assert response.status_code == 200
    payload = response.json()
    retrieval_sections = [
        section for section in payload["sections"]
        if section["key"] == "query_aware_retrieval"
    ]
    assert retrieval_sections
    retrieval_items = retrieval_sections[0]["items"]
    assert any("秘银钥匙" in item["snippet"] for item in retrieval_items)
    assert all(item.get("chapter_index") is None or item["chapter_index"] <= 34 for item in retrieval_items)
    assert all(item["metadata"]["explanation"]["reason"] for item in retrieval_items)
    assert "检索依据" in payload["prompt_context"]


def test_dialog_payloads_include_longform_evidence_range_block(db_session):
    project = Project(name="Dialog Evidence Range", current_word_count=1)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    for index in range(1, 6):
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
    athena_dialog = Dialog(project_id=project.id, dialog_type="athena")
    hermes_dialog = Dialog(project_id=project.id, dialog_type="hermes")
    db_session.add_all([athena_dialog, hermes_dialog])
    db_session.commit()
    from app.core.longform_memory import rebuild_longform_memory

    rebuild_longform_memory(db_session, project.id)

    diagnosis = dialogs._build_diagnosis(db_session, project.id)
    athena_payload = dialogs._build_chat_call_payload(
        db_session,
        athena_dialog.id,
        project,
        diagnosis,
        dialog_type="athena",
    )
    hermes_payload = dialogs._build_chat_call_payload(
        db_session,
        hermes_dialog.id,
        project,
        diagnosis,
        dialog_type="hermes",
    )

    for payload in [athena_payload, hermes_payload]:
        block = next(
            block for block in payload["context_blocks"]
            if block["kind"] == "longform_evidence_range"
        )
        assert "当前总字数：5000" in block["content"]
        assert "chapter: 5" in block["content"]
        assert "global: 1" in block["content"]


def test_longform_scale_smoke_reports_memory_retrieval_and_resume_progress(db_session):
    from app.core.longform_scale_smoke import run_longform_scale_smoke

    report = run_longform_scale_smoke(
        db_session,
        chapter_count=120,
        words_per_chapter=1000,
        target_chapter_index=120,
        query="星环钥匙",
    )

    assert report["chapter_count"] == 120
    assert report["target_chapter_index"] == 120
    assert report["total_words"] == 120000
    assert report["memory"]["counts_by_type"] == {"chapter": 120, "arc": 6, "volume": 2, "global": 1}
    assert report["retrieval"]["documents_by_source_type"]["chapter"] == 120
    assert report["retrieval"]["documents_by_source_type"]["longform_memory"] == 129
    assert "query_aware_retrieval" in report["context"]["section_keys"]
    assert report["task"]["status"] == "completed"
    assert report["task"]["progress"]["completed_count"] == 120
    assert report["task"]["progress"]["last_completed_chapter_index"] == 120
    assert report["task"]["progress"]["can_resume"] is False
    assert "completed_chapter_indexes" not in report["task"]["progress"]


def test_longform_scale_smoke_reports_stage_timings(db_session):
    from app.core.longform_scale_smoke import run_longform_scale_smoke

    report = run_longform_scale_smoke(
        db_session,
        chapter_count=5,
        words_per_chapter=200,
        target_chapter_index=5,
        query="星环钥匙",
    )

    assert set(report["timings_ms"]) == {
        "seed_project",
        "task_progress",
        "memory_rebuild",
        "retrieval_reindex",
        "context_build",
        "task_complete",
    }
    assert all(isinstance(value, int) and value >= 0 for value in report["timings_ms"].values())
    assert sum(report["timings_ms"].values()) <= report["elapsed_ms"]


def test_longform_scale_smoke_compacts_checkpoint_progress_fields():
    from app.core.longform_scale_smoke import _compact_progress

    progress = {
        "chapter_range": {"start": 1, "end": 1000},
        "next_chapter_index": 1001,
        "completed_count": 1000,
        "total_count": 1000,
        "can_resume": False,
        "completed_until_chapter_index": 1000,
        "first_completed_chapter_index": 1,
        "last_completed_chapter_index": 1000,
    }

    compact = _compact_progress(progress)

    assert compact["completed_until_chapter_index"] == 1000
    assert compact["first_completed_chapter_index"] == 1
    assert compact["last_completed_chapter_index"] == 1000
    assert compact["checkpoint_count"] == 0
    assert "completed_chapter_indexes" not in compact


def test_longform_scale_smoke_uses_batched_task_progress(db_session, monkeypatch):
    from app.core.longform_scale_smoke import run_longform_scale_smoke
    from app.services.tasks.background_task_service import BackgroundTaskService

    batch_calls: list[list[int]] = []
    original_many = BackgroundTaskService.mark_range_progress_many

    def count_many(self, task_id, *, completed_chapter_indexes):
        indexes = list(completed_chapter_indexes)
        batch_calls.append(indexes)
        return original_many(self, task_id, completed_chapter_indexes=indexes)

    def fail_single(*_args, **_kwargs):
        raise AssertionError("longform smoke should batch range progress")

    monkeypatch.setattr(BackgroundTaskService, "mark_range_progress_many", count_many)
    monkeypatch.setattr(BackgroundTaskService, "mark_range_progress", fail_single)

    report = run_longform_scale_smoke(
        db_session,
        chapter_count=3,
        words_per_chapter=80,
        target_chapter_index=3,
    )

    assert batch_calls == [[1, 2, 3]]
    assert report["task"]["progress"]["completed_count"] == 3
    assert report["task"]["progress"]["checkpoint_count"] == 3


def test_longform_scale_smoke_cli_exposes_main():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "longform_scale_smoke.py"
    spec = importlib.util.spec_from_file_location("longform_scale_smoke_cli", script_path)

    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert callable(module.main)


def test_longform_scale_smoke_cli_fails_when_thresholds_are_exceeded(monkeypatch, capsys):
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "longform_scale_smoke.py"
    spec = importlib.util.spec_from_file_location("longform_scale_smoke_cli", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def fake_run_smoke_report(_args):
        return {
            "elapsed_ms": 1200,
            "timings_ms": {
                "retrieval_reindex": 900,
                "context_build": 150,
            },
        }

    monkeypatch.setattr(module, "_run_smoke_report", fake_run_smoke_report, raising=False)

    exit_code = module.main(
        [
            "--chapters",
            "1000",
            "--max-elapsed-ms",
            "1000",
            "--max-stage-ms",
            "retrieval_reindex=800",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "elapsed_ms 1200 exceeded max 1000" in captured.err
    assert "retrieval_reindex 900 exceeded max 800" in captured.err


def test_longform_scale_smoke_cli_rejects_invalid_stage_threshold_before_running(monkeypatch):
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "longform_scale_smoke.py"
    spec = importlib.util.spec_from_file_location("longform_scale_smoke_cli", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def fail_if_run(_args):
        raise AssertionError("smoke should not run when threshold args are invalid")

    monkeypatch.setattr(module, "_run_smoke_report", fail_if_run, raising=False)

    with pytest.raises(SystemExit):
        module.main(["--max-stage-ms", "retrieval_reindex"])


def test_longform_scale_smoke_cli_cleans_up_generated_project(monkeypatch):
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "longform_scale_smoke.py"
    spec = importlib.util.spec_from_file_location("longform_scale_smoke_cli", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cleaned_project_ids: list[str] = []

    monkeypatch.setattr(
        module,
        "_run_smoke_report",
        lambda _args: {"project_id": "project-smoke-1", "elapsed_ms": 10, "timings_ms": {}},
        raising=False,
    )
    monkeypatch.setattr(module, "_cleanup_smoke_project", cleaned_project_ids.append, raising=False)

    exit_code = module.main(["--cleanup"])

    assert exit_code == 0
    assert cleaned_project_ids == ["project-smoke-1"]


def test_refresh_longform_memory_for_chapter_updates_only_affected_scopes(db_session):
    from app.core.longform_memory import rebuild_longform_memory, refresh_longform_memory_for_chapter

    project = Project(name="Incremental Memory Refresh")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    for index in range(1, 121):
        db_session.add(
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章",
                content=f"第{index}章正文。星环钥匙维持第一形态。",
                word_count=1000,
                status="generated",
            )
        )
    db_session.commit()
    rebuild_longform_memory(db_session, project.id)

    tracked_scopes = ["chapter:44", "chapter:45", "arc:41-60", "volume:1-100", "global"]
    before = {
        memory.scope_key: memory.id
        for memory in db_session.query(LongformMemory)
        .filter(LongformMemory.project_id == project.id, LongformMemory.scope_key.in_(tracked_scopes))
        .all()
    }
    chapter = (
        db_session.query(ChapterContent)
        .filter(ChapterContent.project_id == project.id, ChapterContent.chapter_index == 45)
        .one()
    )
    chapter.content = "星环钥匙第二形态在本章显现，陆辞确认潮汐钟被改写。"
    chapter.word_count = 1500
    db_session.commit()

    result = refresh_longform_memory_for_chapter(db_session, project.id, 45)

    assert sorted(result["updated_scope_keys"]) == ["arc:41-60", "chapter:45", "global", "volume:1-100"]
    assert result["counts_by_type"] == {"chapter": 120, "arc": 6, "volume": 2, "global": 1}
    assert result["current_word_count"] == 120500
    after = {
        memory.scope_key: memory
        for memory in db_session.query(LongformMemory)
        .filter(LongformMemory.project_id == project.id, LongformMemory.scope_key.in_(tracked_scopes))
        .all()
    }
    assert after["chapter:44"].id == before["chapter:44"]
    for scope_key in ["chapter:45", "arc:41-60", "volume:1-100", "global"]:
        assert after[scope_key].id != before[scope_key]
    assert "星环钥匙第二形态" in after["chapter:45"].summary
    db_session.refresh(project)
    assert project.current_word_count == 120500


def test_refresh_longform_memory_for_chapter_avoids_full_content_scan(db_session):
    from app.core.longform_memory import rebuild_longform_memory, refresh_longform_memory_for_chapter

    project = Project(name="Incremental Refresh Projection")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    for index in range(1, 121):
        db_session.add(
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章",
                content="单章刷新不应重新读取全书正文。" * 100,
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
    rebuild_longform_memory(db_session, project.id)
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement.lower())

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        result = refresh_longform_memory_for_chapter(db_session, project.id, 45)
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert sorted(result["updated_scope_keys"]) == ["arc:41-60", "chapter:45", "global", "volume:1-100"]
    chapter_select_clauses = [
        statement.split("from chapter_contents", 1)[0]
        for statement in statements
        if "from chapter_contents" in statement
    ]
    assert chapter_select_clauses
    content_select_clauses = [
        clause for clause in chapter_select_clauses
        if "chapter_contents.content" in clause
    ]
    assert len(content_select_clauses) == 1
    for column in [
        "model",
        "prompt_tokens",
        "completion_tokens",
        "generation_time",
        "temperature",
        "created_at",
        "updated_at",
    ]:
        assert all(f"chapter_contents.{column}" not in clause for clause in chapter_select_clauses)


def test_sync_changed_longform_memory_retrieval_documents_preserves_unrelated_docs(db_session):
    from app.core.athena_retrieval import (
        reindex_project_retrieval,
        search_retrieval,
        sync_longform_memory_retrieval_documents,
    )
    from app.core.longform_memory import rebuild_longform_memory, refresh_longform_memory_for_chapter

    project = Project(name="Incremental Retrieval Sync")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    for index in range(1, 81):
        db_session.add(
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章",
                content=f"第{index}章正文。星环钥匙维持第一形态。",
                word_count=1000,
                status="generated",
            )
        )
    db_session.commit()
    rebuild_longform_memory(db_session, project.id)
    reindex_project_retrieval(db_session, project.id)
    chapter_44_doc_id = _longform_memory_doc_id(db_session, project.id, "memory:chapter:44")
    chapter_45_doc_id = _longform_memory_doc_id(db_session, project.id, "memory:chapter:45")

    chapter = (
        db_session.query(ChapterContent)
        .filter(ChapterContent.project_id == project.id, ChapterContent.chapter_index == 45)
        .one()
    )
    chapter.content = "星环钥匙第二形态启动，灯塔区潮汐钟出现反向刻度。"
    db_session.commit()
    refresh_result = refresh_longform_memory_for_chapter(db_session, project.id, 45)

    sync_result = sync_longform_memory_retrieval_documents(
        db_session,
        project.id,
        refresh_result["updated_memory_ids"],
    )

    assert sorted(sync_result["synced_scope_keys"]) == ["arc:41-60", "chapter:45", "global", "volume:1-80"]
    assert _longform_memory_doc_id(db_session, project.id, "memory:chapter:44") == chapter_44_doc_id
    assert _longform_memory_doc_id(db_session, project.id, "memory:chapter:45") != chapter_45_doc_id
    results = search_retrieval(
        db_session,
        project.id,
        "星环钥匙第二形态",
        source_type="longform_memory",
        max_chapter_index=80,
    )
    assert any(
        item["source_ref"] == "memory:chapter:45" and "星环钥匙第二形态" in item["snippet"]
        for item in results["items"]
    )


def test_sync_longform_memory_retrieval_documents_deletes_old_docs_in_bulk(db_session):
    from app.core.athena_retrieval import reindex_project_retrieval, sync_longform_memory_retrieval_documents
    from app.core.longform_memory import rebuild_longform_memory

    project = Project(name="Bulk Memory Retrieval Sync")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    for index in range(1, 31):
        db_session.add(
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章",
                content=f"第{index}章正文。星环钥匙批量同步。",
                word_count=1000,
                status="generated",
            )
        )
    db_session.commit()
    rebuild_longform_memory(db_session, project.id)
    reindex_project_retrieval(db_session, project.id)
    memory_ids = [
        row[0]
        for row in (
            db_session.query(LongformMemory.id)
            .filter(LongformMemory.project_id == project.id)
            .order_by(LongformMemory.scope_key.asc())
            .limit(12)
            .all()
        )
    ]
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        result = sync_longform_memory_retrieval_documents(db_session, project.id, memory_ids)
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert len(result["synced_scope_keys"]) == len(memory_ids)
    per_ref_selects = [
        statement
        for statement in statements
        if "from retrieval_documents" in statement and "retrieval_documents.source_ref = ?" in statement
    ]
    assert per_ref_selects == []


def _longform_memory_doc_id(db_session, project_id: str, source_ref: str) -> str:
    return (
        db_session.query(RetrievalDocument.id)
        .filter(
            RetrievalDocument.project_id == project_id,
            RetrievalDocument.source_type == "longform_memory",
            RetrievalDocument.source_ref == source_ref,
        )
        .scalar()
    )


def test_longform_maintenance_diagnostics_does_not_select_chapter_content(db_session):
    from app.core.longform_memory import get_longform_maintenance_diagnostics

    project = Project(name="Maintenance Projection")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    for index in range(1, 6):
        db_session.add(
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章",
                content="诊断不应选择的大段正文。" * 1000,
                word_count=1000,
                status="generated",
            )
        )
    db_session.commit()
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement.lower())

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        payload = get_longform_maintenance_diagnostics(db_session, project.id)
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert payload["chapter_count"] == 5
    chapter_select_clauses = [
        statement.split("from chapter_contents", 1)[0]
        for statement in statements
        if "from chapter_contents" in statement
    ]
    assert chapter_select_clauses
    assert all("chapter_contents.content" not in clause for clause in chapter_select_clauses)


def test_longform_maintenance_diagnostics_projects_memory_and_retrieval_columns(db_session):
    from app.core.athena_retrieval import reindex_project_retrieval
    from app.core.longform_memory import get_longform_maintenance_diagnostics, rebuild_longform_memory

    project = Project(name="Maintenance Projection Narrow")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    for index in range(1, 4):
        db_session.add(
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章",
                content="诊断不应读取宽字段。" * 100,
                word_count=1000,
                status="generated",
            )
        )
    db_session.commit()
    rebuild_longform_memory(db_session, project.id)
    reindex_project_retrieval(db_session, project.id)
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement.lower())

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        payload = get_longform_maintenance_diagnostics(db_session, project.id)
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert payload["status"] == "current"
    memory_select_clauses = [
        statement.split("from longform_memories", 1)[0]
        for statement in statements
        if "from longform_memories" in statement
    ]
    retrieval_select_clauses = [
        statement.split("from retrieval_documents", 1)[0]
        for statement in statements
        if "from retrieval_documents" in statement
    ]
    assert memory_select_clauses
    assert retrieval_select_clauses
    for column in ["title", "summary", "memory_metadata", "created_at", "start_chapter_index", "end_chapter_index"]:
        assert all(f"longform_memories.{column}" not in clause for clause in memory_select_clauses)
    for column in ["title", "content_hash", "document_metadata", "created_at", "chapter_index", "profile_version"]:
        assert all(f"retrieval_documents.{column}" not in clause for clause in retrieval_select_clauses)


def test_longform_maintenance_diagnostics_reports_stale_memory_after_chapter_edit(client, db_session):
    from app.core.longform_memory import rebuild_longform_memory

    project = Project(name="Maintenance Diagnostics")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    for index in range(1, 4):
        db_session.add(
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章",
                content=f"第{index}章正文。星环钥匙第一形态。",
                word_count=1000,
                status="generated",
            )
        )
    db_session.commit()
    rebuild_longform_memory(db_session, project.id)
    chapter = (
        db_session.query(ChapterContent)
        .filter(ChapterContent.project_id == project.id, ChapterContent.chapter_index == 2)
        .one()
    )
    chapter.content = "第2章正文已编辑。星环钥匙第六形态。"
    chapter.word_count = 1200
    db_session.commit()

    response = client.get(f"/api/v1/projects/{project.id}/athena/longform/maintenance/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "stale"
    assert payload["chapter_count"] == 3
    assert payload["stale_memory_count"] == 1
    assert payload["stale_chapter_indexes"] == [2]
    assert payload["missing_memory_chapter_indexes"] == []


def test_longform_maintenance_diagnostics_reports_stale_retrieval_after_memory_refresh(client, db_session):
    from app.core.athena_retrieval import reindex_project_retrieval
    from app.core.longform_memory import rebuild_longform_memory, refresh_longform_memory_for_chapter

    project = Project(name="Maintenance Retrieval Diagnostics")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    for index in range(1, 4):
        db_session.add(
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章",
                content=f"第{index}章正文。星环钥匙第一形态。",
                word_count=1000,
                status="generated",
            )
        )
    db_session.commit()
    rebuild_longform_memory(db_session, project.id)
    reindex_project_retrieval(db_session, project.id)
    chapter = (
        db_session.query(ChapterContent)
        .filter(ChapterContent.project_id == project.id, ChapterContent.chapter_index == 2)
        .one()
    )
    chapter.content = "第2章正文已编辑。星环钥匙第七形态。"
    db_session.commit()
    refresh_longform_memory_for_chapter(db_session, project.id, 2)

    response = client.get(f"/api/v1/projects/{project.id}/athena/longform/maintenance/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "stale"
    assert payload["stale_memory_count"] == 0
    assert payload["stale_retrieval_count"] == 1
    assert payload["stale_retrieval_chapter_indexes"] == [2]
    assert payload["latest_synced_chapter_index"] == 3


def test_longform_maintenance_repair_refreshes_memory_and_retrieval(client, db_session):
    from app.core.athena_retrieval import reindex_project_retrieval
    from app.core.longform_memory import rebuild_longform_memory

    project = Project(name="Maintenance Repair")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    for index in range(1, 4):
        db_session.add(
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章",
                content=f"第{index}章正文。星环钥匙第一形态。",
                word_count=1000,
                status="generated",
            )
        )
    db_session.commit()
    rebuild_longform_memory(db_session, project.id)
    reindex_project_retrieval(db_session, project.id)
    chapter = (
        db_session.query(ChapterContent)
        .filter(ChapterContent.project_id == project.id, ChapterContent.chapter_index == 2)
        .one()
    )
    chapter.content = "第2章正文已编辑。星环钥匙最终形态。"
    chapter.word_count = 1200
    db_session.commit()
    before = client.get(f"/api/v1/projects/{project.id}/athena/longform/maintenance/diagnostics").json()
    assert before["status"] == "stale"

    response = client.post(f"/api/v1/projects/{project.id}/athena/longform/maintenance/repair")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["refreshed_chapter_indexes"] == [2]
    assert "chapter:2" in payload["synced_scope_keys"]
    assert payload["remaining"]["status"] == "current"
    assert payload["remaining"]["stale_memory_count"] == 0
    assert payload["remaining"]["stale_retrieval_count"] == 0
    after = client.get(f"/api/v1/projects/{project.id}/athena/longform/maintenance/diagnostics").json()
    assert after["status"] == "current"


def test_longform_maintenance_repair_batches_large_backlog(client, db_session):
    project = Project(name="Maintenance Repair Batch")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    for index in range(1, 6):
        db_session.add(
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章",
                content=f"第{index}章正文。星环钥匙第一形态。",
                word_count=1000,
                status="generated",
            )
        )
    db_session.commit()

    response = client.post(f"/api/v1/projects/{project.id}/athena/longform/maintenance/repair?repair_limit=2")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["repaired_memory_count"] == 2
    assert payload["refreshed_chapter_indexes"] == [1, 2]
    assert payload["has_more"] is True
    assert payload["remaining_issue_count"] > 0
    assert payload["remaining"]["status"] == "stale"
    assert payload["remaining"]["missing_memory_count"] == 3
    assert "chapter:1" in payload["synced_scope_keys"]
    assert "chapter:2" in payload["synced_scope_keys"]

    second_response = client.post(f"/api/v1/projects/{project.id}/athena/longform/maintenance/repair?repair_limit=10")

    assert second_response.status_code == 200
    second_payload = second_response.json()
    assert second_payload["has_more"] is False
    assert second_payload["remaining_issue_count"] == 0
    assert second_payload["remaining"]["status"] == "current"


def test_longform_maintenance_repair_batches_large_missing_memory_backlog(db_session, monkeypatch):
    import app.core.longform_memory as longform_memory

    project = Project(name="Maintenance Repair Large Missing Backlog")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    for index in range(1, 61):
        db_session.add(
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章",
                content=f"第{index}章正文。星环钥匙第一形态。",
                word_count=1000,
                status="generated",
            )
        )
    db_session.commit()

    def fail_full_rebuild(*_args, **_kwargs):
        raise AssertionError("large missing backlog should be repaired in bounded batches")

    monkeypatch.setattr(longform_memory, "rebuild_longform_memory", fail_full_rebuild)

    result = longform_memory.repair_longform_maintenance(db_session, project.id, repair_limit=10)

    assert result["repaired_memory_count"] == 10
    assert result["refreshed_chapter_indexes"] == list(range(1, 11))
    assert result["has_more"] is True
    assert result["remaining_issue_count"] > 0
    assert result["remaining"]["status"] == "stale"
    assert result["remaining"]["missing_memory_count"] == 50
    assert result["remaining"]["missing_retrieval_count"] == 50
    for chapter_index in range(1, 11):
        assert f"chapter:{chapter_index}" in result["synced_scope_keys"]
