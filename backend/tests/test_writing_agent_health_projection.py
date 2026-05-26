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


def test_inspect_agent_health_projection_surfaces_command_contract_gap(db_session, monkeypatch):
    project = Project(name="Agent Health Command Contracts")
    db_session.add(project)
    db_session.commit()
    _patch_ready_sources(monkeypatch)
    monkeypatch.setattr(
        agent_health_projection,
        "inspect_agent_command_contracts",
        lambda **kwargs: {
            "status": "completed",
            "summary": {
                "total_commands": 8,
                "agent_control_commands": 2,
                "commands_with_control_projection": 1,
                "gap_count": 1,
            },
            "gaps": [{"code": "missing_control_projection_type", "command_name": "continue"}],
            "recommended_next_tools": ["inspect_agent_command_contracts"],
        },
        raising=False,
    )

    output = agent_health_projection.inspect_agent_health_projection(
        db_session,
        project.id,
        adapter_metadata_by_name={},
        static_adapter_tool_names=set(),
        action_execution_tool_names=set(),
    )

    assert output["status"] == "degraded"
    assert output["command_contracts"]["summary"]["gap_count"] == 1
    diagnostic = next(item for item in output["diagnostics"] if item["code"] == "agent_command_contract_gaps")
    assert diagnostic["severity"] == "warning"
    assert diagnostic["gap_count"] == 1
    assert "inspect_agent_control_plane_readiness" in output["recommended_tools"]
    assert "inspect_agent_command_contracts" in output["recommended_tools"]


def test_inspect_agent_health_projection_includes_control_plane_readiness(db_session, monkeypatch):
    project = Project(name="Agent Health Control Plane")
    db_session.add(project)
    db_session.commit()
    _patch_ready_sources(monkeypatch)
    monkeypatch.setattr(agent_health_projection, "build_agent_tool_plan", _tool_plan_with_passed_profile_policy)

    output = agent_health_projection.inspect_agent_health_projection(
        db_session,
        project.id,
        adapter_metadata_by_name={},
        static_adapter_tool_names=set(),
        action_execution_tool_names=set(),
    )

    readiness = output["control_plane_readiness"]
    assert readiness["status"] == "ready"
    assert readiness["summary"]["agent_control_commands"] == 2
    assert readiness["summary"]["command_gap_count"] == 0
    assert readiness["summary"]["total_gap_count"] == 0
    assert readiness["recommended_next_tools"] == ["inspect_agent_health_projection"]


def test_inspect_agent_health_projection_control_plane_readiness_tracks_command_gaps(db_session, monkeypatch):
    project = Project(name="Agent Health Control Plane Gap")
    db_session.add(project)
    db_session.commit()
    _patch_ready_sources(monkeypatch)
    monkeypatch.setattr(
        agent_health_projection,
        "inspect_agent_command_contracts",
        lambda **kwargs: {
            "status": "completed",
            "summary": {
                "total_commands": 8,
                "agent_control_commands": 2,
                "commands_with_control_projection": 1,
                "gap_count": 1,
            },
            "gaps": [{"code": "missing_control_projection_type", "command_name": "continue"}],
            "recommended_next_tools": ["inspect_agent_command_contracts"],
        },
        raising=False,
    )

    output = agent_health_projection.inspect_agent_health_projection(
        db_session,
        project.id,
        adapter_metadata_by_name={},
        static_adapter_tool_names=set(),
        action_execution_tool_names=set(),
    )

    readiness = output["control_plane_readiness"]
    assert readiness["status"] == "degraded"
    assert readiness["summary"]["command_gap_count"] == 1
    assert readiness["summary"]["total_gap_count"] == 1
    assert "inspect_agent_command_contracts" in readiness["recommended_next_tools"]


def test_inspect_agent_health_projection_surfaces_latest_run_loop_risk(db_session, monkeypatch):
    project = Project(name="Agent Health Loop Risk")
    db_session.add(project)
    db_session.flush()
    run = WritingAgentRun(
        project_id=project.id,
        goal="重复查看工具面",
        status="success",
        entrypoint="api",
        input={
            "tools": [
                {"tool_name": "describe_agent_tools", "params": {"chapter_index": 1}},
                {"tool_name": "describe_agent_tools", "params": {"chapter_index": 1}},
                {"tool_name": "describe_agent_tools", "params": {"chapter_index": 1}},
            ]
        },
    )
    db_session.add(run)
    db_session.flush()
    for index in range(1, 4):
        db_session.add(
            WritingAgentStep(
                run_id=run.id,
                project_id=project.id,
                step_index=index,
                tool_name="describe_agent_tools",
                status="success",
                input={"params": {"chapter_index": 1}},
                output={"status": "completed"},
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

    assert output["loop_risk"]["status"] == "warning"
    assert output["loop_risk"]["detector"] == "generic_repeat"
    assert output["loop_risk"]["detectors"][0]["evidence"][0]["tool_name"] == "describe_agent_tools"
    assert output["loop_risk"]["recommended_next_action"]["next_tool"] == "inspect_agent_health_projection"
    diagnostic = next(item for item in output["diagnostics"] if item["code"] == "agent_loop_risk_warning")
    assert diagnostic["detector"] == "generic_repeat"
    assert "inspect_agent_trace_audit" in output["recommended_tools"]


def test_inspect_agent_health_projection_reports_creative_quality_insufficient_data(db_session, monkeypatch):
    project = Project(name="Agent Health Quality Sparse")
    db_session.add(project)
    db_session.commit()
    _patch_ready_sources(monkeypatch)
    monkeypatch.setattr(agent_health_projection, "build_agent_tool_plan", _tool_plan_with_passed_profile_policy)

    output = agent_health_projection.inspect_agent_health_projection(
        db_session,
        project.id,
        adapter_metadata_by_name={},
        static_adapter_tool_names=set(),
        action_execution_tool_names=set(),
    )

    assert output["creative_quality"] == {
        "status": "insufficient_data",
        "trend": "insufficient_data",
        "window": {"chapter_count": 0, "review_step_count": 0, "latest_chapter_index": None},
        "chapters": [],
        "recommended_next_tools": ["review_chapter_quality", "review_chapter_continuity"],
    }


def test_inspect_agent_health_projection_reports_creative_quality_clear_window(db_session, monkeypatch):
    project = Project(name="Agent Health Quality Clear")
    db_session.add(project)
    db_session.flush()
    _seed_review_step(db_session, project.id, 1, "review_chapter_quality", "ready")
    _seed_review_step(db_session, project.id, 1, "review_chapter_continuity", "ready")
    _seed_review_step(db_session, project.id, 2, "review_chapter_quality", "ready")
    _seed_review_step(db_session, project.id, 2, "review_chapter_continuity", "ready")
    db_session.commit()
    _patch_ready_sources(monkeypatch)
    monkeypatch.setattr(agent_health_projection, "build_agent_tool_plan", _tool_plan_with_passed_profile_policy)

    output = agent_health_projection.inspect_agent_health_projection(
        db_session,
        project.id,
        adapter_metadata_by_name={},
        static_adapter_tool_names=set(),
        action_execution_tool_names=set(),
    )

    assert output["creative_quality"]["status"] == "ready"
    assert output["creative_quality"]["trend"] == "clear"
    assert output["creative_quality"]["window"] == {
        "chapter_count": 2,
        "review_step_count": 4,
        "latest_chapter_index": 2,
    }
    assert [chapter["risk_score"] for chapter in output["creative_quality"]["chapters"]] == [0, 0]
    assert not any(item["code"] == "creative_quality_risk_rising" for item in output["diagnostics"])


def test_inspect_agent_health_projection_reports_creative_quality_risk_rising(db_session, monkeypatch):
    project = Project(name="Agent Health Quality Rising")
    db_session.add(project)
    db_session.flush()
    _seed_review_step(db_session, project.id, 1, "review_chapter_quality", "ready")
    _seed_review_step(db_session, project.id, 2, "review_chapter_quality", "warning", warnings=1, code="known_typo")
    _seed_review_step(
        db_session,
        project.id,
        3,
        "review_chapter_continuity",
        "blocked",
        blockers=1,
        code="timeline_anchor_conflict",
    )
    db_session.commit()
    _patch_ready_sources(monkeypatch)
    monkeypatch.setattr(agent_health_projection, "build_agent_tool_plan", _tool_plan_with_passed_profile_policy)

    output = agent_health_projection.inspect_agent_health_projection(
        db_session,
        project.id,
        adapter_metadata_by_name={},
        static_adapter_tool_names=set(),
        action_execution_tool_names=set(),
    )

    assert output["creative_quality"]["status"] == "needs_attention"
    assert output["creative_quality"]["trend"] == "risk_rising"
    assert [chapter["risk_score"] for chapter in output["creative_quality"]["chapters"]] == [0, 1, 3]
    diagnostic = next(item for item in output["diagnostics"] if item["code"] == "creative_quality_risk_rising")
    assert diagnostic["latest_chapter_index"] == 3
    assert diagnostic["severity"] == "error"
    assert "review_chapter_quality" in output["recommended_tools"]
    assert "review_chapter_continuity" in output["recommended_tools"]
    assert "plan_chapter_revision" in output["recommended_tools"]


def test_inspect_agent_health_projection_reports_context_compression_warning(db_session, monkeypatch):
    project = Project(name="Agent Health Context Compression")
    db_session.add(project)
    db_session.commit()
    _patch_ready_sources(monkeypatch)
    monkeypatch.setattr(agent_health_projection, "build_agent_tool_plan", _tool_plan_with_passed_profile_policy)
    monkeypatch.setattr(
        agent_health_projection,
        "inspect_agent_context_compression_projection",
        lambda *args, **kwargs: {
            "status": "warning",
            "strategy": {"granularity": "chapter_window"},
            "summary": {"usage_ratio": 0.95, "prompt_context_chars": 3800, "max_chars": 4000},
            "risks": [{"code": "context_window_pressure", "severity": "warning"}],
            "recommended_next_tools": ["summarize_longform_context", "inspect_agent_memory_route"],
            "recovery": {
                "status": "optional",
                "reason": "context_compression_window_pressure",
                "next_tools": ["summarize_longform_context", "inspect_agent_memory_route"],
                "tools": [],
            },
        },
        raising=False,
    )

    output = agent_health_projection.inspect_agent_health_projection(
        db_session,
        project.id,
        chapter_index=4,
        adapter_metadata_by_name={},
        static_adapter_tool_names=set(),
        action_execution_tool_names=set(),
    )

    assert output["context_compression"]["status"] == "warning"
    diagnostic = next(item for item in output["diagnostics"] if item["code"] == "agent_context_compression_warning")
    assert diagnostic["severity"] == "warning"
    assert diagnostic["risk_codes"] == ["context_window_pressure"]
    assert "summarize_longform_context" in output["recommended_tools"]
    assert "inspect_agent_memory_route" in output["recommended_tools"]


def test_inspect_agent_health_projection_reports_memory_activation_debt(db_session, monkeypatch):
    project = Project(name="Agent Health Memory Activation")
    db_session.add(project)
    db_session.commit()
    _patch_ready_sources(monkeypatch)
    monkeypatch.setattr(agent_health_projection, "build_agent_tool_plan", _tool_plan_with_passed_profile_policy)
    monkeypatch.setattr(
        agent_health_projection,
        "build_memory_activation_plan",
        lambda *args, **kwargs: {
            "status": "degraded",
            "coverage": {
                "memory_coverage_debt": {
                    "status": "degraded",
                    "issue_count": 2,
                    "missing_memory_count": 1,
                    "missing_retrieval_count": 1,
                },
                "activated_counts": {"longform": 1, "foreshadowing": 0, "world_model": 0, "style": 0},
            },
            "risks": [{"code": "memory_coverage_debt", "severity": "warning"}],
            "recommended_next_tools": ["repair_longform_maintenance", "inspect_agent_memory_route"],
        },
        raising=False,
    )

    output = agent_health_projection.inspect_agent_health_projection(
        db_session,
        project.id,
        chapter_index=3,
        adapter_metadata_by_name={},
        static_adapter_tool_names=set(),
        action_execution_tool_names=set(),
    )

    assert output["memory_activation"]["status"] == "degraded"
    diagnostic = next(item for item in output["diagnostics"] if item["code"] == "agent_memory_activation_degraded")
    assert diagnostic["severity"] == "warning"
    assert diagnostic["risk_codes"] == ["memory_coverage_debt"]
    assert "repair_longform_maintenance" in output["recommended_tools"]
    assert "inspect_agent_memory_route" in output["recommended_tools"]


def test_inspect_agent_health_projection_closes_generate_review_diagnose_recovery_fixture(db_session, monkeypatch):
    project = Project(name="Agent Health Closed Loop")
    db_session.add(project)
    db_session.flush()
    _seed_review_step(db_session, project.id, 1, "review_chapter_quality", "ready")
    run = WritingAgentRun(
        project_id=project.id,
        goal="生成、审查、诊断并给出恢复建议",
        status="success",
        entrypoint="api",
        input={
            "tools": [
                {"tool_name": "generate_chapter", "params": {"chapter_index": 2}},
                {"tool_name": "review_chapter_quality", "params": {"chapter_index": 2}},
                {"tool_name": "review_chapter_continuity", "params": {"chapter_index": 2}},
                {"tool_name": "inspect_agent_health_projection", "params": {"run_id": "self"}},
            ]
        },
    )
    db_session.add(run)
    db_session.flush()
    db_session.add_all(
        [
            WritingAgentStep(
                run_id=run.id,
                project_id=project.id,
                step_index=1,
                tool_name="generate_chapter",
                status="success",
                input={"params": {"chapter_index": 2}},
                output={"status": "success", "chapter_index": 2},
                chapter_index=2,
            ),
            WritingAgentStep(
                run_id=run.id,
                project_id=project.id,
                step_index=2,
                tool_name="review_chapter_quality",
                status="success",
                input={"params": {"chapter_index": 2}},
                output={
                    "status": "warning",
                    "chapter_index": 2,
                    "finding_count": 1,
                    "warning_count": 1,
                    "blocker_count": 0,
                    "findings": [
                        {
                            "code": "scene_density_low",
                            "severity": "warning",
                            "message": "场景密度不足。",
                            "evidence": {},
                        }
                    ],
                },
                chapter_index=2,
            ),
            WritingAgentStep(
                run_id=run.id,
                project_id=project.id,
                step_index=3,
                tool_name="review_chapter_continuity",
                status="success",
                input={"params": {"chapter_index": 2}},
                output={
                    "status": "blocked",
                    "chapter_index": 2,
                    "finding_count": 1,
                    "warning_count": 0,
                    "blocker_count": 1,
                    "findings": [
                        {
                            "code": "timeline_anchor_conflict",
                            "severity": "blocker",
                            "message": "时间锚点冲突。",
                            "evidence": {},
                        }
                    ],
                },
                chapter_index=2,
            ),
        ]
    )
    for step_index in range(4, 7):
        db_session.add(
            WritingAgentStep(
                run_id=run.id,
                project_id=project.id,
                step_index=step_index,
                tool_name="inspect_agent_health_projection",
                status="success",
                input={"params": {"run_id": run.id}},
                output={"status": "completed"},
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

    diagnostic_codes = {item["code"] for item in output["diagnostics"]}
    assert output["loop_risk"]["status"] == "warning"
    assert output["loop_risk"]["recommended_next_action"]["next_tool"] == "inspect_agent_health_projection"
    assert output["creative_quality"]["trend"] == "risk_rising"
    assert {"agent_loop_risk_warning", "creative_quality_risk_rising"}.issubset(diagnostic_codes)
    assert "inspect_agent_trace_audit" in output["recommended_tools"]
    assert "review_chapter_quality" in output["recommended_tools"]
    assert "review_chapter_continuity" in output["recommended_tools"]
    assert "plan_chapter_revision" in output["recommended_tools"]


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
    monkeypatch.setattr(
        agent_health_projection,
        "build_memory_activation_plan",
        lambda *args, **kwargs: {
            "status": "ready",
            "coverage": {
                "memory_coverage_debt": {"status": "ready", "issue_count": 0},
                "activated_counts": {"longform": 0, "foreshadowing": 0, "world_model": 0, "style": 0},
            },
            "risks": [],
            "recommended_next_tools": ["preflight_writing", "generate_chapter"],
        },
        raising=False,
    )
    monkeypatch.setattr(
        agent_health_projection,
        "inspect_agent_command_contracts",
        lambda **kwargs: {
            "status": "completed",
            "summary": {
                "total_commands": 8,
                "agent_control_commands": 2,
                "commands_with_control_projection": 2,
                "gap_count": 0,
            },
            "gaps": [],
            "recommended_next_tools": ["inspect_agent_command_contracts"],
        },
        raising=False,
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


def _seed_review_step(
    db_session,
    project_id,
    chapter_index,
    tool_name,
    status,
    *,
    warnings=0,
    blockers=0,
    code="quality_signal",
):
    run = WritingAgentRun(project_id=project_id, goal=f"review {chapter_index}", status="success", entrypoint="api")
    db_session.add(run)
    db_session.flush()
    findings = []
    findings.extend({"code": code, "severity": "warning", "message": "warning", "evidence": {}} for _ in range(warnings))
    findings.extend({"code": code, "severity": "blocker", "message": "blocker", "evidence": {}} for _ in range(blockers))
    db_session.add(
        WritingAgentStep(
            run_id=run.id,
            project_id=project_id,
            step_index=1,
            tool_name=tool_name,
            status="success",
            input={"params": {"chapter_index": chapter_index}},
            output={
                "status": status,
                "chapter_index": chapter_index,
                "finding_count": len(findings),
                "warning_count": warnings,
                "blocker_count": blockers,
                "findings": findings,
            },
            chapter_index=chapter_index,
        )
    )
