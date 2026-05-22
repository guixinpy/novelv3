from app.models import AIModelCallTrace, Dialog, DialogMessage, Project, WritingAgentRun, WritingAgentStep
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


def test_inspect_agent_trace_audit_includes_dialog_approval_events_without_raw_hash(db_session):
    project = Project(name="Trace Audit Approval Events")
    db_session.add(project)
    db_session.flush()
    dialog = Dialog(project_id=project.id, dialog_type="hermes", state="running")
    db_session.add(dialog)
    db_session.flush()
    run = WritingAgentRun(
        project_id=project.id,
        goal="确认后生成第2章",
        status="running",
        entrypoint="dialog_pending_action",
        input={"chapter_index": 2},
        dialog_id=dialog.id,
    )
    db_session.add(run)
    db_session.flush()
    message = DialogMessage(
        dialog_id=dialog.id,
        role="system",
        content="操作已确认，正在生成中...",
        action_result={
            "type": "generate_chapter",
            "status": "generating",
            "data": {
                "agent_run_id": run.id,
                "approval_decision": {
                    "kind": "pending_action_decision",
                    "pending_action_id": "pending-1",
                    "action_type": "generate_chapter",
                    "pending_action_type": "generate_chapter",
                    "decision": "confirm",
                    "decision_comment": "",
                    "resolved_at": "2026-05-22T12:00:00+00:00",
                    "approval_mode": "single",
                    "approval_contract_hash": "approval:secret-hash",
                    "approval_contract_version": "phase108.agent_plan_approval_contract.v1",
                },
            },
        },
    )
    db_session.add(message)
    db_session.flush()
    result_message = DialogMessage(
        dialog_id=dialog.id,
        role="system",
        content="第2章正文生成完成。",
        action_result={
            "type": "generate_chapter",
            "status": "success",
            "data": {
                "agent_run_id": run.id,
                "status": "success",
            },
        },
    )
    db_session.add(result_message)
    db_session.flush()
    run.request_message_id = message.id
    run.response_message_id = result_message.id
    db_session.commit()

    output = inspect_agent_trace_audit(db_session, project.id, run_id=run.id)

    assert output["dialog_events"] == {
        "approval_message": {
            "id": message.id,
            "role": "system",
            "action_type": "generate_chapter",
            "action_status": "generating",
        },
        "result_message": {
            "id": result_message.id,
            "role": "system",
            "action_type": "generate_chapter",
            "action_status": "success",
        },
    }
    assert output["approval_events"] == [
        {
            "kind": "pending_action_decision",
            "message_id": message.id,
            "action_type": "generate_chapter",
            "pending_action_type": "generate_chapter",
            "decision": "confirm",
            "decision_label": "已确认",
            "approval_mode": "single",
            "approval_contract_bound": True,
            "approval_contract_version": "phase108.agent_plan_approval_contract.v1",
            "resolved_at": "2026-05-22T12:00:00+00:00",
        }
    ]
    assert "approval:secret-hash" not in str(output["approval_events"])
    assert output["audit"]["approval_event_count"] == 1
