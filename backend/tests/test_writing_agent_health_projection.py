from app.models import Project, WritingAgentRun, WritingAgentStep
from app.services.writing_agent import agent_health_projection


def test_inspect_agent_health_projection_surfaces_profile_policy_issue_without_delegate_edges(db_session, monkeypatch):
    project = Project(name="Agent Health Profile Policy")
    db_session.add(project)
    db_session.commit()
    _patch_ready_sources(monkeypatch)
    monkeypatch.setattr(agent_health_projection, "build_agent_tool_plan", _tool_plan_with_profile_policy_issue)

    output = agent_health_projection.inspect_agent_health_projection(
        db_session,
        project.id,
        adapter_metadata_by_name={},
        static_adapter_tool_names=set(),
        action_execution_tool_names=set(),
    )

    assert output["status"] == "needs_attention"
    assert output["profile_policy"]["status"] == "needs_attention"
    assert output["profile_policy"]["summary"]["issues"] == 1
    assert output["profile_policy"]["issues"][0]["code"] == "delegate_target_missing_definition"
    assert "delegate_edges" not in output["profile_policy"]
    assert any(item["code"] == "agent_profile_policy_needs_attention" for item in output["diagnostics"])
    assert "describe_agent_tools" in output["recommended_tools"]


def test_inspect_agent_health_projection_imports_trace_profile_policy_status(db_session, monkeypatch):
    project = Project(name="Agent Health Trace Audit")
    db_session.add(project)
    db_session.flush()
    run = WritingAgentRun(project_id=project.id, goal="检查上一轮", status="success", entrypoint="api")
    db_session.add(run)
    db_session.flush()
    db_session.add(
        WritingAgentStep(
            run_id=run.id,
            project_id=project.id,
            step_index=1,
            tool_name="describe_agent_tools",
            status="success",
            output={
                "status": "completed",
                "agent_profile_tool_projection": {
                    "consistency_audit": {
                        "version": "phase215.agent_profile_policy_audit.v1",
                        "status": "needs_attention",
                        "summary": {"issues": 1, "delegate_edges": 1},
                        "issues": [
                            {
                                "code": "delegate_target_missing_tool_rule",
                                "severity": "error",
                                "profile": "orchestrator",
                                "target": "ghost_worker",
                            }
                        ],
                        "delegate_edges": [{"source": "orchestrator", "target": "ghost_worker"}],
                    }
                },
            },
        )
    )
    db_session.commit()
    _patch_ready_sources(monkeypatch)
    monkeypatch.setattr(agent_health_projection, "build_agent_tool_plan", _tool_plan_with_passed_profile_policy)

    output = agent_health_projection.inspect_agent_health_projection(
        db_session,
        project.id,
        run_id=run.id,
        adapter_metadata_by_name={},
        static_adapter_tool_names=set(),
        action_execution_tool_names=set(),
    )

    assert output["trace_audit"]["run_id"] == run.id
    assert output["trace_audit"]["profile_policy_status"] == "needs_attention"
    assert output["trace_audit"]["profile_policy_issue_count"] == 1
    assert any(item["code"] == "latest_run_profile_policy_needs_attention" for item in output["diagnostics"])
    assert "inspect_agent_trace_audit" in output["recommended_tools"]


def _patch_ready_sources(monkeypatch):
    monkeypatch.setattr(
        agent_health_projection,
        "inspect_agent_route_preference_projection",
        lambda **kwargs: {
            "status": "ready",
            "summary": {
                "route_count": 4,
                "recommended_migration_count": 0,
                "missing_preferred_tool_count": 0,
            },
            "trace": {"missing_preferred_tools": []},
        },
    )
    monkeypatch.setattr(
        agent_health_projection,
        "build_agent_tool_contract_snapshot",
        lambda **kwargs: {
            "status": "completed",
            "summary": {"gap_count": 0, "tools_needing_work": 0},
            "coverage": {},
            "recommended_next_steps": [],
        },
    )
    monkeypatch.setattr(
        agent_health_projection,
        "inspect_agent_write_gate_coverage",
        lambda **kwargs: {
            "status": "completed",
            "summary": {
                "high_risk_direct_write_count": 0,
                "missing_agent_plan_gate_count": 0,
            },
            "recommended_next_targets": [],
        },
    )


def _tool_plan_with_profile_policy_issue(*args, **kwargs):
    return {
        "agent_profile_tool_projection": {
            "consistency_audit": {
                "version": "phase215.agent_profile_policy_audit.v1",
                "status": "needs_attention",
                "summary": {"issues": 1, "delegate_edges": 1},
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
        }
    }


def _tool_plan_with_passed_profile_policy(*args, **kwargs):
    return {
        "agent_profile_tool_projection": {
            "consistency_audit": {
                "version": "phase215.agent_profile_policy_audit.v1",
                "status": "passed",
                "summary": {"issues": 0, "delegate_edges": 4},
                "issues": [],
                "delegate_edges": [{"source": "orchestrator", "target": "drafting_worker"}],
            }
        }
    }
