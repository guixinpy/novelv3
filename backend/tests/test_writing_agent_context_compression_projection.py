from app.models import Project
from app.services.writing_agent import agent_context_compression_projection
from app.services.writing_agent.agent_context_compression_projection import inspect_agent_context_compression_projection


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
    assert output["recommended_next_tools"] == ["summarize_longform_context", "inspect_agent_memory_route"]
    assert output["recovery"]["status"] == "optional"
    assert output["recovery"]["tools"][0]["tool_name"] == "summarize_longform_context"


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


def _context_summary(*, prompt_context_chars, max_chars, diagnostics=None):
    return {
        "status": "completed",
        "chapter_index": 1,
        "prompt_context_chars": prompt_context_chars,
        "limits": {"max_chars": max_chars},
        "sections": [],
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
    }
