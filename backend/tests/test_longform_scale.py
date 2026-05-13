import importlib.util
from pathlib import Path

from app.api import dialogs
from app.models import ChapterContent, Dialog, LongformMemory, Project


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


def test_longform_scale_smoke_cli_exposes_main():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "longform_scale_smoke.py"
    spec = importlib.util.spec_from_file_location("longform_scale_smoke_cli", script_path)

    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert callable(module.main)
