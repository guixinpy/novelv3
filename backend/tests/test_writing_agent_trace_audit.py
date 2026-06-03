from datetime import datetime, timedelta, timezone

from app.models import AIModelCallTrace, Dialog, DialogMessage, Project, WritingAgentRun, WritingAgentStep
from app.schemas.writing_agent import WritingAgentStepOut
from app.services.writing_agent.agent_trace_audit import inspect_agent_trace_anomaly_trends, inspect_agent_trace_audit


def test_writing_agent_step_binding_fields_are_modelled():
    assert hasattr(WritingAgentStep, "tool_call_id")
    assert hasattr(WritingAgentStep, "resource_binding")
    assert "tool_call_id" in WritingAgentStepOut.model_fields
    assert "resource_binding" in WritingAgentStepOut.model_fields


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
            tool_call_id="toolcall:test",
            resource_binding={
                "tool_call_id": "toolcall:test",
                "tool_name": "generate_chapter",
                "target_type": "chapter",
                "target_id": "chapter:2",
                "source_plan_id": "plan:direct",
                "source_step_id": "step:write",
                "binding_source": "server_derived",
            },
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


def test_inspect_agent_trace_audit_includes_profile_policy_audit(db_session):
    project = Project(name="Trace Profile Policy Audit")
    db_session.add(project)
    db_session.flush()
    run = WritingAgentRun(project_id=project.id, goal="检查 profile 策略", status="success", entrypoint="api")
    db_session.add(run)
    db_session.flush()
    db_session.add(
        WritingAgentStep(
            run_id=run.id,
            project_id=project.id,
            step_index=1,
            tool_name="describe_agent_tools",
            status="success",
            input={"params": {"agent_profile": "orchestrator"}},
            output={
                "status": "completed",
                "agent_profile_tool_projection": {
                    "consistency_audit": {
                        "version": "phase215.agent_profile_policy_audit.v1",
                        "status": "needs_attention",
                        "summary": {"issues": 1, "delegate_edges": 4},
                        "issues": [
                            {
                                "code": "delegate_target_missing_definition",
                                "severity": "error",
                                "profile": "orchestrator",
                                "target": "ghost_worker",
                            }
                        ],
                        "delegate_edges": [{"source": "orchestrator", "target": "ghost_worker"}],
                    }
                },
            },
            target_type="agent_tool_plan",
        )
    )
    db_session.commit()

    output = inspect_agent_trace_audit(db_session, project.id, run_id=run.id)

    assert output["audit"]["profile_policy_status"] == "needs_attention"
    assert output["audit"]["profile_policy_issue_count"] == 1
    assert output["profile_policy_audit"]["status"] == "needs_attention"
    assert output["profile_policy_audit"]["summary"]["issues"] == 1
    assert output["profile_policy_audit"]["issues"][0]["code"] == "delegate_target_missing_definition"
    assert "delegate_edges" not in output["profile_policy_audit"]


def test_inspect_agent_trace_audit_includes_control_plane_readiness(db_session):
    project = Project(name="Trace Control Plane Readiness")
    db_session.add(project)
    db_session.flush()
    run = WritingAgentRun(
        project_id=project.id,
        goal="检查控制平面",
        status="success",
        entrypoint="api",
        input={
            "planner": {
                "trace": {
                    "agent_health_projection": {
                        "control_plane_readiness": {
                            "status": "degraded",
                            "version": "phase46.agent_control_plane_readiness.v1",
                            "summary": {
                                "tool_gap_count": 1,
                                "command_gap_count": 2,
                                "total_gap_count": 3,
                                "agent_control_commands": 2,
                            },
                            "recommended_next_tools": [
                                "inspect_agent_control_plane_readiness",
                                "inspect_agent_command_contracts",
                            ],
                        }
                    }
                }
            }
        },
    )
    db_session.add(run)
    db_session.commit()

    output = inspect_agent_trace_audit(db_session, project.id, run_id=run.id)

    assert output["audit"]["control_plane_status"] == "degraded"
    assert output["audit"]["control_plane_gap_count"] == 3
    readiness = output["control_plane_readiness"]
    assert readiness["status"] == "degraded"
    assert readiness["summary"]["total_gap_count"] == 3
    assert readiness["summary"]["agent_control_commands"] == 2
    assert readiness["recommended_next_tools"] == [
        "inspect_agent_control_plane_readiness",
        "inspect_agent_command_contracts",
    ]
    assert output["recommended_actions"] == [
        {
            "tool_name": "inspect_agent_control_plane_readiness",
            "reason_code": "agent_control_plane_degraded",
        }
    ]


def test_inspect_agent_trace_audit_includes_command_contracts(db_session):
    project = Project(name="Trace Command Contracts")
    db_session.add(project)
    db_session.flush()
    run = WritingAgentRun(
        project_id=project.id,
        goal="检查命令契约",
        status="success",
        entrypoint="api",
        input={
            "planner": {
                "trace": {
                    "agent_health_projection": {
                        "command_contracts": {
                            "status": "completed",
                            "summary": {
                                "total_commands": 8,
                                "public_commands": 5,
                                "agent_control_commands": 2,
                                "available_commands": 5,
                                "gap_count": 2,
                            },
                            "commands": [{"name": "legacy_world_model"}],
                        }
                    }
                }
            }
        },
    )
    db_session.add(run)
    db_session.commit()

    output = inspect_agent_trace_audit(db_session, project.id, run_id=run.id)

    assert output["audit"]["command_contract_gap_count"] == 2
    contracts = output["command_contracts"]
    assert contracts["summary"]["total_commands"] == 8
    assert contracts["summary"]["agent_control_commands"] == 2
    assert contracts["summary"]["gap_count"] == 2
    assert "commands" not in contracts
    assert output["recommended_actions"] == [
        {
            "tool_name": "inspect_agent_command_contracts",
            "reason_code": "agent_command_contracts_have_gaps",
        }
    ]


def test_inspect_agent_trace_audit_includes_safe_intent_chain_summary(db_session):
    project = Project(name="Trace Intent Chain")
    db_session.add(project)
    db_session.flush()
    planner_output = {
        "status": "completed",
        "intent_projection": {
            "rule_id": "preflight_context_budget_intent",
            "candidate": {
                "type": "preflight_context_budget",
                "params": {
                    "chapter_index": 3,
                    "max_context_chars": 1200,
                },
            },
        },
        "planner": {
            "intent_class": "preflight_context_budget",
            "mapped_from_action_type": "preflight_context_budget",
            "mapped_from_rule_id": "preflight_context_budget_intent",
            "chapter_index": 3,
        },
        "plan": {
            "tools": [
                {
                    "tool_name": "preflight_writing",
                    "params": {
                        "chapter_index": 3,
                        "max_context_chars": 1200,
                    },
                }
            ]
        },
    }
    run = WritingAgentRun(
        project_id=project.id,
        goal="检查第3章上下文预算",
        status="success",
        entrypoint="dialog_auto_plan",
        input={"planner": planner_output},
        output={"status": "success"},
    )
    db_session.add(run)
    db_session.flush()
    db_session.add(
        WritingAgentStep(
            run_id=run.id,
            project_id=project.id,
            step_index=1,
            tool_name="preflight_writing",
            status="success",
            input={"params": {"chapter_index": 3, "max_context_chars": 1200}},
            output={"status": "ready"},
            chapter_index=3,
        )
    )
    db_session.commit()

    output = inspect_agent_trace_audit(db_session, project.id, run_id=run.id)

    assert output["audit"]["intent_chain_status"] == "available"
    assert output["audit"]["planned_tool_count"] == 1
    assert output["audit"]["matched_planned_tool_count"] == 1
    assert output["intent_chain"] == {
        "status": "available",
        "source": "run_input_planner",
        "rule_id": "preflight_context_budget_intent",
        "intent_class": "preflight_context_budget",
        "mapped_from_action_type": "preflight_context_budget",
        "chapter_index": 3,
        "planned_tool_count": 1,
        "executed_tool_count": 1,
        "matched_tool_count": 1,
        "planned_tools": [
            {
                "tool_name": "preflight_writing",
                "status": "executed",
                "step_index": 1,
            }
        ],
    }
    assert "max_context_chars" not in str(output["intent_chain"])


def test_inspect_agent_trace_audit_includes_end_to_end_chain_summary(db_session):
    project = Project(name="Trace End To End Chain")
    db_session.add(project)
    db_session.flush()
    dialog = Dialog(project_id=project.id, dialog_type="hermes", state="running")
    db_session.add(dialog)
    db_session.flush()
    planner_output = {
        "status": "completed",
        "intent_projection": {
            "rule_id": "preflight_context_budget_intent",
            "candidate": {
                "type": "preflight_context_budget",
                "params": {
                    "chapter_index": 3,
                    "max_context_chars": 1200,
                },
            },
        },
        "planner": {
            "intent_class": "preflight_context_budget",
            "mapped_from_action_type": "preflight_context_budget",
            "mapped_from_rule_id": "preflight_context_budget_intent",
            "chapter_index": 3,
        },
        "plan": {"tools": [{"tool_name": "preflight_writing"}]},
    }
    run = WritingAgentRun(
        project_id=project.id,
        goal="预检第3章上下文预算",
        status="success",
        entrypoint="dialog_auto_plan",
        input={"planner": planner_output},
        output={"status": "success"},
        dialog_id=dialog.id,
    )
    db_session.add(run)
    db_session.flush()
    trace = AIModelCallTrace(
        id="trace-e2e-secret",
        project_id=project.id,
        trace_type="preflight_context_budget",
        status="success",
        model="local-preflight-model",
        chapter_index=3,
        context_blocks=[{"key": "budget-secret-key", "content": "不应进入闭环摘要。"}],
    )
    db_session.add(trace)
    db_session.flush()
    db_session.add(
        WritingAgentStep(
            run_id=run.id,
            project_id=project.id,
            step_index=1,
            tool_name="preflight_writing",
            status="success",
            input={"params": {"chapter_index": 3, "max_context_chars": 1200}},
            output={"status": "ready", "trace_id": trace.id},
            trace_id=trace.id,
            chapter_index=3,
        )
    )
    result_message = DialogMessage(
        dialog_id=dialog.id,
        role="system",
        content="第3章上下文预算预检完成。",
        action_result={
            "type": "preflight_writing",
            "status": "success",
            "data": {"agent_run_id": run.id, "status": "success", "trace_id": trace.id},
        },
    )
    db_session.add(result_message)
    db_session.flush()
    run.response_message_id = result_message.id
    db_session.commit()

    output = inspect_agent_trace_audit(db_session, project.id, run_id=run.id)

    assert output["audit"]["end_to_end_chain_status"] == "complete"
    assert output["end_to_end_chain"] == {
        "status": "complete",
        "coverage": {
            "intent": True,
            "planned_tools": True,
            "executed_tools": True,
            "model_traces": True,
            "result_message": True,
        },
        "intent_chain_status": "available",
        "planned_tool_count": 1,
        "executed_tool_count": 1,
        "matched_tool_count": 1,
        "tool_step_count": 1,
        "model_trace_count": 1,
        "result_message": {
            "status": "available",
            "action_type": "preflight_writing",
            "action_status": "success",
        },
        "segments": [
            {
                "stage": "intent",
                "status": "available",
                "rule_id": "preflight_context_budget_intent",
                "intent_class": "preflight_context_budget",
                "chapter_index": 3,
            },
            {"stage": "planned_tools", "status": "available", "count": 1},
            {"stage": "executed_tools", "status": "available", "count": 1},
            {"stage": "model_traces", "status": "available", "count": 1},
            {
                "stage": "result_message",
                "status": "available",
                "action_type": "preflight_writing",
                "action_status": "success",
            },
        ],
    }
    assert "trace-e2e-secret" not in str(output["end_to_end_chain"])
    assert "budget-secret-key" not in str(output["end_to_end_chain"])
    assert "max_context_chars" not in str(output["end_to_end_chain"])
    assert result_message.id not in str(output["end_to_end_chain"])


def test_inspect_agent_trace_audit_includes_safe_anomaly_summary(db_session):
    project = Project(name="Trace Anomaly Summary")
    db_session.add(project)
    db_session.flush()
    dialog = Dialog(project_id=project.id, dialog_type="hermes", state="running")
    db_session.add(dialog)
    db_session.flush()
    planner_output = {
        "status": "completed",
        "intent_projection": {
            "rule_id": "generate_chapter_intent",
            "candidate": {
                "type": "generate_chapter",
                "params": {
                    "chapter_index": 4,
                    "secret_context_key": "should-not-leak",
                },
            },
        },
        "planner": {
            "intent_class": "generate_chapter",
            "mapped_from_action_type": "generate_chapter",
            "mapped_from_rule_id": "generate_chapter_intent",
            "chapter_index": 4,
        },
        "plan": {
            "tools": [
                {"tool_name": "generate_chapter"},
                {"tool_name": "inspect_agent_memory_route"},
            ]
        },
    }
    run = WritingAgentRun(
        project_id=project.id,
        goal="生成第4章",
        status="success",
        entrypoint="dialog_auto_plan",
        input={"planner": planner_output},
        output={"status": "success"},
        dialog_id=dialog.id,
    )
    db_session.add(run)
    db_session.flush()
    failed_trace = AIModelCallTrace(
        id="trace-anomaly-secret-id",
        project_id=project.id,
        trace_type="chapter_generation",
        status="failed",
        model="deepseek-chat",
        chapter_index=4,
        error_message="provider timeout with secret trace id",
        context_blocks=[
            {
                "key": "secret-context-key",
                "kind": "longform_memory",
                "title": "长篇记忆",
                "content": "这段上下文不应进入异常摘要。",
                "sources": [{"source_id": "source-secret-id"}],
                "truncated": True,
            }
        ],
    )
    db_session.add(failed_trace)
    db_session.flush()
    db_session.add_all(
        [
            WritingAgentStep(
                run_id=run.id,
                project_id=project.id,
                step_index=1,
                tool_name="generate_chapter",
                status="failed",
                input={"params": {"chapter_index": 4}},
                output={"status": "failed", "trace_id": failed_trace.id},
                trace_id=failed_trace.id,
                chapter_index=4,
            ),
            WritingAgentStep(
                id="step-anomaly-secret-id",
                run_id=run.id,
                project_id=project.id,
                step_index=2,
                tool_name="preflight_writing",
                status="success",
                input={"params": {"chapter_index": 4}},
                output={"status": "ready"},
                chapter_index=4,
            ),
        ]
    )
    db_session.commit()

    output = inspect_agent_trace_audit(db_session, project.id, run_id=run.id)

    assert output["audit"]["anomaly_status"] == "failed"
    assert output["audit"]["anomaly_issue_count"] == 6
    assert output["anomaly_summary"] == {
        "status": "failed",
        "issue_count": 6,
        "severity_counts": {"critical": 2, "warning": 3, "info": 1},
        "failed_step_count": 1,
        "failed_trace_count": 1,
        "missing_trace_binding_count": 1,
        "unmatched_planned_tool_count": 1,
        "missing_result_message": True,
        "truncated_context_block_count": 1,
        "issues": [
            {
                "code": "failed_tool_step",
                "severity": "critical",
                "tool_name": "generate_chapter",
                "status": "failed",
                "step_index": 1,
                "chapter_index": 4,
            },
            {
                "code": "failed_model_trace",
                "severity": "critical",
                "trace_type": "chapter_generation",
                "status": "failed",
                "chapter_index": 4,
                "error_recorded": True,
            },
            {
                "code": "missing_trace_binding",
                "severity": "warning",
                "tool_name": "preflight_writing",
                "status": "success",
                "step_index": 2,
                "chapter_index": 4,
            },
            {
                "code": "planned_tool_not_executed",
                "severity": "warning",
                "tool_name": "inspect_agent_memory_route",
            },
            {
                "code": "missing_result_message",
                "severity": "warning",
                "stage": "result_message",
            },
            {
                "code": "truncated_context_block",
                "severity": "info",
                "kind": "longform_memory",
                "title": "长篇记忆",
                "char_count": 14,
                "source_count": 1,
            },
        ],
    }
    assert "trace-anomaly-secret-id" not in str(output["anomaly_summary"])
    assert "step-anomaly-secret-id" not in str(output["anomaly_summary"])
    assert "secret-context-key" not in str(output["anomaly_summary"])
    assert "source-secret-id" not in str(output["anomaly_summary"])
    assert "should-not-leak" not in str(output["anomaly_summary"])
    assert "这段上下文不应进入异常摘要" not in str(output["anomaly_summary"])


def test_inspect_agent_trace_anomaly_trends_aggregates_recent_runs_safely(db_session):
    project = Project(name="Trace Anomaly Trends")
    db_session.add(project)
    db_session.flush()
    base_time = datetime(2026, 6, 3, 8, 0, tzinfo=timezone.utc)
    dialog = Dialog(project_id=project.id, dialog_type="hermes", state="running")
    db_session.add(dialog)
    db_session.flush()

    noisy_run = WritingAgentRun(
        id="run-trend-secret-noisy",
        project_id=project.id,
        goal="生成第5章",
        status="success",
        entrypoint="dialog_auto_plan",
        dialog_id=dialog.id,
        input={
            "planner": {
                "intent_projection": {
                    "rule_id": "generate_chapter_intent",
                    "candidate": {"type": "generate_chapter", "params": {"chapter_index": 5}},
                },
                "planner": {
                    "intent_class": "generate_chapter",
                    "mapped_from_rule_id": "generate_chapter_intent",
                    "chapter_index": 5,
                },
                "plan": {
                    "tools": [
                        {"tool_name": "generate_chapter"},
                        {"tool_name": "inspect_agent_memory_route"},
                    ]
                },
            }
        },
        created_at=base_time + timedelta(minutes=2),
    )
    missing_trace_run = WritingAgentRun(
        id="run-trend-secret-missing-trace",
        project_id=project.id,
        goal="预检第4章",
        status="success",
        entrypoint="dialog_auto_plan",
        created_at=base_time + timedelta(minutes=1),
    )
    clear_run = WritingAgentRun(
        id="run-trend-secret-clear",
        project_id=project.id,
        goal="检查第3章记忆",
        status="success",
        entrypoint="dialog_auto_plan",
        created_at=base_time,
    )
    db_session.add_all([noisy_run, missing_trace_run, clear_run])
    db_session.flush()
    failed_trace = AIModelCallTrace(
        id="trace-trend-secret-failed",
        project_id=project.id,
        trace_type="chapter_generation",
        status="failed",
        model="deepseek-chat",
        chapter_index=5,
        error_message="provider timeout secret",
        context_blocks=[
            {
                "key": "trend-secret-context-key",
                "kind": "longform_memory",
                "title": "长篇记忆",
                "content": "不应进入趋势摘要。",
                "sources": [{"source_id": "trend-source-secret"}],
                "truncated": True,
            }
        ],
    )
    clear_trace = AIModelCallTrace(
        id="trace-trend-secret-clear",
        project_id=project.id,
        trace_type="memory_route",
        status="success",
        model="local",
        chapter_index=3,
        context_blocks=[],
    )
    db_session.add_all([failed_trace, clear_trace])
    db_session.flush()
    db_session.add_all(
        [
            WritingAgentStep(
                id="step-trend-secret-failed",
                run_id=noisy_run.id,
                project_id=project.id,
                step_index=1,
                tool_name="generate_chapter",
                status="failed",
                output={"status": "failed", "trace_id": failed_trace.id},
                trace_id=failed_trace.id,
                chapter_index=5,
            ),
            WritingAgentStep(
                id="step-trend-secret-missing-trace",
                run_id=missing_trace_run.id,
                project_id=project.id,
                step_index=1,
                tool_name="preflight_writing",
                status="success",
                output={"status": "ready"},
                chapter_index=4,
            ),
            WritingAgentStep(
                id="step-trend-secret-clear",
                run_id=clear_run.id,
                project_id=project.id,
                step_index=1,
                tool_name="inspect_agent_memory_route",
                status="success",
                output={"status": "completed", "trace_id": clear_trace.id},
                trace_id=clear_trace.id,
                chapter_index=3,
            ),
        ]
    )
    db_session.commit()

    output = inspect_agent_trace_anomaly_trends(db_session, project.id, limit=5)

    assert output["status"] == "completed"
    assert output["trend"] == {
        "status": "failed",
        "run_count": 3,
        "affected_run_count": 2,
        "issue_count": 6,
        "severity_counts": {"critical": 2, "warning": 3, "info": 1},
        "issue_counts": {
            "failed_tool_step": 1,
            "failed_model_trace": 1,
            "missing_trace_binding": 1,
            "missing_result_message": 1,
            "planned_tool_not_executed": 1,
            "truncated_context_block": 1,
        },
        "dominant_issue_code": "failed_model_trace",
    }
    assert output["filters"] == {"limit": 5, "chapter_index": None}
    assert output["runs"] == [
        {
            "run_index": 1,
            "goal": "生成第5章",
            "status": "success",
            "entrypoint": "dialog_auto_plan",
            "chapter_index": 5,
            "anomaly_status": "failed",
            "issue_count": 5,
            "critical_issue_count": 2,
            "warning_issue_count": 2,
            "info_issue_count": 1,
            "top_issue_codes": [
                "failed_model_trace",
                "failed_tool_step",
                "missing_result_message",
                "planned_tool_not_executed",
                "truncated_context_block",
            ],
        },
        {
            "run_index": 2,
            "goal": "预检第4章",
            "status": "success",
            "entrypoint": "dialog_auto_plan",
            "chapter_index": 4,
            "anomaly_status": "needs_attention",
            "issue_count": 1,
            "critical_issue_count": 0,
            "warning_issue_count": 1,
            "info_issue_count": 0,
            "top_issue_codes": ["missing_trace_binding"],
        },
    ]
    assert output["recommended_next_tools"] == ["inspect_agent_trace_audit", "plan_recovery_tools"]
    assert output["trace"] == {
        "source": "inspect_agent_trace_anomaly_trends",
        "version": "phase74.agent_trace_anomaly_trends.v1",
        "mutability": "read",
    }
    assert "run-trend-secret" not in str(output)
    assert "trace-trend-secret" not in str(output)
    assert "step-trend-secret" not in str(output)
    assert "trend-secret-context-key" not in str(output)
    assert "trend-source-secret" not in str(output)
    assert "不应进入趋势摘要" not in str(output)


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
                        "next_tool": "prepare_repair_longform_maintenance",
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
            "tool_name": "prepare_repair_longform_maintenance",
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
    trace = AIModelCallTrace(
        id="trace-chain",
        project_id=project.id,
        trace_type="chapter_generation",
        status="success",
        model="deepseek-chat",
        chapter_index=2,
        context_blocks=[{"key": "outline", "content": "第2章承接灯塔记忆线索。"}],
    )
    db_session.add(trace)
    db_session.flush()
    db_session.add(
        WritingAgentStep(
            run_id=run.id,
            project_id=project.id,
            step_index=1,
            tool_name="generate_chapter",
            status="success",
            input={"params": {"chapter_index": 2}},
            output={
                "status": "success",
                "trace_id": trace.id,
                "approval_verification_event": {
                    "event_type": "contract_verified",
                    "status": "ready",
                    "reason": "approval_contract_verified",
                    "approval_contract_bound": True,
                    "approval_contract_version": "phase108.agent_plan_approval_contract.v1",
                    "write_step_count": 1,
                    "tool_call_ids": ["toolcall:test"],
                    "resource_bindings": [
                        {
                            "tool_call_id": "toolcall:test",
                            "tool_name": "generate_chapter",
                            "target_type": "chapter",
                            "target_id": "chapter:2",
                            "source_plan_id": "plan:direct",
                            "source_step_id": "step:write",
                            "binding_source": "server_derived",
                        }
                    ],
                },
            },
            trace_id=trace.id,
            target_type="chapter",
            target_id="chapter-2",
            chapter_index=2,
            tool_call_id="toolcall:test",
            resource_binding={
                "tool_call_id": "toolcall:test",
                "tool_name": "generate_chapter",
                "target_type": "chapter",
                "target_id": "chapter:2",
                "source_plan_id": "plan:direct",
                "source_step_id": "step:write",
                "binding_source": "server_derived",
            },
        )
    )
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
                    "chapter_index": 2,
                    "chapter_index_source": "inferred_next_unwritten",
                    "chapter_target_conflict": {
                        "status": "reserved",
                        "chapter_index": 2,
                        "reason": "pending_or_running_generation",
                        "source": "range_task",
                        "source_label": "批量生成任务",
                    },
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
            "chapter_index": 2,
            "chapter_index_source": "inferred_next_unwritten",
            "chapter_index_source_label": "系统推断",
            "chapter_target_conflict": {
                "status": "reserved",
                "chapter_index": 2,
                "reason": "pending_or_running_generation",
                "source": "range_task",
                "source_label": "批量生成任务",
            },
            "approval_contract_bound": True,
            "approval_contract_version": "phase108.agent_plan_approval_contract.v1",
            "resolved_at": "2026-05-22T12:00:00+00:00",
        }
    ]
    assert "approval:secret-hash" not in str(output["approval_events"])
    assert output["audit"]["approval_event_count"] == 1
    assert [event["event_type"] for event in output["event_chain"]] == [
        "approval_decision",
        "run_dispatched",
        "tool_step",
        "contract_verified",
        "trace_attached",
        "result_message",
    ]
    assert output["event_chain"][0]["decision_label"] == "已确认"
    assert output["event_chain"][0]["chapter_index"] == 2
    assert output["event_chain"][0]["chapter_index_source"] == "inferred_next_unwritten"
    assert output["event_chain"][0]["chapter_index_source_label"] == "系统推断"
    assert output["event_chain"][0]["chapter_target_conflict"] == {
        "status": "reserved",
        "chapter_index": 2,
        "reason": "pending_or_running_generation",
        "source": "range_task",
        "source_label": "批量生成任务",
    }
    assert output["event_chain"][1]["run_id"] == run.id
    assert output["event_chain"][2]["tool_name"] == "generate_chapter"
    assert output["event_chain"][2]["tool_call_id"] == "toolcall:test"
    assert output["event_chain"][2]["resource_binding"]["target_id"] == "chapter:2"
    assert output["event_chain"][3]["reason"] == "approval_contract_verified"
    assert output["event_chain"][3]["tool_call_ids"] == ["toolcall:test"]
    assert output["event_chain"][3]["resource_bindings"][0]["target_id"] == "chapter:2"
    assert output["event_chain"][4]["trace_id"] == "trace-chain"
    assert output["event_chain"][5]["message_id"] == result_message.id
    assert "approval:secret-hash" not in str(output["event_chain"])
    assert output["steps"][0]["tool_call_id"] == "toolcall:test"
    assert output["steps"][0]["resource_binding"]["target_id"] == "chapter:2"
    assert output["audit"]["event_chain_count"] == 6


def test_inspect_agent_trace_audit_includes_dialog_route_decision_events(db_session):
    project = Project(name="Trace Audit Route Decisions")
    db_session.add(project)
    db_session.flush()
    dialog = Dialog(project_id=project.id, dialog_type="hermes", state="chatting")
    db_session.add(dialog)
    db_session.flush()
    request_message = DialogMessage(dialog_id=dialog.id, role="user", content="继续吧")
    response_message = DialogMessage(
        dialog_id=dialog.id,
        role="assistant",
        content="上一轮 Agent 运行存在可恢复阻塞，我已先规划恢复工具链。",
        meta={
            "dialog_route_decision": {
                "version": "phase20.dialog_continue_route_decision.v1",
                "trigger": "low_detail_continue",
                "selected_route": "recover_blocked_run",
                "reason_code": "recoverable_run_found",
                "priority": ["recover_blocked_run", "recommended_followups", "chapter_generation"],
                "source_run_id": "blocked-run",
            }
        },
    )
    db_session.add_all([request_message, response_message])
    db_session.flush()
    run = WritingAgentRun(
        project_id=project.id,
        goal="恢复上一轮阻塞",
        status="success",
        entrypoint="dialog_auto_plan",
        dialog_id=dialog.id,
        request_message_id=request_message.id,
    )
    db_session.add(run)
    db_session.flush()
    trace = AIModelCallTrace(
        id="trace-route-decision",
        project_id=project.id,
        trace_type="dialog_route_decision",
        status="success",
        model="local-dialog-router",
        dialog_id=dialog.id,
        request_message_id=request_message.id,
        response_message_id=response_message.id,
        trace_metadata={
            "dialog_route_decision": response_message.meta["dialog_route_decision"],
            "agent_run_id": run.id,
            "source_run_id": "blocked-run",
            "action_type": "plan_recovery_tools",
        },
    )
    db_session.add(trace)
    db_session.commit()

    output = inspect_agent_trace_audit(db_session, project.id, run_id=run.id)

    assert output["audit"]["dialog_route_event_count"] == 1
    assert output["dialog_route_events"] == [
        {
            "trace_id": "trace-route-decision",
            "trace_type": "dialog_route_decision",
            "status": "success",
            "model": "local-dialog-router",
            "action_type": "plan_recovery_tools",
            "selected_route": "recover_blocked_run",
            "selected_route_label": "恢复阻塞运行",
            "reason_code": "recoverable_run_found",
            "reason_label": "发现可恢复的阻塞运行",
            "source_run_id": "blocked-run",
            "request_message_id": request_message.id,
            "response_message_id": response_message.id,
        }
    ]
    assert output["event_chain"][0] == {
        "event_type": "dialog_route_decision",
        "trace_id": "trace-route-decision",
        "action_type": "plan_recovery_tools",
        "selected_route": "recover_blocked_run",
        "selected_route_label": "恢复阻塞运行",
        "reason_code": "recoverable_run_found",
        "reason_label": "发现可恢复的阻塞运行",
        "source_run_id": "blocked-run",
        "request_message_id": request_message.id,
        "response_message_id": response_message.id,
    }
    assert "priority" not in str(output["dialog_route_events"])
