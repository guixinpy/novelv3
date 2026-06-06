import json

from app.models import AIModelCallTrace, ChapterContent, ChapterRevision, LongformMemory, Version
from test_support.writing_agent_run_helpers import (
    approved_compress_chapter_to_target_tool,
    approved_expand_chapter_to_target_tool,
    seed_longform_project,
)


def test_agent_expand_chapter_to_target_updates_chapter_versions_and_requires_review(client, db_session, monkeypatch):
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "苏晚晴的梦境"
    chapter.content = "短章。" * 300
    chapter.word_count = 600
    project.current_word_count = 600
    db_session.commit()

    expanded_content = "林深和苏晚晴在门外压低声音，顺着雾气复盘证词。" * 100

    class FakeAIResult:
        content = json.dumps({"content": expanded_content, "change_summary": "补足场景密度。"}, ensure_ascii=False)
        prompt_tokens = 111
        completion_tokens = 222
        model = "fake-deepseek"

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            assert "不要新增世界模型事实" in messages[-1]["content"]
            return FakeAIResult()

    monkeypatch.setattr("app.core.chapter_expansion.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "扩写第1章到目标字数",
            "tools": [approved_expand_chapter_to_target_tool(db_session, project.id, chapter_index=1)],
        },
    )

    output = response.json()["steps"][0]["output"]
    patched = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    revision = db_session.query(ChapterRevision).filter_by(id=output["revision_id"]).one()
    versions = db_session.query(Version).filter_by(project_id=project.id, node_type="chapter", node_id=chapter.id).all()
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "completed"
    assert output["previous_word_count"] == 600
    assert output["word_count"] >= 2000
    assert patched.content == expanded_content
    assert patched.word_count >= 2000
    db_session.refresh(project)
    assert project.current_word_count == patched.word_count
    assert revision.status == "completed"
    assert revision.base_version_id
    assert revision.result_version_id
    assert len(versions) == 2
    assert output["should_generate_next_chapter"] is False
    assert output["recommended_next_tools"] == ["review_chapter_quality"]


def test_agent_expand_chapter_to_target_then_review_clears_under_target_warning(client, db_session, monkeypatch):
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "苏晚晴的梦境"
    chapter.content = "短章。" * 300
    chapter.word_count = 600
    db_session.commit()
    expanded_content = "林深和苏晚晴在门外压低声音，顺着雾气复盘证词。" * 100

    class FakeAIResult:
        content = json.dumps({"content": expanded_content, "change_summary": "补足场景密度。"}, ensure_ascii=False)
        prompt_tokens = 111
        completion_tokens = 222
        model = "fake-deepseek"

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            return FakeAIResult()

    monkeypatch.setattr("app.core.chapter_expansion.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "扩写并复审",
            "tools": [
                approved_expand_chapter_to_target_tool(db_session, project.id, chapter_index=1),
                {"tool_name": "review_chapter_quality", "params": {"chapter_index": 1}},
            ],
        },
    )

    review = response.json()["steps"][1]["output"]
    codes = {finding["code"] for finding in review["findings"]}
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "chapter_under_target" not in codes
    assert review["blocker_count"] == 0


def test_agent_expand_chapter_to_target_blocks_direct_followup_generation(client, db_session, monkeypatch):
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.content = "短章。" * 300
    chapter.word_count = 600
    db_session.commit()
    expanded_content = "林深和苏晚晴在门外压低声音，顺着雾气复盘证词。" * 100
    calls = []

    class FakeAIResult:
        content = json.dumps({"content": expanded_content, "change_summary": "补足场景密度。"}, ensure_ascii=False)
        prompt_tokens = 111
        completion_tokens = 222
        model = "fake-deepseek"

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            return FakeAIResult()

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append(action_type)
        return {"status": "success", "chapter_index": 2}

    monkeypatch.setattr("app.core.chapter_expansion.AIService", FakeAIService)
    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "扩写后直接生成下一章",
            "tools": [
                approved_expand_chapter_to_target_tool(db_session, project.id, chapter_index=1),
                {"tool_name": "generate_chapter", "params": {"chapter_index": 2}},
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert [step["tool_name"] for step in payload["steps"]] == ["execute_expand_chapter_to_target_with_approval"]
    assert calls == []


def test_agent_expand_chapter_to_target_skips_when_chapter_already_at_target(client, db_session, monkeypatch):
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.content = "林深和苏晚晴在门外压低声音，顺着雾气复盘证词。" * 100
    chapter.word_count = 2100
    db_session.commit()
    calls = []

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            calls.append(messages)
            raise AssertionError("AI should not be called for an already-target chapter")

    monkeypatch.setattr("app.core.chapter_expansion.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "扩写已达标章节",
            "tools": [approved_expand_chapter_to_target_tool(db_session, project.id, chapter_index=1)],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "skipped"
    assert output["reason"] == "chapter_already_at_target"
    assert output["should_generate_next_chapter"] is True
    assert calls == []


def test_agent_compress_chapter_to_target_updates_chapter_versions_and_requires_review(client, db_session, monkeypatch):
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "废弃实验室"
    chapter.content = "林深和苏晚晴在实验室里反复检查雾晶记录，确认线索。 " * 120
    chapter.word_count = 3000
    project.current_word_count = 3000
    db_session.commit()

    compressed_content = "林深和苏晚晴在实验室里检查雾晶记录，确认线索。 " * 100

    class FakeAIResult:
        content = json.dumps({"content": compressed_content, "change_summary": "压缩重复检查与解释段落。"}, ensure_ascii=False)
        prompt_tokens = 111
        completion_tokens = 222
        model = "fake-deepseek"

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            assert "压缩到目标字数范围" in messages[-1]["content"]
            return FakeAIResult()

    monkeypatch.setattr("app.core.chapter_compression.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "压缩第1章到目标字数",
            "tools": [
                approved_compress_chapter_to_target_tool(
                    db_session,
                    project.id,
                    chapter_index=1,
                    target_max_word_count=2300,
                )
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    patched = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    revision = db_session.query(ChapterRevision).filter_by(id=output["revision_id"]).one()
    versions = db_session.query(Version).filter_by(project_id=project.id, node_type="chapter", node_id=chapter.id).all()
    db_session.refresh(project)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "completed"
    assert output["previous_word_count"] == 3000
    assert 2000 <= output["word_count"] <= 2300
    assert patched.content == compressed_content.strip()
    assert 2000 <= patched.word_count <= 2300
    assert project.current_word_count == patched.word_count
    assert revision.status == "completed"
    assert revision.base_version_id
    assert revision.result_version_id
    assert len(versions) == 2
    assert output["should_generate_next_chapter"] is False
    assert output["recommended_next_tools"] == ["review_chapter_quality"]


def test_agent_compress_chapter_to_target_retries_when_forbidden_terms_remain(client, db_session, monkeypatch):
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "暗网迷途"
    chapter.content = "林深追踪N-07线索。苏晚晴低声说我就是N-07。" * 300
    chapter.word_count = 3600
    db_session.commit()

    calls = []

    class FakeAIResult:
        prompt_tokens = 111
        completion_tokens = 222
        model = "fake-deepseek"

        def __init__(self, content):
            self.content = content

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            calls.append(messages[-1]["content"])
            if len(calls) == 1:
                return FakeAIResult(
                    json.dumps(
                        {
                            "content": "林深追踪N-07线索。我就是N-07。" * 220,
                            "change_summary": "仍有残留。",
                        },
                        ensure_ascii=False,
                    )
                )
            return FakeAIResult(
                json.dumps(
                    {
                        "content": "林深追踪N-07线索，确认这只是未验证编号。" * 220,
                        "change_summary": "移除硬确认。",
                    },
                    ensure_ascii=False,
                )
            )

    monkeypatch.setattr("app.core.chapter_compression.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "压缩并移除禁用词",
            "tools": [
                approved_compress_chapter_to_target_tool(
                    db_session,
                    project.id,
                    chapter_index=1,
                    forbidden_terms=["我就是N-07"],
                )
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    patched = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    assert response.status_code == 200
    assert output["status"] == "completed"
    assert output["postcondition_retry_count"] == 1
    assert output["remaining_forbidden_terms"] == []
    assert len(calls) == 2
    assert "我就是N-07" not in patched.content


def test_agent_compress_chapter_to_target_blocks_when_forbidden_terms_survive_all_attempts(
    client,
    db_session,
    monkeypatch,
):
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "暗网迷途"
    original_content = "林深追踪N-07线索。苏晚晴低声说我就是N-07。" * 300
    chapter.content = original_content
    chapter.word_count = 3600
    db_session.commit()

    class FakeAIResult:
        content = json.dumps({"content": "林深追踪N-07线索。我就是N-07。" * 220, "change_summary": "仍有残留。"}, ensure_ascii=False)
        prompt_tokens = 111
        completion_tokens = 222
        model = "fake-deepseek"

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            return FakeAIResult()

    monkeypatch.setattr("app.core.chapter_compression.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "压缩并移除禁用词",
            "tools": [
                approved_compress_chapter_to_target_tool(
                    db_session,
                    project.id,
                    chapter_index=1,
                    forbidden_terms=["我就是N-07"],
                )
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    patched = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    assert response.status_code == 200
    assert output["status"] == "blocked"
    assert output["reason"] == "forbidden_terms_remaining"
    assert output["remaining_forbidden_terms"] == ["我就是N-07"]
    assert patched.content == original_content


def test_agent_compress_chapter_to_target_then_review_clears_over_target_warning(client, db_session, monkeypatch):
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "废弃实验室"
    chapter.content = "林深和苏晚晴在实验室里反复检查雾晶记录，确认线索。 " * 120
    chapter.word_count = 3000
    db_session.commit()
    compressed_content = "林深和苏晚晴在实验室里检查雾晶记录，确认线索。 " * 100

    class FakeAIResult:
        content = json.dumps({"content": compressed_content, "change_summary": "压缩重复检查与解释段落。"}, ensure_ascii=False)
        prompt_tokens = 111
        completion_tokens = 222
        model = "fake-deepseek"

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            return FakeAIResult()

    monkeypatch.setattr("app.core.chapter_compression.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "压缩并复审",
            "tools": [
                approved_compress_chapter_to_target_tool(
                    db_session,
                    project.id,
                    chapter_index=1,
                    target_max_word_count=2300,
                ),
                {"tool_name": "review_chapter_quality", "params": {"chapter_index": 1}},
            ],
        },
    )

    review = response.json()["steps"][1]["output"]
    codes = {finding["code"] for finding in review["findings"]}
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "chapter_over_target" not in codes
    assert "chapter_under_target" not in codes
    assert review["blocker_count"] == 0


def test_agent_compress_chapter_to_target_blocks_direct_followup_generation(client, db_session, monkeypatch):
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.content = "林深和苏晚晴在实验室里反复检查雾晶记录，确认线索。 " * 120
    chapter.word_count = 3000
    db_session.commit()
    compressed_content = "林深和苏晚晴在实验室里检查雾晶记录，确认线索。 " * 100
    calls = []

    class FakeAIResult:
        content = json.dumps({"content": compressed_content, "change_summary": "压缩重复检查与解释段落。"}, ensure_ascii=False)
        prompt_tokens = 111
        completion_tokens = 222
        model = "fake-deepseek"

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            return FakeAIResult()

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append(action_type)
        return {"status": "success", "chapter_index": 2}

    monkeypatch.setattr("app.core.chapter_compression.AIService", FakeAIService)
    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "压缩后直接生成下一章",
            "tools": [
                approved_compress_chapter_to_target_tool(
                    db_session,
                    project.id,
                    chapter_index=1,
                    target_max_word_count=2300,
                ),
                {"tool_name": "generate_chapter", "params": {"chapter_index": 2}},
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert [step["tool_name"] for step in payload["steps"]] == ["execute_compress_chapter_to_target_with_approval"]
    assert calls == []


def test_agent_compress_chapter_to_target_skips_when_chapter_already_within_target(client, db_session, monkeypatch):
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.content = "林深和苏晚晴在门外压低声音，顺着雾气复盘证词。" * 100
    chapter.word_count = 2100
    db_session.commit()
    calls = []

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            calls.append(messages)
            raise AssertionError("AI should not be called for an already-target chapter")

    monkeypatch.setattr("app.core.chapter_compression.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "压缩已达标章节",
            "tools": [approved_compress_chapter_to_target_tool(db_session, project.id, chapter_index=1)],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "skipped"
    assert output["reason"] == "chapter_already_within_target"
    assert calls == []


def test_agent_compress_chapter_to_target_repairs_under_target_retry(client, db_session, monkeypatch):
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "暗河引路"
    chapter.content = "林深和苏晚晴沿着暗河追查雾晶管线，反复核对线索。 " * 120
    chapter.word_count = 3000
    project.current_word_count = 3000
    db_session.commit()

    too_short = "林深和苏晚晴沿着暗河追查线索。 " * 80
    repaired = "林深和苏晚晴沿着暗河追查雾晶管线，确认警报来源。 " * 100
    calls = []

    class FakeAIResult:
        prompt_tokens = 111
        completion_tokens = 222
        model = "fake-deepseek"

        def __init__(self, content):
            self.content = json.dumps({"content": content, "change_summary": "压缩并恢复场景密度。"}, ensure_ascii=False)

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            calls.append(messages[-1]["content"])
            return FakeAIResult(too_short if len(calls) == 1 else repaired)

    monkeypatch.setattr("app.core.chapter_compression.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "压缩第1章并修复过短候选",
            "tools": [
                approved_compress_chapter_to_target_tool(
                    db_session,
                    project.id,
                    chapter_index=1,
                    target_max_word_count=2300,
                )
            ],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    traces = (
        db_session.query(AIModelCallTrace)
        .filter_by(project_id=project.id, trace_type="chapter_compression", chapter_index=1)
        .order_by(AIModelCallTrace.created_at.asc(), AIModelCallTrace.id.asc())
        .all()
    )
    patched = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    revision_count = db_session.query(ChapterRevision).filter_by(project_id=project.id, chapter_index=1).count()
    version_count = db_session.query(Version).filter_by(project_id=project.id, node_type="chapter", node_id=chapter.id).count()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert output["status"] == "completed"
    assert output["compression_attempt_count"] == 2
    assert len(output["failed_attempts"]) == 1
    assert output["failed_attempts"][0]["direction"] == "under_target"
    assert 2000 <= output["word_count"] <= 2300
    assert patched.content == repaired.strip()
    assert revision_count == 1
    assert version_count == 2
    assert len(calls) == 2
    assert "上一次压缩结果低于目标下限" in calls[1]
    assert [trace.status for trace in traces] == ["failed", "success"]


def test_agent_compress_chapter_to_target_falls_back_to_source_trim_after_under_target_retries(
    client, db_session, monkeypatch
):
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    opening = "林深推开废弃实验室的铁门，确认门缝里还压着父亲留下的空白信纸。"
    ending = "门后的红灯重新亮起，林深知道名单上的下一个名字已经出现。"
    middle = [f"潮湿走廊里第{i}次传来雾晶回声，墙皮落下细小灰尘。" for i in range(128)]
    source_content = opening + "".join(middle) + ending
    chapter.title = "废弃实验室"
    chapter.content = source_content
    chapter.word_count = 2706
    project.current_word_count = 2706
    db_session.commit()

    too_short = "林深和苏晚晴在废弃实验室追查雾晶线索。 " * 75
    calls = []

    class FakeAIResult:
        content = json.dumps({"content": too_short, "change_summary": "模型压缩过短。"}, ensure_ascii=False)
        prompt_tokens = 111
        completion_tokens = 222
        model = "fake-deepseek"

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            calls.append(messages[-1]["content"])
            return FakeAIResult()

    monkeypatch.setattr("app.core.chapter_compression.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "模型连续过短时从原文保守裁剪",
            "tools": [
                approved_compress_chapter_to_target_tool(
                    db_session,
                    project.id,
                    chapter_index=1,
                    target_max_word_count=2300,
                )
            ],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    patched = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    traces = (
        db_session.query(AIModelCallTrace)
        .filter_by(project_id=project.id, trace_type="chapter_compression", chapter_index=1)
        .order_by(AIModelCallTrace.created_at.asc(), AIModelCallTrace.id.asc())
        .all()
    )
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert output["status"] == "completed"
    assert output["compression_attempt_count"] == 3
    assert output["deterministic_trim_applied"] is True
    assert len(output["failed_attempts"]) == 2
    assert all(attempt["direction"] == "under_target" for attempt in output["failed_attempts"])
    assert 2000 <= output["word_count"] <= 2300
    assert patched.content != too_short.strip()
    assert opening in patched.content
    assert ending in patched.content
    assert len(calls) == 3
    assert [trace.status for trace in traces] == ["failed", "failed", "success"]


def test_agent_compress_chapter_to_target_refreshes_longform_memory_and_retrieval(
    client, db_session, monkeypatch
):
    from app.core.athena_retrieval import reindex_project_retrieval, search_retrieval
    from app.core.longform_memory import rebuild_longform_memory

    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "雾港密室"
    chapter.content = "林深和苏晚晴在雾港密室反复核对旧照片，旧照片里只有灰色灯塔。 " * 120
    chapter.word_count = 3000
    project.current_word_count = 3000
    db_session.commit()
    rebuild_longform_memory(db_session, project.id)
    reindex_project_retrieval(db_session, project.id)

    compressed_content = "林深在雾港密室确认蓝珀钥匙启动，苏晚晴记下灰色灯塔坐标。 " * 100

    class FakeAIResult:
        content = json.dumps({"content": compressed_content, "change_summary": "压缩到蓝珀钥匙线索。"}, ensure_ascii=False)
        prompt_tokens = 111
        completion_tokens = 222
        model = "fake-deepseek"

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            return FakeAIResult()

    monkeypatch.setattr("app.core.chapter_compression.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "压缩后同步长篇记忆",
            "tools": [
                approved_compress_chapter_to_target_tool(
                    db_session,
                    project.id,
                    chapter_index=1,
                    target_max_word_count=2300,
                )
            ],
        },
    )

    payload = response.json()
    db_session.expire_all()
    chapter_memory = (
        db_session.query(LongformMemory)
        .filter_by(project_id=project.id, memory_type="chapter", scope_key="chapter:1")
        .one()
    )
    retrieval_results = search_retrieval(
        db_session,
        project.id,
        "蓝珀钥匙",
        source_type="longform_memory",
        max_chapter_index=2,
    )
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert "蓝珀钥匙" in chapter_memory.summary
    assert any(
        item["source_ref"] == "memory:chapter:1" and "蓝珀钥匙" in item["snippet"]
        for item in retrieval_results["items"]
    )


def test_agent_compress_chapter_to_target_blocks_after_retry_exhaustion(client, db_session, monkeypatch):
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    original_content = "林深和苏晚晴沿着暗河追查雾晶管线，反复核对线索。 " * 180
    chapter.content = original_content
    chapter.word_count = 4500
    db_session.commit()

    too_short = "林深和苏晚晴沿着暗河追查线索。 " * 80
    calls = []

    class FakeAIResult:
        content = json.dumps({"content": too_short, "change_summary": "仍然过短。"}, ensure_ascii=False)
        prompt_tokens = 111
        completion_tokens = 222
        model = "fake-deepseek"

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            calls.append(messages[-1]["content"])
            return FakeAIResult()

    monkeypatch.setattr("app.core.chapter_compression.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "压缩第1章但候选持续过短",
            "tools": [approved_compress_chapter_to_target_tool(db_session, project.id, chapter_index=1)],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    patched = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    revision_count = db_session.query(ChapterRevision).filter_by(project_id=project.id, chapter_index=1).count()
    version_count = db_session.query(Version).filter_by(project_id=project.id, node_type="chapter", node_id=chapter.id).count()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert output["reason"] == "compressed_content_outside_target"
    assert output["compression_attempt_count"] == 3
    assert output["deterministic_trim_applied"] is False
    assert len(output["failed_attempts"]) == 3
    assert len(calls) == 3
    assert patched.content == original_content
    assert revision_count == 0
    assert version_count == 0


def test_agent_compress_chapter_to_target_repairs_near_target_candidate_from_source(client, db_session, monkeypatch):
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    source_sentences = [
        "他把旧号码牌贴进证物袋，确认暗河另一端仍有回声。",
        "苏晚晴在墙面找到被水泡开的蓝色封条。",
        "林深听见管道深处传来三短一长的敲击。",
        "两人把警报频率记进随身本，准备回到灯塔核对。",
        "陈默留下的旧坐标在纸背浮出，指向下游闸门。",
        "雾晶管线旁的冷光忽明忽暗，像在回应失踪者的低语。",
    ]
    source_text = "".join(source_sentences)
    chapter.content = ("林深和苏晚晴沿着暗河追查雾晶管线，反复核对线索。 " * 120) + source_text
    chapter.word_count = 3050
    project.current_word_count = 3050
    db_session.commit()

    almost_enough = "林深和苏晚晴沿着暗河追查雾晶管线，确认警报来源。 " * 85
    calls = []

    class FakeAIResult:
        content = json.dumps({"content": almost_enough, "change_summary": "轻量压缩。"}, ensure_ascii=False)
        prompt_tokens = 111
        completion_tokens = 222
        model = "fake-deepseek"

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            calls.append(messages[-1]["content"])
            return FakeAIResult()

    monkeypatch.setattr("app.core.chapter_compression.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "压缩第1章并用源文恢复轻微缺口",
            "tools": [
                approved_compress_chapter_to_target_tool(
                    db_session,
                    project.id,
                    chapter_index=1,
                    target_max_word_count=2300,
                )
            ],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    patched = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert output["status"] == "completed"
    assert output["compression_attempt_count"] == 1
    assert output["deterministic_repair_applied"] is True
    assert 2000 <= output["word_count"] <= 2300
    assert any(sentence in patched.content for sentence in source_sentences)
    assert len(calls) == 1


def test_agent_compress_chapter_to_target_trims_near_over_target_candidate(client, db_session, monkeypatch):
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    opening = "林深握紧灯塔钥匙，确认暗河入口没有被封死。"
    ending = "苏晚晴把号码牌压在掌心，决定回到灯塔核对名单。"
    middle = [f"他们沿着潮湿管道继续记录第{i}处雾晶回声。" for i in range(120)]
    over_target_candidate = opening + "".join(middle) + ending
    chapter.content = over_target_candidate
    chapter.word_count = 2433
    project.current_word_count = 2433
    db_session.commit()
    calls = []

    class FakeAIResult:
        content = json.dumps({"content": over_target_candidate, "change_summary": "模型返回原稿。"}, ensure_ascii=False)
        prompt_tokens = 111
        completion_tokens = 222
        model = "fake-deepseek"

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            calls.append(messages[-1]["content"])
            return FakeAIResult()

    monkeypatch.setattr("app.core.chapter_compression.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "压缩第1章并裁剪轻微超长候选",
            "tools": [
                approved_compress_chapter_to_target_tool(
                    db_session,
                    project.id,
                    chapter_index=1,
                    target_max_word_count=2300,
                )
            ],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    patched = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert output["status"] == "completed"
    assert output["compression_attempt_count"] == 1
    assert output["deterministic_trim_applied"] is True
    assert 2000 <= output["word_count"] <= 2300
    assert opening in patched.content
    assert ending in patched.content
    assert len(calls) == 1


def test_agent_compress_chapter_to_target_trims_large_over_target_candidate(client, db_session, monkeypatch):
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    opening = "林深推开第三研究所的铁门，确认门缝里还压着空白信纸。"
    protected_dialogue = "“别碰那张纸。”苏晚晴按住他的手，“雾晶反应还在。”"
    ending = "门后的红灯重新亮起，林深知道名单上的下一个名字已经出现。"
    low_signal = [f"潮湿走廊里回声第{i}次拉长，墙皮落下细小灰尘。" for i in range(135)]
    candidate = opening + protected_dialogue + "".join(low_signal) + ending
    chapter.content = candidate
    chapter.word_count = 2878
    project.current_word_count = 2878
    db_session.commit()
    calls = []

    class FakeAIResult:
        content = json.dumps({"content": candidate, "change_summary": "模型返回仍然超长的候选。"}, ensure_ascii=False)
        prompt_tokens = 111
        completion_tokens = 222
        model = "fake-deepseek"

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            calls.append(messages[-1]["content"])
            return FakeAIResult()

    monkeypatch.setattr("app.core.chapter_compression.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "压缩大幅超长章节",
            "tools": [
                approved_compress_chapter_to_target_tool(
                    db_session,
                    project.id,
                    chapter_index=1,
                    target_max_word_count=2300,
                )
            ],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    patched = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    revision_count = db_session.query(ChapterRevision).filter_by(project_id=project.id, chapter_index=1).count()
    version_count = db_session.query(Version).filter_by(project_id=project.id, node_type="chapter", node_id=chapter.id).count()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert output["status"] == "completed"
    assert output["deterministic_trim_applied"] is True
    assert 2000 <= output["word_count"] <= 2300
    assert opening in patched.content
    assert protected_dialogue in patched.content
    assert ending in patched.content
    assert revision_count == 1
    assert version_count == 2
    assert len(calls) == 1
