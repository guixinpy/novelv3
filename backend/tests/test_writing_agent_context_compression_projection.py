from app.models import LongformMemory, Project
from app.services.writing_agent import agent_context_compression_projection
from app.services.writing_agent.agent_context_compression_projection import (
    build_agent_context_compression_payload,
    inspect_agent_context_compression_projection,
)


def test_context_compression_projection_reports_ready_chapter_window(db_session, monkeypatch):
    project = Project(name="Context Projection Ready")
    db_session.add(project)
    db_session.commit()
    monkeypatch.setattr(
        agent_context_compression_projection,
        "summarize_longform_context",
        lambda *args, **kwargs: _context_summary(prompt_context_chars=1200, max_chars=4000),
    )

    output = inspect_agent_context_compression_projection(db_session, project.id, chapter_index=3, max_chars=4000)

    assert output["status"] == "ready"
    assert output["strategy"] == {
        "granularity": "chapter_window",
        "protect_current_chapter": True,
        "protect_head_sections": ["project", "active_state"],
        "protect_tail_sections": ["recent_chapters", "critical_context"],
    }
    assert output["summary"]["usage_ratio"] == 0.3
    assert output["risks"] == []
    assert output["compression_plan"] == {
        "status": "not_needed",
        "mode": "head_tail_protected_pretrim",
        "target_max_chars": 4000,
        "protected_head_sections": ["project", "active_state"],
        "protected_tail_sections": ["recent_chapters", "critical_context"],
        "pretrim_order": [],
        "summary_tool": None,
        "payload_tool": None,
        "llm_summary_required": False,
    }
    assert output["recommended_next_tools"] == []


def test_context_compression_projection_warns_when_window_pressure_rises(db_session, monkeypatch):
    project = Project(name="Context Projection Pressure")
    db_session.add(project)
    db_session.commit()
    monkeypatch.setattr(
        agent_context_compression_projection,
        "summarize_longform_context",
        lambda *args, **kwargs: _context_summary(
            prompt_context_chars=3800,
            max_chars=4000,
            diagnostics=[{"code": "prompt_context_truncated", "severity": "info"}],
        ),
    )

    output = inspect_agent_context_compression_projection(db_session, project.id, chapter_index=8, max_chars=4000)

    assert output["status"] == "warning"
    assert output["summary"]["usage_ratio"] == 0.95
    assert [risk["code"] for risk in output["risks"]] == ["context_window_pressure", "prompt_context_truncated"]
    assert output["recommended_next_tools"] == [
        "build_agent_context_compression_payload",
        "inspect_agent_memory_route",
    ]
    assert output["compression_plan"] == {
        "status": "recommended",
        "mode": "head_tail_protected_pretrim",
        "target_max_chars": 3000,
        "protected_head_sections": ["project", "active_state"],
        "protected_tail_sections": ["recent_chapters", "critical_context"],
        "pretrim_order": ["source_sections", "critical_context", "recent_chapters"],
        "summary_tool": {
            "tool_name": "summarize_longform_context",
            "params": {"chapter_index": 8, "max_chars": 3000, "include_prompt_context": False},
        },
        "payload_tool": {
            "tool_name": "build_agent_context_compression_payload",
            "params": {"chapter_index": 8, "max_chars": 4000, "context_guard_failure_count": 0},
        },
        "llm_summary_required": True,
    }
    assert output["recovery"]["status"] == "optional"
    assert [tool["tool_name"] for tool in output["recovery"]["tools"]] == [
        "build_agent_context_compression_payload"
    ]


def test_context_compression_payload_builds_head_tail_protected_dry_run(db_session, monkeypatch):
    project = Project(name="Context Compression Payload")
    db_session.add(project)
    db_session.commit()
    calls: list[dict[str, object]] = []

    def fake_summary(*args, **kwargs):
        calls.append(dict(kwargs))
        return _context_summary(
            prompt_context_chars=3800,
            max_chars=kwargs.get("max_chars") or 4000,
            diagnostics=[{"code": "prompt_context_truncated", "severity": "info"}],
            include_prompt_context=kwargs.get("include_prompt_context") is True,
            sections=[
                {"key": "recent_chapters", "title": "近期章节", "item_count": 2, "items": [{"title": "第七章"}]},
                {"key": "critical_context", "title": "关键上下文", "item_count": 3, "items": [{"title": "灯塔旧案"}]},
            ],
            source_sections=[
                {"key": "recent_chapters", "title": "近期章节", "item_count": 2},
                {"key": "critical_context", "title": "关键上下文", "item_count": 3},
            ],
        )

    monkeypatch.setattr(agent_context_compression_projection, "summarize_longform_context", fake_summary)

    output = build_agent_context_compression_payload(db_session, project.id, chapter_index=8, max_chars=4000)

    assert output["status"] == "ready"
    assert [call.get("include_prompt_context") for call in calls] == [False, True]
    assert calls[1]["max_chars"] == 3000
    payload = output["compression_payload"]
    assert payload["mode"] == "head_tail_protected_pretrim"
    assert payload["execution_mode"] == "dry_run"
    assert payload["target_max_chars"] == 3000
    assert [section["key"] for section in payload["protected_head"]] == ["project", "active_state"]
    assert payload["summary"]["tool_name"] == "summarize_longform_context"
    assert [section["key"] for section in payload["protected_tail"]] == ["recent_chapters", "critical_context"]
    assert [section["key"] for section in payload["pretrimmed_sections"]] == [
        "source_sections",
        "critical_context",
        "recent_chapters",
    ]
    assert output["side_effects"] == {"writes": [], "runtime_context_mutated": False}
    assert output["trace"]["runtime_behavior_changed"] is False


def test_context_compression_summary_record_persists_compressed_payload(db_session, monkeypatch):
    project = Project(name="Context Compression Summary Record")
    db_session.add(project)
    db_session.commit()
    compressed_context = "【压缩长篇记忆】\n保留当前目标、关键旧案和近期章节尾部。"

    def fake_payload(db, project_id, *, chapter_index=None, max_chars=None, context_guard_failure_count=0):
        return {
            "status": "ready",
            "project_id": project_id,
            "chapter_index": chapter_index,
            "compression_payload": {
                "execution_mode": "dry_run",
                "target_max_chars": 3000,
                "original_prompt_context_chars": 3800,
                "compressed_context_chars": len(compressed_context),
                "compression_ratio": 0.02,
                "compressed_context": compressed_context,
                "pretrimmed_sections": [{"key": "recent_chapters"}, {"key": "critical_context"}],
            },
            "projection": {"status": "warning"},
            "compression_plan": {"status": "recommended"},
            "evidence": {"source_section_keys": ["recent_chapters", "critical_context"]},
            "side_effects": {"writes": [], "runtime_context_mutated": False},
            "trace": {"source": "test_payload"},
        }

    monkeypatch.setattr(agent_context_compression_projection, "build_agent_context_compression_payload", fake_payload)

    output = agent_context_compression_projection.record_agent_context_compression_summary(
        db_session,
        project.id,
        chapter_index=8,
        max_chars=4000,
    )

    assert output["status"] == "completed"
    assert output["summary"] == {
        "created_nodes": 1,
        "updated_nodes": 0,
        "memory_type": "context_compression_summary",
    }
    assert output["record"]["scope_key"] == "context_compression:chapter:8:max_chars:4000"
    assert output["record"]["summary"] == compressed_context
    assert output["record"]["metadata"]["target_max_chars"] == 3000
    assert output["record"]["metadata"]["source_section_keys"] == ["recent_chapters", "critical_context"]
    assert output["side_effects"]["writes"][0]["table"] == "longform_memories"

    record = (
        db_session.query(LongformMemory)
        .filter(
            LongformMemory.project_id == project.id,
            LongformMemory.memory_type == "context_compression_summary",
            LongformMemory.scope_key == "context_compression:chapter:8:max_chars:4000",
        )
        .one()
    )
    assert record.start_chapter_index == 8
    assert record.end_chapter_index == 8
    assert record.title == "第8章上下文压缩摘要"
    assert record.summary == compressed_context
    assert record.memory_metadata["compression_ratio"] == 0.02


def test_context_compression_summary_record_skips_when_payload_not_ready(db_session, monkeypatch):
    project = Project(name="Context Compression Summary Skip")
    db_session.add(project)
    db_session.commit()

    monkeypatch.setattr(
        agent_context_compression_projection,
        "build_agent_context_compression_payload",
        lambda *args, **kwargs: {
            "status": "not_needed",
            "compression_payload": None,
            "side_effects": {"writes": [], "runtime_context_mutated": False},
            "recommended_next_tools": [],
            "recovery": {},
            "trace": {"source": "test_payload"},
        },
    )

    output = agent_context_compression_projection.record_agent_context_compression_summary(
        db_session,
        project.id,
        chapter_index=8,
        max_chars=4000,
    )

    assert output["status"] == "skipped"
    assert output["reason"] == "compression_payload_not_ready"
    assert output["side_effects"] == {"writes": [], "runtime_context_mutated": False}
    assert (
        db_session.query(LongformMemory)
        .filter(LongformMemory.project_id == project.id, LongformMemory.memory_type == "context_compression_summary")
        .count()
        == 0
    )


def test_context_compression_projection_blocks_after_repeated_guard_failures(db_session, monkeypatch):
    project = Project(name="Context Projection Guard")
    db_session.add(project)
    db_session.commit()
    monkeypatch.setattr(
        agent_context_compression_projection,
        "summarize_longform_context",
        lambda *args, **kwargs: _context_summary(prompt_context_chars=1600, max_chars=4000),
    )

    output = inspect_agent_context_compression_projection(
        db_session,
        project.id,
        chapter_index=12,
        max_chars=4000,
        context_guard_failure_count=3,
    )

    assert output["status"] == "blocked"
    assert output["risks"][0]["code"] == "context_guard_open"
    assert output["summary"]["context_guard_failure_count"] == 3
    assert output["recommended_next_tools"] == ["inspect_agent_memory_route"]
    assert output["recovery"] == {
        "status": "recommended",
        "reason": "context_guard_open",
        "next_tools": ["inspect_agent_memory_route"],
        "tools": [
            {
                "tool_name": "inspect_agent_memory_route",
                "params": {
                    "chapter_index": 12,
                    "query": "上下文压缩连续失败，诊断第12章长篇记忆、检索覆盖和压缩窗口。",
                    "include_context_summary": False,
                },
            }
        ],
    }


def _context_summary(
    *,
    prompt_context_chars,
    max_chars,
    diagnostics=None,
    include_prompt_context=False,
    sections=None,
    source_sections=None,
):
    return {
        "status": "completed",
        "chapter_index": 1,
        "prompt_context_chars": prompt_context_chars,
        "limits": {"max_chars": max_chars},
        "project": {"id": "project-1", "name": "测试项目", "genre": None},
        "context_summary": {
            "goal": "整理第8章写作上下文",
            "active_state": {"target_outline": {"title": "第八章"}, "previous_chapter": {"title": "第七章"}},
            "recent_chapters": [{"title": "第七章"}],
            "critical_context": sections or [],
        },
        "sections": sections or [],
        "source_sections": source_sections or [],
        "source_section_keys": [section["key"] for section in source_sections or []],
        "diagnostics": diagnostics or [],
        "memory_provenance": {
            "version": "test.memory_provenance.v1",
            "status": "available",
            "sources": [],
            "source_count": 0,
            "windows": {"sections": {}},
            "recovery": {"status": "none", "reason": "test", "next_tools": [], "tools": []},
            "trace": {"source": "summarize_longform_context", "version": "test.memory_provenance.v1"},
        },
        "prompt_context": "完整上下文" * 800 if include_prompt_context else None,
    }
