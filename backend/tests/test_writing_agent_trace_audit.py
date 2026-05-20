from app.models import AIModelCallTrace, Project, WritingAgentRun, WritingAgentStep
from app.services.writing_agent.agent_trace_audit import inspect_agent_trace_audit


def test_inspect_agent_trace_audit_summarizes_successful_run_without_raw_context(db_session):
    project = Project(name="Trace Audit Success")
    db_session.add(project)
    db_session.flush()
    run = WritingAgentRun(
        project_id=project.id,
        goal="生成第2章",
        status="success",
        entrypoint="chapter_generate",
        input={"chapter_index": 2},
        output={"status": "success"},
    )
    trace = AIModelCallTrace(
        id="trace-success",
        project_id=project.id,
        trace_type="chapter_generation",
        status="success",
        model="deepseek-chat",
        prompt_tokens=120,
        completion_tokens=300,
        latency_ms=1500,
        chapter_index=2,
        context_blocks=[
            {
                "key": "recent_chapters",
                "kind": "longform_memory",
                "title": "近期章节记忆",
                "content": "灯塔区集体失忆案继续发酵。",
                "sources": [{"source_type": "longform_memory", "source_id": "memory-1"}],
            }
        ],
        trace_metadata={"budget": {"used_context_chars": 14}, "prompt_id": "chapter-v1"},
    )
    db_session.add_all([run, trace])
    db_session.flush()
    db_session.add(
        WritingAgentStep(
            run_id=run.id,
            project_id=project.id,
            step_index=1,
            tool_name="generate_chapter",
            status="success",
            input={"params": {"chapter_index": 2}},
            output={"status": "success", "trace_id": trace.id},
            trace_id=trace.id,
            target_type="chapter",
            target_id="chapter-2",
            chapter_index=2,
        )
    )
    db_session.commit()

    output = inspect_agent_trace_audit(db_session, project.id, run_id=run.id)

    assert output["status"] == "completed"
    assert output["audit"]["status"] == "completed"
    assert output["run"]["id"] == run.id
    assert output["steps"][0]["tool_name"] == "generate_chapter"
    assert output["traces"][0]["id"] == "trace-success"
    assert output["traces"][0]["context_block_count"] == 1
    assert output["context"]["total_blocks"] == 1
    assert output["context"]["blocks"][0]["key"] == "recent_chapters"
    assert output["context"]["blocks"][0]["source_count"] == 1
    assert "content" not in output["context"]["blocks"][0]
    assert output["failure"] is None
    assert output["recommended_actions"] == []


def test_inspect_agent_trace_audit_exposes_recommended_recovery_for_blocked_run(db_session):
    project = Project(name="Trace Audit Blocked")
    db_session.add(project)
    db_session.flush()
    run = WritingAgentRun(
        project_id=project.id,
        goal="继续生成",
        status="blocked",
        entrypoint="api",
        input={"chapter_index": 3},
        error="长篇记忆未就绪",
    )
    db_session.add(run)
    db_session.flush()
    db_session.add(
        WritingAgentStep(
            run_id=run.id,
            project_id=project.id,
            step_index=1,
            tool_name="inspect_agent_memory_route",
            status="blocked",
            input={"params": {"chapter_index": 3}},
            output={
                "status": "blocked",
                "agent_tool_result": {
                    "recovery": {
                        "status": "recommended",
                        "next_tool": "repair_longform_maintenance",
                        "reason_code": "longform_memory_needs_maintenance",
                    }
                },
            },
            chapter_index=3,
        )
    )
    db_session.commit()

    output = inspect_agent_trace_audit(db_session, project.id, run_id=run.id)

    assert output["status"] == "completed"
    assert output["audit"]["status"] == "blocked"
    assert output["failure"]["tool_name"] == "inspect_agent_memory_route"
    assert output["failure"]["message"] == "长篇记忆未就绪"
    assert output["recommended_actions"] == [
        {
            "tool_name": "repair_longform_maintenance",
            "reason_code": "longform_memory_needs_maintenance",
            "source_step_index": 1,
        }
    ]
