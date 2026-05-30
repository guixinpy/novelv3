import json
from unittest.mock import AsyncMock, patch

from app.core.athena_longform import import_setup_to_world_model
from app.core.world_contracts import DERIVED
from app.core.world_proposal_service import create_bundle, write_candidate_fact
from app.models import (
    AIModelCallTrace,
    BackgroundTask,
    ChapterContent,
    ChapterRevision,
    LongformMemory,
    Outline,
    Project,
    ProjectProfileVersion,
    RevisionAnnotation,
    RevisionCorrection,
    Setup,
    Storyline,
    Version,
    WorldFactClaim,
    WorldProposalItem,
    WorldProposalReview,
    WritingAgentRun,
    WritingAgentStep,
)
from app.schemas.world_proposals import ProposalCandidateFactCreate
from app.services.writing_agent.memory_provenance_contract import MEMORY_PROVENANCE_REQUIRED_FIELDS
from app.services.writing_agent.approval_contract import build_agent_plan_approval_contract


def test_writing_agent_run_and_step_persist(client, db_session):
    project = Project(name="Agent Persist")
    db_session.add(project)
    db_session.flush()

    run = WritingAgentRun(
        project_id=project.id,
        goal="生成第2章",
        status="running",
        entrypoint="api",
        input={"chapter_index": 2},
    )
    db_session.add(run)
    db_session.flush()
    db_session.add(
        AIModelCallTrace(id="trace-1", project_id=project.id, trace_type="chapter_generation", status="success")
    )
    step = WritingAgentStep(
        run_id=run.id,
        project_id=project.id,
        step_index=1,
        tool_name="generate_chapter",
        status="success",
        input={"params": {"chapter_index": 2}},
        output={"trace_id": "trace-1"},
        trace_id="trace-1",
        target_type="chapter",
        target_id="chapter-1",
        chapter_index=2,
    )
    db_session.add(step)
    db_session.commit()

    saved_run = db_session.query(WritingAgentRun).filter_by(project_id=project.id).one()
    saved_step = db_session.query(WritingAgentStep).filter_by(run_id=saved_run.id).one()

    assert saved_run.goal == "生成第2章"
    assert saved_run.input == {"chapter_index": 2}
    assert saved_step.tool_name == "generate_chapter"
    assert saved_step.output == {"trace_id": "trace-1"}


def test_create_agent_run_blocks_direct_setup_without_approval(client, db_session, monkeypatch):
    project_id = _create_project(client, "Agent API")
    _create_trace(db_session, project_id, "trace-setup", "setup_generation")
    calls: list[str] = []

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append(action_type)
        return {"status": "success", "trace_id": "trace-setup"}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "生成设定",
            "tools": [{"tool_name": "generate_setup", "command_args": "城市悬疑"}],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "blocked"
    assert payload["goal"] == "生成设定"
    assert len(payload["steps"]) == 1
    assert payload["steps"][0]["tool_name"] == "generate_setup"
    assert payload["steps"][0]["status"] == "blocked"
    assert payload["steps"][0]["trace_id"] is None
    assert payload["steps"][0]["output"]["reason"] == "approval_required_before_write"
    assert payload["steps"][0]["output"]["recommended_next_tools"] == ["prepare_generate_setup_execution"]
    envelope = payload["steps"][0]["output"]["agent_tool_result"]
    assert envelope["execution_route"] == "static_adapter"
    assert envelope["adapter"]["write_policy"] == "approval_required_redirect"
    assert calls == []


def test_planner_continuation_blocks_unapproved_write_tools(client):
    project_id = _create_project(client, "Planner Continuation Guard")

    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "执行规划工具链：修订章节",
            "entrypoint": "ui_planner_continuation_execute",
            "tools": [
                {
                    "tool_name": "apply_planner_revision_patch",
                    "params": {"chapter_index": 1},
                    "planner": {"plan_id": "plan:revision-1"},
                }
            ],
            "input": {
                "planner_continuation": True,
                "source_run_id": "run-source-1",
                "source_plan_id": "plan:revision-1",
                "planner": {
                    "trace": {"plan_id": "plan:revision-1"},
                    "approval_contract": {
                        "status": "not_required",
                        "write_steps": [],
                    },
                },
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "blocked"
    assert payload["error"] == "Planner continuation requires approval"
    assert [step["tool_name"] for step in payload["steps"]] == ["apply_planner_revision_patch"]
    step = payload["steps"][0]
    assert step["status"] == "blocked"
    output = step["output"]
    assert output["status"] == "blocked"
    assert output["reason"] == "planner_continuation_requires_approval"
    assert output["source_run_id"] == "run-source-1"
    assert output["source_plan_id"] == "plan:revision-1"
    assert output["blocked_tool"] == "apply_planner_revision_patch"
    assert output["approval_contract_status"] == "not_required"
    assert output["tool_execution_metadata"] == {
        "mutability": "guarded_write",
        "requires_confirmation": True,
    }
    assert output["recommended_next_tools"] == [
        "preview_agent_plan_approval_contract",
        "verify_agent_plan_approval_contract",
    ]


def test_planner_continuation_allows_read_approval_preview(client):
    project_id = _create_project(client, "Planner Continuation Read Guard")
    plan = {
        "project_id": project_id,
        "trace": {
            "plan_id": "plan:revision-preview",
            "source_projection_id": "projection:revision-preview",
            "planner_version": "phase53.context_gate.v1",
        },
        "steps": [
            {
                "step_index": 1,
                "step_id": "step:write",
                "tool_name": "apply_planner_revision_patch",
                "params": {"chapter_index": 1},
                "mutability": "guarded_write",
                "requires_confirmation": True,
            }
        ],
    }

    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "预览规划审批契约",
            "entrypoint": "ui_planner_continuation_execute",
            "tools": [
                {
                    "tool_name": "preview_agent_plan_approval_contract",
                    "params": {"plan": plan},
                    "planner": {"plan_id": "plan:revision-preview"},
                }
            ],
            "input": {
                "planner_continuation": True,
                "source_run_id": "run-source-2",
                "source_plan_id": "plan:revision-preview",
                "planner": {
                    "trace": {"plan_id": "plan:revision-preview"},
                    "approval_contract": {
                        "status": "requires_confirmation",
                        "write_steps": plan["steps"],
                    },
                },
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    step = payload["steps"][0]
    assert step["tool_name"] == "preview_agent_plan_approval_contract"
    assert step["status"] == "success"
    assert step["target_type"] == "agent_plan_approval_contract"
    assert step["output"]["status"] == "requires_confirmation"
    assert step["output"]["write_step_count"] == 1


def test_planner_continuation_executes_confirmed_write_tool_after_contract_verification(
    client,
    db_session,
    monkeypatch,
):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    calls = []

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append((action_type, project_id, command_args, action_params))
        return {"status": "success", "chapter_index": 2, "trace_id": "trace-generated-2"}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)
    plan = _planner_generate_chapter_plan(project.id, chapter_index=2)
    approval_hash = plan["approval_contract"]["approval"]["approval_contract_hash"]

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "执行已审批规划工具链：续写章节",
            "entrypoint": "ui_planner_continuation_execute",
            "tools": plan["tools"],
            "input": {
                "planner_continuation": True,
                "source_run_id": "run-source-approved",
                "source_plan_id": plan["trace"]["plan_id"],
                "confirm_execute": True,
                "approval_contract_hash": approval_hash,
                "approval_contract": plan["approval_contract"],
                "planner": plan,
            },
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "success"
    step = payload["steps"][0]
    assert step["tool_name"] == "generate_chapter"
    assert step["status"] == "success"
    assert step["output"]["status"] == "success"
    assert step["output"]["planner_continuation_approval"] == {
        "status": "ready",
        "reason": "approval_contract_verified",
        "approval_contract_hash": approval_hash,
        "source_plan_id": plan["trace"]["plan_id"],
        "blocked_tool": None,
    }
    assert len(calls) == 1
    action_type, called_project_id, command_args, action_params = calls[0]
    assert action_type == "generate_chapter"
    assert called_project_id == project.id
    assert "上一章状态卡" in command_args
    assert action_params == {"chapter_index": 2}


def test_planner_continuation_blocks_write_tool_on_approval_hash_mismatch(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    calls = []

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append(action_type)
        return {"status": "success", "chapter_index": 2}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)
    plan = _planner_generate_chapter_plan(project.id, chapter_index=2)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "执行漂移的规划工具链：续写章节",
            "entrypoint": "ui_planner_continuation_execute",
            "tools": plan["tools"],
            "input": {
                "planner_continuation": True,
                "source_run_id": "run-source-drift",
                "source_plan_id": plan["trace"]["plan_id"],
                "confirm_execute": True,
                "approval_contract_hash": "approval:stale",
                "approval_contract": plan["approval_contract"],
                "planner": plan,
            },
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert payload["error"] == "Planner continuation requires approval"
    step = payload["steps"][0]
    assert step["tool_name"] == "generate_chapter"
    assert step["status"] == "blocked"
    output = step["output"]
    assert output["reason"] == "planner_continuation_requires_approval"
    assert output["approval_verification"]["status"] == "blocked"
    assert output["approval_verification"]["reason"] == "approval_contract_hash_mismatch"
    assert output["approval_verification"]["drift"]["expected_approval_contract_hash"] == "approval:stale"
    assert calls == []


def test_planner_continuation_executes_confirmed_revision_patch_after_contract_verification(
    client,
    db_session,
    monkeypatch,
):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    calls = []

    def fake_apply_revision_patch(db, project_id, chapter_index, *, revision_id=None):
        calls.append((project_id, chapter_index, revision_id))
        return {
            "status": "success",
            "chapter_index": chapter_index,
            "revision_id": revision_id,
            "result_version_id": "chapter-version-revised",
        }

    monkeypatch.setattr(
        "app.services.writing_agent.revision_patch_tool.apply_planner_revision_patch_tool",
        fake_apply_revision_patch,
    )
    plan = _planner_revision_patch_plan(project.id, chapter_index=1, revision_id="revision-1")
    approval_hash = plan["approval_contract"]["approval"]["approval_contract_hash"]

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "执行已审批规划工具链：应用章节修订补丁",
            "entrypoint": "ui_planner_continuation_execute",
            "tools": plan["tools"],
            "input": {
                "planner_continuation": True,
                "source_run_id": "run-source-revision-approved",
                "source_plan_id": plan["trace"]["plan_id"],
                "confirm_execute": True,
                "approval_contract_hash": approval_hash,
                "approval_contract": plan["approval_contract"],
                "planner": plan,
            },
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "success"
    step = payload["steps"][0]
    assert step["tool_name"] == "apply_planner_revision_patch"
    assert step["status"] == "success"
    assert step["output"]["planner_continuation_approval"]["approval_contract_hash"] == approval_hash
    assert calls == [(project.id, 1, "revision-1")]


def test_planner_continuation_blocks_revision_patch_when_mutation_fingerprint_missing_target(
    client,
    db_session,
    monkeypatch,
):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    calls = []

    def fake_apply_revision_patch(db, project_id, chapter_index, *, revision_id=None):
        calls.append((project_id, chapter_index, revision_id))
        return {"status": "success", "chapter_index": chapter_index}

    monkeypatch.setattr(
        "app.services.writing_agent.revision_patch_tool.apply_planner_revision_patch_tool",
        fake_apply_revision_patch,
    )
    plan = _planner_revision_patch_plan(project.id, chapter_index=1, revision_id="")
    approval_hash = plan["approval_contract"]["approval"]["approval_contract_hash"]

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "执行缺少目标的规划工具链：应用章节修订补丁",
            "entrypoint": "ui_planner_continuation_execute",
            "tools": plan["tools"],
            "input": {
                "planner_continuation": True,
                "source_run_id": "run-source-revision-missing-target",
                "source_plan_id": plan["trace"]["plan_id"],
                "confirm_execute": True,
                "approval_contract_hash": approval_hash,
                "approval_contract": plan["approval_contract"],
                "planner": plan,
            },
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert payload["error"] == "Planner continuation requires approval"
    step = payload["steps"][0]
    assert step["tool_name"] == "apply_planner_revision_patch"
    assert step["status"] == "blocked"
    output = step["output"]
    assert output["approval_verification"]["reason"] == "mutation_fingerprint_not_ready"
    assert output["approval_verification"]["drift"]["mutation_fingerprint_drift_count"] == 1
    assert output["approval_verification"]["drift"]["mutation_fingerprints"][0]["target_type"] == (
        "chapter_revision_patch"
    )
    assert calls == []


def test_planner_continuation_executes_confirmed_world_model_resolution_after_contract_verification(
    client,
    db_session,
):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.planner.world-model.approved",
        predicate="role",
        subject_ref="char.林深",
    )
    decisions = [{"proposal_item_id": item.id, "action": "reject", "reason": "规划审批后拒绝错误事实"}]
    plan = _planner_world_model_resolution_plan(project.id, decisions=decisions)
    approval_hash = plan["approval_contract"]["approval"]["approval_contract_hash"]

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "执行已审批规划工具链：应用世界模型提案处理",
            "entrypoint": "ui_planner_continuation_execute",
            "tools": plan["tools"],
            "input": {
                "planner_continuation": True,
                "source_run_id": "run-source-world-model-approved",
                "source_plan_id": plan["trace"]["plan_id"],
                "confirm_execute": True,
                "approval_contract_hash": approval_hash,
                "approval_contract": plan["approval_contract"],
                "planner": plan,
            },
        },
    )

    payload = response.json()
    db_session.expire_all()
    stored_item = db_session.query(WorldProposalItem).filter_by(id=item.id).one()
    reviews = db_session.query(WorldProposalReview).filter_by(proposal_item_id=item.id).all()
    assert response.status_code == 200
    assert payload["status"] == "success"
    step = payload["steps"][0]
    assert step["tool_name"] == "apply_world_model_proposal_resolution"
    assert step["status"] == "success"
    assert step["output"]["applied_count"] == 1
    assert step["output"]["planner_continuation_approval"]["approval_contract_hash"] == approval_hash
    assert stored_item.item_status == "rejected"
    assert [review.review_action for review in reviews] == ["reject"]


def test_planner_continuation_blocks_world_model_resolution_on_approval_hash_mismatch(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.planner.world-model.drift",
        predicate="role",
        subject_ref="char.林深",
    )
    decisions = [{"proposal_item_id": item.id, "action": "reject", "reason": "漂移审批不应执行"}]
    plan = _planner_world_model_resolution_plan(project.id, decisions=decisions)
    before_review_count = db_session.query(WorldProposalReview).count()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "执行漂移的规划工具链：应用世界模型提案处理",
            "entrypoint": "ui_planner_continuation_execute",
            "tools": plan["tools"],
            "input": {
                "planner_continuation": True,
                "source_run_id": "run-source-world-model-drift",
                "source_plan_id": plan["trace"]["plan_id"],
                "confirm_execute": True,
                "approval_contract_hash": "approval:stale",
                "approval_contract": plan["approval_contract"],
                "planner": plan,
            },
        },
    )

    payload = response.json()
    db_session.expire_all()
    stored_item = db_session.query(WorldProposalItem).filter_by(id=item.id).one()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert payload["error"] == "Planner continuation requires approval"
    step = payload["steps"][0]
    assert step["tool_name"] == "apply_world_model_proposal_resolution"
    assert step["status"] == "blocked"
    output = step["output"]
    assert output["approval_verification"]["reason"] == "approval_contract_hash_mismatch"
    assert stored_item.item_status == "pending"
    assert db_session.query(WorldProposalReview).count() == before_review_count


def test_planner_continuation_blocks_world_model_resolution_when_mutation_fingerprint_missing_target(
    client,
    db_session,
):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    before_review_count = db_session.query(WorldProposalReview).count()
    plan = _planner_world_model_resolution_plan(project.id, decisions=[])
    approval_hash = plan["approval_contract"]["approval"]["approval_contract_hash"]

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "执行缺少目标的规划工具链：应用世界模型提案处理",
            "entrypoint": "ui_planner_continuation_execute",
            "tools": plan["tools"],
            "input": {
                "planner_continuation": True,
                "source_run_id": "run-source-world-model-missing-target",
                "source_plan_id": plan["trace"]["plan_id"],
                "confirm_execute": True,
                "approval_contract_hash": approval_hash,
                "approval_contract": plan["approval_contract"],
                "planner": plan,
            },
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    step = payload["steps"][0]
    assert step["tool_name"] == "apply_world_model_proposal_resolution"
    assert step["status"] == "blocked"
    output = step["output"]
    assert output["approval_verification"]["reason"] == "mutation_fingerprint_not_ready"
    assert output["approval_verification"]["drift"]["mutation_fingerprints"][0]["target_type"] == (
        "world_model_proposal_bundle"
    )
    assert db_session.query(WorldProposalReview).count() == before_review_count


def test_agent_run_can_describe_current_tool_plan(client):
    project_id = _create_project(client, "Agent Tool Plan API")

    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "查看当前 Agent 工具",
            "tools": [{"tool_name": "describe_agent_tools", "params": {"chapter_index": 1}}],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["steps"][0]["tool_name"] == "describe_agent_tools"
    assert payload["steps"][0]["target_type"] == "agent_tool_plan"
    output = payload["steps"][0]["output"]
    assert output["status"] == "completed"
    assert "visible_tools" in output
    assert "hidden_tools" in output
    assert "diagnostics" in output
    assert "generate_setup" in {tool["name"] for tool in output["visible_tools"]}


def test_agent_run_detail_exposes_agent_profile_projection_for_auto_plan(client):
    project_id = _create_project(client, "Agent Profile Projection API")

    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "看看现在能做什么",
            "input": {"auto_plan": True},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["agent_profile"] == "orchestrator"
    assert payload["agent_profile_scope"]["status"] == "applied"
    assert payload["agent_profile_scope"]["agent_profile"] == "orchestrator"
    assert payload["agent_profile_scope"]["allowed_visible_tool_count"] > 0
    assert payload["agent_profile_scope"]["profile_filtered_visible_tool_count"] > 0
    assert payload["agent_tool_discovery"]["version"] == "phase210.agent_tool_discovery_projection.v1"
    assert payload["agent_tool_discovery"]["scope_applied"] is True
    assert payload["agent_tool_discovery"]["scope_source"] == "agent_profile"
    assert payload["agent_tool_discovery"]["requested_profile"] == "orchestrator"
    assert payload["agent_tool_discovery"]["effective_profile"] == "orchestrator"
    assert payload["agent_tool_discovery"]["visible_tool_count"] == payload["agent_profile_scope"]["allowed_visible_tool_count"]
    assert (
        payload["agent_tool_discovery"]["filtered_by_profile_count"]
        == payload["agent_profile_scope"]["profile_filtered_visible_tool_count"]
    )
    assert payload["agent_tool_discovery"]["filter_stages"] == ["profile"]
    definition = payload["agent_profile_definition"]
    assert definition["version"] == "phase212.agent_profile_definition.v1"
    assert definition["profile"] == "orchestrator"
    assert definition["display_name"] == "编排主控"
    assert definition["role"] == "orchestrator"
    assert definition["tier"] == "reasoning"
    assert definition["delegation_allowed"] is True
    assert definition["source"] == "planner_trace"
    audit = payload["agent_profile_policy_audit"]
    assert audit["version"] == "phase215.agent_profile_policy_audit.v1"
    assert audit["status"] == "passed"
    assert audit["summary"]["issues"] == 0
    assert audit["summary"]["delegate_edges"] == 4
    command_contracts = payload["agent_command_contracts"]
    assert command_contracts["source"] == "planner_trace.agent_health_projection.command_contracts"
    assert command_contracts["summary"]["agent_control_commands"] == 2
    assert isinstance(command_contracts["summary"]["gap_count"], int)
    control_plane = payload["agent_control_plane_readiness"]
    assert control_plane["source"] == "planner_trace.agent_health_projection.control_plane_readiness"
    assert control_plane["summary"]["agent_control_commands"] == 2
    assert isinstance(control_plane["summary"]["total_gap_count"], int)
    health = payload["output"]["continuation_state"]["profile_policy_health"]
    assert health == {
        "status": "passed",
        "reason": "agent_profile_policy_passed",
        "issue_count": 0,
        "recommended_tools": [],
    }
    assert "delegate_edges" not in health

    detail = client.get(f"/api/v1/projects/{project_id}/agent-runs/{payload['id']}")

    assert detail.status_code == 200
    detail_payload = detail.json()
    assert detail_payload["agent_profile"] == "orchestrator"
    assert detail_payload["agent_profile_scope"] == payload["agent_profile_scope"]
    assert detail_payload["agent_tool_discovery"] == payload["agent_tool_discovery"]
    assert detail_payload["agent_profile_definition"] == payload["agent_profile_definition"]
    assert detail_payload["agent_profile_policy_audit"] == audit
    assert detail_payload["agent_command_contracts"] == command_contracts
    assert detail_payload["agent_control_plane_readiness"] == control_plane


def test_agent_run_output_exposes_agent_loop_contract_for_success(client):
    project_id = _create_project(client, "Agent Loop Success")

    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "查看当前 Agent 工具",
            "tools": [{"tool_name": "describe_agent_tools", "params": {"chapter_index": 1}}],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    agent_loop = payload["output"]["continuation_state"]["agent_loop"]
    assert agent_loop["version"] == "phase219.agent_loop_contract.v1"
    assert agent_loop["loop_kind"] == "sequential_tool_plan"
    assert agent_loop["budget"] == {
        "max_iterations": 1,
        "used_iterations": 1,
        "remaining_iterations": 0,
    }
    assert agent_loop["exit_reason"] == "completed"
    assert agent_loop["requires_user_action"] is False
    assert agent_loop["stop_hooks"]["status"] == "clear"
    assert agent_loop["stop_hooks"]["allow_continue"] is True
    assert agent_loop["loop_risk"]["status"] == "clear"
    assert agent_loop["loop_risk"]["detector"] is None
    assert agent_loop["loop_risk"]["max_repeat_count"] == 1
    assert agent_loop["loop_risk"]["tool_name"] is None
    assert agent_loop["loop_risk"]["signature"] is None
    assert agent_loop["loop_risk"]["thresholds"] == {"warning": 3, "critical": 5, "global_circuit_breaker": 30}
    assert agent_loop["loop_risk"]["detectors"] == []
    assert agent_loop["loop_risk"]["recommended_next_action"] == {
        "status": "none",
        "reason": "loop_risk_clear",
        "next_tool": None,
        "recommended_tools": [],
        "requires_user_input": False,
        "allow_continue": True,
    }
    assert agent_loop["next_action"] == {"kind": "none", "tool_name": None, "requires_confirmation": False}
    assert agent_loop["tool_call_sequence"] == [
        {
            "step_index": 1,
            "tool_name": "describe_agent_tools",
                "status": "success",
                "tool_call_id": None,
                "target_type": "agent_tool_plan",
                "chapter_index": 1,
            }
        ]


def test_agent_run_output_exposes_agent_loop_contract_for_blocked_run(client):
    project_id = _create_project(client, "Agent Loop Blocked")

    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "检查第1章是否可写",
            "tools": [{"tool_name": "preflight_writing", "params": {"chapter_index": 1}}],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    agent_loop = payload["output"]["continuation_state"]["agent_loop"]
    assert payload["status"] == "blocked"
    assert agent_loop["exit_reason"] == "blocked"
    assert agent_loop["requires_user_action"] is True
    assert agent_loop["next_action"] == {
        "kind": "request_input",
        "tool_name": "generate_setup",
        "requires_confirmation": True,
    }
    assert agent_loop["budget"]["used_iterations"] == 1
    assert agent_loop["tool_call_sequence"][0]["tool_name"] == "preflight_writing"
    assert agent_loop["tool_call_sequence"][0]["status"] == "blocked"


def test_agent_run_output_exposes_agent_loop_contract_for_failed_tool(client):
    project_id = _create_project(client, "Agent Loop Failed")

    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "调用不存在的工具",
            "tools": [{"tool_name": "missing_agent_tool", "params": {}}],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    agent_loop = payload["output"]["continuation_state"]["agent_loop"]
    assert payload["status"] == "failed"
    assert agent_loop["exit_reason"] == "tool_failed"
    assert agent_loop["requires_user_action"] is True
    assert agent_loop["next_action"] == {
        "kind": "inspect_failure",
        "tool_name": "inspect_agent_health_projection",
        "requires_confirmation": False,
    }
    assert agent_loop["budget"]["used_iterations"] == 1
    assert agent_loop["tool_call_sequence"][0]["tool_name"] == "missing_agent_tool"
    assert agent_loop["tool_call_sequence"][0]["status"] == "failed"


def test_agent_loop_risk_warns_on_repeated_adjacent_tool_calls(client):
    project_id = _create_project(client, "Agent Loop Risk")
    repeated_tool = {"tool_name": "describe_agent_tools", "params": {"chapter_index": 1}}

    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "重复查看工具面",
            "tools": [repeated_tool, repeated_tool, repeated_tool],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    loop_risk = payload["output"]["continuation_state"]["agent_loop"]["loop_risk"]
    assert loop_risk["status"] == "warning"
    assert loop_risk["detector"] == "generic_repeat"
    assert loop_risk["tool_name"] == "describe_agent_tools"
    assert loop_risk["max_repeat_count"] == 3
    assert loop_risk["signature"].startswith("describe_agent_tools:")
    assert loop_risk["thresholds"] == {"warning": 3, "critical": 5, "global_circuit_breaker": 30}
    assert loop_risk["detectors"][0]["detector"] == "generic_repeat"
    assert loop_risk["recommended_next_action"]["next_tool"] == "inspect_agent_health_projection"
    assert payload["output"]["continuation_state"]["agent_loop"]["stop_hooks"]["status"] == "clear"


def test_agent_loop_stop_hooks_block_critical_loop_risk(client):
    project_id = _create_project(client, "Agent Loop Critical StopHooks")
    repeated_tools = [
        {"tool_name": "describe_agent_tools", "params": {"chapter_index": 1}},
        {"tool_name": "describe_agent_tools", "params": {"chapter_index": 1}},
        {"tool_name": "describe_agent_tools", "params": {"chapter_index": 1}},
        {"tool_name": "describe_agent_tools", "params": {"chapter_index": 1}},
        {"tool_name": "describe_agent_tools", "params": {"chapter_index": 1}},
    ]

    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={"goal": "重复工具调用触发 stop hooks", "tools": repeated_tools},
    )

    payload = response.json()
    stop_hooks = payload["output"]["continuation_state"]["agent_loop"]["stop_hooks"]
    assert response.status_code == 200
    assert stop_hooks["status"] == "blocked"
    assert stop_hooks["reason"] == "loop_risk_critical"
    assert stop_hooks["allow_continue"] is False
    assert stop_hooks["hooks"][0]["code"] == "critical_loop_risk"
    assert stop_hooks["hooks"][0]["detector"] == "generic_repeat"
    assert "inspect_agent_trace_audit" in stop_hooks["recommended_tools"]


def test_agent_tool_input_validation_blocks_missing_required_params(client):
    project_id = _create_project(client, "Agent Tool Validation Missing")

    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "预览审批契约但缺少计划参数",
            "tools": [{"tool_name": "preview_agent_plan_approval_contract", "params": {}}],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "failed"
    step = payload["steps"][0]
    assert step["tool_name"] == "preview_agent_plan_approval_contract"
    assert step["status"] == "failed"
    output = step["output"]
    assert output["status"] == "failed"
    assert output["error"] == "Tool input validation failed"
    assert output["validation"]["status"] == "failed"
    assert output["validation"]["issues"] == [
        {"code": "missing_required_param", "path": "plan", "message": "Missing required param: plan"}
    ]
    assert payload["output"]["continuation_state"]["agent_loop"]["exit_reason"] == "tool_failed"


def test_agent_tool_input_validation_blocks_wrong_param_type(client):
    project_id = _create_project(client, "Agent Tool Validation Type")

    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "用错误章节参数执行预检",
            "tools": [{"tool_name": "preflight_writing", "params": {"chapter_index": "abc"}}],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "failed"
    output = payload["steps"][0]["output"]
    assert output["status"] == "failed"
    assert output["validation"]["issues"] == [
        {
            "code": "invalid_param_type",
            "path": "chapter_index",
            "message": "Param chapter_index must be integer.",
        }
    ]
    assert payload["output"]["continuation_state"]["agent_loop"]["tool_call_sequence"][0]["status"] == "failed"


def test_agent_run_result_metrics_include_adapter_metadata(client):
    project_id = _create_project(client, "Agent Result Metrics")

    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "查看工具并记录执行指标",
            "tools": [{"tool_name": "describe_agent_tools", "params": {"chapter_index": 1}}],
        },
    )

    envelope = response.json()["steps"][0]["output"]["agent_tool_result"]
    assert response.status_code == 200
    assert envelope["adapter"]["tool_name"] == "describe_agent_tools"
    assert envelope["adapter"]["adapter_type"] == "static"
    assert envelope["adapter"]["mutability"] == "read"
    assert envelope["execution_route"] == "static_adapter"
    assert envelope["elapsed_ms"] >= 0
    assert envelope["output_size_bytes"] > 0


def test_agent_run_can_plan_writing_tool_chain(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "规划继续写下一章",
            "tools": [
                {
                    "tool_name": "plan_writing_agent_run",
                    "params": {"goal": "继续写下一章", "chapter_index": 2},
                }
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    step = payload["steps"][0]
    assert step["target_type"] == "agent_tool_plan"
    output = step["output"]
    assert output["status"] == "completed"
    assert output["intent_class"] == "continue_next_chapter"
    assert "generate_chapter" in [tool["tool_name"] for tool in output["tools"]]
    assert output["trace"]["selected_tools"][0] == "describe_agent_tools"


def test_agent_run_can_summarize_longform_context(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2, 3], generated_chapters=[1, 2])
    from app.core.longform_memory import repair_longform_maintenance

    db_session.add_all(
        [
            LongformMemory(
                project_id=project.id,
                memory_type="chapter",
                scope_key="chapter:1",
                start_chapter_index=1,
                end_chapter_index=1,
                title="雾港线索1",
                summary="林深发现旧灯塔的雾晶回声，苏晚晴提供第一份证词。",
                status="current",
                memory_metadata={"word_count": 80, "source": "test"},
            ),
            LongformMemory(
                project_id=project.id,
                memory_type="chapter",
                scope_key="chapter:2",
                start_chapter_index=2,
                end_chapter_index=2,
                title="雾港线索2",
                summary="雾安局巡逻队逼近，记忆诊所留下新的异常档案。",
                status="current",
                memory_metadata={"word_count": 80, "source": "test"},
            ),
        ]
    )
    db_session.commit()
    repair_longform_maintenance(db_session, project.id)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "查看长篇上下文",
            "tools": [
                {
                    "tool_name": "summarize_longform_context",
                    "params": {
                        "chapter_index": 3,
                        "query": "续写下一章",
                        "max_chars": 12000,
                    },
                }
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    step = payload["steps"][0]
    assert step["tool_name"] == "summarize_longform_context"
    assert step["target_type"] == "longform_context_summary"
    output = step["output"]
    assert output["status"] == "completed"
    assert output["chapter_index"] == 3
    assert output["project"]["target_chapter_count"] == 600
    assert output["progress"]["generated_chapter_count"] == 2
    assert output["progress"]["latest_generated_chapter_index"] == 2
    assert output["context_summary"]["goal"] == "续写下一章"
    assert "recent_chapters" in output["source_section_keys"]
    assert "prompt_context" not in output
    assert output["limits"]["max_chars"] == 12000
    assert output["prompt_context_chars"] > 0
    provenance = output["memory_provenance"]
    _assert_memory_provenance_contract(provenance)
    assert provenance["status"] == "available"
    assert provenance["boundaries"]["world_truth"]["status"] == "separated"
    assert provenance["boundaries"]["world_truth"]["canonical_source"] == "Athena/world_model"
    assert "longform_context_package:recent_chapters" in {
        source["source_ref"] for source in provenance["sources"]
    }
    assert provenance["windows"]["sections"]["recent_chapters"] == {
        "total": 2,
        "returned": 2,
        "limit": 5,
        "has_more": False,
    }
    assert provenance["prompt_context"]["included"] is False
    assert provenance["prompt_context"]["max_chars"] == 12000
    envelope = output["agent_tool_result"]
    assert envelope["adapter"]["tool_name"] == "summarize_longform_context"
    assert envelope["adapter"]["mutability"] == "read"


def test_agent_run_longform_context_provenance_reports_limited_sections(client, db_session, monkeypatch):
    project = Project(name="Longform Provenance Window")
    db_session.add(project)
    db_session.commit()

    def fake_context_package(db, project_id: str, chapter_index: int, *, user_query: str | None = None):
        return {
            "project_id": project_id,
            "chapter_index": chapter_index,
            "sections": [
                {
                    "key": "manual_overflow",
                    "title": "人工溢出上下文",
                    "items": [
                        {
                            "id": f"memory-{index}",
                            "memory_type": "chapter",
                            "scope_key": f"chapter:{index}",
                            "title": f"第{index}章",
                            "summary": f"第{index}章摘要。",
                        }
                        for index in range(1, 7)
                    ],
                }
            ],
            "prompt_context": "雾港记忆" * 360,
        }

    monkeypatch.setattr(
        "app.services.writing_agent.longform_context_summary.build_longform_context_package",
        fake_context_package,
    )
    monkeypatch.setattr(
        "app.services.writing_agent.longform_context_summary.get_longform_maintenance_diagnostics",
        lambda db, project_id, limit=5: {"ready_for_writing": True, "issue_count": 0},
    )

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查长篇上下文来源窗口",
            "tools": [
                {
                    "tool_name": "summarize_longform_context",
                    "params": {"chapter_index": 7, "max_chars": 1200},
                }
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    output = payload["steps"][0]["output"]
    assert output["diagnostics"][0]["code"] == "section_items_limited"
    provenance = output["memory_provenance"]
    _assert_memory_provenance_contract(provenance)
    assert provenance["windows"]["sections"]["manual_overflow"] == {
        "total": 6,
        "returned": 5,
        "limit": 5,
        "has_more": True,
    }
    assert provenance["prompt_context"]["truncated"] is True
    assert provenance["recovery"]["status"] == "optional"
    assert "summarize_longform_context" in provenance["recovery"]["next_tools"]
    assert provenance["recovery"]["tools"] == [
        {
            "tool_name": "summarize_longform_context",
            "params": {
                "chapter_index": 7,
                "query": "缩小上下文窗口后重新汇总第7章写作上下文。",
                "max_chars": 2400,
            },
        }
    ]

    preview = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "预览截断上下文重试",
            "tools": [{"tool_name": "plan_recommended_followups", "params": {"run_id": payload["id"]}}],
        },
    )

    followup = preview.json()["steps"][0]["output"]
    assert preview.status_code == 200
    assert followup["status"] == "completed"
    assert "memory_provenance.recovery.tools" in followup["recommended_followups"]["source_fields"]
    assert followup["tools"] == [
        {
            "tool_name": "summarize_longform_context",
            "params": {
                "chapter_index": 7,
                "query": "缩小上下文窗口后重新汇总第7章写作上下文。",
                "max_chars": 2400,
            },
            "planner": {
                "step_index": 1,
                "reason": "根据上一轮 summarize_longform_context 的 provenance 恢复建议规划后继工具 summarize_longform_context。",
                "on_missing": "record_issue",
                "on_failure": "record_issue",
                "expected_output": "推荐后继工具输出。",
                "post_generation": False,
                "planner_version": "phase101.recommended_followup_planner.v1",
                "source_run_id": payload["id"],
                "source_step_index": 1,
                "source_tool": "summarize_longform_context",
            },
        }
    ]


def _assert_memory_provenance_contract(provenance):
    assert set(MEMORY_PROVENANCE_REQUIRED_FIELDS).issubset(provenance)
    assert isinstance(provenance["sources"], list)
    assert isinstance(provenance["windows"], dict)
    assert isinstance(provenance["recovery"], dict)
    assert isinstance(provenance["trace"], dict)


def test_agent_run_longform_context_provenance_exhausts_retry_at_max_window(client, db_session, monkeypatch):
    project = Project(name="Longform Provenance Exhausted")
    db_session.add(project)
    db_session.commit()

    def fake_context_package(db, project_id: str, chapter_index: int, *, user_query: str | None = None):
        return {
            "project_id": project_id,
            "chapter_index": chapter_index,
            "sections": [
                {
                    "key": "manual_overflow",
                    "title": "人工溢出上下文",
                    "items": [
                        {
                            "id": f"memory-{index}",
                            "memory_type": "chapter",
                            "scope_key": f"chapter:{index}",
                            "title": f"第{index}章",
                            "summary": f"第{index}章摘要。",
                        }
                        for index in range(1, 7)
                    ],
                }
            ],
            "prompt_context": "雾港记忆" * 4000,
        }

    monkeypatch.setattr(
        "app.services.writing_agent.longform_context_summary.build_longform_context_package",
        fake_context_package,
    )
    monkeypatch.setattr(
        "app.services.writing_agent.longform_context_summary.get_longform_maintenance_diagnostics",
        lambda db, project_id, limit=5: {"ready_for_writing": True, "issue_count": 0},
    )

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查最大上下文窗口来源",
            "tools": [
                {
                    "tool_name": "summarize_longform_context",
                    "params": {"chapter_index": 7, "max_chars": 12000},
                }
            ],
        },
    )

    payload = response.json()
    provenance = payload["steps"][0]["output"]["memory_provenance"]
    assert response.status_code == 200
    assert provenance["status"] == "truncated"
    assert provenance["recovery"]["status"] == "exhausted"
    assert provenance["recovery"]["reason"] == "longform_context_window_limit_exhausted"
    assert provenance["recovery"]["next_tools"] == ["inspect_agent_memory_route"]
    assert provenance["recovery"]["tools"] == [
        {
            "tool_name": "inspect_agent_memory_route",
            "params": {
                "chapter_index": 7,
                "query": "最大上下文窗口仍截断，诊断第7章长篇记忆与检索覆盖。",
                "include_context_summary": False,
            },
        }
    ]

    preview = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "预览最大窗口截断后的后继",
            "tools": [{"tool_name": "plan_recommended_followups", "params": {"run_id": payload["id"]}}],
        },
    )

    followup = preview.json()["steps"][0]["output"]
    assert preview.status_code == 200
    assert followup["trace"]["selected_tools"] == ["inspect_agent_memory_route"]
    assert followup["tools"] == [
        {
            "tool_name": "inspect_agent_memory_route",
            "params": {
                "chapter_index": 7,
                "query": "最大上下文窗口仍截断，诊断第7章长篇记忆与检索覆盖。",
                "include_context_summary": False,
            },
            "planner": {
                "step_index": 1,
                "reason": "根据上一轮 summarize_longform_context 的 provenance 恢复建议规划后继工具 inspect_agent_memory_route。",
                "on_missing": "record_issue",
                "on_failure": "record_issue",
                "expected_output": "推荐后继工具输出。",
                "post_generation": False,
                "planner_version": "phase101.recommended_followup_planner.v1",
                "source_run_id": payload["id"],
                "source_step_index": 1,
                "source_tool": "summarize_longform_context",
            },
        }
    ]


def test_agent_run_can_plan_recovery_tools_from_blocked_run(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1, 2])
    blocked = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第3章是否可写",
            "tools": [{"tool_name": "preflight_writing", "params": {"chapter_index": 3}}],
        },
    )
    blocked_run_id = blocked.json()["id"]
    blocked_step = db_session.query(WritingAgentStep).filter(WritingAgentStep.run_id == blocked_run_id).one()
    blocked_step.tool_call_id = "toolcall:preflight-3"
    blocked_step.resource_binding = {
        "tool_call_id": "toolcall:preflight-3",
        "tool_name": "preflight_writing",
        "target_type": "chapter",
        "target_id": "chapter:3",
        "source_plan_id": "plan:preflight",
        "source_step_id": "step:preflight",
        "binding_source": "server_derived",
    }
    db_session.add(blocked_step)
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "规划上一轮阻塞的恢复工具",
            "tools": [{"tool_name": "plan_recovery_tools", "params": {"run_id": blocked_run_id}}],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["steps"][0]["target_type"] == "agent_tool_plan"
    assert output["status"] == "completed"
    assert output["source_run_id"] == blocked_run_id
    assert output["source_step"]["tool_name"] == "preflight_writing"
    assert output["source_step_id"] == output["source_step"]["id"]
    assert output["source_step"]["tool_call_id"] == "toolcall:preflight-3"
    assert output["source_step"]["resource_binding"]["target_id"] == "chapter:3"
    assert output["hash_payload"]["source_tool_call_id"] == "toolcall:preflight-3"
    assert output["hash_payload"]["source_resource_binding"]["target_id"] == "chapter:3"
    assert output["preview_only"] is True
    assert output["can_execute"] is True
    assert output["requires_confirmation"] is True
    assert output["plan_hash"]
    assert output["recovery"]["next_tool"] == "expand_outline_window"
    assert output["tools"][0]["tool_name"] == "expand_outline_window"
    assert output["tools"][0]["params"] == {"start_chapter": 3, "end_chapter": 3}
    assert output["trace"]["selected_tools"] == ["expand_outline_window"]


def test_agent_run_recovery_plan_redirects_legacy_longform_repair_to_prepare(client, db_session):
    project = Project(name="Legacy Longform Repair Recovery")
    db_session.add(project)
    db_session.flush()
    run = WritingAgentRun(project_id=project.id, goal="legacy repair", status="blocked", input={})
    db_session.add(run)
    db_session.flush()
    db_session.add(
        WritingAgentStep(
            run_id=run.id,
            project_id=project.id,
            step_index=1,
            tool_name="summarize_longform_context",
            status="blocked",
            output={
                "agent_tool_result": {
                    "recovery": {
                        "status": "recommended",
                        "source_tool": "summarize_longform_context",
                        "reason_code": "longform_memory_needs_maintenance",
                        "next_tool": "repair_longform_maintenance",
                        "next_params": {},
                        "continuation_tools": [
                            {"tool_name": "summarize_longform_context", "params": {"chapter_index": 2}},
                            {"tool_name": "preflight_writing", "params": {"chapter_index": 2}},
                        ],
                    }
                }
            },
        )
    )
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "规划旧版长篇维护恢复",
            "tools": [{"tool_name": "plan_recovery_tools", "params": {"run_id": run.id}}],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert output["recovery"]["legacy_next_tool"] == "repair_longform_maintenance"
    assert output["recovery"]["next_tool"] == "prepare_repair_longform_maintenance"
    assert output["tools"][0]["tool_name"] == "prepare_repair_longform_maintenance"
    assert [tool["tool_name"] for tool in output["tools"][0]["params"]["post_approval_continuation_tools"]] == [
        "summarize_longform_context",
        "preflight_writing",
    ]
    assert output["trace"]["selected_tools"] == ["prepare_repair_longform_maintenance"]


def test_agent_run_auto_plan_previews_recovery_tool_plan_by_default(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1, 2])
    blocked = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第3章是否可写",
            "tools": [{"tool_name": "preflight_writing", "params": {"chapter_index": 3}}],
        },
    )
    blocked_run_id = blocked.json()["id"]

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "恢复上一轮阻塞",
            "input": {"auto_plan": True, "recovery_run_id": blocked_run_id},
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["input"]["planner"]["mode"] == "preview"
    assert payload["input"]["planner"]["source_run_id"] == blocked_run_id
    assert payload["input"]["planner"]["preview_only"] is True
    assert payload["input"]["planner"]["execution_policy"]["requires_confirmation"] is True
    assert payload["input"]["tools"][0]["tool_name"] == "plan_recovery_tools"
    assert payload["input"]["tools"][0]["params"] == {"run_id": blocked_run_id}
    assert [step["tool_name"] for step in payload["steps"]] == ["plan_recovery_tools"]
    preview = payload["steps"][0]["output"]
    assert preview["plan_hash"]
    assert preview["can_execute"] is True
    assert preview["preview_only"] is True
    assert preview["tools"][0]["tool_name"] == "expand_outline_window"


def test_agent_run_auto_plan_recovers_latest_blocked_run_from_goal(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    blocked_run = WritingAgentRun(
        project_id=project.id,
        goal="阻塞的直接章节执行",
        status="blocked",
        entrypoint="api",
        input={},
    )
    db_session.add(blocked_run)
    db_session.flush()
    db_session.add(
        WritingAgentStep(
            run_id=blocked_run.id,
            project_id=project.id,
            step_index=1,
            tool_name="execute_generate_chapter_with_approval",
            status="blocked",
            input={"params": {"chapter_index": 2}},
            output={
                "status": "blocked",
                "agent_tool_result": {
                    "recovery": {
                        "status": "recommended",
                        "source_tool": "execute_generate_chapter_with_approval",
                        "reason_code": "resource_binding_target_mismatch",
                        "next_tool": "prepare_generate_chapter_execution",
                        "next_params": {"chapter_index": 2},
                    }
                },
            },
        )
    )
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "恢复上一轮阻塞",
            "input": {"auto_plan": True},
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["input"]["planner"]["intent_class"] == "recover_blocked_run"
    assert [tool["tool_name"] for tool in payload["input"]["tools"]] == ["describe_agent_tools", "plan_recovery_tools"]
    assert payload["input"]["tools"][1]["params"] == {"run_id": blocked_run.id}
    assert [step["tool_name"] for step in payload["steps"]] == ["describe_agent_tools", "plan_recovery_tools"]
    preview = payload["steps"][1]["output"]
    assert preview["source_run_id"] == blocked_run.id
    assert preview["recovery"]["next_tool"] == "prepare_generate_chapter_execution"
    assert preview["tools"][0]["tool_name"] == "prepare_generate_chapter_execution"
    assert preview["tools"][0]["params"] == {"chapter_index": 2}


def test_agent_run_auto_plan_executes_recovery_after_hash_confirmation(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1, 2])
    blocked = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第3章是否可写",
            "tools": [{"tool_name": "preflight_writing", "params": {"chapter_index": 3}}],
        },
    )
    blocked_run_id = blocked.json()["id"]
    preview_response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "规划上一轮阻塞的恢复工具",
            "tools": [{"tool_name": "plan_recovery_tools", "params": {"run_id": blocked_run_id}}],
        },
    )
    plan_hash = preview_response.json()["steps"][0]["output"]["plan_hash"]

    class FakeOutline:
        id = "outline-recovery-3"
        total_chapters = 600
        outline_expansion_result = {"added_chapter_count": 1}
        last_expansion_trace_id = None

    async def fake_expand_outline_window(project_id, *, start_chapter, end_chapter, db, command_args=None):
        assert project_id == project.id
        assert start_chapter == 3
        assert end_chapter == 3
        return FakeOutline()

    monkeypatch.setattr("app.api.outlines.expand_outline_window", fake_expand_outline_window)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "执行上一轮阻塞恢复",
            "input": {
                "auto_plan": True,
                "recovery_run_id": blocked_run_id,
                "execute_recovery": True,
                "confirm_execute": True,
                "recovery_plan_hash": plan_hash,
            },
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["input"]["planner"]["mode"] == "execute"
    assert payload["input"]["planner"]["plan_hash"] == plan_hash
    assert payload["input"]["planner"]["execution_policy"]["confirmed"] is True
    assert payload["input"]["tools"][0]["tool_name"] == "expand_outline_window"
    assert [step["tool_name"] for step in payload["steps"]] == ["expand_outline_window"]


def test_agent_run_auto_plan_rejects_recovery_execute_hash_mismatch(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1, 2])
    blocked = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第3章是否可写",
            "tools": [{"tool_name": "preflight_writing", "params": {"chapter_index": 3}}],
        },
    )
    blocked_run_id = blocked.json()["id"]

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "尝试执行过期恢复计划",
            "input": {
                "auto_plan": True,
                "recovery_run_id": blocked_run_id,
                "execute_recovery": True,
                "confirm_execute": True,
                "recovery_plan_hash": "stale-plan-hash",
            },
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["input"]["planner"]["mode"] == "preview"
    assert payload["input"]["planner"]["execution_policy"]["status"] == "hash_mismatch"
    assert payload["input"]["tools"][0]["tool_name"] == "plan_recovery_tools"
    assert [step["tool_name"] for step in payload["steps"]] == ["plan_recovery_tools"]


def test_agent_run_auto_plan_previews_recommended_followups_by_default(client, db_session):
    project_id, source_run = _seed_recommended_followup_source_run(
        db_session,
        ["review_chapter_quality", "review_chapter_continuity"],
    )

    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "规划上一轮推荐后继",
            "input": {"auto_plan": True, "recommended_followup_run_id": source_run.id},
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["input"]["planner"]["mode"] == "preview"
    assert payload["input"]["planner"]["source_run_id"] == source_run.id
    assert payload["input"]["planner"]["execution_policy"]["requires_confirmation"] is True
    assert payload["input"]["tools"][0]["tool_name"] == "plan_recommended_followups"
    assert payload["input"]["tools"][0]["params"] == {"run_id": source_run.id}
    assert [step["tool_name"] for step in payload["steps"]] == ["plan_recommended_followups"]
    preview = payload["steps"][0]["output"]
    assert preview["plan_hash"]
    assert preview["preview_only"] is True
    assert [tool["tool_name"] for tool in preview["tools"]] == ["review_chapter_quality", "review_chapter_continuity"]


def test_agent_run_auto_plan_executes_recommended_followups_after_hash_confirmation(client, db_session):
    project_id, source_run = _seed_recommended_followup_source_run(
        db_session,
        ["review_chapter_quality", "review_chapter_continuity"],
    )
    preview = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "预览推荐后继",
            "tools": [{"tool_name": "plan_recommended_followups", "params": {"run_id": source_run.id}}],
        },
    )
    plan_hash = preview.json()["steps"][0]["output"]["plan_hash"]

    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "执行推荐后继",
            "input": {
                "auto_plan": True,
                "recommended_followup_run_id": source_run.id,
                "execute_recommended_followups": True,
                "confirm_execute": True,
                "recommended_followup_plan_hash": plan_hash,
            },
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["input"]["planner"]["mode"] == "execute"
    assert payload["input"]["planner"]["plan_hash"] == plan_hash
    assert payload["input"]["planner"]["execution_policy"]["confirmed"] is True
    assert [tool["tool_name"] for tool in payload["input"]["tools"]] == [
        "review_chapter_quality",
        "review_chapter_continuity",
    ]
    assert [step["tool_name"] for step in payload["steps"]] == ["review_chapter_quality", "review_chapter_continuity"]


def test_agent_run_auto_plan_rejects_recommended_followup_hash_mismatch(client, db_session):
    project_id, source_run = _seed_recommended_followup_source_run(db_session, ["review_chapter_quality"])

    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "执行过期推荐后继",
            "input": {
                "auto_plan": True,
                "recommended_followup_run_id": source_run.id,
                "execute_recommended_followups": True,
                "confirm_execute": True,
                "recommended_followup_plan_hash": "stale-plan-hash",
            },
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["input"]["planner"]["mode"] == "preview"
    assert payload["input"]["planner"]["execution_policy"]["status"] == "hash_mismatch"
    assert payload["input"]["tools"][0]["tool_name"] == "plan_recommended_followups"
    assert [step["tool_name"] for step in payload["steps"]] == ["plan_recommended_followups"]


def test_agent_run_auto_plan_rejects_recommended_followup_execute_without_confirmation(client, db_session):
    project_id, source_run = _seed_recommended_followup_source_run(db_session, ["review_chapter_quality"])
    preview = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "预览推荐后继",
            "tools": [{"tool_name": "plan_recommended_followups", "params": {"run_id": source_run.id}}],
        },
    )
    plan_hash = preview.json()["steps"][0]["output"]["plan_hash"]

    for input_payload in (
        {
            "auto_plan": True,
            "recommended_followup_run_id": source_run.id,
            "execute_recommended_followups": True,
            "recommended_followup_plan_hash": plan_hash,
        },
        {
            "auto_plan": True,
            "recommended_followup_run_id": source_run.id,
            "execute_recommended_followups": True,
            "confirm_execute": True,
        },
    ):
        response = client.post(
            f"/api/v1/projects/{project_id}/agent-runs",
            json={"goal": "未确认执行推荐后继", "input": input_payload},
        )
        payload = response.json()
        assert response.status_code == 200
        assert payload["status"] == "success"
        assert payload["input"]["planner"]["mode"] == "preview"
        assert payload["input"]["planner"]["execution_policy"]["status"] == "confirmation_required"
        assert payload["input"]["tools"][0]["tool_name"] == "plan_recommended_followups"
        assert [step["tool_name"] for step in payload["steps"]] == ["plan_recommended_followups"]


def test_agent_run_auto_plan_does_not_execute_guarded_recommended_followups(client, db_session):
    project_id, source_run = _seed_recommended_followup_source_run(
        db_session,
        ["apply_planner_revision_patch", "review_chapter_quality"],
    )
    preview = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "预览含写工具的推荐后继",
            "tools": [{"tool_name": "plan_recommended_followups", "params": {"run_id": source_run.id}}],
        },
    )
    preview_output = preview.json()["steps"][0]["output"]
    plan_hash = preview_output["plan_hash"]
    assert [tool["tool_name"] for tool in preview_output["tools"]] == ["review_chapter_quality"]
    assert preview_output["trace"]["rejected_tools"] == [
        {"tool_name": "apply_planner_revision_patch", "reason": "requires_confirmation"}
    ]

    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "执行安全推荐后继",
            "input": {
                "auto_plan": True,
                "recommended_followup_run_id": source_run.id,
                "execute_recommended_followups": True,
                "confirm_execute": True,
                "recommended_followup_plan_hash": plan_hash,
            },
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert [tool["tool_name"] for tool in payload["input"]["tools"]] == ["review_chapter_quality"]
    assert [step["tool_name"] for step in payload["steps"]] == ["review_chapter_quality"]
    assert payload["input"]["planner"]["trace"]["rejected_tools"] == [
        {"tool_name": "apply_planner_revision_patch", "reason": "requires_confirmation"}
    ]


def test_agent_run_recommended_followup_preview_projects_provenance_write_tools(client, db_session):
    project = Project(name="Recommended Followup Provenance Write Tools")
    db_session.add(project)
    db_session.flush()
    source_run = WritingAgentRun(project_id=project.id, goal="诊断检索覆盖", status="success", input={})
    db_session.add(source_run)
    db_session.flush()
    write_tools = [{"tool_name": "repair_longform_maintenance", "params": {}}]
    db_session.add(
        WritingAgentStep(
            run_id=source_run.id,
            project_id=project.id,
            step_index=1,
            tool_name="inspect_agent_memory_route",
            status="success",
            chapter_index=13,
            input={"params": {"chapter_index": 13}},
            output={
                "status": "completed",
                "agent_tool_result": {
                    "recommendations": {
                        "source_fields": [
                            "memory_provenance.recovery.tools",
                            "memory_provenance.recovery.write_tools",
                        ],
                        "canonical_followups": ["inspect_agent_memory_route"],
                        "provenance_recovery_tools": [
                            {
                                "tool_name": "inspect_agent_memory_route",
                                "params": {
                                    "chapter_index": 13,
                                    "query": "检索索引为空，诊断第13章长篇记忆与检索覆盖。",
                                    "include_context_summary": False,
                                },
                            }
                        ],
                        "provenance_write_tools": write_tools,
                    }
                },
            },
        )
    )
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "预览检索覆盖恢复后继",
            "tools": [{"tool_name": "plan_recommended_followups", "params": {"run_id": source_run.id}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert output["status"] == "completed"
    assert [tool["tool_name"] for tool in output["tools"]] == ["inspect_agent_memory_route"]
    assert output["recommended_followups"]["provenance_write_tools"] == write_tools


def test_agent_recovery_preview_blocks_requires_user_input(client):
    project_id = _create_project(client, "Recovery Needs Setup Input")
    blocked = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "检查第1章是否可写",
            "tools": [{"tool_name": "preflight_writing", "params": {"chapter_index": 1}}],
        },
    )
    blocked_run_id = blocked.json()["id"]

    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "预览缺设定恢复",
            "tools": [{"tool_name": "plan_recovery_tools", "params": {"run_id": blocked_run_id}}],
        },
    )

    preview = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert preview["recovery"]["reason_code"] == "missing_setup"
    assert preview["can_execute"] is False
    assert preview["guardrails"]["status"] == "blocked"
    assert preview["guardrails"]["blockers"][0]["code"] == "requires_user_input"
    assert preview["execution_policy"]["status"] == "requires_user_input"


def test_agent_recovery_execute_rejects_hidden_tool_after_state_drift(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1, 2])
    blocked = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第3章是否可写",
            "tools": [{"tool_name": "preflight_writing", "params": {"chapter_index": 3}}],
        },
    )
    blocked_run_id = blocked.json()["id"]
    preview_response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "规划上一轮阻塞的恢复工具",
            "tools": [{"tool_name": "plan_recovery_tools", "params": {"run_id": blocked_run_id}}],
        },
    )
    plan_hash = preview_response.json()["steps"][0]["output"]["plan_hash"]
    db_session.query(Storyline).filter(Storyline.project_id == project.id).delete()
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "执行已漂移的恢复计划",
            "input": {
                "auto_plan": True,
                "recovery_run_id": blocked_run_id,
                "execute_recovery": True,
                "confirm_execute": True,
                "recovery_plan_hash": plan_hash,
            },
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["input"]["planner"]["mode"] == "preview"
    assert payload["input"]["planner"]["execution_policy"]["status"] == "tool_not_visible"
    assert [step["tool_name"] for step in payload["steps"]] == ["plan_recovery_tools"]
    preview = payload["steps"][0]["output"]
    assert preview["can_execute"] is False
    assert preview["guardrails"]["blockers"][0]["code"] == "tool_not_visible"


def test_agent_recovery_preview_blocks_repeated_failed_plan(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1, 2])
    blocked = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第3章是否可写",
            "tools": [{"tool_name": "preflight_writing", "params": {"chapter_index": 3}}],
        },
    )
    blocked_run_id = blocked.json()["id"]
    preview_response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "规划上一轮阻塞的恢复工具",
            "tools": [{"tool_name": "plan_recovery_tools", "params": {"run_id": blocked_run_id}}],
        },
    )
    plan_hash = preview_response.json()["steps"][0]["output"]["plan_hash"]
    failed_run = WritingAgentRun(
        project_id=project.id,
        goal="失败的恢复执行",
        status="failed",
        entrypoint="api",
        input={"planner": {"mode": "execute", "source_run_id": blocked_run_id, "plan_hash": plan_hash}},
    )
    db_session.add(failed_run)
    db_session.flush()
    db_session.add(
        WritingAgentStep(
            run_id=failed_run.id,
            project_id=project.id,
            step_index=1,
            tool_name="expand_outline_window",
            status="failed",
            input={"params": {"start_chapter": 3, "end_chapter": 3}},
            output={"status": "failed", "error": "outline expansion failed"},
            error="outline expansion failed",
        )
    )
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "再次预览失败恢复",
            "tools": [{"tool_name": "plan_recovery_tools", "params": {"run_id": blocked_run_id}}],
        },
    )

    preview = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert preview["can_execute"] is False
    assert preview["guardrails"]["status"] == "blocked"
    assert preview["guardrails"]["blockers"][0]["code"] == "repeat_failed_recovery"
    assert preview["execution_policy"]["status"] == "repeat_failed_recovery"


def test_agent_run_auto_plan_executes_high_level_next_chapter_goal(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    from app.core.longform_memory import repair_longform_maintenance

    repair_longform_maintenance(db_session, project.id)
    _create_trace(db_session, project.id, "trace-chapter-2", "chapter_generation")

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        if action_type == "generate_chapter":
            self.db.add(
                ChapterContent(
                    project_id=project_id,
                    chapter_index=action_params["chapter_index"],
                    title="雾港线索2",
                    content="林深在记忆诊所外追踪新的雾晶线索，苏晚晴提醒他不要过早相信雾安局留下的证词。",
                    word_count=2200,
                    status="generated",
                )
            )
            self.db.commit()
            return {"status": "success", "chapter_index": action_params["chapter_index"], "trace_id": "trace-chapter-2"}
        return {"status": "success"}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "继续写下一章",
            "input": {"auto_plan": True, "chapter_index": 2},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    step_names = [step["tool_name"] for step in payload["steps"]]
    assert step_names[:5] == [
        "describe_agent_tools",
        "inspect_agent_knowledge_base_route",
        "summarize_longform_context",
        "preflight_writing",
        "generate_chapter",
    ]
    assert step_names[-1] == "analyze_chapter_world_model"
    knowledge_step = next(step for step in payload["steps"] if step["tool_name"] == "inspect_agent_knowledge_base_route")
    assert knowledge_step["target_type"] == "agent_knowledge_base_route"
    assert knowledge_step["output"]["agent_tool_result"]["adapter"]["mutability"] == "read"
    context_step = next(step for step in payload["steps"] if step["tool_name"] == "summarize_longform_context")
    assert context_step["target_type"] == "longform_context_summary"
    assert context_step["output"]["agent_tool_result"]["adapter"]["mutability"] == "read"
    generate_step = next(step for step in payload["steps"] if step["tool_name"] == "generate_chapter")
    assert generate_step["input"]["planner"]["reason"] == "依赖满足后生成第2章正文。"
    envelope = generate_step["output"]["agent_tool_result"]
    assert envelope["tool_name"] == "generate_chapter"
    assert envelope["step_status"] == "success"
    assert envelope["result_status"] == "success"
    assert envelope["is_error"] is False
    assert envelope["trace_id"] == "trace-chapter-2"
    assert envelope["planner"]["reason"] == "依赖满足后生成第2章正文。"
    quality_step = next(step for step in payload["steps"] if step["tool_name"] == "review_chapter_quality")
    assert quality_step["input"]["planner"]["post_generation"] is True
    assert payload["input"]["planner"]["intent_class"] == "continue_next_chapter"
    assert payload["input"]["tools"][0]["tool_name"] == "describe_agent_tools"


def test_agent_auto_plan_longform_context_blocks_stale_maintenance_before_generation(
    client,
    db_session,
    monkeypatch,
):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    calls: list[str] = []

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append(action_type)
        return {"status": "success"}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "继续写下一章",
            "input": {"auto_plan": True, "chapter_index": 2},
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert [step["tool_name"] for step in payload["steps"]] == [
        "describe_agent_tools",
        "inspect_agent_knowledge_base_route",
        "summarize_longform_context",
    ]
    context_output = payload["steps"][2]["output"]
    assert context_output["should_generate_next_chapter"] is False
    assert context_output["recommended_actions"] == ["prepare_repair_longform_maintenance"]
    assert context_output["decision"]["reason"] == "longform_memory_needs_maintenance"
    provenance = context_output["memory_provenance"]
    assert provenance["status"] == "blocked"
    assert provenance["recovery"]["status"] == "recommended"
    assert provenance["recovery"]["next_tools"] == ["prepare_repair_longform_maintenance"]
    assert calls == []
    state = payload["output"]["continuation_state"]
    assert state["version"] == "phase56.continuation_state.v1"
    assert state["status"] == "blocked"
    assert state["target_chapter_index"] == 2
    assert state["last_successful_tool"]["tool_name"] == "summarize_longform_context"
    assert state["blocked_tool"]["tool_name"] == "summarize_longform_context"
    assert state["next_expected_tool"] == "prepare_repair_longform_maintenance"
    assert state["recommended_followups"]["status"] == "suppressed"
    assert state["recommended_followups"]["reason"] == "recovery_required"
    assert state["recovery"]["status"] == "recommended"
    assert state["recovery"]["next_tool"] == "prepare_repair_longform_maintenance"
    assert state["recovery"]["memory_provenance_status"] == "blocked"
    assert state["recovery"]["memory_provenance_recovery_status"] == "recommended"
    assert state["memory_provenance"]["source_tool"] == "summarize_longform_context"
    assert state["memory_provenance"]["status"] == "blocked"
    assert state["memory_provenance"]["recovery"]["next_tools"] == ["prepare_repair_longform_maintenance"]
    assert state["consumed"]["longform_context"] is True
    assert state["consumed"]["generated_chapter"] is False

    preview = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "预览上下文维护恢复",
            "tools": [{"tool_name": "plan_recovery_tools", "params": {"run_id": payload["id"]}}],
        },
    )

    recovery = preview.json()["steps"][0]["output"]
    assert preview.status_code == 200
    assert recovery["status"] == "completed"
    assert recovery["source_step"]["tool_name"] == "summarize_longform_context"
    assert recovery["recovery"]["next_tool"] == "prepare_repair_longform_maintenance"
    assert [tool["tool_name"] for tool in recovery["tools"]] == [
        "prepare_repair_longform_maintenance",
    ]
    assert [tool["tool_name"] for tool in recovery["tools"][0]["params"]["post_approval_continuation_tools"]] == [
        "summarize_longform_context",
        "preflight_writing",
        "generate_chapter",
    ]
    assert recovery["tools"][0]["params"]["post_approval_continuation_tools"][0]["params"]["chapter_index"] == 2
    assert recovery["trace"]["selected_tools"] == [
        "prepare_repair_longform_maintenance",
    ]
    assert recovery["execution_policy"]["safe_auto_execute"] is False


def test_agent_run_prepares_longform_context_recovery_after_confirmation(
    client,
    db_session,
    monkeypatch,
):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    calls: list[str] = []

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append(action_type)
        assert action_type == "generate_chapter"
        assert action_params == {"chapter_index": 2}
        return {"status": "success", "trace_id": None}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    blocked = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "继续写下一章",
            "input": {"auto_plan": True, "chapter_index": 2},
        },
    )
    blocked_run_id = blocked.json()["id"]

    preview = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "预览上下文恢复链",
            "tools": [{"tool_name": "plan_recovery_tools", "params": {"run_id": blocked_run_id}}],
        },
    )
    plan_hash = preview.json()["steps"][0]["output"]["plan_hash"]

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "执行上下文恢复并继续生成",
            "input": {
                "auto_plan": True,
                "recovery_run_id": blocked_run_id,
                "execute_recovery": True,
                "confirm_execute": True,
                "recovery_plan_hash": plan_hash,
            },
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["input"]["planner"]["mode"] == "execute"
    assert payload["input"]["planner"]["plan_hash"] == plan_hash
    assert [step["tool_name"] for step in payload["steps"]] == [
        "prepare_repair_longform_maintenance",
    ]
    prepare_output = payload["steps"][0]["output"]
    assert prepare_output["status"] == "approval_required"
    assert prepare_output["side_effects"] == {"executed": [], "skipped": ["repair_longform_maintenance"]}
    assert prepare_output["recommended_next_tools"] == ["execute_repair_longform_maintenance_with_approval"]
    assert [tool["tool_name"] for tool in prepare_output["post_approval_continuation_tools"]] == [
        "summarize_longform_context",
        "preflight_writing",
        "generate_chapter",
    ]
    state = payload["output"]["continuation_state"]
    assert state["version"] == "phase56.continuation_state.v1"
    assert state["status"] == "completed"
    assert state["target_chapter_index"] == 2
    assert state["last_successful_tool"]["tool_name"] == "prepare_repair_longform_maintenance"
    assert state["next_expected_tool"] is None
    assert state["recommended_followups"]["next_tool"] == "execute_repair_longform_maintenance_with_approval"
    assert state["consumed"]["longform_maintenance"] is False
    assert state["consumed"]["longform_context"] is False
    assert state["consumed"]["preflight"] is False
    assert state["consumed"]["generated_chapter"] is False
    assert state["consumed"]["world_model_proposals"] is False
    assert calls == []


def test_agent_run_can_repair_longform_maintenance(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "修复长篇记忆维护状态",
            "tools": [{"tool_name": "repair_longform_maintenance", "params": {"repair_limit": 10}}],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert payload["steps"][0]["target_type"] == "longform_maintenance"
    assert output["status"] == "blocked"
    assert output["reason"] == "approval_required_before_write"
    assert output["required_approval"]["prepare_tool"] == "prepare_repair_longform_maintenance"
    assert output["required_approval"]["execute_tool"] == "execute_repair_longform_maintenance_with_approval"
    assert output["side_effects"] == {
        "executed": [],
        "skipped": ["repair_longform_maintenance"],
    }
    assert output["recommended_next_tools"] == ["prepare_repair_longform_maintenance"]
    assert output["agent_tool_result"]["adapter"]["mutability"] == "guarded_write"
    assert output["agent_tool_result"]["adapter"]["write_policy"] == "approval_required_redirect"


def test_agent_run_can_plan_longform_chapter_batch(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2, 3], generated_chapters=[1])

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "规划接下来两章的批次任务",
            "tools": [
                {
                    "tool_name": "plan_longform_chapter_batch",
                    "params": {"start_chapter": 2, "batch_size": 2},
                }
            ],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["steps"][0]["target_type"] == "longform_batch_plan"
    assert output["status"] == "completed"
    assert output["batch"]["chapter_indexes"] == [2, 3]
    assert output["dag"]["node_count"] <= 8
    assert [node["node_id"] for node in output["dag"]["nodes"]] == [
        "context_diagnostics",
        "preflight_gate",
        "chapter_generation",
        "quality_review",
        "continuity_review",
        "world_model_intake",
        "batch_checkpoint",
    ]
    assert output["dag"]["nodes"][2]["tool_name"] == "generate_chapter"
    assert output["dag"]["nodes"][2]["depends_on"] == ["preflight_gate"]
    assert output["execution_policy"]["mode"] == "preview"
    assert output["execution_policy"]["requires_queue"] is True


def test_agent_run_plan_longform_chapter_batch_blocks_on_source_continuation(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        return {"status": "success"}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)
    blocked = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "继续写下一章",
            "input": {"auto_plan": True, "chapter_index": 2},
        },
    )

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "从阻塞运行规划批次",
            "tools": [
                {
                    "tool_name": "plan_longform_chapter_batch",
                    "params": {"source_run_id": blocked.json()["id"]},
                }
            ],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert output["status"] == "blocked"
    assert output["recommended_next_tools"] == ["plan_recovery_tools"]
    assert output["source_continuation_state"]["status"] == "blocked"
    assert output["source_continuation_state"]["next_expected_tool"] == "prepare_repair_longform_maintenance"
    assert output["dag"]["nodes"] == []


def test_agent_run_previews_longform_chapter_batch_enqueue(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2, 3], generated_chapters=[1])

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "准备把接下来两章加入批次队列",
            "tools": [
                {
                    "tool_name": "enqueue_longform_chapter_batch",
                    "params": {"start_chapter": 2, "batch_size": 2},
                }
            ],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["steps"][0]["target_type"] == "background_task"
    assert output["status"] == "confirmation_required"
    assert output["preview_only"] is True
    assert output["can_enqueue"] is True
    assert output["plan_hash"]
    assert output["required_confirmation"] == {"confirm_enqueue": True, "plan_hash": output["plan_hash"]}
    assert output["batch"]["chapter_indexes"] == [2, 3]
    assert output["queue_policy"]["starts_runner"] is False
    assert db_session.query(BackgroundTask).filter(BackgroundTask.project_id == project.id).count() == 0


def test_agent_run_rejects_longform_chapter_batch_enqueue_hash_mismatch(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2, 3], generated_chapters=[1])

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "尝试执行过期批次计划",
            "tools": [
                {
                    "tool_name": "enqueue_longform_chapter_batch",
                    "params": {
                        "start_chapter": 2,
                        "batch_size": 2,
                        "confirm_enqueue": True,
                        "plan_hash": "stale",
                    },
                }
            ],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert output["status"] == "hash_mismatch"
    assert output["can_enqueue"] is False
    assert output["expected_plan_hash"]
    assert output["provided_plan_hash"] == "stale"
    assert db_session.query(BackgroundTask).filter(BackgroundTask.project_id == project.id).count() == 0


def test_agent_run_confirms_longform_chapter_batch_enqueue(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2, 3], generated_chapters=[1])
    preview_response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "准备把接下来两章加入批次队列",
            "tools": [
                {
                    "tool_name": "enqueue_longform_chapter_batch",
                    "params": {"start_chapter": 2, "batch_size": 2},
                }
            ],
        },
    )
    plan_hash = preview_response.json()["steps"][0]["output"]["plan_hash"]

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "确认加入批次队列",
            "tools": [
                {
                    "tool_name": "enqueue_longform_chapter_batch",
                    "params": {
                        "start_chapter": 2,
                        "batch_size": 2,
                        "confirm_enqueue": True,
                        "plan_hash": plan_hash,
                    },
                }
            ],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    task = db_session.query(BackgroundTask).filter(BackgroundTask.id == output["task"]["id"]).one()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert output["status"] == "queued"
    assert output["plan_hash"] == plan_hash
    assert output["task"]["task_type"] == "longform_chapter_batch"
    assert output["task"]["status"] == "pending"
    assert output["task"]["chapter_range"] == {"start": 2, "end": 3}
    assert output["batch"]["chapter_indexes"] == [2, 3]
    assert task.payload["plan_hash"] == plan_hash
    assert task.payload["batch"]["chapter_indexes"] == [2, 3]
    assert task.payload["dag"]["node_count"] <= 8
    assert task.payload["queue_policy"]["starts_runner"] is False

    duplicate_response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "重复确认同一批次",
            "tools": [
                {
                    "tool_name": "enqueue_longform_chapter_batch",
                    "params": {
                        "start_chapter": 2,
                        "batch_size": 2,
                        "confirm_enqueue": True,
                        "plan_hash": plan_hash,
                    },
                }
            ],
        },
    )
    duplicate_output = duplicate_response.json()["steps"][0]["output"]
    assert duplicate_output["status"] == "queued"
    assert duplicate_output["task"]["id"] == output["task"]["id"]
    assert db_session.query(BackgroundTask).filter(BackgroundTask.project_id == project.id).count() == 1


def test_agent_run_longform_chapter_batch_enqueue_blocks_on_source_continuation(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        return {"status": "success"}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)
    blocked = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "继续写下一章",
            "input": {"auto_plan": True, "chapter_index": 2},
        },
    )

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "尝试从阻塞运行加入批次队列",
            "tools": [
                {
                    "tool_name": "enqueue_longform_chapter_batch",
                    "params": {"source_run_id": blocked.json()["id"]},
                }
            ],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert output["status"] == "blocked"
    assert output["can_enqueue"] is False
    assert output["recommended_next_tools"] == ["plan_recovery_tools"]
    assert db_session.query(BackgroundTask).filter(BackgroundTask.project_id == project.id).count() == 0


def test_agent_run_inspects_longform_chapter_batch_queue(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2, 3], generated_chapters=[1])
    preview_response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "准备把接下来两章加入批次队列",
            "tools": [
                {
                    "tool_name": "enqueue_longform_chapter_batch",
                    "params": {"start_chapter": 2, "batch_size": 2},
                }
            ],
        },
    )
    plan_hash = preview_response.json()["steps"][0]["output"]["plan_hash"]
    enqueue_response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "确认加入批次队列",
            "tools": [
                {
                    "tool_name": "enqueue_longform_chapter_batch",
                    "params": {
                        "start_chapter": 2,
                        "batch_size": 2,
                        "confirm_enqueue": True,
                        "plan_hash": plan_hash,
                    },
                }
            ],
        },
    )
    task_id = enqueue_response.json()["steps"][0]["output"]["task"]["id"]

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "查看长篇批次队列",
            "tools": [{"tool_name": "inspect_longform_chapter_batch", "params": {"task_id": task_id}}],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["steps"][0]["target_type"] == "background_task"
    assert output["status"] == "completed"
    assert output["summary"]["total"] == 1
    assert output["summary"]["returned"] == 1
    assert output["summary"]["by_status"] == {"pending": 1}
    assert output["queue"]["depth"] == 1
    assert output["queue"]["active"] == 1
    assert output["queue"]["terminal"] == 0
    assert output["tasks"][0]["id"] == task_id
    assert output["tasks"][0]["plan_hash"] == plan_hash
    assert output["selected_task"]["id"] == task_id
    assert output["selected_task"]["batch"]["chapter_indexes"] == [2, 3]
    assert output["selected_task"]["dag"]["node_count"] <= 8
    assert output["selected_task"]["execution_readiness"]["status"] == "materialized_only"
    assert output["selected_task"]["resume"]["can_resume"] is False
    assert output["selected_task"]["queue_policy"]["starts_runner"] is False


def test_agent_run_inspect_longform_chapter_batch_reports_missing_selection(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "查看不存在的长篇批次",
            "tools": [{"tool_name": "inspect_longform_chapter_batch", "params": {"task_id": "missing-task"}}],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert output["status"] == "not_found"
    assert output["summary"]["total"] == 0
    assert output["selected_task"] is None
    assert output["trace"]["rejected_tools"] == [
        {"tool_name": "inspect_longform_chapter_batch", "reason": "selected_task_not_found"}
    ]


def test_agent_run_can_preflight_longform_chapter_batch_checkpoint(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    preview_response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "准备把下一章加入批次队列",
            "tools": [
                {
                    "tool_name": "enqueue_longform_chapter_batch",
                    "params": {"start_chapter": 2, "batch_size": 1},
                }
            ],
        },
    )
    plan_hash = preview_response.json()["steps"][0]["output"]["plan_hash"]
    enqueue_response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "确认加入批次队列",
            "tools": [
                {
                    "tool_name": "enqueue_longform_chapter_batch",
                    "params": {
                        "start_chapter": 2,
                        "batch_size": 1,
                        "confirm_enqueue": True,
                        "plan_hash": plan_hash,
                    },
                }
            ],
        },
    )
    task_id = enqueue_response.json()["steps"][0]["output"]["task"]["id"]

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "预检长篇批次任务",
            "tools": [
                {
                    "tool_name": "execute_longform_chapter_batch_preflight",
                    "params": {"task_id": task_id, "max_chapters": 1, "confirm_checkpoint": True},
                }
            ],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    task = db_session.query(BackgroundTask).filter(BackgroundTask.id == task_id).one()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["steps"][0]["target_type"] == "background_task"
    assert output["status"] == "ready"
    assert output["task"]["id"] == task_id
    assert output["task"]["status"] == "pending"
    assert output["canonical_execution_plan"]["chapter_indexes"] == [2]
    assert output["canonical_execution_plan"]["stopped_before_node"] == "chapter_generation"
    assert output["checkpoint"]["status"] == "ready"
    assert output["checkpoint"]["ready_chapter_indexes"] == [2]
    assert output["checkpoint"]["blocked_chapter_indexes"] == []
    assert output["checkpoint"]["safe_nodes_executed"] == ["preflight_gate"]
    assert output["checkpoint"]["generation_started"] is False
    assert output["execution_policy"]["mode"] == "preflight_only"
    assert output["execution_policy"]["can_execute_after_confirmation"] is False
    assert output["side_effects"]["executed"] == ["background_task_result_checkpoint"]
    assert {"start_runner", "generate_chapter", "world_model_apply"}.issubset(set(output["side_effects"]["skipped"]))
    assert task.status == "pending"
    assert task.result["preflight_checkpoint"]["task_id"] == task_id
    assert task.result["preflight_checkpoint"]["status"] == "ready"
    assert len(task.result["execution_checkpoints"]) == 1
    assert (
        db_session.query(ChapterContent)
        .filter(ChapterContent.project_id == project.id, ChapterContent.chapter_index == 2)
        .count()
        == 0
    )
    inspect_response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "查看预检断点",
            "tools": [{"tool_name": "inspect_longform_chapter_batch", "params": {"task_id": task_id}}],
        },
    )
    inspected_task = inspect_response.json()["steps"][0]["output"]["selected_task"]
    assert inspected_task["preflight_checkpoint"]["status"] == "ready"
    assert len(inspected_task["execution_checkpoints"]) == 1


def test_agent_run_preflight_longform_chapter_batch_requires_checkpoint_confirmation(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    preview_response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "准备把下一章加入批次队列",
            "tools": [
                {
                    "tool_name": "enqueue_longform_chapter_batch",
                    "params": {"start_chapter": 2, "batch_size": 1},
                }
            ],
        },
    )
    plan_hash = preview_response.json()["steps"][0]["output"]["plan_hash"]
    enqueue_response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "确认加入批次队列",
            "tools": [
                {
                    "tool_name": "enqueue_longform_chapter_batch",
                    "params": {
                        "start_chapter": 2,
                        "batch_size": 1,
                        "confirm_enqueue": True,
                        "plan_hash": plan_hash,
                    },
                }
            ],
        },
    )
    task_id = enqueue_response.json()["steps"][0]["output"]["task"]["id"]

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "未确认时预检长篇批次任务",
            "tools": [
                {
                    "tool_name": "execute_longform_chapter_batch_preflight",
                    "params": {"task_id": task_id, "max_chapters": 1},
                }
            ],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    task = db_session.query(BackgroundTask).filter(BackgroundTask.id == task_id).one()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert output["status"] == "blocked"
    assert output["reason"] == "checkpoint_confirmation_required"
    assert output["required_confirmation"] == {"confirm_checkpoint": True, "task_id": task_id}
    assert output["side_effects"]["executed"] == []
    assert "preflight_checkpoint" not in (task.result or {})
    assert (
        db_session.query(ChapterContent)
        .filter(ChapterContent.project_id == project.id, ChapterContent.chapter_index == 2)
        .count()
        == 0
    )


def test_agent_run_preflight_longform_chapter_batch_blocks_on_dependencies(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2, 3], generated_chapters=[1])
    preview_response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "准备把第三章加入批次队列",
            "tools": [
                {
                    "tool_name": "enqueue_longform_chapter_batch",
                    "params": {"start_chapter": 3, "batch_size": 1},
                }
            ],
        },
    )
    plan_hash = preview_response.json()["steps"][0]["output"]["plan_hash"]
    enqueue_response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "确认加入批次队列",
            "tools": [
                {
                    "tool_name": "enqueue_longform_chapter_batch",
                    "params": {
                        "start_chapter": 3,
                        "batch_size": 1,
                        "confirm_enqueue": True,
                        "plan_hash": plan_hash,
                    },
                }
            ],
        },
    )
    task_id = enqueue_response.json()["steps"][0]["output"]["task"]["id"]

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "预检缺少前章的长篇批次任务",
            "tools": [
                {
                    "tool_name": "execute_longform_chapter_batch_preflight",
                    "params": {"task_id": task_id, "max_chapters": 1, "confirm_checkpoint": True},
                }
            ],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    task = db_session.query(BackgroundTask).filter(BackgroundTask.id == task_id).one()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert output["status"] == "blocked"
    assert output["checkpoint"]["status"] == "blocked"
    assert output["checkpoint"]["blocked_chapter_indexes"] == [3]
    assert output["checkpoint"]["ready_chapter_indexes"] == []
    assert output["checkpoint"]["chapter_preflights"][0]["status"] == "blocked"
    assert output["recommended_next_tools"] == ["inspect_longform_chapter_batch", "plan_recovery_tools"]
    assert output["side_effects"]["executed"] == ["background_task_result_checkpoint"]
    assert task.status == "pending"
    assert task.result["preflight_checkpoint"]["status"] == "blocked"
    assert (
        db_session.query(ChapterContent)
        .filter(ChapterContent.project_id == project.id, ChapterContent.chapter_index == 3)
        .count()
        == 0
    )


def test_agent_run_can_prepare_longform_chapter_batch_execution_manifest(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    preview_response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "准备把下一章加入批次队列",
            "tools": [
                {
                    "tool_name": "enqueue_longform_chapter_batch",
                    "params": {"start_chapter": 2, "batch_size": 1},
                }
            ],
        },
    )
    plan_hash = preview_response.json()["steps"][0]["output"]["plan_hash"]
    enqueue_response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "确认加入批次队列",
            "tools": [
                {
                    "tool_name": "enqueue_longform_chapter_batch",
                    "params": {
                        "start_chapter": 2,
                        "batch_size": 1,
                        "confirm_enqueue": True,
                        "plan_hash": plan_hash,
                    },
                }
            ],
        },
    )
    task_id = enqueue_response.json()["steps"][0]["output"]["task"]["id"]
    client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "预检长篇批次任务",
            "tools": [
                {
                    "tool_name": "execute_longform_chapter_batch_preflight",
                    "params": {"task_id": task_id, "max_chapters": 1, "confirm_checkpoint": True},
                }
            ],
        },
    )

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "准备长篇批次执行契约",
            "tools": [
                {
                    "tool_name": "prepare_longform_chapter_batch_execution",
                    "params": {"task_id": task_id, "confirm_prepare": True},
                }
            ],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    task = db_session.query(BackgroundTask).filter(BackgroundTask.id == task_id).one()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["steps"][0]["target_type"] == "background_task"
    assert output["status"] == "approval_required"
    assert output["task"]["id"] == task_id
    assert output["task"]["status"] == "pending"
    assert output["attempt_manifest_hash"]
    assert output["approval_contract_hash"]
    assert output["attempt_manifest"]["task_id"] == task_id
    assert output["attempt_manifest"]["plan_hash"] == plan_hash
    assert output["attempt_manifest"]["chapter_indexes"] == [2]
    assert output["attempt_manifest"]["stopped_before_node"] == "chapter_generation"
    assert output["agent_plan"]["project_id"] == project.id
    assert output["agent_plan"]["steps"][0]["tool_name"] == "generate_chapter"
    assert output["agent_plan"]["steps"][0]["params"] == {"chapter_index": 2}
    assert output["agent_plan_approval_contract"]["status"] == "requires_confirmation"
    assert output["agent_plan_approval_contract"]["write_step_count"] == 1
    assert output["agent_plan_approval_contract_hash"] == output["agent_plan_approval_contract"]["approval"][
        "approval_contract_hash"
    ]
    assert output["approval_contract"]["agent_plan_approval_contract_hash"] == output["agent_plan_approval_contract"][
        "approval"
    ]["approval_contract_hash"]
    assert output["approval_contract"]["required_confirmation"] == {
        "confirm_execute": True,
        "task_id": task_id,
        "attempt_manifest_hash": output["attempt_manifest_hash"],
        "approval_contract_hash": output["approval_contract_hash"],
    }
    assert output["approval_contract"]["consume_tool"] == "execute_longform_chapter_batch"
    assert output["side_effects"]["executed"] == ["background_task_result_execution_prepare"]
    assert {"start_runner", "generate_chapter", "world_model_apply"}.issubset(set(output["side_effects"]["skipped"]))
    assert task.status == "pending"
    assert task.result["attempt_manifest"]["hash"] == output["attempt_manifest_hash"]
    assert task.result["approval_contract"]["hash"] == output["approval_contract_hash"]
    assert task.result["agent_plan"] == output["agent_plan"]
    assert task.result["agent_plan_approval_contract"] == output["agent_plan_approval_contract"]
    assert task.result["agent_plan_approval_contract_hash"] == output["agent_plan_approval_contract_hash"]
    assert (
        db_session.query(ChapterContent)
        .filter(ChapterContent.project_id == project.id, ChapterContent.chapter_index == 2)
        .count()
        == 0
    )
    inspect_response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "查看执行准备契约",
            "tools": [{"tool_name": "inspect_longform_chapter_batch", "params": {"task_id": task_id}}],
        },
    )
    inspected_task = inspect_response.json()["steps"][0]["output"]["selected_task"]
    assert inspected_task["attempt_manifest"]["hash"] == output["attempt_manifest_hash"]
    assert inspected_task["approval_contract"]["hash"] == output["approval_contract_hash"]


def test_agent_run_prepare_longform_chapter_batch_execution_requires_prepare_confirmation(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    preview_response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "准备把下一章加入批次队列",
            "tools": [
                {
                    "tool_name": "enqueue_longform_chapter_batch",
                    "params": {"start_chapter": 2, "batch_size": 1},
                }
            ],
        },
    )
    plan_hash = preview_response.json()["steps"][0]["output"]["plan_hash"]
    enqueue_response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "确认加入批次队列",
            "tools": [
                {
                    "tool_name": "enqueue_longform_chapter_batch",
                    "params": {
                        "start_chapter": 2,
                        "batch_size": 1,
                        "confirm_enqueue": True,
                        "plan_hash": plan_hash,
                    },
                }
            ],
        },
    )
    task_id = enqueue_response.json()["steps"][0]["output"]["task"]["id"]
    client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "确认预检长篇批次任务",
            "tools": [
                {
                    "tool_name": "execute_longform_chapter_batch_preflight",
                    "params": {"task_id": task_id, "max_chapters": 1, "confirm_checkpoint": True},
                }
            ],
        },
    )

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "未确认时准备长篇批次执行契约",
            "tools": [{"tool_name": "prepare_longform_chapter_batch_execution", "params": {"task_id": task_id}}],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    task = db_session.query(BackgroundTask).filter(BackgroundTask.id == task_id).one()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert output["status"] == "blocked"
    assert output["reason"] == "prepare_confirmation_required"
    assert output["required_confirmation"] == {"confirm_prepare": True, "task_id": task_id}
    assert output["side_effects"]["executed"] == []
    assert "attempt_manifest" not in (task.result or {})
    assert "approval_contract" not in (task.result or {})


def test_agent_run_prepare_longform_chapter_batch_execution_requires_ready_preflight(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    preview_response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "准备把下一章加入批次队列",
            "tools": [
                {
                    "tool_name": "enqueue_longform_chapter_batch",
                    "params": {"start_chapter": 2, "batch_size": 1},
                }
            ],
        },
    )
    plan_hash = preview_response.json()["steps"][0]["output"]["plan_hash"]
    enqueue_response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "确认加入批次队列",
            "tools": [
                {
                    "tool_name": "enqueue_longform_chapter_batch",
                    "params": {
                        "start_chapter": 2,
                        "batch_size": 1,
                        "confirm_enqueue": True,
                        "plan_hash": plan_hash,
                    },
                }
            ],
        },
    )
    task_id = enqueue_response.json()["steps"][0]["output"]["task"]["id"]

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "尝试跳过预检准备执行",
            "tools": [{"tool_name": "prepare_longform_chapter_batch_execution", "params": {"task_id": task_id}}],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    task = db_session.query(BackgroundTask).filter(BackgroundTask.id == task_id).one()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert output["status"] == "blocked"
    assert output["reason"] == "missing_ready_preflight_checkpoint"
    assert output["recommended_next_tools"] == ["execute_longform_chapter_batch_preflight"]
    assert "attempt_manifest" not in (task.result or {})
    assert (
        db_session.query(ChapterContent)
        .filter(ChapterContent.project_id == project.id, ChapterContent.chapter_index == 2)
        .count()
        == 0
    )


def test_agent_run_can_execute_approved_longform_chapter_batch_once(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    prepared = _prepare_longform_batch_execution_contract(client, project.id)
    task_id = prepared["task_id"]

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        assert action_type == "generate_chapter"
        assert action_params == {"chapter_index": 2}
        self.db.add(
            ChapterContent(
                project_id=project_id,
                chapter_index=2,
                title="雾港线索2",
                content="林深和苏晚晴追入记忆诊所后巷，发现雾晶核心的回声正在扩大。",
                word_count=80,
                status="generated",
            )
        )
        self.db.commit()
        return {"status": "success", "chapter_index": 2, "trace_id": "trace-batch-chapter-2"}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "执行已批准的长篇批次",
            "tools": [
                {
                    "tool_name": "execute_longform_chapter_batch",
                    "params": {
                        "task_id": task_id,
                        "confirm_execute": True,
                        "attempt_manifest_hash": prepared["attempt_manifest_hash"],
                        "approval_contract_hash": prepared["approval_contract_hash"],
                    },
                }
            ],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    task = db_session.query(BackgroundTask).filter(BackgroundTask.id == task_id).one()
    chapter = (
        db_session.query(ChapterContent)
        .filter(ChapterContent.project_id == project.id, ChapterContent.chapter_index == 2)
        .one()
    )
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["steps"][0]["target_type"] == "background_task"
    assert output["status"] == "completed"
    assert output["chapter_index"] == 2
    assert output["executed_chapter_indexes"] == [2]
    assert output["generation"]["status"] == "success"
    assert output["evidence"]["chapter_content_written"] is True
    assert output["evidence"]["agent_plan_approval_verified"] is True
    assert output["agent_plan_approval_verification"]["status"] == "ready"
    assert output["execution_resource_binding"]["status"] == "ready"
    assert output["execution_resource_binding"]["resource_binding"]["target_id"] == "chapter:2"
    verification_event = output["approval_verification_event"]
    assert {
        key: verification_event[key]
        for key in (
            "event_type",
            "status",
            "reason",
            "approval_contract_bound",
            "approval_contract_version",
            "write_step_count",
            "tool_contract_drift_count",
        )
    } == {
        "event_type": "contract_verified",
        "status": "ready",
        "reason": "approval_contract_verified",
        "approval_contract_bound": True,
        "approval_contract_version": "phase108.agent_plan_approval_contract.v1",
        "write_step_count": 1,
        "tool_contract_drift_count": 0,
    }
    assert verification_event["tool_call_ids"][0].startswith("toolcall:")
    assert verification_event["resource_bindings"][0]["tool_name"] == "generate_chapter"
    assert verification_event["resource_bindings"][0]["target_type"] == "chapter"
    assert verification_event["resource_bindings"][0]["target_id"] == "chapter:2"
    assert output["execution_checkpoint"]["status"] == "completed"
    assert output["side_effects"]["executed"] == [
        "generate_chapter",
        "background_task_result_execution_checkpoint",
        "background_task_range_progress",
    ]
    assert "inherited_generate_chapter_post_generation_hooks" in output["side_effects"]["inherited"]
    assert chapter.title == "雾港线索2"
    assert task.status == "pending"
    assert task.result["batch_execution_result"]["status"] == "chapter_generated"
    assert task.result["progress"]["completed_chapter_indexes"] == [2]
    assert task.result["execution_checkpoints"][-1]["checkpoint_type"] == "chapter_generation"
    persisted_step = db_session.query(WritingAgentStep).filter(WritingAgentStep.run_id == payload["id"]).one()
    assert persisted_step.tool_call_id.startswith("toolcall:")
    assert persisted_step.resource_binding["target_id"] == "chapter:2"
    assert payload["steps"][0]["tool_call_id"] == persisted_step.tool_call_id
    assert payload["steps"][0]["resource_binding"]["target_id"] == "chapter:2"

    inspect_response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "查看批次执行结果",
            "tools": [{"tool_name": "inspect_longform_chapter_batch", "params": {"task_id": task_id}}],
        },
    )
    inspected_task = inspect_response.json()["steps"][0]["output"]["selected_task"]
    assert inspected_task["batch_execution_result"]["status"] == "chapter_generated"
    assert inspected_task["execution_readiness"]["status"] == "phase62_executed"


def test_agent_run_execute_longform_chapter_batch_blocks_resource_binding_mismatch(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    prepared = _prepare_longform_batch_execution_contract(client, project.id)
    calls: list[str] = []

    def fake_verify(*args, **kwargs):
        return {
            "status": "ready",
            "reason": "approval_contract_verified",
            "current_contract": {"version": "phase108.agent_plan_approval_contract.v1"},
            "drift": {
                "expected_approval_contract_hash": "approval:test",
                "write_step_count": 1,
                "tool_contract_drift_count": 0,
                "resource_bindings": [
                    {
                        "tool_call_id": "toolcall:wrong",
                        "tool_name": "generate_chapter",
                        "target_type": "chapter",
                        "target_id": "chapter:99",
                        "source_plan_id": "plan:wrong",
                        "source_step_id": "step:write",
                        "binding_source": "server_derived",
                    }
                ],
            },
        }

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append(action_type)
        return {"status": "success", "chapter_index": 2}

    monkeypatch.setattr("app.services.writing_agent.batch_execution.verify_agent_plan_approval_contract", fake_verify)
    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "拒绝资源绑定错配的长篇批次执行",
            "tools": [
                {
                    "tool_name": "execute_longform_chapter_batch",
                    "params": {
                        "task_id": prepared["task_id"],
                        "confirm_execute": True,
                        "attempt_manifest_hash": prepared["attempt_manifest_hash"],
                        "approval_contract_hash": prepared["approval_contract_hash"],
                    },
                }
            ],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert output["status"] == "blocked"
    assert output["reason"] == "resource_binding_target_mismatch"
    assert output["execution_resource_binding"]["status"] == "blocked"
    assert output["execution_resource_binding"]["expected"]["target_id"] == "chapter:2"
    assert output["execution_resource_binding"]["resource_bindings"][0]["target_id"] == "chapter:99"
    continuation = payload["output"]["continuation_state"]
    assert continuation["blocked_tool"]["tool_call_id"] == "toolcall:wrong"
    assert continuation["blocked_tool"]["resource_binding"]["target_id"] == "chapter:99"
    assert continuation["failure"]["tool_call_id"] == "toolcall:wrong"
    assert continuation["failure"]["resource_binding"]["target_id"] == "chapter:99"
    assert continuation["recovery"]["status"] == "recommended"
    assert continuation["recovery"]["reason_code"] == "resource_binding_target_mismatch"
    assert continuation["recovery"]["next_tool"] == "prepare_longform_chapter_batch_execution"
    assert continuation["recovery"]["next_params"] == {"task_id": prepared["task_id"], "confirm_prepare": True}
    assert calls == []
    assert (
        db_session.query(ChapterContent)
        .filter(ChapterContent.project_id == project.id, ChapterContent.chapter_index == 2)
        .count()
        == 0
    )
    recovery_preview = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "规划资源绑定错配恢复",
            "tools": [{"tool_name": "plan_recovery_tools", "params": {"run_id": payload["id"]}}],
        },
    )
    recovery_output = recovery_preview.json()["steps"][0]["output"]
    assert recovery_preview.status_code == 200
    assert recovery_output["status"] == "completed"
    assert recovery_output["recovery"]["reason_code"] == "resource_binding_target_mismatch"
    assert len(recovery_output["tools"]) == 1
    assert recovery_output["tools"][0]["tool_name"] == "prepare_longform_chapter_batch_execution"
    assert recovery_output["tools"][0]["params"] == {"task_id": prepared["task_id"], "confirm_prepare": True}
    assert recovery_output["execution_policy"]["safe_auto_execute"] is False


def test_agent_run_execute_longform_chapter_batch_recovers_missing_resource_binding(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    prepared = _prepare_longform_batch_execution_contract(client, project.id)
    calls: list[str] = []

    def fake_verify(*args, **kwargs):
        return {
            "status": "ready",
            "reason": "approval_contract_verified",
            "current_contract": {"version": "phase108.agent_plan_approval_contract.v1"},
            "drift": {
                "expected_approval_contract_hash": prepared["approval_contract_hash"],
                "write_step_count": 1,
                "tool_contract_drift_count": 0,
                "resource_bindings": [],
            },
        }

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append(action_type)
        return {"status": "success", "chapter_index": 2}

    monkeypatch.setattr("app.services.writing_agent.batch_execution.verify_agent_plan_approval_contract", fake_verify)
    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "恢复缺失资源绑定的长篇批次执行",
            "tools": [
                {
                    "tool_name": "execute_longform_chapter_batch",
                    "params": {
                        "task_id": prepared["task_id"],
                        "confirm_execute": True,
                        "attempt_manifest_hash": prepared["attempt_manifest_hash"],
                        "approval_contract_hash": prepared["approval_contract_hash"],
                    },
                }
            ],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    continuation = payload["output"]["continuation_state"]
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert output["reason"] == "resource_binding_missing"
    assert output["execution_resource_binding"]["expected"]["target_id"] == "chapter:2"
    assert continuation["recovery"]["status"] == "recommended"
    assert continuation["recovery"]["reason_code"] == "resource_binding_missing"
    assert continuation["recovery"]["next_tool"] == "prepare_longform_chapter_batch_execution"
    assert continuation["recovery"]["next_params"] == {"task_id": prepared["task_id"], "confirm_prepare": True}
    assert calls == []


def test_agent_run_auto_plan_executes_binding_recovery_prepare_only_after_hash_confirmation(
    client,
    db_session,
    monkeypatch,
):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    prepared = _prepare_longform_batch_execution_contract(client, project.id)
    calls: list[str] = []

    def fake_verify(*args, **kwargs):
        return {
            "status": "ready",
            "reason": "approval_contract_verified",
            "current_contract": {"version": "phase108.agent_plan_approval_contract.v1"},
            "drift": {
                "expected_approval_contract_hash": prepared["approval_contract_hash"],
                "write_step_count": 1,
                "tool_contract_drift_count": 0,
                "resource_bindings": [
                    {
                        "tool_call_id": "toolcall:wrong",
                        "tool_name": "generate_chapter",
                        "target_type": "chapter",
                        "target_id": "chapter:99",
                        "source_plan_id": "plan:wrong",
                        "source_step_id": "step:write",
                        "binding_source": "server_derived",
                    }
                ],
            },
        }

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append(action_type)
        return {"status": "success", "chapter_index": 2}

    monkeypatch.setattr("app.services.writing_agent.batch_execution.verify_agent_plan_approval_contract", fake_verify)
    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    blocked = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "阻断资源绑定错配的长篇批次执行",
            "tools": [
                {
                    "tool_name": "execute_longform_chapter_batch",
                    "params": {
                        "task_id": prepared["task_id"],
                        "confirm_execute": True,
                        "attempt_manifest_hash": prepared["attempt_manifest_hash"],
                        "approval_contract_hash": prepared["approval_contract_hash"],
                    },
                }
            ],
        },
    )
    blocked_run_id = blocked.json()["id"]
    preview = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "预览资源绑定恢复",
            "tools": [{"tool_name": "plan_recovery_tools", "params": {"run_id": blocked_run_id}}],
        },
    )
    preview_output = preview.json()["steps"][0]["output"]
    plan_hash = preview_output["plan_hash"]

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "执行资源绑定恢复 prepare",
            "input": {
                "auto_plan": True,
                "recovery_run_id": blocked_run_id,
                "execute_recovery": True,
                "confirm_execute": True,
                "recovery_plan_hash": plan_hash,
            },
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    assert blocked.status_code == 200
    assert blocked.json()["status"] == "blocked"
    assert preview.status_code == 200
    assert preview_output["can_execute"] is True
    assert len(preview_output["tools"]) == 1
    assert preview_output["tools"][0]["tool_name"] == "prepare_longform_chapter_batch_execution"
    assert preview_output["execution_policy"]["safe_auto_execute"] is False
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["input"]["planner"]["mode"] == "execute"
    assert payload["input"]["planner"]["plan_hash"] == plan_hash
    assert payload["input"]["tools"][0]["tool_name"] == "prepare_longform_chapter_batch_execution"
    assert [step["tool_name"] for step in payload["steps"]] == ["prepare_longform_chapter_batch_execution"]
    assert output["status"] == "approval_required"
    assert output["task"]["id"] == prepared["task_id"]
    assert "generate_chapter" in output["side_effects"]["skipped"]
    assert calls == []
    assert (
        db_session.query(ChapterContent)
        .filter(ChapterContent.project_id == project.id, ChapterContent.chapter_index == 2)
        .count()
        == 0
    )


def test_agent_run_auto_plan_executes_direct_binding_recovery_prepare_only_after_hash_confirmation(
    client,
    db_session,
    monkeypatch,
):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    prepare = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "准备直接生成第2章",
            "tools": [{"tool_name": "prepare_generate_chapter_execution", "params": {"chapter_index": 2}}],
        },
    )
    approval = prepare.json()["steps"][0]["output"]
    calls: list[str] = []

    def fake_verify(*args, **kwargs):
        return {
            "status": "ready",
            "reason": "approval_contract_verified",
            "current_contract": {"version": "phase108.agent_plan_approval_contract.v1"},
            "drift": {
                "expected_approval_contract_hash": approval["agent_plan_approval_contract_hash"],
                "write_step_count": 1,
                "tool_contract_drift_count": 0,
                "resource_bindings": [
                    {
                        "tool_call_id": "toolcall:wrong",
                        "tool_name": "generate_chapter",
                        "target_type": "chapter",
                        "target_id": "chapter:99",
                        "source_plan_id": "plan:wrong",
                        "source_step_id": "step:write",
                        "binding_source": "server_derived",
                    }
                ],
            },
        }

    async def fake_generate(*args, **kwargs):
        calls.append("generate_chapter")
        return {"status": "success", "chapter_index": 2}

    monkeypatch.setattr(
        "app.services.writing_agent.chapter_generation_execution.verify_agent_plan_approval_contract",
        fake_verify,
    )
    monkeypatch.setattr("app.services.writing_agent.chapter_generation_tool.execute_generate_chapter_tool", fake_generate)

    blocked = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "阻断资源绑定错配的直接章节执行",
            "tools": [
                {
                    "tool_name": "execute_generate_chapter_with_approval",
                    "params": {
                        "chapter_index": 2,
                        "confirm_execute": True,
                        "approval_contract_hash": approval["agent_plan_approval_contract_hash"],
                        "approval_contract": approval["agent_plan_approval_contract"],
                    },
                }
            ],
        },
    )
    blocked_run_id = blocked.json()["id"]
    preview = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "预览直接章节资源绑定恢复",
            "tools": [{"tool_name": "plan_recovery_tools", "params": {"run_id": blocked_run_id}}],
        },
    )
    preview_output = preview.json()["steps"][0]["output"]
    plan_hash = preview_output["plan_hash"]

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "执行直接章节资源绑定恢复 prepare",
            "input": {
                "auto_plan": True,
                "recovery_run_id": blocked_run_id,
                "execute_recovery": True,
                "confirm_execute": True,
                "recovery_plan_hash": plan_hash,
            },
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    assert prepare.status_code == 200
    assert approval["status"] == "approval_required"
    assert blocked.status_code == 200
    assert blocked.json()["status"] == "blocked"
    assert preview.status_code == 200
    assert preview_output["can_execute"] is True
    assert len(preview_output["tools"]) == 1
    assert preview_output["tools"][0]["tool_name"] == "prepare_generate_chapter_execution"
    assert preview_output["execution_policy"]["safe_auto_execute"] is False
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["input"]["planner"]["mode"] == "execute"
    assert payload["input"]["planner"]["plan_hash"] == plan_hash
    assert payload["input"]["tools"][0]["tool_name"] == "prepare_generate_chapter_execution"
    assert [step["tool_name"] for step in payload["steps"]] == ["prepare_generate_chapter_execution"]
    assert output["status"] == "approval_required"
    assert output["chapter_index"] == 2
    assert output["side_effects"]["skipped"] == ["generate_chapter"]
    assert calls == []
    assert (
        db_session.query(ChapterContent)
        .filter(ChapterContent.project_id == project.id, ChapterContent.chapter_index == 2)
        .count()
        == 0
    )


def test_agent_run_execute_longform_chapter_batch_requires_confirmation(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    prepared = _prepare_longform_batch_execution_contract(client, project.id)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "拒绝未确认的长篇批次执行",
            "tools": [
                {
                    "tool_name": "execute_longform_chapter_batch",
                    "params": {
                        "task_id": prepared["task_id"],
                        "confirm_execute": False,
                        "attempt_manifest_hash": prepared["attempt_manifest_hash"],
                        "approval_contract_hash": prepared["approval_contract_hash"],
                    },
                }
            ],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert output["status"] == "blocked"
    assert output["reason"] == "confirmation_required"
    assert (
        db_session.query(ChapterContent)
        .filter(ChapterContent.project_id == project.id, ChapterContent.chapter_index == 2)
        .count()
        == 0
    )


def test_agent_run_execute_longform_chapter_batch_blocks_hash_mismatch(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    prepared = _prepare_longform_batch_execution_contract(client, project.id)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "拒绝错误哈希的长篇批次执行",
            "tools": [
                {
                    "tool_name": "execute_longform_chapter_batch",
                    "params": {
                        "task_id": prepared["task_id"],
                        "confirm_execute": True,
                        "attempt_manifest_hash": "wrong-attempt-hash",
                        "approval_contract_hash": prepared["approval_contract_hash"],
                    },
                }
            ],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert output["status"] == "blocked"
    assert output["reason"] == "attempt_manifest_hash_mismatch"
    assert (
        db_session.query(ChapterContent)
        .filter(ChapterContent.project_id == project.id, ChapterContent.chapter_index == 2)
        .count()
        == 0
    )


def test_agent_run_execute_longform_chapter_batch_blocks_chapter_state_drift(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    prepared = _prepare_longform_batch_execution_contract(client, project.id)
    db_session.add(
        ChapterContent(
            project_id=project.id,
            chapter_index=2,
            title="提前写入",
            content="用户或其他任务已经生成了这一章。",
            word_count=20,
            status="generated",
        )
    )
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "拒绝状态漂移后的长篇批次执行",
            "tools": [
                {
                    "tool_name": "execute_longform_chapter_batch",
                    "params": {
                        "task_id": prepared["task_id"],
                        "confirm_execute": True,
                        "attempt_manifest_hash": prepared["attempt_manifest_hash"],
                        "approval_contract_hash": prepared["approval_contract_hash"],
                    },
                }
            ],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert output["status"] == "blocked"
    assert output["reason"] == "chapter_state_drift"
    assert output["generated_chapter_indexes"] == [2]


def test_agent_run_execute_longform_chapter_batch_requires_agent_plan_approval_contract(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    prepared = _prepare_longform_batch_execution_contract(client, project.id)
    task = db_session.query(BackgroundTask).filter(BackgroundTask.id == prepared["task_id"]).one()
    task.result = {key: value for key, value in (task.result or {}).items() if key != "agent_plan_approval_contract"}
    db_session.add(task)
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "拒绝缺少 Agent 计划审批验证的长篇批次执行",
            "tools": [
                {
                    "tool_name": "execute_longform_chapter_batch",
                    "params": {
                        "task_id": prepared["task_id"],
                        "confirm_execute": True,
                        "attempt_manifest_hash": prepared["attempt_manifest_hash"],
                        "approval_contract_hash": prepared["approval_contract_hash"],
                    },
                }
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert output["status"] == "blocked"
    assert output["reason"] == "agent_plan_approval_verification_missing"
    assert (
        db_session.query(ChapterContent)
        .filter(ChapterContent.project_id == project.id, ChapterContent.chapter_index == 2)
        .count()
        == 0
    )


def test_agent_run_execute_longform_chapter_batch_blocks_agent_plan_approval_hash_drift(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    prepared = _prepare_longform_batch_execution_contract(client, project.id)
    task = db_session.query(BackgroundTask).filter(BackgroundTask.id == prepared["task_id"]).one()
    result = dict(task.result or {})
    agent_plan = dict(result["agent_plan"])
    agent_plan["steps"] = [{**agent_plan["steps"][0], "params": {"chapter_index": 3}}]
    result["agent_plan"] = agent_plan
    task.result = result
    db_session.add(task)
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "拒绝 Agent 计划审批哈希漂移后的长篇批次执行",
            "tools": [
                {
                    "tool_name": "execute_longform_chapter_batch",
                    "params": {
                        "task_id": prepared["task_id"],
                        "confirm_execute": True,
                        "attempt_manifest_hash": prepared["attempt_manifest_hash"],
                        "approval_contract_hash": prepared["approval_contract_hash"],
                    },
                }
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert output["status"] == "blocked"
    assert output["reason"] == "agent_plan_approval_hash_mismatch"
    assert output["agent_plan_approval_verification"]["reason"] == "approval_contract_hash_mismatch"


def test_agent_run_can_review_longform_chapter_batch_execution(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    prepared = _prepare_longform_batch_execution_contract(client, project.id)
    _execute_approved_longform_batch_chapter(client, project.id, prepared, monkeypatch)
    calls: list[tuple[str, int]] = []

    def fake_quality(db, project_id: str, chapter_index: int):
        calls.append(("quality", chapter_index))
        return {
            "status": "ready",
            "chapter_index": chapter_index,
            "finding_count": 0,
            "blocker_count": 0,
            "findings": [],
            "recommended_actions": [],
        }

    def fake_continuity(db, project_id: str, chapter_index: int, *, lookback: int):
        calls.append(("continuity", lookback))
        return {
            "status": "ready",
            "chapter_index": chapter_index,
            "finding_count": 0,
            "blocker_count": 0,
            "findings": [],
            "recommended_actions": [],
        }

    def fake_world_model(db, project_id: str, chapter_index: int):
        calls.append(("world_model", chapter_index))
        return {
            "status": "completed",
            "chapter_index": chapter_index,
            "proposal_bundle_id": "bundle-2",
            "created": {"proposal_items": 3},
            "updated": {"proposal_items": 0},
            "skipped": {"duplicates": 1},
        }

    monkeypatch.setattr("app.core.chapter_quality_review.review_chapter_quality", fake_quality)
    monkeypatch.setattr("app.core.chapter_continuity_review.review_chapter_continuity", fake_continuity)
    monkeypatch.setattr("app.core.athena_longform.analyze_chapter_to_world_proposals", fake_world_model)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "审查已执行的长篇批次",
            "tools": [
                {
                    "tool_name": "review_longform_chapter_batch_execution",
                    "params": {"task_id": prepared["task_id"], "lookback": 12, "confirm_review": True},
                }
            ],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    task = db_session.query(BackgroundTask).filter(BackgroundTask.id == prepared["task_id"]).one()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["steps"][0]["target_type"] == "background_task"
    assert output["status"] == "completed"
    assert output["chapter_index"] == 2
    assert output["review_gate"]["status"] == "passed"
    assert output["reviews"]["quality"]["status"] == "ready"
    assert output["reviews"]["continuity"]["status"] == "ready"
    assert output["reviews"]["world_model"]["proposal_bundle_id"] == "bundle-2"
    assert output["side_effects"]["executed"] == [
        "review_chapter_quality",
        "review_chapter_continuity",
        "analyze_chapter_world_model",
        "background_task_result_post_generation_review",
    ]
    assert calls == [("quality", 2), ("continuity", 12), ("world_model", 2)]
    assert task.result["post_generation_review_result"]["status"] == "passed"
    assert task.result["execution_checkpoints"][-1]["checkpoint_type"] == "post_generation_review"

    inspect_response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "查看审查证据",
            "tools": [{"tool_name": "inspect_longform_chapter_batch", "params": {"task_id": prepared["task_id"]}}],
        },
    )
    inspected_task = inspect_response.json()["steps"][0]["output"]["selected_task"]
    assert inspected_task["post_generation_review_result"]["status"] == "passed"
    assert inspected_task["execution_readiness"]["status"] == "phase63_reviewed"


def test_agent_run_review_longform_chapter_batch_requires_review_confirmation(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    prepared = _prepare_longform_batch_execution_contract(client, project.id)
    _execute_approved_longform_batch_chapter(client, project.id, prepared, monkeypatch)
    calls: list[str] = []

    def fake_quality(db, project_id: str, chapter_index: int):
        calls.append("quality")
        return {"status": "ready", "chapter_index": chapter_index, "finding_count": 0, "blocker_count": 0}

    monkeypatch.setattr("app.core.chapter_quality_review.review_chapter_quality", fake_quality)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "未确认时审查已执行的长篇批次",
            "tools": [
                {
                    "tool_name": "review_longform_chapter_batch_execution",
                    "params": {"task_id": prepared["task_id"]},
                }
            ],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    task = db_session.query(BackgroundTask).filter(BackgroundTask.id == prepared["task_id"]).one()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert output["status"] == "blocked"
    assert output["reason"] == "review_confirmation_required"
    assert output["required_confirmation"] == {"confirm_review": True, "task_id": prepared["task_id"]}
    assert output["side_effects"]["executed"] == []
    assert calls == []
    assert "post_generation_review_result" not in (task.result or {})


def test_agent_run_review_longform_chapter_batch_requires_execution_evidence(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    prepared = _prepare_longform_batch_execution_contract(client, project.id)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "拒绝未执行批次的审查",
            "tools": [
                {
                    "tool_name": "review_longform_chapter_batch_execution",
                    "params": {"task_id": prepared["task_id"], "confirm_review": True},
                }
            ],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert output["status"] == "blocked"
    assert output["reason"] == "missing_batch_execution_result"


def test_agent_run_review_longform_chapter_batch_blocks_before_world_model_on_quality_blocker(
    client,
    db_session,
    monkeypatch,
):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    prepared = _prepare_longform_batch_execution_contract(client, project.id)
    _execute_approved_longform_batch_chapter(client, project.id, prepared, monkeypatch)
    calls: list[str] = []

    def fake_quality(db, project_id: str, chapter_index: int):
        calls.append("quality")
        return {
            "status": "blocked",
            "chapter_index": chapter_index,
            "finding_count": 1,
            "blocker_count": 1,
            "findings": [{"code": "generic_chapter_title", "severity": "blocker", "message": "标题占位", "evidence": {}}],
            "recommended_actions": ["revise_chapter"],
        }

    def fake_continuity(db, project_id: str, chapter_index: int, *, lookback: int):
        calls.append("continuity")
        return {
            "status": "ready",
            "chapter_index": chapter_index,
            "finding_count": 0,
            "blocker_count": 0,
            "findings": [],
            "recommended_actions": [],
        }

    def fake_world_model(db, project_id: str, chapter_index: int):
        calls.append("world_model")
        return {"status": "completed", "chapter_index": chapter_index}

    monkeypatch.setattr("app.core.chapter_quality_review.review_chapter_quality", fake_quality)
    monkeypatch.setattr("app.core.chapter_continuity_review.review_chapter_continuity", fake_continuity)
    monkeypatch.setattr("app.core.athena_longform.analyze_chapter_to_world_proposals", fake_world_model)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "质量阻塞时不要回灌世界模型",
            "tools": [
                {
                    "tool_name": "review_longform_chapter_batch_execution",
                    "params": {"task_id": prepared["task_id"], "confirm_review": True},
                }
            ],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    task = db_session.query(BackgroundTask).filter(BackgroundTask.id == prepared["task_id"]).one()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert output["status"] == "blocked"
    assert output["reason"] == "post_generation_review_has_blockers"
    assert output["review_gate"]["status"] == "needs_revision"
    assert output["reviews"]["world_model"]["status"] == "skipped"
    assert output["reviews"]["world_model"]["reason"] == "review_blockers_present"
    assert output["recommended_next_tools"] == ["plan_chapter_revision", "create_revision_draft", "inspect_longform_chapter_batch"]
    assert calls == ["quality", "continuity"]
    assert task.result["post_generation_review_result"]["status"] == "needs_revision"


def test_agent_run_review_longform_chapter_batch_is_idempotent(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    prepared = _prepare_longform_batch_execution_contract(client, project.id)
    _execute_approved_longform_batch_chapter(client, project.id, prepared, monkeypatch)
    calls: list[str] = []

    def fake_quality(db, project_id: str, chapter_index: int):
        calls.append("quality")
        return {
            "status": "ready",
            "chapter_index": chapter_index,
            "finding_count": 0,
            "blocker_count": 0,
            "findings": [],
            "recommended_actions": [],
        }

    def fake_continuity(db, project_id: str, chapter_index: int, *, lookback: int):
        calls.append("continuity")
        return {
            "status": "ready",
            "chapter_index": chapter_index,
            "finding_count": 0,
            "blocker_count": 0,
            "findings": [],
            "recommended_actions": [],
        }

    def fake_world_model(db, project_id: str, chapter_index: int):
        calls.append("world_model")
        return {"status": "skipped", "reason": "missing_world_model_profile", "chapter_index": chapter_index}

    monkeypatch.setattr("app.core.chapter_quality_review.review_chapter_quality", fake_quality)
    monkeypatch.setattr("app.core.chapter_continuity_review.review_chapter_continuity", fake_continuity)
    monkeypatch.setattr("app.core.athena_longform.analyze_chapter_to_world_proposals", fake_world_model)

    first = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "首次审查",
            "tools": [
                {
                    "tool_name": "review_longform_chapter_batch_execution",
                    "params": {"task_id": prepared["task_id"], "confirm_review": True},
                }
            ],
        },
    )
    calls_after_first = list(calls)
    second = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "重复审查",
            "tools": [
                {
                    "tool_name": "review_longform_chapter_batch_execution",
                    "params": {"task_id": prepared["task_id"]},
                }
            ],
        },
    )

    second_output = second.json()["steps"][0]["output"]
    assert first.status_code == 200
    assert first.json()["status"] == "success"
    assert calls_after_first == ["quality", "continuity", "world_model"]
    assert second.status_code == 200
    assert second.json()["status"] == "success"
    assert second_output["status"] == "skipped"
    assert second_output["reason"] == "post_generation_review_already_recorded"
    assert second_output["post_generation_review_result"]["status"] == "passed"
    assert calls == calls_after_first


def test_agent_run_routes_passed_longform_batch_review_to_next_batch_preview(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2, 3], generated_chapters=[1])
    prepared = _prepare_longform_batch_execution_contract(client, project.id)
    _execute_approved_longform_batch_chapter(client, project.id, prepared, monkeypatch)
    _review_executed_longform_batch_chapter(client, project.id, prepared["task_id"], monkeypatch, status="passed")
    calls: list[tuple[int | None, int | None]] = []

    def fake_batch_plan(
        db,
        project_id: str,
        *,
        source_run_id: str | None,
        start_chapter: int | None,
        batch_size: int | None,
    ):
        calls.append((start_chapter, batch_size))
        return {
            "status": "completed",
            "plan_version": "phase57.longform_batch_plan.v1",
            "batch": {"start_chapter": 3, "end_chapter": 3, "batch_size": 1, "chapter_indexes": [3]},
            "dag": {"node_count": 7, "nodes": [], "edges": []},
        }

    monkeypatch.setattr(
        "app.services.writing_agent.batch_planner.build_longform_chapter_batch_plan",
        fake_batch_plan,
    )

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "审查通过后规划下一章批次",
            "tools": [
                {
                    "tool_name": "route_longform_chapter_batch_after_review",
                    "params": {"task_id": prepared["task_id"], "next_batch_size": 1},
                }
            ],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    task = db_session.query(BackgroundTask).filter(BackgroundTask.id == prepared["task_id"]).one()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert output["status"] == "completed"
    assert output["route_decision"]["decision"] == "continue_to_next_batch"
    assert output["route_decision"]["next_chapter_index"] == 3
    assert output["post_generation_route_result"]["next_batch_plan"]["batch"]["chapter_indexes"] == [3]
    assert output["recommended_next_tools"] == ["enqueue_longform_chapter_batch", "inspect_longform_chapter_batch"]
    assert calls == [(3, 1)]
    assert task.result["post_generation_route_result"]["route_decision"]["decision"] == "continue_to_next_batch"
    assert task.result["execution_checkpoints"][-1]["checkpoint_type"] == "post_generation_route"
    assert db_session.query(BackgroundTask).filter(BackgroundTask.project_id == project.id).count() == 1

    inspect_response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "查看路由证据",
            "tools": [{"tool_name": "inspect_longform_chapter_batch", "params": {"task_id": prepared["task_id"]}}],
        },
    )
    inspected_task = inspect_response.json()["steps"][0]["output"]["selected_task"]
    assert inspected_task["post_generation_route_result"]["route_decision"]["decision"] == "continue_to_next_batch"
    assert inspected_task["execution_readiness"]["status"] == "phase64_routed_passed"


def test_agent_run_routes_blocked_longform_batch_review_to_revision_plan(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    prepared = _prepare_longform_batch_execution_contract(client, project.id)
    _execute_approved_longform_batch_chapter(client, project.id, prepared, monkeypatch)
    _review_executed_longform_batch_chapter(client, project.id, prepared["task_id"], monkeypatch, status="needs_revision")
    calls: list[int] = []

    def fake_revision_plan(db, project_id: str, chapter_index: int):
        calls.append(chapter_index)
        return {
            "status": "blocked",
            "chapter_index": chapter_index,
            "should_generate_next_chapter": False,
            "revision_actions": [{"action": "retitle_chapter", "severity": "blocker"}],
            "recommended_next_tools": ["create_revision_draft"],
        }

    monkeypatch.setattr("app.core.chapter_revision_planner.plan_chapter_revision", fake_revision_plan)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "审查未通过后规划修订路径",
            "tools": [
                {
                    "tool_name": "route_longform_chapter_batch_after_review",
                    "params": {"task_id": prepared["task_id"]},
                }
            ],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    task = db_session.query(BackgroundTask).filter(BackgroundTask.id == prepared["task_id"]).one()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert output["status"] == "completed"
    assert output["route_decision"]["decision"] == "stop_for_revision"
    assert output["post_generation_route_result"]["recovery_plan"]["revision_plan"]["revision_actions"][0]["action"] == "retitle_chapter"
    assert output["recommended_next_tools"] == ["plan_chapter_revision", "create_revision_draft", "inspect_longform_chapter_batch"]
    assert calls == [2]
    assert task.result["post_generation_route_result"]["route_decision"]["decision"] == "stop_for_revision"
    assert db_session.query(BackgroundTask).filter(BackgroundTask.project_id == project.id).count() == 1


def test_agent_run_post_review_routing_requires_phase63_review(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    prepared = _prepare_longform_batch_execution_contract(client, project.id)
    _execute_approved_longform_batch_chapter(client, project.id, prepared, monkeypatch)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "缺少审查结果时拒绝路由",
            "tools": [
                {
                    "tool_name": "route_longform_chapter_batch_after_review",
                    "params": {"task_id": prepared["task_id"]},
                }
            ],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert output["status"] == "blocked"
    assert output["reason"] == "missing_post_generation_review_result"


def test_agent_run_post_review_routing_blocks_review_hash_mismatch(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2, 3], generated_chapters=[1])
    prepared = _prepare_longform_batch_execution_contract(client, project.id)
    _execute_approved_longform_batch_chapter(client, project.id, prepared, monkeypatch)
    _review_executed_longform_batch_chapter(client, project.id, prepared["task_id"], monkeypatch, status="passed")

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "拒绝过期审查哈希",
            "tools": [
                {
                    "tool_name": "route_longform_chapter_batch_after_review",
                    "params": {
                        "task_id": prepared["task_id"],
                        "expected_post_generation_review_hash": "wrong-review-hash",
                    },
                }
            ],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert output["status"] == "blocked"
    assert output["reason"] == "post_generation_review_hash_mismatch"


def test_agent_run_post_review_routing_is_idempotent(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2, 3], generated_chapters=[1])
    prepared = _prepare_longform_batch_execution_contract(client, project.id)
    _execute_approved_longform_batch_chapter(client, project.id, prepared, monkeypatch)
    _review_executed_longform_batch_chapter(client, project.id, prepared["task_id"], monkeypatch, status="passed")
    calls: list[int | None] = []

    def fake_batch_plan(
        db,
        project_id: str,
        *,
        source_run_id: str | None,
        start_chapter: int | None,
        batch_size: int | None,
    ):
        calls.append(start_chapter)
        return {
            "status": "completed",
            "batch": {"start_chapter": 3, "end_chapter": 3, "batch_size": 1, "chapter_indexes": [3]},
        }

    monkeypatch.setattr(
        "app.services.writing_agent.batch_planner.build_longform_chapter_batch_plan",
        fake_batch_plan,
    )

    first = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "首次路由",
            "tools": [
                {
                    "tool_name": "route_longform_chapter_batch_after_review",
                    "params": {"task_id": prepared["task_id"]},
                }
            ],
        },
    )
    second = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "重复路由",
            "tools": [
                {
                    "tool_name": "route_longform_chapter_batch_after_review",
                    "params": {"task_id": prepared["task_id"]},
                }
            ],
        },
    )

    output = second.json()["steps"][0]["output"]
    assert first.status_code == 200
    assert first.json()["status"] == "success"
    assert second.status_code == 200
    assert second.json()["status"] == "success"
    assert output["status"] == "skipped"
    assert output["reason"] == "post_generation_route_already_recorded"
    assert output["post_generation_route_result"]["route_decision"]["decision"] == "continue_to_next_batch"
    assert calls == [3]


def test_agent_run_list_and_detail_are_project_scoped(client, db_session):
    project_a = _create_project(client, "Project A")
    project_b = _create_project(client, "Project B")
    run = WritingAgentRun(project_id=project_a, goal="A run", status="success", entrypoint="api", input={})
    other_run = WritingAgentRun(project_id=project_b, goal="B run", status="success", entrypoint="api", input={})
    db_session.add_all([run, other_run])
    db_session.commit()

    listing = client.get(f"/api/v1/projects/{project_a}/agent-runs")
    detail = client.get(f"/api/v1/projects/{project_a}/agent-runs/{run.id}")
    cross_project_detail = client.get(f"/api/v1/projects/{project_b}/agent-runs/{run.id}")

    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["id"] == run.id
    assert detail.status_code == 200
    assert detail.json()["id"] == run.id
    assert cross_project_detail.status_code == 404


def test_cancel_agent_run_marks_pending_or_running_run_cancelled(client, db_session):
    project_id = _create_project(client, "Cancel Project")
    run = WritingAgentRun(project_id=project_id, goal="cancel me", status="running", entrypoint="api", input={})
    db_session.add(run)
    db_session.commit()

    response = client.post(f"/api/v1/projects/{project_id}/agent-runs/{run.id}/cancel")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert response.json()["finished_at"] is not None


def test_agent_run_blocks_direct_storyline_without_approval(client, db_session, monkeypatch):
    project_id = _create_project(client, "Trace Project")
    _create_trace(db_session, project_id, "trace-storyline", "storyline_generation")
    calls: list[str] = []

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append(action_type)
        return {"status": "success", "trace_id": "trace-storyline"}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "生成故事线",
            "tools": [{"tool_name": "generate_storyline", "command_args": "主线和支线"}],
        },
    )

    step = response.json()["steps"][0]
    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert step["trace_id"] is None
    assert step["output"]["reason"] == "approval_required_before_write"
    assert step["output"]["recommended_next_tools"] == ["prepare_generate_storyline_execution"]
    assert calls == []


def test_agent_run_stops_after_unapproved_direct_generation_tool(client, db_session, monkeypatch):
    project_id = _create_project(client, "Fail Project")
    calls = []

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append(action_type)
        return {"status": "failed", "error": "model unavailable"}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "失败后停止",
            "tools": [
                {"tool_name": "generate_setup"},
                {"tool_name": "generate_storyline"},
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert payload["error"] == "Agent run blocked"
    assert [step["status"] for step in payload["steps"]] == ["blocked"]
    assert payload["steps"][0]["output"]["recommended_next_tools"] == ["prepare_generate_setup_execution"]
    assert calls == []


def test_agent_run_records_normalized_output_for_unsupported_tool(client):
    project_id = _create_project(client, "Unsupported Tool Project")

    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "调用不存在的工具",
            "tools": [{"tool_name": "not_a_real_tool", "params": {"chapter_index": 1}}],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "failed"
    assert payload["error"] == "Unsupported writing agent tool: not_a_real_tool"
    step = payload["steps"][0]
    assert step["status"] == "failed"
    assert step["output"]["status"] == "failed"
    assert step["output"]["error"] == "Unsupported writing agent tool: not_a_real_tool"
    envelope = step["output"]["agent_tool_result"]
    assert envelope["version"] == "phase42.tool_result.v1"
    assert envelope["tool_name"] == "not_a_real_tool"
    assert envelope["step_status"] == "failed"
    assert envelope["result_status"] == "failed"
    assert envelope["is_error"] is True
    assert envelope["execution_route"] == "unsupported"


def test_agent_run_records_chapter_length_and_world_model_diagnostics(client, db_session, monkeypatch):
    project_id = _create_project(client, "Diagnostics Project")
    trace = AIModelCallTrace(
        project_id=project_id,
        trace_type="chapter_generation",
        status="success",
        chapter_index=2,
        trace_metadata={
            "chapter_word_target": {
                "status": "over",
                "actual_word_count": 3735,
                "target_min_word_count": 2000,
                "target_average_word_count": 2000,
                "target_max_word_count": 3000,
            }
        },
    )
    db_session.add(trace)
    db_session.commit()

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        return {"status": "success", "trace_id": trace.id, "chapter_index": 2}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "生成第2章",
            "tools": [{"tool_name": "generate_chapter", "params": {"chapter_index": 2}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    length_decision = output["chapter_length_decision"]
    assert length_decision["status"] == "over"
    assert length_decision["decision"] == "accept_with_warning"
    assert length_decision["severity"] == "warning"
    assert length_decision["actual_word_count"] == 3735
    assert length_decision["target_min_word_count"] == 2000
    assert length_decision["target_average_word_count"] == 2000
    assert length_decision["target_max_word_count"] == 3000
    assert length_decision["repeated_drift_count"] == 0
    assert length_decision["recommended_actions"] == []
    assert output["world_model_proposal_diagnostic"]["status"] == "missing"
    assert output["world_model_proposal_diagnostic"]["reason"] == "missing_profile"


def test_agent_run_continuation_state_exposes_recommended_followups(client, monkeypatch):
    project_id = _create_project(client, "Continuation Followups")

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        return {"status": "success", "chapter_index": action_params["chapter_index"]}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "生成第2章",
            "tools": [{"tool_name": "generate_chapter", "params": {"chapter_index": 2}}],
        },
    )

    payload = response.json()
    state = payload["output"]["continuation_state"]
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert state["recommended_followups"]["status"] == "recommended"
    assert state["recommended_followups"]["source_tool"] == "generate_chapter"
    assert state["recommended_followups"]["next_tool"] == "review_chapter_quality"
    assert state["recommended_followups"]["canonical_followups"] == [
        "review_chapter_quality",
        "review_chapter_continuity",
        "analyze_chapter_world_model",
    ]


def test_agent_preflight_blocks_when_target_outline_is_missing(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1, 2])

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第3章是否可写",
            "tools": [
                {"tool_name": "preflight_writing", "params": {"chapter_index": 3}},
                {"tool_name": "generate_chapter", "params": {"chapter_index": 3}},
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert payload["error"] == "第3章缺少章节大纲。"
    assert payload["output"]["blocked_step_count"] == 1
    assert len(payload["steps"]) == 1
    step = payload["steps"][0]
    assert step["tool_name"] == "preflight_writing"
    assert step["status"] == "blocked"
    assert step["target_type"] == "preflight"
    assert step["chapter_index"] == 3
    assert step["output"]["status"] == "blocked"
    assert step["output"]["checks"]["outline_chapter"]["status"] == "missing"
    assert step["output"]["issues"][0]["code"] == "missing_outline_chapter"
    recovery = step["output"]["agent_tool_result"]["recovery"]
    assert recovery["status"] == "recommended"
    assert recovery["reason_code"] == "missing_outline_chapter"
    assert recovery["next_tool"] == "expand_outline_window"
    assert recovery["next_params"] == {"start_chapter": 3, "end_chapter": 3}
    assert recovery["should_continue_current_run"] is False


def test_agent_preflight_ready_when_required_context_exists(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2, 3], generated_chapters=[1, 2])
    import_setup_to_world_model(db_session, project.id)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第3章是否可写",
            "tools": [{"tool_name": "preflight_writing", "params": {"chapter_index": 3}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "ready"
    assert output["checks"]["world_model_profile"]["status"] == "ready"
    assert output["checks"]["outline_chapter"]["status"] == "ready"
    assert output["checks"]["previous_chapter"]["status"] == "ready"


def test_agent_preflight_reports_previous_chapter_state_card(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "空白信的秘密"
    chapter.content = "林深和苏晚晴在灯塔下发现空白信，信纸显出雾晶是钥匙。两人决定前往下城黑市。"
    chapter.word_count = 2000
    db_session.commit()
    import_setup_to_world_model(db_session, project.id)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第2章是否可写",
            "tools": [{"tool_name": "preflight_writing", "params": {"chapter_index": 2}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    card = output["checks"]["previous_chapter_state_card"]
    assert response.status_code == 200
    assert card["status"] == "ready"
    assert card["chapter_index"] == 1
    assert card["title"] == "空白信的秘密"
    assert "雾晶是钥匙" in card["last_excerpt"]
    assert "空白信" in card["key_terms"]
    assert "下城" in card["key_terms"]


def test_agent_preflight_reports_memory_activation_plan(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2, 3], generated_chapters=[1, 2])
    _seed_activation_memories(db_session, project.id)
    import_setup_to_world_model(db_session, project.id)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第3章长期记忆是否可用",
            "tools": [{"tool_name": "preflight_writing", "params": {"chapter_index": 3}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    activation = output["checks"]["memory_activation"]
    assert response.status_code == 200
    assert activation["status"] in {"ready", "degraded"}
    assert activation["activated_counts"]["longform"] >= 2
    assert "空白信" in activation["prompt_preview"]
    assert "雾晶" in activation["prompt_preview"]
    assert "潮下车站" not in activation["prompt_preview"]


def test_agent_preflight_blocks_when_generated_chapter_outline_gap_exists(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 3, 4], generated_chapters=[1, 2, 3])
    for chapter in db_session.query(ChapterContent).filter(ChapterContent.project_id == project.id):
        chapter.word_count = 2000
    db_session.commit()
    import_setup_to_world_model(db_session, project.id)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第4章是否可写",
            "tools": [{"tool_name": "preflight_writing", "params": {"chapter_index": 4}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert output["checks"]["historical_outline_gaps"]["status"] == "missing"
    assert output["checks"]["historical_outline_gaps"]["chapter_indexes"] == [2]
    assert output["issues"][0]["code"] == "missing_historical_outline_chapters"
    assert output["issues"][0]["suggested_tool"] == "backfill_outline_gaps"
    recovery = output["agent_tool_result"]["recovery"]
    assert recovery["status"] == "recommended"
    assert recovery["reason_code"] == "missing_historical_outline_chapters"
    assert recovery["next_tool"] == "backfill_outline_gaps"
    assert recovery["next_params"] == {"before_chapter": 4}
    assert recovery["should_continue_current_run"] is False


def test_agent_backfill_outline_gaps_uses_existing_chapter_content_then_preflight_ready(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 3, 4], generated_chapters=[1, 2, 3])
    for chapter in db_session.query(ChapterContent).filter(ChapterContent.project_id == project.id):
        chapter.word_count = 2000
    db_session.commit()
    import_setup_to_world_model(db_session, project.id)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "回填历史大纲缺口并检查第4章",
            "tools": [
                {"tool_name": "backfill_outline_gaps", "params": {"before_chapter": 4}},
                {"tool_name": "preflight_writing", "params": {"chapter_index": 4}},
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["steps"][0]["output"]["backfilled_chapter_indexes"] == [2]
    assert payload["steps"][1]["output"]["status"] == "ready"
    outline = db_session.query(Outline).filter(Outline.project_id == project.id).one()
    assert [chapter["chapter_index"] for chapter in outline.chapters] == [1, 2, 3, 4]
    chapter_two = next(chapter for chapter in outline.chapters if chapter["chapter_index"] == 2)
    assert chapter_two["title"] == "雾港线索2"
    assert chapter_two["purpose"] == "根据已生成正文自动回填章节大纲。"


def test_agent_preflight_missing_previous_chapter_recovery_recommends_prior_generation(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2, 3], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第3章是否可写",
            "tools": [{"tool_name": "preflight_writing", "params": {"chapter_index": 3}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    recovery = output["agent_tool_result"]["recovery"]
    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert output["issues"][0]["code"] == "missing_previous_chapter"
    assert recovery["status"] == "recommended"
    assert recovery["reason_code"] == "missing_previous_chapter"
    assert recovery["next_tool"] == "generate_chapter"
    assert recovery["next_params"] == {"chapter_index": 2}
    assert recovery["should_continue_current_run"] is False


def test_agent_preflight_missing_setup_recovery_requests_setup_generation(client):
    project_id = _create_project(client, "Missing Setup Recovery")

    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "检查第1章是否可写",
            "tools": [{"tool_name": "preflight_writing", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    recovery = output["agent_tool_result"]["recovery"]
    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert output["issues"][0]["code"] == "missing_setup"
    assert recovery["policy_version"] == "phase47.recovery_policy.v1"
    assert recovery["status"] == "recommended"
    assert recovery["reason_code"] == "missing_setup"
    assert recovery["next_tool"] == "generate_setup"
    assert recovery["next_params"] == {}
    assert recovery["requires_user_input"] is True
    assert recovery["user_input_fields"] == ["command_args"]


def test_agent_import_setup_world_model_creates_profile(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[])

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "导入世界模型",
            "tools": [{"tool_name": "import_setup_world_model"}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "completed"
    assert output["profile_version"] == 1
    assert db_session.query(ProjectProfileVersion).filter_by(project_id=project.id).count() == 1


def test_agent_analyze_chapter_world_model_records_proposal_output(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "分析第1章",
            "tools": [{"tool_name": "analyze_chapter_world_model", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "completed"
    assert output["chapter_index"] == 1
    assert output["created"]["proposal_items"] >= 1


def test_agent_skips_analyze_when_generate_step_already_auto_analyzed_same_chapter(
    client,
    db_session,
    monkeypatch,
):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2, 3, 4], generated_chapters=[1, 2, 3])
    trace = AIModelCallTrace(
        project_id=project.id,
        trace_type="chapter_generation",
        status="success",
        chapter_index=4,
        trace_metadata={
            "chapter_word_target": {
                "status": "within",
                "actual_word_count": 2100,
                "target_min_word_count": 2000,
                "target_average_word_count": 2000,
                "target_max_word_count": 3000,
            }
        },
    )
    db_session.add(trace)
    db_session.commit()

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        return {
            "status": "success",
            "chapter_index": 4,
            "trace_id": trace.id,
            "athena_analysis": {
                "status": "completed",
                "chapter_index": 4,
                "proposal_bundle_id": "bundle-4",
                "created": {"proposal_items": 3},
                "updated": {"proposal_items": 0},
            },
        }

    def fail_duplicate_analysis(**_kwargs):
        raise AssertionError("duplicate analyze should have been skipped")

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)
    monkeypatch.setattr("app.core.athena_longform.analyze_chapter_to_world_proposals", fail_duplicate_analysis)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "生成第4章并分析世界模型",
            "tools": [
                {"tool_name": "generate_chapter", "params": {"chapter_index": 4}},
                {"tool_name": "analyze_chapter_world_model", "params": {"chapter_index": 4}},
            ],
        },
    )

    payload = response.json()
    analyze_output = payload["steps"][1]["output"]
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert analyze_output["status"] == "skipped"
    assert analyze_output["reason"] == "chapter_already_analyzed_in_run"
    assert analyze_output["chapter_index"] == 4
    assert analyze_output["source_step_id"] == payload["steps"][0]["id"]
    assert analyze_output["proposal_bundle_id"] == "bundle-4"


def test_agent_chapter_length_decision_flags_repeated_over_target_drift(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2, 3], generated_chapters=[1, 2, 3])
    for chapter in db_session.query(ChapterContent).filter(ChapterContent.project_id == project.id):
        chapter.word_count = 3300
    trace = AIModelCallTrace(
        project_id=project.id,
        trace_type="chapter_generation",
        status="success",
        chapter_index=3,
        trace_metadata={
            "chapter_word_target": {
                "status": "over",
                "actual_word_count": 3300,
                "target_min_word_count": 2000,
                "target_average_word_count": 2000,
                "target_max_word_count": 3000,
            }
        },
    )
    db_session.add(trace)
    db_session.commit()

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        return {"status": "success", "trace_id": trace.id, "chapter_index": 3}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "生成第3章",
            "tools": [{"tool_name": "generate_chapter", "params": {"chapter_index": 3}}],
        },
    )

    decision = response.json()["steps"][0]["output"]["chapter_length_decision"]
    assert response.status_code == 200
    assert decision["status"] == "over"
    assert decision["decision"] == "requires_policy_review"
    assert decision["severity"] == "warning"
    assert decision["repeated_drift_count"] == 3
    assert decision["policy_reason"] == "repeated_over_target"
    assert "revise_or_adjust_project_target" in decision["recommended_actions"]


def test_agent_preflight_warns_when_repeated_over_target_drift_requires_review(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2, 3, 4], generated_chapters=[1, 2, 3])
    for chapter in db_session.query(ChapterContent).filter(ChapterContent.project_id == project.id):
        chapter.word_count = 3300
    db_session.commit()
    import_setup_to_world_model(db_session, project.id)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第4章是否可写",
            "tools": [{"tool_name": "preflight_writing", "params": {"chapter_index": 4}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "ready"
    assert output["checks"]["length_policy"]["status"] == "review_required"
    assert output["checks"]["length_policy"]["reason"] == "repeated_over_target"
    assert output["issues"][0]["code"] == "repeated_chapter_length_drift"
    assert output["issues"][0]["severity"] == "warning"


def test_agent_preflight_keeps_historical_length_debt_out_of_recent_drift_warning(client, db_session):
    project = _seed_longform_project(
        db_session,
        outline_chapters=list(range(1, 10)),
        generated_chapters=list(range(1, 9)),
    )
    for chapter in db_session.query(ChapterContent).filter(ChapterContent.project_id == project.id):
        chapter.word_count = 3200 if chapter.chapter_index <= 3 else 2100
    db_session.commit()
    import_setup_to_world_model(db_session, project.id)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第9章是否可写",
            "tools": [{"tool_name": "preflight_writing", "params": {"chapter_index": 9}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    length_policy = output["checks"]["length_policy"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "ready"
    assert length_policy["status"] == "ready"
    assert length_policy["historical_over_target_count"] == 3
    assert length_policy["recent_over_target_count"] == 0
    assert [issue["code"] for issue in output["issues"]] == []


def test_agent_generate_chapter_appends_length_feedback_after_repeated_over_target_drift(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2, 3, 4], generated_chapters=[1, 2, 3])
    for chapter in db_session.query(ChapterContent).filter(ChapterContent.project_id == project.id):
        chapter.word_count = 3300
    db_session.commit()

    captured: dict[str, object] = {}

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        captured["action_type"] = action_type
        captured["command_args"] = command_args
        return {"status": "success", "chapter_index": 4}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "生成第4章",
            "tools": [
                {
                    "tool_name": "generate_chapter",
                    "command_args": "保留悬疑压迫感",
                    "params": {"chapter_index": 4},
                }
            ],
        },
    )

    command_args = str(captured["command_args"])
    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert captured["action_type"] == "generate_chapter"
    assert "保留悬疑压迫感" in command_args
    assert "近期章节连续偏长" in command_args
    assert "2000-3000字" in command_args
    assert "必须控制" not in command_args
    assert output["agent_generation_feedback"]["reason"] == "repeated_over_target"


def test_agent_generate_chapter_appends_memory_activation_without_future_leak(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2, 3], generated_chapters=[1, 2])
    _seed_activation_memories(db_session, project.id)
    db_session.commit()

    captured: dict[str, object] = {}

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        captured["action_type"] = action_type
        captured["command_args"] = command_args
        return {"status": "success", "chapter_index": 3}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "生成第3章",
            "tools": [{"tool_name": "generate_chapter", "params": {"chapter_index": 3}}],
        },
    )

    command_args = str(captured["command_args"])
    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert captured["action_type"] == "generate_chapter"
    assert "Writing Agent 长记忆激活" in command_args
    assert "空白信" in command_args
    assert "雾晶" in command_args
    assert "潮下车站" not in command_args
    assert output["agent_memory_activation"]["status"] in {"ready", "degraded"}
    assert output["agent_memory_activation"]["activated_counts"]["longform"] >= 2
    assert output["agent_memory_activation"]["memory_provenance"]["source_count"] >= 2
    assert "prompt_block" not in output["agent_memory_activation"]


def test_agent_generate_chapter_appends_length_feedback_after_repeated_under_target_drift(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2, 3, 4], generated_chapters=[1, 2, 3])
    for chapter in db_session.query(ChapterContent).filter(ChapterContent.project_id == project.id):
        chapter.word_count = 1200
    db_session.commit()

    captured: dict[str, object] = {}

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        captured["command_args"] = command_args
        return {"status": "success", "chapter_index": 4}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "生成第4章",
            "tools": [{"tool_name": "generate_chapter", "params": {"chapter_index": 4}}],
        },
    )

    command_args = str(captured["command_args"])
    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "近期章节连续偏短" in command_args
    assert "2000-3000字" in command_args
    assert "必须写足" not in command_args
    assert output["agent_generation_feedback"]["reason"] == "repeated_under_target"


def test_agent_generate_chapter_ignores_old_over_target_debt_when_recent_window_is_clean(
    client,
    db_session,
    monkeypatch,
):
    project = _seed_longform_project(
        db_session,
        outline_chapters=list(range(1, 10)),
        generated_chapters=list(range(1, 9)),
    )
    for chapter in db_session.query(ChapterContent).filter(ChapterContent.project_id == project.id):
        chapter.word_count = 3200 if chapter.chapter_index <= 3 else 2100
    db_session.commit()

    captured: dict[str, object] = {}

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        captured["command_args"] = command_args
        return {"status": "success", "chapter_index": 9}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "生成第9章",
            "tools": [{"tool_name": "generate_chapter", "params": {"chapter_index": 9}}],
        },
    )

    command_args = str(captured["command_args"])
    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "近期章节连续偏长" not in command_args
    assert "agent_generation_feedback" not in output


def test_agent_generate_chapter_ignores_old_under_target_debt_when_recent_window_is_clean(
    client,
    db_session,
    monkeypatch,
):
    project = _seed_longform_project(
        db_session,
        outline_chapters=list(range(1, 10)),
        generated_chapters=list(range(1, 9)),
    )
    for chapter in db_session.query(ChapterContent).filter(ChapterContent.project_id == project.id):
        chapter.word_count = 1200 if chapter.chapter_index <= 3 else 2100
    db_session.commit()

    captured: dict[str, object] = {}

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        captured["command_args"] = command_args
        return {"status": "success", "chapter_index": 9}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "生成第9章",
            "tools": [{"tool_name": "generate_chapter", "params": {"chapter_index": 9}}],
        },
    )

    command_args = str(captured["command_args"])
    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "近期章节连续偏短" not in command_args
    assert "agent_generation_feedback" not in output


def test_agent_generate_chapter_appends_previous_state_card(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "空白信的秘密"
    chapter.content = "林深和苏晚晴在灯塔下发现空白信，信纸显出雾晶是钥匙。两人决定前往下城黑市。"
    chapter.word_count = 2000
    db_session.commit()

    captured: dict[str, object] = {}

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        captured["command_args"] = command_args
        return {"status": "success", "chapter_index": 2}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "生成第2章",
            "tools": [
                {
                    "tool_name": "generate_chapter",
                    "command_args": "保持紧张感",
                    "params": {"chapter_index": 2},
                }
            ],
        },
    )

    command_args = str(captured["command_args"])
    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert "保持紧张感" in command_args
    assert "上一章状态卡" in command_args
    assert "空白信的秘密" in command_args
    assert "雾晶是钥匙" in command_args
    assert "下城" in command_args
    assert output["agent_continuity_feedback"]["card"]["title"] == "空白信的秘密"


def test_agent_review_chapter_quality_flags_generic_title_and_length(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    chapter.title = "第2章"
    chapter.word_count = 3400
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "审稿第2章",
            "tools": [{"tool_name": "review_chapter_quality", "params": {"chapter_index": 2}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "blocked"
    assert {finding["code"] for finding in output["findings"]} >= {"generic_chapter_title", "chapter_over_target"}
    assert "revise_chapter" in output["recommended_actions"]


def test_agent_review_chapter_quality_accepts_elastic_2000_plus_length(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "雾中回声"
    chapter.word_count = 2482
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "审稿第1章",
            "tools": [{"tool_name": "review_chapter_quality", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    codes = {finding["code"] for finding in output["findings"]}
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "chapter_over_target" not in codes


def test_agent_review_chapter_quality_accepts_slight_soft_over_target(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "雾中回声"
    chapter.word_count = 3159
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "审稿第1章",
            "tools": [{"tool_name": "review_chapter_quality", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    codes = {finding["code"] for finding in output["findings"]}
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "chapter_over_target" not in codes


def test_agent_review_chapter_quality_warns_on_soft_over_target_without_blocking(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "雾中回声"
    chapter.word_count = 3846
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "审稿第1章",
            "tools": [{"tool_name": "review_chapter_quality", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    finding = next(item for item in output["findings"] if item["code"] == "chapter_over_target")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "warning"
    assert output["blocker_count"] == 0
    assert finding["severity"] == "warning"
    assert "revise_chapter" not in output["recommended_actions"]


def test_agent_review_chapter_quality_blocks_premature_n07_identity_reveal(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[19], generated_chapters=[19])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=19).one()
    chapter.title = "暗网迷途"
    chapter.word_count = 2084
    chapter.content = (
        "苏晚晴醒来后声音颤抖。"
        "“N-07。”她说，“我看到了N-07……那是我。”"
        "她又说自己是从第三研究所逃出来的，十年前那场雾灾是他们制造的。"
        "林深立刻确认苏晚晴是实验体。"
    )
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "审稿第19章",
            "tools": [{"tool_name": "review_chapter_quality", "params": {"chapter_index": 19}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    finding = next(item for item in output["findings"] if item["code"] == "premature_mystery_reveal")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "blocked"
    assert finding["severity"] == "blocker"
    assert "revise_chapter" in output["recommended_actions"]


def test_agent_review_chapter_quality_warns_on_revelation_strength_overreach(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[26], generated_chapters=[26])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=26).one()
    chapter.title = "深处的回响"
    chapter.word_count = 2400
    chapter.content = (
        "旧录像里，十年前的实验室灯光一盏盏亮起，林深看见父亲把一个孩子推进舱室。"
        "屏幕右下角跳出雾灾当夜的时间戳。"
        "林深忽然明白，雾灾不是天灾，是人祸。"
        "更可怕的是，他自己，是那个打开潘多拉魔盒的人。"
    )
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "审稿第26章",
            "tools": [{"tool_name": "review_chapter_quality", "params": {"chapter_index": 26}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    finding = next(item for item in output["findings"] if item["code"] == "revelation_strength_overreach")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "warning"
    assert output["blocker_count"] == 0
    assert finding["severity"] == "warning"
    assert "不是天灾，是人祸" in finding["evidence"]["matched_terms"]


def test_agent_review_chapter_quality_allows_hypothesis_framed_revelation(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[26], generated_chapters=[26])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=26).one()
    chapter.title = "深处的回响"
    chapter.word_count = 2400
    chapter.content = (
        "旧录像只留下断续片段，时间戳指向雾灾当夜。"
        "林深不敢立刻下结论，只能把它记为一种可能：雾灾也许不是天灾，而是人为实验失控。"
        "至于那个孩子是否与他有关，还需要等存储器解析后再确认。"
    )
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "审稿第26章",
            "tools": [{"tool_name": "review_chapter_quality", "params": {"chapter_index": 26}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    codes = {item["code"] for item in output["findings"]}
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "revelation_strength_overreach" not in codes


def test_agent_review_chapter_quality_warns_on_duplicate_specific_title(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    first = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    second = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    first.title = "废弃实验室"
    second.title = "废弃实验室"
    second.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "审稿第2章",
            "tools": [{"tool_name": "review_chapter_quality", "params": {"chapter_index": 2}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    finding = next(item for item in output["findings"] if item["code"] == "duplicate_chapter_title")
    assert response.status_code == 200
    assert output["status"] == "warning"
    assert finding["severity"] == "warning"
    assert finding["evidence"]["matched_chapter_indexes"] == [1]


def test_agent_review_chapter_quality_flags_known_typo_pattern(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "门后回声"
    chapter.content = "林深看见一个四十多岁的女人，戴着眼睛，头发扎成发髻。"
    chapter.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "审稿第1章",
            "tools": [{"tool_name": "review_chapter_quality", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    finding = next(item for item in output["findings"] if item["code"] == "known_typo_pattern")
    assert response.status_code == 200
    assert output["status"] == "warning"
    assert finding["severity"] == "warning"
    assert finding["evidence"]["matched_text"] == "戴着眼睛"
    assert finding["evidence"]["suggestion"] == "戴着眼镜"


def test_agent_review_chapter_quality_flags_future_outline_overlap(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2, 3, 4], generated_chapters=[1, 2, 3])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=3).one()
    chapter.title = "雾中童谣"
    chapter.content = "顾衍出现在地下实验室，警告他们不要靠近黑市雾晶。"
    chapter.word_count = 2000
    outline = db_session.query(Outline).filter_by(project_id=project.id).one()
    chapters = [dict(item) for item in outline.chapters]
    chapters[3]["title"] = "顾衍的警告"
    chapters[3]["summary"] = "顾衍现身并警告主角不要继续调查。"
    outline.chapters = chapters
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "审稿第3章",
            "tools": [{"tool_name": "review_chapter_quality", "params": {"chapter_index": 3}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "blocked"
    assert any(finding["code"] == "future_outline_overlap" for finding in output["findings"])


def test_agent_review_chapter_quality_ignores_single_future_character_name_match(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2, 3, 4], generated_chapters=[1, 2, 3])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=3).one()
    chapter.title = "雾中童谣"
    chapter.content = "林深接到苏晚晴的电话，两人只确认了旧码头的见面时间。"
    chapter.word_count = 2000
    outline = db_session.query(Outline).filter_by(project_id=project.id).one()
    chapters = [dict(item) for item in outline.chapters]
    chapters[3]["title"] = "苏晚晴的梦境"
    chapters[3]["summary"] = "苏晚晴在梦境里看见雾港旧案的另一段证词。"
    outline.chapters = chapters
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "审稿第3章",
            "tools": [{"tool_name": "review_chapter_quality", "params": {"chapter_index": 3}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "ready"
    assert all(finding["code"] != "future_outline_overlap" for finding in output["findings"])


def test_agent_review_chapter_quality_flags_character_profile_drift(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "黑市雾晶"
    chapter.content = "苏晚晴低声说，她以前是雾安局研究员，只是一直隐瞒身份。"
    chapter.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "审稿第1章",
            "tools": [{"tool_name": "review_chapter_quality", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    finding = next(item for item in output["findings"] if item["code"] == "character_profile_drift")
    assert response.status_code == 200
    assert output["status"] == "blocked"
    assert finding["severity"] == "blocker"
    assert finding["evidence"]["character"] == "苏晚晴"
    assert "失踪者家属" in finding["evidence"]["known_profile"]


def test_agent_review_chapter_quality_flags_ability_boundary_drift(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "黑市雾晶"
    chapter.content = "苏晚晴抬手制造幻觉，凭空创造出一段真实记忆骗过守卫。"
    chapter.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "审稿第1章",
            "tools": [{"tool_name": "review_chapter_quality", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    finding = next(item for item in output["findings"] if item["code"] == "ability_boundary_drift")
    assert response.status_code == 200
    assert output["status"] == "blocked"
    assert finding["severity"] == "blocker"
    assert "制造幻觉" in finding["evidence"]["matched_terms"]


def test_agent_review_chapter_quality_warns_on_convenient_key_item_acquisition(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "黑市雾晶"
    chapter.content = "老赵看了林深一眼，立刻把稀有记忆雾晶给了他，让他们马上离开。"
    chapter.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "审稿第1章",
            "tools": [{"tool_name": "review_chapter_quality", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    finding = next(item for item in output["findings"] if item["code"] == "convenient_key_item_acquisition")
    assert response.status_code == 200
    assert output["status"] == "warning"
    assert finding["severity"] == "warning"
    assert "记忆雾晶" in finding["evidence"]["matched_terms"]


def test_agent_review_chapter_quality_flags_unclosed_quote_tail(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "信任裂缝"
    chapter.content = "林深走进雾中，听见父亲的声音响起——“林深，好久不见。"
    chapter.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "审稿第1章",
            "tools": [{"tool_name": "review_chapter_quality", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    finding = next(item for item in output["findings"] if item["code"] == "unclosed_dialogue_quote")
    assert response.status_code == 200
    assert output["status"] == "blocked"
    assert finding["severity"] == "blocker"


def test_agent_review_chapter_continuity_flags_event_date_conflict(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    first = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    second = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    first.content = "信封上的邮戳日期是2045年8月9日——雾灾发生前三天。"
    first.word_count = 2000
    second.content = "林深看了看信封上的邮戳——2045年7月12日。那是雾灾发生的前三天。"
    second.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第2章连续性锚点",
            "tools": [{"tool_name": "review_chapter_continuity", "params": {"chapter_index": 2}}],
        },
    )

    payload = response.json()
    step = payload["steps"][0]
    output = step["output"]
    finding = output["findings"][0]
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert step["status"] == "success"
    assert step["target_type"] == "review"
    assert output["status"] == "blocked"
    assert finding["code"] == "timeline_anchor_conflict"
    assert finding["severity"] == "blocker"
    assert finding["evidence"]["event_key"] == "fog_disaster_minus_3_days"
    assert finding["evidence"]["values"] == ["2045年8月9日", "2045年7月12日"]


def test_agent_review_chapter_continuity_flags_identifier_kind_conflict(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    first = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    second = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    first.content = "顾衍把军牌扔在桌上，上面刻着编号：N-017。"
    first.word_count = 2000
    second.content = "顾衍掏出军牌，翻到背面。上面刻着一串编号——N-07。"
    second.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第2章编号锚点",
            "tools": [{"tool_name": "review_chapter_continuity", "params": {"chapter_index": 2}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    finding = output["findings"][0]
    assert output["status"] == "blocked"
    assert finding["code"] == "identifier_anchor_conflict"
    assert finding["evidence"]["anchor_key"] == "顾衍:military_tag_number"
    assert finding["evidence"]["values"] == ["N-017", "N-07"]


def test_agent_review_chapter_continuity_warns_on_adjacent_transition_gap(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    first = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    second = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    first.content = "夜里，林深和苏晚晴躲进暗渠尽头的地下临时藏身点，决定暂时不再移动。"
    first.word_count = 2000
    second.content = "清晨，赵猛的安全屋里弥漫着铁锈味，陈默开始破解终端里的旧档案。"
    second.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第2章相邻跳切",
            "tools": [{"tool_name": "review_chapter_continuity", "params": {"chapter_index": 2}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    finding = next(item for item in output["findings"] if item["code"] == "adjacent_chapter_transition_gap")
    assert response.status_code == 200
    assert output["status"] == "warning"
    assert finding["severity"] == "warning"
    assert finding["evidence"]["previous_chapter_index"] == 1
    assert finding["evidence"]["current_chapter_index"] == 2
    assert "地下临时藏身点" in finding["evidence"]["previous_excerpt"]
    assert "赵猛的安全屋" in finding["evidence"]["current_excerpt"]


def test_agent_review_chapter_continuity_allows_explicit_adjacent_transition(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    first = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    second = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    first.content = "夜里，林深和苏晚晴躲进暗渠尽头的地下临时藏身点，决定暂时不再移动。"
    first.word_count = 2000
    second.content = "几小时后，赵猛带他们穿过排水管转移到安全屋，清晨的铁锈味从墙缝里渗出来。"
    second.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第2章相邻跳切",
            "tools": [{"tool_name": "review_chapter_continuity", "params": {"chapter_index": 2}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    codes = {finding["code"] for finding in output["findings"]}
    assert response.status_code == 200
    assert "adjacent_chapter_transition_gap" not in codes


def test_agent_review_chapter_continuity_warns_on_identifier_semantic_drift(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    first = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    second = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    first.content = "林深打开证物柜，柜号是G-07，里面只剩半张照片。"
    first.word_count = 2000
    second.content = "陈默推断G-07可能不是柜号，而是G项目的第七号实验项目。"
    second.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第2章编号语义",
            "tools": [{"tool_name": "review_chapter_continuity", "params": {"chapter_index": 2}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    finding = next(item for item in output["findings"] if item["code"] == "identifier_semantic_drift")
    assert response.status_code == 200
    assert output["status"] == "warning"
    assert finding["severity"] == "warning"
    assert finding["evidence"]["identifier"] == "G-07"
    assert finding["evidence"]["previous_semantic_kind"] == "evidence_locker"
    assert finding["evidence"]["current_semantic_kind"] == "project_number"
    assert finding["evidence"]["current_is_hypothesis"] is True


def test_agent_review_chapter_continuity_allows_experiment_code_distinction(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    first = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    second = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    first.content = "顾衍把军牌扔在桌上，上面刻着编号：N-017。"
    first.word_count = 2000
    second.content = "顾衍掏出军牌，正面的编号仍是N-017；背面浮出暗纹——N-07。那不是军牌编号，更像实验代号。"
    second.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第2章编号锚点",
            "tools": [{"tool_name": "review_chapter_continuity", "params": {"chapter_index": 2}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert output["status"] == "ready"
    assert output["finding_count"] == 0


def test_agent_review_chapter_continuity_flags_relationship_name_conflict(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    first = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    second = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    first.content = "名单第一是林建国——他父亲的名字。"
    first.word_count = 2000
    second.content = "空白信背面浮出署名——林远山。林深认出那是父亲留下的字迹。"
    second.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第2章关系姓名锚点",
            "tools": [{"tool_name": "review_chapter_continuity", "params": {"chapter_index": 2}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    finding = output["findings"][0]
    assert response.status_code == 200
    assert output["status"] == "blocked"
    assert finding["code"] == "relationship_name_anchor_conflict"
    assert finding["evidence"]["anchor_key"] == "林深:father_name"
    assert finding["evidence"]["values"] == ["林建国", "林远山"]


def test_agent_review_chapter_continuity_blocks_against_confirmed_father_truth(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    import_setup_to_world_model(db_session, project.id)
    _seed_confirmed_world_fact(
        db_session,
        project_id=project.id,
        claim_id="claim.continuity.father-name",
        subject_ref="林深",
        predicate="father_name",
        object_ref_or_value="林建国",
        chapter_index=1,
    )
    second = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    second.content = "空白信背面浮出署名——林远山。林深认出那是父亲留下的字迹。"
    second.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第2章稳定父亲姓名锚点",
            "tools": [{"tool_name": "review_chapter_continuity", "params": {"chapter_index": 2}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    finding = next(item for item in output["findings"] if item["code"] == "stable_truth_anchor_conflict")
    assert response.status_code == 200
    assert output["status"] == "blocked"
    assert finding["severity"] == "blocker"
    assert finding["evidence"]["anchor_key"] == "林深:father_name"
    assert finding["evidence"]["truth_value"] == "林建国"
    assert finding["evidence"]["observed_values"] == ["林远山"]


def test_agent_review_chapter_continuity_blocks_against_confirmed_military_tag_truth(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    import_setup_to_world_model(db_session, project.id)
    _seed_confirmed_world_fact(
        db_session,
        project_id=project.id,
        claim_id="claim.continuity.guyan.military-tag",
        subject_ref="顾衍",
        predicate="military_tag_number",
        object_ref_or_value="N-017",
        chapter_index=1,
    )
    second = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    second.content = "顾衍掏出军牌，翻到背面。上面刻着一串编号——N-07。"
    second.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第2章稳定军牌锚点",
            "tools": [{"tool_name": "review_chapter_continuity", "params": {"chapter_index": 2}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    finding = next(item for item in output["findings"] if item["code"] == "stable_truth_anchor_conflict")
    assert response.status_code == 200
    assert output["status"] == "blocked"
    assert finding["evidence"]["anchor_key"] == "顾衍:military_tag_number"
    assert finding["evidence"]["truth_value"] == "N-017"
    assert finding["evidence"]["observed_values"] == ["N-07"]


def test_agent_review_chapter_continuity_blocks_against_confirmed_relative_event_date_truth(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    import_setup_to_world_model(db_session, project.id)
    _seed_confirmed_world_fact(
        db_session,
        project_id=project.id,
        claim_id="claim.continuity.fog-disaster-minus-3-days",
        subject_ref="event.fog_disaster.minus_3_days",
        predicate="relative_event_date",
        object_ref_or_value="2045年8月9日",
        chapter_index=1,
    )
    second = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    second.content = "信封上的邮戳日期是2045年8月12日——雾灾发生前三天。"
    second.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第2章稳定雾灾日期锚点",
            "tools": [{"tool_name": "review_chapter_continuity", "params": {"chapter_index": 2}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    finding = next(item for item in output["findings"] if item["code"] == "stable_truth_anchor_conflict")
    assert response.status_code == 200
    assert output["status"] == "blocked"
    assert finding["evidence"]["anchor_key"] == "fog_disaster_minus_3_days"
    assert finding["evidence"]["truth_value"] == "2045年8月9日"
    assert finding["evidence"]["observed_values"] == ["2045年8月12日"]


def test_agent_seed_continuity_anchor_proposals_creates_missing_anchor_items(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "补齐稳定连续性锚点提案",
            "tools": [{"tool_name": "seed_continuity_anchor_proposals"}],
        },
    )

    output = response.json()["steps"][0]["output"]
    stored_items = db_session.query(WorldProposalItem).filter_by(project_id=project.id).all()
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "blocked"
    assert output["created_item_count"] >= 5
    assert output["should_generate_next_chapter"] is False
    recommendations = output["agent_tool_result"]["recommendations"]
    assert recommendations["source_fields"] == ["recommended_actions"]
    assert recommendations["runtime_followups"] == ["apply_world_model_proposal_resolution"]
    assert recommendations["policy_followups"] == ["apply_world_model_proposal_resolution"]
    assert recommendations["canonical_followups"] == ["apply_world_model_proposal_resolution"]
    assert {(item.subject_ref, item.predicate) for item in stored_items} >= {
        ("林深", "father_name"),
        ("顾衍", "military_tag_number"),
        ("identifier.N-07", "identifier_meaning"),
        ("event.fog_disaster", "event_date"),
        ("event.fog_disaster.minus_3_days", "relative_event_date"),
    }


def test_agent_apply_world_model_proposal_resolution_allows_confirmed_continuity_anchor_approval(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={"goal": "seed", "tools": [{"tool_name": "seed_continuity_anchor_proposals"}]},
    )
    item = (
        db_session.query(WorldProposalItem)
        .filter_by(project_id=project.id, subject_ref="林深", predicate="father_name")
        .one()
    )

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "审批稳定锚点",
            "tools": [
                {
                    "tool_name": "apply_world_model_proposal_resolution",
                    "params": {
                        "confirm_apply": True,
                        "decisions": [
                            {
                                "proposal_item_id": item.id,
                                "action": "approve",
                                "reason": "确认父亲姓名锚点",
                                "evidence_refs": ["chapter:10", "chapter:11", "chapter:13"],
                            }
                        ],
                    },
                }
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    db_session.expire_all()
    stored_item = db_session.query(WorldProposalItem).filter_by(id=item.id).one()
    stored_claim = db_session.query(WorldFactClaim).filter_by(project_id=project.id, predicate="father_name").one()
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["applied_count"] == 1
    assert output["after_actionable_items"] == 4
    assert output["should_generate_next_chapter"] is False
    assert stored_item.item_status == "approved"
    assert stored_item.approved_claim_id == stored_claim.claim_id
    assert stored_claim.subject_ref == "林深"
    assert stored_claim.object_ref_or_value == "林建国"


def test_agent_plan_chapter_revision_maps_review_findings_to_actions(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    chapter.title = "第2章"
    chapter.word_count = 3400
    original_content = chapter.content
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "规划第2章修订",
            "tools": [{"tool_name": "plan_chapter_revision", "params": {"chapter_index": 2}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    chapter_after_plan = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "blocked"
    assert output["should_generate_next_chapter"] is False
    assert {action["action"] for action in output["revision_actions"]} >= {
        "retitle_chapter",
        "compress_chapter",
    }
    assert "revise_chapter" in output["recommended_next_tools"]
    assert chapter_after_plan.content == original_content
    assert chapter_after_plan.title == "第2章"


def test_agent_plan_chapter_revision_maps_drift_findings_to_actions(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "黑市雾晶"
    chapter.content = "苏晚晴低声说，她以前是雾安局研究员。随后她制造幻觉骗过守卫。"
    chapter.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "规划第1章漂移修订",
            "tools": [{"tool_name": "plan_chapter_revision", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    actions = {action["action"]: action for action in output["revision_actions"]}
    assert response.status_code == 200
    assert output["status"] == "blocked"
    assert "fix_character_profile_drift" in actions
    assert "respect_ability_boundary" in actions
    assert actions["fix_character_profile_drift"]["source_finding"] == "character_profile_drift"
    assert actions["respect_ability_boundary"]["source_finding"] == "ability_boundary_drift"
    assert actions["fix_character_profile_drift"]["evidence"]["character"] == "苏晚晴"
    assert "制造幻觉" in actions["respect_ability_boundary"]["evidence"]["matched_terms"]


def test_agent_plan_chapter_revision_records_revision_plan_target_type(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "规划第1章修订",
            "tools": [{"tool_name": "plan_chapter_revision", "params": {"chapter_index": 1}}],
        },
    )

    step = response.json()["steps"][0]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert step["target_type"] == "revision_plan"
    assert step["output"]["status"] == "ready"
    assert step["output"]["should_generate_next_chapter"] is True


def test_agent_plan_chapter_revision_blocks_followup_generation_when_plan_is_blocked(
    client,
    db_session,
    monkeypatch,
):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2, 3], generated_chapters=[1, 2])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    chapter.title = "第2章"
    chapter.word_count = 3200
    db_session.commit()
    calls = []

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append(action_type)
        return {"status": "success", "chapter_index": 3}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "先规划第2章修订，再尝试生成第3章",
            "tools": [
                {"tool_name": "plan_chapter_revision", "params": {"chapter_index": 2}},
                {"tool_name": "generate_chapter", "params": {"chapter_index": 3}},
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert payload["steps"][0]["tool_name"] == "plan_chapter_revision"
    assert payload["steps"][0]["status"] == "success"
    assert payload["steps"][0]["output"]["should_generate_next_chapter"] is False
    assert len(payload["steps"]) == 1
    assert calls == []


def test_agent_plan_chapter_revision_reports_world_model_pressure_without_reviewing_items(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.word_count = 2000
    import_setup_to_world_model(db_session, project.id)
    profile = db_session.query(ProjectProfileVersion).filter_by(project_id=project.id).one()
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile.id,
        profile_version=profile.version,
        created_by="athena.test",
        title="待审事实",
    )
    item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="athena.test",
        candidate=ProposalCandidateFactCreate(
            project_id=project.id,
            project_profile_version_id=profile.id,
            profile_version=profile.version,
            claim_id="claim.phase8.agent.role",
            chapter_index=1,
            subject_ref="char.林深",
            predicate="role",
            object_ref_or_value="雾港调查者",
            claim_layer="truth",
            evidence_refs=["chapter:1"],
            authority_type=DERIVED,
            confidence=0.9,
            contract_version=profile.contract_version,
        ),
    )
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "规划第1章修订并检查世界模型压力",
            "tools": [{"tool_name": "plan_chapter_revision", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    stored_item = db_session.query(WorldProposalItem).filter_by(id=item.id).one()
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "warning"
    assert output["world_model_proposal_pressure"]["total_items"] == 1
    assert "review_world_model_proposals" in output["recommended_next_tools"]
    assert stored_item.item_status == "pending"


def test_agent_review_world_model_proposals_reports_queue_without_reviewing_items(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase10.agent.role",
        predicate="role",
        subject_ref="char.林深",
    )
    before_review_count = db_session.query(WorldProposalReview).count()
    before_fact_count = db_session.query(WorldFactClaim).count()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "汇总世界模型待审提案队列",
            "tools": [{"tool_name": "review_world_model_proposals", "params": {"limit": 20}}],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    stored_item = db_session.query(WorldProposalItem).filter_by(id=item.id).one()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["steps"][0]["target_type"] == "world_model"
    assert output["status"] == "blocked"
    assert output["report_only"] is True
    assert output["total_items"] == 1
    assert output["returned_items"] == 1
    assert output["risk_counts"]["high"] == 1
    assert output["review_mode_counts"]["individual"] == 1
    assert output["clusters"][0]["item_ids"] == [item.id]
    assert output["should_generate_next_chapter"] is False
    assert stored_item.item_status == "pending"
    assert db_session.query(WorldProposalReview).count() == before_review_count
    assert db_session.query(WorldFactClaim).count() == before_fact_count


def test_agent_review_world_model_proposals_ready_when_queue_empty(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "确认世界模型待审提案队列为空",
            "tools": [{"tool_name": "review_world_model_proposals"}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "ready"
    assert output["total_items"] == 0
    assert output["risk_counts"] == {"high": 0, "medium": 0, "low": 0}
    assert output["review_mode_counts"] == {"individual": 0, "batch": 0}
    assert output["recommended_actions"] == ["preflight_writing"]
    assert output["should_generate_next_chapter"] is True


def test_agent_review_world_model_proposals_blocks_followup_generation(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase10.agent.status",
        predicate="status",
        subject_ref="char.苏晚晴",
    )
    calls = []

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append(action_type)
        return {"status": "success", "chapter_index": 2}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查提案队列后尝试生成第2章",
            "tools": [
                {"tool_name": "review_world_model_proposals", "params": {"limit": 20}},
                {"tool_name": "generate_chapter", "params": {"chapter_index": 2}},
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert payload["steps"][0]["tool_name"] == "review_world_model_proposals"
    assert payload["steps"][0]["status"] == "success"
    assert payload["steps"][0]["output"]["should_generate_next_chapter"] is False
    assert len(payload["steps"]) == 1
    assert calls == []


def test_agent_plan_world_model_proposal_resolution_orders_review_steps_without_writes(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    high_item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase11.agent.status",
        predicate="status",
        subject_ref="char.林深",
    )
    low_item_one = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase11.agent.mentioned-one",
        predicate="mentioned_in_chapter",
        subject_ref="char.林深",
    )
    low_item_two = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase11.agent.mentioned-two",
        predicate="mentioned_in_chapter",
        subject_ref="char.苏晚晴",
    )
    before_review_count = db_session.query(WorldProposalReview).count()
    before_fact_count = db_session.query(WorldFactClaim).count()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "规划世界模型待审提案解决顺序",
            "tools": [{"tool_name": "plan_world_model_proposal_resolution", "params": {"limit": 20}}],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    steps = output["resolution_steps"]
    stored_high_item = db_session.query(WorldProposalItem).filter_by(id=high_item.id).one()
    stored_low_item_one = db_session.query(WorldProposalItem).filter_by(id=low_item_one.id).one()
    stored_low_item_two = db_session.query(WorldProposalItem).filter_by(id=low_item_two.id).one()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["steps"][0]["target_type"] == "world_model"
    assert output["status"] == "blocked"
    assert output["report_only"] is True
    assert output["plan_only"] is True
    assert output["total_items"] == 3
    assert output["high_priority_step_count"] == 1
    assert output["batch_step_count"] == 1
    assert output["requires_human_confirmation"] is True
    assert output["can_auto_apply"] is False
    assert output["should_generate_next_chapter"] is False
    assert steps[0]["action_type"] == "review_individual"
    assert steps[0]["risk_level"] == "high"
    assert steps[0]["item_ids"] == [high_item.id]
    assert steps[1]["action_type"] == "review_batch"
    assert steps[1]["risk_level"] == "low"
    assert set(steps[1]["item_ids"]) == {low_item_one.id, low_item_two.id}
    assert steps[1]["candidate_count"] == 2
    assert stored_high_item.item_status == "pending"
    assert stored_low_item_one.item_status == "pending"
    assert stored_low_item_two.item_status == "pending"
    assert db_session.query(WorldProposalReview).count() == before_review_count
    assert db_session.query(WorldFactClaim).count() == before_fact_count


def test_agent_plan_world_model_proposal_resolution_ready_when_queue_empty(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "确认无需解决世界模型提案",
            "tools": [{"tool_name": "plan_world_model_proposal_resolution"}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "ready"
    assert output["resolution_steps"] == []
    assert output["high_priority_step_count"] == 0
    assert output["batch_step_count"] == 0
    assert output["requires_human_confirmation"] is False
    assert output["can_auto_apply"] is False
    assert output["recommended_actions"] == ["preflight_writing"]
    assert output["should_generate_next_chapter"] is True


def test_agent_plan_world_model_proposal_resolution_keeps_full_batch_item_ids(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    seeded_item_ids = []
    for index in range(12):
        item = _seed_pending_world_proposal(
            db_session,
            project_id=project.id,
            claim_id=f"claim.phase11.agent.batch-full-{index}",
            predicate="mentioned_in_chapter",
            subject_ref=f"char.batch-{index}",
        )
        seeded_item_ids.append(item.id)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "规划低风险批量提案",
            "tools": [{"tool_name": "plan_world_model_proposal_resolution", "params": {"limit": 20}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    batch_step = output["resolution_steps"][0]
    assert response.status_code == 200
    assert batch_step["action_type"] == "review_batch"
    assert batch_step["candidate_count"] == 12
    assert set(batch_step["item_ids"]) == set(seeded_item_ids)


def test_agent_plan_world_model_proposal_resolution_counts_medium_separately_from_high(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase11.agent.high-count",
        predicate="status",
        subject_ref="char.林深",
    )
    _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase11.agent.medium-count",
        predicate="symbolic_hint",
        subject_ref="char.苏晚晴",
    )

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "区分高风险和中风险提案规划",
            "tools": [{"tool_name": "plan_world_model_proposal_resolution", "params": {"limit": 20}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert output["high_priority_step_count"] == 1
    assert [step["risk_level"] for step in output["resolution_steps"]] == ["high", "medium"]


def test_agent_review_world_model_proposals_allows_resolution_plan_followup(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase11.agent.chain",
        predicate="role",
        subject_ref="char.林深",
    )

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "先看队列再规划解决顺序",
            "tools": [
                {"tool_name": "review_world_model_proposals", "params": {"limit": 20}},
                {"tool_name": "plan_world_model_proposal_resolution", "params": {"limit": 20}},
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert [step["tool_name"] for step in payload["steps"]] == [
        "review_world_model_proposals",
        "plan_world_model_proposal_resolution",
    ]
    assert payload["steps"][0]["output"]["should_generate_next_chapter"] is False
    assert payload["steps"][1]["output"]["should_generate_next_chapter"] is False
    assert payload["steps"][1]["output"]["resolution_steps"][0]["action_type"] == "review_individual"


def test_agent_plan_world_model_proposal_resolution_blocks_followup_generation(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase11.agent.blocks-generation",
        predicate="status",
        subject_ref="char.苏晚晴",
    )
    calls = []

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append(action_type)
        return {"status": "success", "chapter_index": 2}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "规划提案解决后尝试生成第2章",
            "tools": [
                {"tool_name": "plan_world_model_proposal_resolution", "params": {"limit": 20}},
                {"tool_name": "generate_chapter", "params": {"chapter_index": 2}},
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert payload["steps"][0]["tool_name"] == "plan_world_model_proposal_resolution"
    assert payload["steps"][0]["status"] == "success"
    assert payload["steps"][0]["output"]["should_generate_next_chapter"] is False
    assert len(payload["steps"]) == 1
    assert calls == []


def test_agent_preview_world_model_proposal_resolution_validates_decisions_without_writes(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    approve_item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase12.agent.approve",
        predicate="role",
        subject_ref="char.林深",
    )
    reject_item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase12.agent.reject",
        predicate="mentioned_in_chapter",
        subject_ref="char.苏晚晴",
    )
    before_review_count = db_session.query(WorldProposalReview).count()
    before_fact_count = db_session.query(WorldFactClaim).count()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "预览世界模型提案解决决策",
            "tools": [
                {
                    "tool_name": "preview_world_model_proposal_resolution",
                    "params": {
                        "decisions": [
                            {
                                "proposal_item_id": approve_item.id,
                                "action": "approve",
                                "reason": "确认角色定位",
                                "evidence_refs": ["test:phase12"],
                            },
                            {
                                "proposal_item_id": reject_item.id,
                                "action": "reject",
                                "reason": "仅作预览拒绝",
                                "evidence_refs": "test:phase12:string-ref",
                            },
                        ]
                    },
                }
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    stored_approve_item = db_session.query(WorldProposalItem).filter_by(id=approve_item.id).one()
    stored_reject_item = db_session.query(WorldProposalItem).filter_by(id=reject_item.id).one()
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "blocked"
    assert output["preview_only"] is True
    assert output["requires_confirmation"] is True
    assert output["can_auto_apply"] is False
    assert output["valid_decision_count"] == 2
    assert output["invalid_decision_count"] == 0
    assert output["would_create_review_count"] == 2
    assert output["would_create_fact_count"] == 1
    assert output["would_resolve_item_count"] == 2
    assert output["remaining_actionable_item_count_after_preview"] == 0
    assert output["would_unblock_generation"] is True
    assert output["should_generate_next_chapter"] is False
    reject_preview = next(decision for decision in output["valid_decisions"] if decision["proposal_item_id"] == reject_item.id)
    assert reject_preview["evidence_refs"] == ["test:phase12:string-ref"]
    assert stored_approve_item.item_status == "pending"
    assert stored_reject_item.item_status == "pending"
    assert db_session.query(WorldProposalReview).count() == before_review_count
    assert db_session.query(WorldFactClaim).count() == before_fact_count


def test_agent_preview_world_model_proposal_resolution_reports_missing_profile_for_non_dict_decision(
    client,
    db_session,
):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "缺少世界模型档案时预览异常决策",
            "tools": [
                {
                    "tool_name": "preview_world_model_proposal_resolution",
                    "params": {"decisions": ["not-a-decision"]},
                }
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "missing_profile"
    assert output["valid_decision_count"] == 0
    assert output["invalid_decision_count"] == 1
    assert output["invalid_decisions"][0]["code"] == "missing_profile"
    assert output["should_generate_next_chapter"] is False


def test_agent_preview_world_model_proposal_resolution_reports_invalid_decisions(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    valid_item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase12.agent.valid",
        predicate="role",
        subject_ref="char.林深",
    )
    unsupported_item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase12.agent.unsupported",
        predicate="status",
        subject_ref="char.苏晚晴",
    )

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "预览无效世界模型提案决策",
            "tools": [
                {
                    "tool_name": "preview_world_model_proposal_resolution",
                    "params": {
                        "decisions": [
                            {
                                "proposal_item_id": valid_item.id,
                                "action": "reject",
                                "reason": "有效拒绝预览",
                            },
                            {
                                "proposal_item_id": valid_item.id,
                                "action": "reject",
                                "reason": "重复决策",
                            },
                            {
                                "proposal_item_id": "proposal-item.missing.phase12",
                                "action": "approve",
                                "reason": "不存在",
                            },
                            {
                                "proposal_item_id": unsupported_item.id,
                                "action": "split",
                                "reason": "不支持的动作",
                            },
                        ]
                    },
                }
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    invalid_codes = {item["code"] for item in output["invalid_decisions"]}
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "blocked"
    assert output["valid_decision_count"] == 1
    assert output["invalid_decision_count"] == 3
    assert invalid_codes == {"duplicate_decision", "missing_item", "unsupported_action"}
    assert output["remaining_actionable_item_count_after_preview"] == 1
    assert output["would_unblock_generation"] is False
    assert output["should_generate_next_chapter"] is False


def test_agent_preview_world_model_proposal_resolution_reports_non_actionable_items(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase12.agent.non-actionable",
        predicate="role",
        subject_ref="char.林深",
    )
    item.item_status = "approved"
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "预览非待审世界模型提案决策",
            "tools": [
                {
                    "tool_name": "preview_world_model_proposal_resolution",
                    "params": {
                        "decisions": [
                            {
                                "proposal_item_id": item.id,
                                "action": "reject",
                                "reason": "已经不是待审项",
                            }
                        ]
                    },
                }
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "blocked"
    assert output["valid_decision_count"] == 0
    assert output["invalid_decision_count"] == 1
    assert output["invalid_decisions"][0]["code"] == "non_actionable_item"
    assert output["should_generate_next_chapter"] is False


def test_agent_preview_world_model_proposal_resolution_blocks_generation_for_empty_queue_decisions(
    client,
    db_session,
):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "空队列下预览无效决策",
            "tools": [
                {
                    "tool_name": "preview_world_model_proposal_resolution",
                    "params": {
                        "decisions": [
                            {
                                "proposal_item_id": "proposal-item.missing.empty-queue",
                                "action": "reject",
                                "reason": "不存在",
                            }
                        ]
                    },
                }
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "blocked"
    assert output["invalid_decision_count"] == 1
    assert output["should_generate_next_chapter"] is False


def test_agent_preview_world_model_proposal_resolution_rejects_non_atomized_world_intake_approve(
    client,
    db_session,
):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    intake_item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase12.agent.world-intake",
        predicate="user_proposed_update",
        subject_ref="project.world_intake",
    )

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "预览未原子化世界入口提案",
            "tools": [
                {
                    "tool_name": "preview_world_model_proposal_resolution",
                    "params": {
                        "decisions": [
                            {
                                "proposal_item_id": intake_item.id,
                                "action": "approve",
                                "reason": "直接审批入口提案",
                            }
                        ]
                    },
                }
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["valid_decision_count"] == 0
    assert output["invalid_decision_count"] == 1
    assert output["invalid_decisions"][0]["code"] == "world_intake_not_atomized"
    assert output["should_generate_next_chapter"] is False


def test_agent_plan_world_model_proposal_resolution_allows_preview_followup(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase12.agent.plan-preview",
        predicate="role",
        subject_ref="char.林深",
    )

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "先规划再预览世界模型提案决策",
            "tools": [
                {"tool_name": "plan_world_model_proposal_resolution", "params": {"limit": 20}},
                {
                    "tool_name": "preview_world_model_proposal_resolution",
                    "params": {
                        "decisions": [
                            {
                                "proposal_item_id": item.id,
                                "action": "reject",
                                "reason": "预览拒绝",
                            }
                        ]
                    },
                },
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert [step["tool_name"] for step in payload["steps"]] == [
        "plan_world_model_proposal_resolution",
        "preview_world_model_proposal_resolution",
    ]
    assert payload["steps"][1]["output"]["valid_decision_count"] == 1


def test_agent_preview_world_model_proposal_resolution_blocks_followup_generation(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase12.agent.blocks-generation",
        predicate="status",
        subject_ref="char.苏晚晴",
    )
    calls = []

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append(action_type)
        return {"status": "success", "chapter_index": 2}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "预览提案决策后尝试生成第2章",
            "tools": [
                {
                    "tool_name": "preview_world_model_proposal_resolution",
                    "params": {
                        "decisions": [
                            {
                                "proposal_item_id": item.id,
                                "action": "reject",
                                "reason": "预览拒绝",
                            }
                        ]
                    },
                },
                {"tool_name": "generate_chapter", "params": {"chapter_index": 2}},
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert payload["steps"][0]["tool_name"] == "preview_world_model_proposal_resolution"
    assert payload["steps"][0]["status"] == "success"
    assert payload["steps"][0]["output"]["should_generate_next_chapter"] is False
    assert len(payload["steps"]) == 1
    assert calls == []


def test_agent_apply_world_model_proposal_resolution_requires_confirmation_without_writes(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase13.agent.needs-confirm",
        predicate="role",
        subject_ref="char.林深",
    )
    before_review_count = db_session.query(WorldProposalReview).count()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "尝试未确认地应用世界模型提案决策",
            "tools": [
                {
                    "tool_name": "apply_world_model_proposal_resolution",
                    "params": {
                        "decisions": [
                            {
                                "proposal_item_id": item.id,
                                "action": "reject",
                                "reason": "未确认，不应落库",
                            }
                        ]
                    },
                }
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    stored_item = db_session.query(WorldProposalItem).filter_by(id=item.id).one()
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "blocked"
    assert output["requires_confirmation"] is True
    assert output["applied_count"] == 0
    assert output["invalid_decision_count"] == 0
    assert output["should_generate_next_chapter"] is False
    assert stored_item.item_status == "pending"
    assert db_session.query(WorldProposalReview).count() == before_review_count


def test_agent_apply_world_model_proposal_resolution_blocks_missing_profile_without_decisions(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "缺少世界模型档案时不能应用空决策",
            "tools": [
                {
                    "tool_name": "apply_world_model_proposal_resolution",
                    "params": {"confirm_apply": True, "decisions": []},
                }
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "missing_profile"
    assert output["profile_version"] is None
    assert output["applied_count"] == 0
    assert output["should_generate_next_chapter"] is False
    assert output["recommended_actions"] == ["import_setup_world_model"]


def test_agent_apply_world_model_proposal_resolution_applies_confirmed_non_merge_decisions(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    reject_item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase13.agent.reject",
        predicate="role",
        subject_ref="char.林深",
    )
    uncertain_item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase13.agent.uncertain",
        predicate="status",
        subject_ref="char.苏晚晴",
    )
    before_fact_count = db_session.query(WorldFactClaim).count()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "确认应用世界模型非合并提案决策",
            "tools": [
                {
                    "tool_name": "apply_world_model_proposal_resolution",
                    "params": {
                        "confirm_apply": True,
                        "decisions": [
                            {
                                "proposal_item_id": reject_item.id,
                                "action": "reject",
                                "reason": "拒绝错误角色事实",
                                "evidence_refs": ["test:phase13"],
                            },
                            {
                                "proposal_item_id": uncertain_item.id,
                                "action": "mark_uncertain",
                                "reason": "状态暂不确定",
                                "evidence_refs": "test:phase13:string-ref",
                            },
                        ],
                    },
                }
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    db_session.expire_all()
    stored_reject_item = db_session.query(WorldProposalItem).filter_by(id=reject_item.id).one()
    stored_uncertain_item = db_session.query(WorldProposalItem).filter_by(id=uncertain_item.id).one()
    reviews = (
        db_session.query(WorldProposalReview)
        .filter(WorldProposalReview.proposal_item_id.in_([reject_item.id, uncertain_item.id]))
        .all()
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "ready"
    assert output["applied_count"] == 2
    assert output["before_actionable_items"] == 2
    assert output["after_actionable_items"] == 0
    assert output["should_generate_next_chapter"] is True
    assert db_session.query(WorldFactClaim).count() == before_fact_count
    assert stored_reject_item.item_status == "rejected"
    assert stored_uncertain_item.item_status == "uncertain"
    assert {review.review_action for review in reviews} == {"reject", "mark_uncertain"}
    assert {review.reviewer_ref for review in reviews} == {"writing_agent.phase13"}


def test_agent_apply_world_model_proposal_resolution_rejects_approval_actions_without_writes(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase13.agent.approve-refused",
        predicate="role",
        subject_ref="char.林深",
    )
    edit_item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase13.agent.approve-edits-refused",
        predicate="role",
        subject_ref="char.苏晚晴",
    )
    before_review_count = db_session.query(WorldProposalReview).count()
    before_fact_count = db_session.query(WorldFactClaim).count()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "尝试在守卫应用中审批事实",
            "tools": [
                {
                    "tool_name": "apply_world_model_proposal_resolution",
                    "params": {
                        "confirm_apply": True,
                        "decisions": [
                            {
                                "proposal_item_id": item.id,
                                "action": "approve",
                                "reason": "本阶段不允许",
                            },
                            {
                                "proposal_item_id": edit_item.id,
                                "action": "approve_with_edits",
                                "reason": "本阶段同样不允许",
                                "edited_fields": {"object_ref_or_value": "雾港协作者"},
                            }
                        ],
                    },
                }
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    stored_item = db_session.query(WorldProposalItem).filter_by(id=item.id).one()
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "blocked"
    assert output["applied_count"] == 0
    assert output["invalid_decision_count"] == 2
    assert {item["code"] for item in output["invalid_decisions"]} == {"approval_not_supported_in_guarded_apply"}
    assert output["should_generate_next_chapter"] is False
    assert stored_item.item_status == "pending"
    assert db_session.query(WorldProposalReview).count() == before_review_count
    assert db_session.query(WorldFactClaim).count() == before_fact_count


def test_agent_apply_world_model_proposal_resolution_rolls_back_when_review_stage_fails(
    client,
    db_session,
):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    valid_item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase13.agent.rollback-valid",
        predicate="role",
        subject_ref="char.林深",
    )
    drift_item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase13.agent.rollback-drift",
        predicate="status",
        subject_ref="char.苏晚晴",
    )
    drift_item.contract_version = "drifted-contract-version"
    db_session.commit()
    before_review_count = db_session.query(WorldProposalReview).count()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "第二条评审阶段失败时整批回滚",
            "tools": [
                {
                    "tool_name": "apply_world_model_proposal_resolution",
                    "params": {
                        "confirm_apply": True,
                        "decisions": [
                            {
                                "proposal_item_id": valid_item.id,
                                "action": "reject",
                                "reason": "第一条本应回滚",
                            },
                            {
                                "proposal_item_id": drift_item.id,
                                "action": "mark_uncertain",
                                "reason": "合约版本漂移导致评审阶段失败",
                            },
                        ],
                    },
                }
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    db_session.expire_all()
    stored_valid_item = db_session.query(WorldProposalItem).filter_by(id=valid_item.id).one()
    stored_drift_item = db_session.query(WorldProposalItem).filter_by(id=drift_item.id).one()
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "blocked"
    assert output["applied_count"] == 0
    assert output["invalid_decision_count"] == 1
    assert output["invalid_decisions"][0]["code"] == "apply_failed"
    assert stored_valid_item.item_status == "pending"
    assert stored_drift_item.item_status == "pending"
    assert db_session.query(WorldProposalReview).count() == before_review_count


def test_agent_apply_world_model_proposal_resolution_blocks_invalid_batch_without_partial_writes(
    client,
    db_session,
):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    valid_item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase13.agent.valid-batch",
        predicate="role",
        subject_ref="char.林深",
    )
    before_review_count = db_session.query(WorldProposalReview).count()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "无效批次不能部分应用",
            "tools": [
                {
                    "tool_name": "apply_world_model_proposal_resolution",
                    "params": {
                        "confirm_apply": True,
                        "decisions": [
                            {
                                "proposal_item_id": valid_item.id,
                                "action": "reject",
                                "reason": "有效但不应部分落库",
                            },
                            {
                                "proposal_item_id": "proposal-item.missing.phase13",
                                "action": "mark_uncertain",
                                "reason": "缺失项导致整批阻断",
                            },
                        ],
                    },
                }
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    stored_valid_item = db_session.query(WorldProposalItem).filter_by(id=valid_item.id).one()
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "blocked"
    assert output["applied_count"] == 0
    assert output["invalid_decision_count"] == 1
    assert output["invalid_decisions"][0]["code"] == "missing_item"
    assert stored_valid_item.item_status == "pending"
    assert db_session.query(WorldProposalReview).count() == before_review_count


def test_agent_preview_world_model_proposal_resolution_allows_apply_followup(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase13.agent.preview-apply",
        predicate="role",
        subject_ref="char.林深",
    )

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "先预览再确认应用世界模型提案决策",
            "tools": [
                {
                    "tool_name": "preview_world_model_proposal_resolution",
                    "params": {
                        "decisions": [
                            {
                                "proposal_item_id": item.id,
                                "action": "reject",
                                "reason": "预览后确认拒绝",
                            }
                        ]
                    },
                },
                {
                    "tool_name": "apply_world_model_proposal_resolution",
                    "params": {
                        "confirm_apply": True,
                        "decisions": [
                            {
                                "proposal_item_id": item.id,
                                "action": "reject",
                                "reason": "预览后确认拒绝",
                            }
                        ],
                    },
                },
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert [step["tool_name"] for step in payload["steps"]] == [
        "preview_world_model_proposal_resolution",
        "apply_world_model_proposal_resolution",
    ]
    assert payload["steps"][1]["output"]["applied_count"] == 1


def test_agent_apply_world_model_proposal_resolution_blocks_followup_generation_when_queue_remains(
    client,
    db_session,
    monkeypatch,
):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    item_to_apply = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase13.agent.apply-one",
        predicate="role",
        subject_ref="char.林深",
    )
    _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase13.agent.remains",
        predicate="status",
        subject_ref="char.苏晚晴",
    )
    calls = []

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append(action_type)
        return {"status": "success", "chapter_index": 2}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "应用部分提案后尝试生成第2章",
            "tools": [
                {
                    "tool_name": "apply_world_model_proposal_resolution",
                    "params": {
                        "confirm_apply": True,
                        "decisions": [
                            {
                                "proposal_item_id": item_to_apply.id,
                                "action": "reject",
                                "reason": "只处理一个，仍有待审项",
                            }
                        ],
                    },
                },
                {"tool_name": "generate_chapter", "params": {"chapter_index": 2}},
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert payload["steps"][0]["tool_name"] == "apply_world_model_proposal_resolution"
    assert payload["steps"][0]["output"]["after_actionable_items"] == 1
    assert payload["steps"][0]["output"]["should_generate_next_chapter"] is False
    assert len(payload["steps"]) == 1
    assert calls == []


def test_agent_apply_world_model_proposal_resolution_allows_generation_when_queue_clears(
    client,
    db_session,
    monkeypatch,
):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase13.agent.clears",
        predicate="role",
        subject_ref="char.林深",
    )
    calls = []

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append(action_type)
        return {"status": "success", "chapter_index": 2}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "清空提案队列后生成第2章",
            "tools": [
                {
                    "tool_name": "apply_world_model_proposal_resolution",
                    "params": {
                        "confirm_apply": True,
                        "decisions": [
                            {
                                "proposal_item_id": item.id,
                                "action": "reject",
                                "reason": "清空队列",
                            }
                        ],
                    },
                },
                {"tool_name": "generate_chapter", "params": {"chapter_index": 2}},
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert [step["tool_name"] for step in payload["steps"]] == [
        "apply_world_model_proposal_resolution",
        "generate_chapter",
    ]
    assert calls == ["generate_chapter"]


def test_agent_draft_world_model_proposal_resolution_decisions_reports_without_writes(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    presence_item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase14.agent.presence",
        predicate="presence_count",
        subject_ref="char.林深",
    )
    location_item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase14.agent.location",
        predicate="present_at_location",
        subject_ref="char.苏晚晴",
    )
    before_review_count = db_session.query(WorldProposalReview).count()
    before_fact_count = db_session.query(WorldFactClaim).count()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "草拟低风险世界模型提案决策",
            "tools": [{"tool_name": "draft_world_model_proposal_resolution_decisions", "params": {"limit": 20}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    stored_presence = db_session.query(WorldProposalItem).filter_by(id=presence_item.id).one()
    stored_location = db_session.query(WorldProposalItem).filter_by(id=location_item.id).one()
    actions = {decision["proposal_item_id"]: decision["action"] for decision in output["draft_decisions"]}
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "blocked"
    assert output["report_only"] is True
    assert output["draft_decision_count"] == 2
    assert actions[presence_item.id] == "reject"
    assert actions[location_item.id] == "mark_uncertain"
    assert output["requires_confirmation"] is True
    assert output["can_auto_apply"] is False
    assert output["should_generate_next_chapter"] is False
    assert stored_presence.item_status == "pending"
    assert stored_location.item_status == "pending"
    assert db_session.query(WorldProposalReview).count() == before_review_count
    assert db_session.query(WorldFactClaim).count() == before_fact_count


def test_agent_draft_world_model_proposal_resolution_decisions_tracks_unclassified_items(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase14.agent.custom",
        predicate="custom_truth",
        subject_ref="char.林深",
    )

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "草拟未知谓词提案决策",
            "tools": [
                {
                    "tool_name": "draft_world_model_proposal_resolution_decisions",
                    "params": {"limit": 20, "include_unclassified": True},
                }
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["draft_decision_count"] == 0
    assert output["unclassified_item_count"] == 1
    assert output["unclassified_items"][0]["predicate"] == "custom_truth"
    assert output["recommended_next_tools"] == ["plan_world_model_proposal_resolution"]


def test_agent_draft_world_model_proposal_resolution_decisions_keeps_plot_signal_unclassified(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase81.identifier.hypothesis",
        predicate="identifier_meaning_hypothesis",
        subject_ref="identifier.G-07",
    )

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "草拟高价值剧情事实提案决策",
            "tools": [
                {
                    "tool_name": "draft_world_model_proposal_resolution_decisions",
                    "params": {"limit": 20, "include_unclassified": True},
                }
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["draft_decision_count"] == 0
    assert output["unclassified_item_count"] == 1
    assert output["unclassified_items"][0]["predicate"] == "identifier_meaning_hypothesis"
    assert output["recommended_next_tools"] == ["plan_world_model_proposal_resolution"]


def test_agent_draft_high_value_world_proposal_resolution_decisions_reports_without_writes(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    high_item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase82.identifier.hypothesis",
        predicate="identifier_meaning_hypothesis",
        subject_ref="identifier.G-07",
    )
    video_item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase84.video.evidence",
        predicate="historical_video_evidence",
        subject_ref="chapter.26.video",
    )
    low_item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase82.presence.low",
        predicate="presence_count",
        subject_ref="char.林深",
    )
    before_review_count = db_session.query(WorldProposalReview).count()
    before_fact_count = db_session.query(WorldFactClaim).count()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "草拟高价值世界模型提案决策",
            "tools": [{"tool_name": "draft_high_value_world_proposal_resolution_decisions", "params": {"limit": 20}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    stored_high = db_session.query(WorldProposalItem).filter_by(id=high_item.id).one()
    stored_low = db_session.query(WorldProposalItem).filter_by(id=low_item.id).one()
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "blocked"
    assert output["report_only"] is True
    assert output["inspected_item_count"] == 3
    assert output["draft_decision_count"] == 2
    assert output["skipped_item_count"] == 1
    draft_by_predicate = {item["predicate"]: item for item in output["draft_decisions"]}
    assert draft_by_predicate["identifier_meaning_hypothesis"]["proposal_item_id"] == high_item.id
    assert draft_by_predicate["historical_video_evidence"]["proposal_item_id"] == video_item.id
    assert set(draft_by_predicate) == {"identifier_meaning_hypothesis", "historical_video_evidence"}
    assert {item["action"] for item in output["draft_decisions"]} == {"mark_uncertain"}
    assert output["requires_confirmation"] is True
    assert output["can_auto_apply"] is False
    assert output["should_generate_next_chapter"] is False
    assert output["recommended_next_tools"] == ["apply_world_model_proposal_resolution"]
    assert stored_high.item_status == "pending"
    assert stored_low.item_status == "pending"
    assert db_session.query(WorldProposalReview).count() == before_review_count
    assert db_session.query(WorldFactClaim).count() == before_fact_count


def test_agent_draft_world_model_proposal_resolution_decisions_ignores_approval_policy_overrides(
    client,
    db_session,
):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase14.agent.custom-approval-policy",
        predicate="custom_truth",
        subject_ref="char.林深",
    )

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "忽略自定义审批草案策略",
            "tools": [
                {
                    "tool_name": "draft_world_model_proposal_resolution_decisions",
                    "params": {
                        "limit": 20,
                        "include_unclassified": True,
                        "predicate_policies": {
                            "custom_truth": {
                                "action": "approve_with_edits",
                                "reason": "不允许草拟审批",
                            }
                        },
                    },
                }
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["draft_decision_count"] == 0
    assert output["unclassified_item_count"] == 1
    assert output["unclassified_items"][0]["predicate"] == "custom_truth"


def test_agent_draft_world_model_proposal_resolution_decisions_allows_apply_followup(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase14.agent.chain",
        predicate="presence_count",
        subject_ref="char.林深",
    )

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "先草拟再应用世界模型提案决策",
            "tools": [
                {"tool_name": "draft_world_model_proposal_resolution_decisions", "params": {"limit": 20}},
                {
                    "tool_name": "apply_world_model_proposal_resolution",
                    "params": {
                        "confirm_apply": True,
                        "decisions": [
                            {
                                "proposal_item_id": item.id,
                                "action": "reject",
                                "reason": "presence_count 是提取元数据，不进入真相层",
                            }
                        ],
                    },
                },
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert [step["tool_name"] for step in payload["steps"]] == [
        "draft_world_model_proposal_resolution_decisions",
        "apply_world_model_proposal_resolution",
    ]
    assert payload["steps"][1]["output"]["applied_count"] == 1


def test_agent_draft_world_model_proposal_resolution_decisions_blocks_followup_generation(
    client,
    db_session,
    monkeypatch,
):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase14.agent.blocks-generation",
        predicate="presence_count",
        subject_ref="char.林深",
    )
    calls = []

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append(action_type)
        return {"status": "success", "chapter_index": 2}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "草拟提案决策后尝试生成第2章",
            "tools": [
                {"tool_name": "draft_world_model_proposal_resolution_decisions", "params": {"limit": 20}},
                {"tool_name": "generate_chapter", "params": {"chapter_index": 2}},
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert payload["steps"][0]["tool_name"] == "draft_world_model_proposal_resolution_decisions"
    assert payload["steps"][0]["output"]["should_generate_next_chapter"] is False
    assert len(payload["steps"]) == 1
    assert calls == []


def test_agent_create_revision_draft_from_plan_is_non_destructive(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    chapter.title = "第2章"
    chapter.word_count = 3400
    original_content = chapter.content
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "为第2章创建修订草稿",
            "tools": [{"tool_name": "create_revision_draft", "params": {"chapter_index": 2}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    chapter_after = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    revision = db_session.query(ChapterRevision).filter_by(id=output["revision_id"]).one()
    annotations = db_session.query(RevisionAnnotation).filter_by(revision_id=revision.id).all()
    corrections = db_session.query(RevisionCorrection).filter_by(revision_id=revision.id).all()
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "drafted"
    assert output["annotation_count"] >= 2
    assert output["correction_count"] == 0
    assert revision.status == "draft"
    assert revision.result_version_id is None
    assert corrections == []
    assert any("[PLAN_ACTION:retitle_chapter]" in item.comment for item in annotations)
    assert any("[PLAN_ACTION:compress_chapter]" in item.comment for item in annotations)
    assert chapter_after.content == original_content
    assert chapter_after.title == "第2章"


def test_agent_create_revision_draft_anchors_drift_actions(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "黑市雾晶"
    chapter.content = "苏晚晴低声说，她以前是雾安局研究员。随后她制造幻觉骗过守卫。"
    chapter.word_count = 2000
    original_content = chapter.content
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "创建第1章漂移修订草稿",
            "tools": [{"tool_name": "create_revision_draft", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    annotations = db_session.query(RevisionAnnotation).filter_by(revision_id=output["revision_id"]).all()
    comments = [annotation.comment or "" for annotation in annotations]
    selected = [annotation.selected_text or "" for annotation in annotations]
    assert response.status_code == 200
    assert output["status"] == "drafted"
    assert output["annotation_count"] == 2
    assert any("[PLAN_ACTION:fix_character_profile_drift]" in comment for comment in comments)
    assert any("[PLAN_ACTION:respect_ability_boundary]" in comment for comment in comments)
    assert any("雾安局研究员" in text for text in selected)
    assert any("制造幻觉" in text for text in selected)
    assert db_session.query(ChapterContent).filter_by(id=chapter.id).one().content == original_content


def test_agent_apply_planner_revision_patch_updates_chapter_and_versions(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "黑市雾晶"
    chapter.content = "苏晚晴低声说，她以前是雾安局研究员。随后她制造幻觉骗过守卫。"
    chapter.word_count = 2000
    db_session.commit()

    draft = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "创建修订草稿",
            "tools": [{"tool_name": "create_revision_draft", "params": {"chapter_index": 1}}],
        },
    )
    revision_id = draft.json()["steps"][0]["output"]["revision_id"]

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "应用planner修订",
            "tools": [{"tool_name": "apply_planner_revision_patch", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    patched = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    revision = db_session.query(ChapterRevision).filter_by(id=revision_id).one()
    assert response.status_code == 200
    assert output["status"] == "completed"
    assert output["revision_id"] == revision_id
    assert output["applied_replacement_count"] == 2
    assert "雾安局研究员" not in patched.content
    assert "制造幻觉" not in patched.content
    assert "雾港大学神经科学教授" in patched.content
    assert "扰乱雾中感知" in patched.content
    assert patched.word_count != 2000
    assert revision.status == "completed"
    assert revision.base_version_id
    assert revision.result_version_id
    assert output["should_generate_next_chapter"] is False


def test_agent_apply_planner_revision_patch_then_review_clears_drift_blockers(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "黑市雾晶"
    chapter.content = "苏晚晴低声说，她以前是雾安局研究员。随后她制造幻觉骗过守卫。"
    chapter.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "修订并复审",
            "tools": [
                {"tool_name": "create_revision_draft", "params": {"chapter_index": 1}},
                {"tool_name": "apply_planner_revision_patch", "params": {"chapter_index": 1}},
                {"tool_name": "review_chapter_quality", "params": {"chapter_index": 1}},
            ],
        },
    )

    review = response.json()["steps"][2]["output"]
    codes = {finding["code"] for finding in review["findings"]}
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "character_profile_drift" not in codes
    assert "ability_boundary_drift" not in codes
    assert review["blocker_count"] == 0


def test_agent_expand_chapter_to_target_updates_chapter_versions_and_requires_review(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
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
            "tools": [{"tool_name": "expand_chapter_to_target", "params": {"chapter_index": 1}}],
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
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
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
                {"tool_name": "expand_chapter_to_target", "params": {"chapter_index": 1}},
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
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
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
                {"tool_name": "expand_chapter_to_target", "params": {"chapter_index": 1}},
                {"tool_name": "generate_chapter", "params": {"chapter_index": 2}},
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert [step["tool_name"] for step in payload["steps"]] == ["expand_chapter_to_target"]
    assert calls == []


def test_agent_expand_chapter_to_target_skips_when_chapter_already_at_target(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
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
            "tools": [{"tool_name": "expand_chapter_to_target", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "skipped"
    assert output["reason"] == "chapter_already_at_target"
    assert output["should_generate_next_chapter"] is True
    assert calls == []


def test_agent_expand_chapter_to_target_blocks_pending_world_model_proposals(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.content = "短章。" * 300
    chapter.word_count = 600
    import_setup_to_world_model(db_session, project.id)
    _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase21.pending",
        predicate="role",
        subject_ref="char.林深",
    )
    db_session.commit()
    calls = []

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            calls.append(messages)
            raise AssertionError("AI should not be called when world proposals are pending")

    monkeypatch.setattr("app.core.chapter_expansion.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "存在世界模型提案时扩写",
            "tools": [{"tool_name": "expand_chapter_to_target", "params": {"chapter_index": 1}}],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert output["status"] == "blocked"
    assert output["reason"] == "pending_world_model_proposals"
    assert output["pending_world_model_proposal_count"] == 1
    assert calls == []


def test_agent_compress_chapter_to_target_updates_chapter_versions_and_requires_review(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
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
                {"tool_name": "compress_chapter_to_target", "params": {"chapter_index": 1, "target_max_word_count": 2300}}
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
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
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
                {
                    "tool_name": "compress_chapter_to_target",
                    "params": {
                        "chapter_index": 1,
                        "forbidden_terms": ["我就是N-07"],
                    },
                }
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
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
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
                {
                    "tool_name": "compress_chapter_to_target",
                    "params": {
                        "chapter_index": 1,
                        "forbidden_terms": ["我就是N-07"],
                    },
                }
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
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
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
                {"tool_name": "compress_chapter_to_target", "params": {"chapter_index": 1, "target_max_word_count": 2300}},
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
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
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
                {"tool_name": "compress_chapter_to_target", "params": {"chapter_index": 1, "target_max_word_count": 2300}},
                {"tool_name": "generate_chapter", "params": {"chapter_index": 2}},
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert [step["tool_name"] for step in payload["steps"]] == ["compress_chapter_to_target"]
    assert calls == []


def test_agent_compress_chapter_to_target_skips_when_chapter_already_within_target(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
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
            "tools": [{"tool_name": "compress_chapter_to_target", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "skipped"
    assert output["reason"] == "chapter_already_within_target"
    assert calls == []


def test_agent_compress_chapter_to_target_blocks_pending_world_model_proposals(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.content = "林深和苏晚晴在实验室里反复检查雾晶记录，确认线索。 " * 120
    chapter.word_count = 3000
    import_setup_to_world_model(db_session, project.id)
    _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase22.pending",
        predicate="role",
        subject_ref="char.林深",
    )
    db_session.commit()
    calls = []

    class FakeAIService:
        async def complete(self, messages, **kwargs):
            calls.append(messages)
            raise AssertionError("AI should not be called when world proposals are pending")

    monkeypatch.setattr("app.core.chapter_compression.AIService", FakeAIService)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "存在世界模型提案时压缩",
            "tools": [
                {"tool_name": "compress_chapter_to_target", "params": {"chapter_index": 1, "target_max_word_count": 2300}}
            ],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert output["reason"] == "pending_world_model_proposals"
    assert output["pending_world_model_proposal_count"] == 1
    assert calls == []


def test_agent_compress_chapter_to_target_repairs_under_target_retry(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
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
                {"tool_name": "compress_chapter_to_target", "params": {"chapter_index": 1, "target_max_word_count": 2300}}
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
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
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
                {"tool_name": "compress_chapter_to_target", "params": {"chapter_index": 1, "target_max_word_count": 2300}}
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

    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
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
                {"tool_name": "compress_chapter_to_target", "params": {"chapter_index": 1, "target_max_word_count": 2300}}
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


def test_refresh_longform_memory_prefers_reviewed_event_summary_proposal(db_session):
    from app.core.athena_longform import analyze_chapter_to_world_proposals
    from app.core.longform_memory import refresh_longform_memory_for_chapter
    from app.core.world_proposal_service import review_proposal_item

    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "蓝雾电梯"
    chapter.content = (
        "林深沿着潮湿管道走了很久，墙上的灰蓝色雾晶回声像旧唱片一样反复刮擦。"
        "他在第二道门后发现蓝雾电梯启动，苏晚晴确认这不是普通出口。"
        + "随后他们又穿过一段漫长的空走廊，脚步声被黑暗吞没，墙面只剩无意义的噪点。" * 8
    )
    chapter.word_count = 2600
    db_session.commit()
    import_setup_to_world_model(db_session, project.id)
    analyze_chapter_to_world_proposals(db=db_session, project_id=project.id, chapter_index=1)
    event_item = (
        db_session.query(WorldProposalItem)
        .filter_by(project_id=project.id, subject_ref="chapter.1", predicate="event_summary")
        .one()
    )
    review_proposal_item(
        db=db_session,
        proposal_item_id=event_item.id,
        reviewer_ref="test",
        action="mark_uncertain",
        reason="章节摘要只进入写作记忆，不进入真相层",
        evidence_refs=["chapter:1"],
        commit=True,
    )

    refresh_longform_memory_for_chapter(db_session, project.id, 1)

    memory = (
        db_session.query(LongformMemory)
        .filter_by(project_id=project.id, memory_type="chapter", scope_key="chapter:1")
        .one()
    )
    assert "蓝雾电梯启动" in memory.summary
    assert memory.memory_metadata["source"] == "reviewed_event_summary"
    assert memory.memory_metadata["event_summary_proposal_item_id"] == event_item.id


def test_analyze_chapter_world_model_creates_new_event_summary_after_terminal_summary_goes_stale(db_session):
    from app.core.athena_longform import analyze_chapter_to_world_proposals
    from app.core.longform_memory import refresh_longform_memory_for_chapter
    from app.core.world_proposal_service import review_proposal_item

    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "蓝雾电梯"
    chapter.content = (
        "林深在旧站台发现蓝雾电梯启动。"
        "苏晚晴确认这不是普通出口。"
        + "墙上的灰蓝色雾晶回声像旧唱片一样反复刮擦。" * 8
    )
    chapter.word_count = 2400
    db_session.commit()
    import_setup_to_world_model(db_session, project.id)
    analyze_chapter_to_world_proposals(db=db_session, project_id=project.id, chapter_index=1)
    old_item = (
        db_session.query(WorldProposalItem)
        .filter_by(project_id=project.id, subject_ref="chapter.1", predicate="event_summary")
        .one()
    )
    review_proposal_item(
        db=db_session,
        proposal_item_id=old_item.id,
        reviewer_ref="test",
        action="mark_uncertain",
        reason="旧摘要先进入写作记忆候选",
        evidence_refs=["chapter:1"],
        commit=True,
    )

    chapter.content = (
        "林深在暗网密室找到回声稳定剂核心线索。"
        "顾衍确认完整配方被转移到第三研究所核心数据库。"
        + "蓝雾电梯的旧线索只剩下墙上的残影。" * 8
    )
    chapter.word_count = 2500
    db_session.commit()

    result = analyze_chapter_to_world_proposals(db=db_session, project_id=project.id, chapter_index=1)

    event_items = (
        db_session.query(WorldProposalItem)
        .filter_by(project_id=project.id, subject_ref="chapter.1", predicate="event_summary")
        .order_by(WorldProposalItem.created_at.asc())
        .all()
    )
    assert result["created"]["proposal_items"] >= 1
    assert len(event_items) == 2
    assert event_items[0].item_status == "uncertain"
    assert event_items[1].item_status == "pending"
    assert "第三研究所核心数据库" in event_items[1].object_ref_or_value["summary"]

    review_proposal_item(
        db=db_session,
        proposal_item_id=event_items[1].id,
        reviewer_ref="test",
        action="mark_uncertain",
        reason="修订后摘要作为写作记忆来源",
        evidence_refs=["chapter:1"],
        commit=True,
    )
    refresh_longform_memory_for_chapter(db_session, project.id, 1)

    memory = (
        db_session.query(LongformMemory)
        .filter_by(project_id=project.id, memory_type="chapter", scope_key="chapter:1")
        .one()
    )
    assert "第三研究所核心数据库" in memory.summary
    assert memory.memory_metadata["source"] == "reviewed_event_summary"
    assert memory.memory_metadata["event_summary_proposal_item_id"] == event_items[1].id


def test_agent_compress_chapter_to_target_blocks_after_retry_exhaustion(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
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
            "tools": [{"tool_name": "compress_chapter_to_target", "params": {"chapter_index": 1}}],
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
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
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
                {"tool_name": "compress_chapter_to_target", "params": {"chapter_index": 1, "target_max_word_count": 2300}}
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
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
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
                {"tool_name": "compress_chapter_to_target", "params": {"chapter_index": 1, "target_max_word_count": 2300}}
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
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
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
                {"tool_name": "compress_chapter_to_target", "params": {"chapter_index": 1, "target_max_word_count": 2300}}
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


def test_agent_create_revision_draft_reuses_existing_draft(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    chapter.title = "第2章"
    chapter.word_count = 3400
    db_session.commit()

    first = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "为第2章创建修订草稿",
            "tools": [{"tool_name": "create_revision_draft", "params": {"chapter_index": 2}}],
        },
    )
    second = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "再次为第2章创建修订草稿",
            "tools": [{"tool_name": "create_revision_draft", "params": {"chapter_index": 2}}],
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200
    first_output = first.json()["steps"][0]["output"]
    second_output = second.json()["steps"][0]["output"]
    assert first_output["revision_id"] == second_output["revision_id"]
    assert db_session.query(ChapterRevision).filter_by(project_id=project.id, chapter_index=2).count() == 1
    assert second_output["revision_index"] == 1


def test_agent_create_revision_draft_does_not_modify_manual_draft(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    chapter.title = "第2章"
    chapter.word_count = 3400
    revision = ChapterRevision(
        project_id=project.id,
        chapter_id=chapter.id,
        chapter_index=2,
        revision_index=1,
        status="draft",
    )
    db_session.add(revision)
    db_session.flush()
    db_session.add(
        RevisionAnnotation(
            revision_id=revision.id,
            paragraph_index=0,
            start_offset=0,
            end_offset=2,
            selected_text="林深",
            comment="用户手写批注",
        )
    )
    db_session.add(
        RevisionCorrection(
            revision_id=revision.id,
            paragraph_index=0,
            original_text="旧句",
            corrected_text="新句",
        )
    )
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "不要覆盖用户手写草稿",
            "tools": [{"tool_name": "create_revision_draft", "params": {"chapter_index": 2}}],
        },
    )

    annotations = db_session.query(RevisionAnnotation).filter_by(revision_id=revision.id).all()
    corrections = db_session.query(RevisionCorrection).filter_by(revision_id=revision.id).all()
    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert response.json()["steps"][0]["output"]["reason"] == "existing_manual_draft"
    assert db_session.query(ChapterRevision).filter_by(project_id=project.id, chapter_index=2).count() == 1
    assert [item.comment for item in annotations] == ["用户手写批注"]
    assert corrections[0].corrected_text == "新句"


def test_agent_create_revision_draft_does_not_compete_with_submitted_revision(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    chapter.title = "第2章"
    chapter.word_count = 3400
    submitted = ChapterRevision(
        project_id=project.id,
        chapter_id=chapter.id,
        chapter_index=2,
        revision_index=1,
        status="submitted",
    )
    db_session.add(submitted)
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "不要创建竞争修订",
            "tools": [{"tool_name": "create_revision_draft", "params": {"chapter_index": 2}}],
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert response.json()["steps"][0]["output"]["reason"] == "existing_active_revision"
    revisions = db_session.query(ChapterRevision).filter_by(project_id=project.id, chapter_index=2).all()
    assert len(revisions) == 1
    assert revisions[0].id == submitted.id
    assert revisions[0].status == "submitted"


def test_agent_create_revision_draft_skips_ready_chapter(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第1章是否需要修订草稿",
            "tools": [{"tool_name": "create_revision_draft", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "skipped"
    assert output["reason"] == "no_revision_actions"
    assert output["revision_id"] is None
    assert db_session.query(ChapterRevision).filter_by(project_id=project.id).count() == 0


def test_agent_create_revision_draft_blocks_followup_generation(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2, 3], generated_chapters=[1, 2])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).one()
    chapter.title = "第2章"
    chapter.word_count = 3400
    db_session.commit()
    calls = []

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append(action_type)
        return {"status": "success", "chapter_index": 3}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "创建第2章修订草稿后尝试生成第3章",
            "tools": [
                {"tool_name": "create_revision_draft", "params": {"chapter_index": 2}},
                {"tool_name": "generate_chapter", "params": {"chapter_index": 3}},
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert payload["steps"][0]["tool_name"] == "create_revision_draft"
    assert payload["steps"][0]["output"]["should_generate_next_chapter"] is False
    assert len(payload["steps"]) == 1
    assert calls == []


@patch("app.api.outlines.load_api_key", return_value="sk-test")
@patch("app.api.outlines.ai_service.complete", new_callable=AsyncMock)
@patch("app.api.outlines.ai_service.parse_json")
def test_agent_expand_outline_window_adds_missing_outline_then_preflight_ready(
    mock_parse,
    mock_complete,
    mock_key,
    client,
    db_session,
):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1, 2])
    import_setup_to_world_model(db_session, project.id)
    mock_complete.return_value.content = "{}"
    mock_parse.return_value = {
        "total_chapters": 600,
        "chapters": [
            {
                "chapter_index": 3,
                "title": "诊所残影",
                "summary": "林深和苏晚晴追查记忆诊所。",
                "scenes": ["诊所门口", "档案室"],
                "characters": ["林深", "苏晚晴"],
                "purpose": "补齐第3章大纲",
            }
        ],
    }

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "补齐第3章大纲并检查可写性",
            "tools": [
                {
                    "tool_name": "expand_outline_window",
                    "params": {
                        "start_chapter": 3,
                        "end_chapter": 3,
                        "command_args": "补齐第3章",
                        "confirm_execute": True,
                    },
                },
                {"tool_name": "preflight_writing", "params": {"chapter_index": 3}},
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["steps"][0]["tool_name"] == "expand_outline_window"
    assert payload["steps"][0]["output"]["added_chapter_count"] == 1
    assert payload["steps"][1]["output"]["status"] == "ready"
    outline = db_session.query(Outline).filter(Outline.project_id == project.id).one()
    assert [chapter["chapter_index"] for chapter in outline.chapters] == [1, 2, 3]


def _create_project(client, name: str) -> str:
    response = client.post("/api/v1/projects", json={"name": name})
    assert response.status_code == 200
    return response.json()["id"]


def _create_trace(db_session, project_id: str, trace_id: str, trace_type: str) -> None:
    db_session.add(AIModelCallTrace(id=trace_id, project_id=project_id, trace_type=trace_type, status="success"))
    db_session.commit()


def _planner_generate_chapter_plan(project_id: str, *, chapter_index: int) -> dict:
    plan_id = f"plan:generate-chapter-{chapter_index}"
    params = {"chapter_index": chapter_index}
    step = {
        "step_index": 1,
        "step_id": f"step:generate-chapter-{chapter_index}",
        "tool_name": "generate_chapter",
        "params": params,
        "mutability": "write",
        "requires_confirmation": True,
        "reason": f"生成第{chapter_index}章正文。",
    }
    tool = {
        "tool_name": "generate_chapter",
        "params": params,
        "planner": {
            "step_index": 1,
            "step_id": step["step_id"],
            "plan_id": plan_id,
            "source_projection_id": f"projection:generate-chapter-{chapter_index}",
            "mutability": "write",
            "requires_confirmation": True,
            "reason": step["reason"],
            "planner_version": "phase53.context_gate.v1",
        },
    }
    plan = {
        "status": "completed",
        "planner_version": "phase53.context_gate.v1",
        "project_id": project_id,
        "intent_class": "continue_next_chapter",
        "goal": f"生成第{chapter_index}章",
        "chapter_index": chapter_index,
        "steps": [step],
        "tools": [tool],
        "trace": {
            "plan_id": plan_id,
            "source_projection_id": f"projection:generate-chapter-{chapter_index}",
            "planner_version": "phase53.context_gate.v1",
            "selected_tools": ["generate_chapter"],
        },
    }
    plan["approval_contract"] = build_agent_plan_approval_contract(plan)
    return plan


def _planner_revision_patch_plan(project_id: str, *, chapter_index: int, revision_id: str) -> dict:
    plan_id = f"plan:revision-patch-{chapter_index}"
    params = {"chapter_index": chapter_index, "revision_id": revision_id}
    step = {
        "step_index": 1,
        "step_id": f"step:revision-patch-{chapter_index}",
        "tool_name": "apply_planner_revision_patch",
        "params": params,
        "mutability": "guarded_write",
        "requires_confirmation": True,
        "reason": f"应用第{chapter_index}章修订补丁。",
    }
    tool = {
        "tool_name": "apply_planner_revision_patch",
        "params": params,
        "planner": {
            "step_index": 1,
            "step_id": step["step_id"],
            "plan_id": plan_id,
            "source_projection_id": f"projection:revision-patch-{chapter_index}",
            "mutability": "guarded_write",
            "requires_confirmation": True,
            "reason": step["reason"],
            "planner_version": "phase53.context_gate.v1",
        },
    }
    plan = {
        "status": "completed",
        "planner_version": "phase53.context_gate.v1",
        "project_id": project_id,
        "intent_class": "apply_revision_patch",
        "goal": f"应用第{chapter_index}章修订补丁",
        "chapter_index": chapter_index,
        "steps": [step],
        "tools": [tool],
        "trace": {
            "plan_id": plan_id,
            "source_projection_id": f"projection:revision-patch-{chapter_index}",
            "planner_version": "phase53.context_gate.v1",
            "selected_tools": ["apply_planner_revision_patch"],
        },
    }
    plan["approval_contract"] = build_agent_plan_approval_contract(plan)
    return plan


def _planner_world_model_resolution_plan(project_id: str, *, decisions: list[dict]) -> dict:
    plan_id = f"plan:world-model-resolution:{project_id}"
    params = {"confirm_apply": True, "decisions": decisions}
    step = {
        "step_index": 1,
        "step_id": f"step:world-model-resolution:{project_id}",
        "tool_name": "apply_world_model_proposal_resolution",
        "params": params,
        "mutability": "guarded_write",
        "requires_confirmation": True,
        "reason": "应用世界模型提案处理决策。",
    }
    tool = {
        "tool_name": "apply_world_model_proposal_resolution",
        "params": params,
        "planner": {
            "step_index": 1,
            "step_id": step["step_id"],
            "plan_id": plan_id,
            "source_projection_id": f"projection:world-model-resolution:{project_id}",
            "mutability": "guarded_write",
            "requires_confirmation": True,
            "reason": step["reason"],
            "planner_version": "phase53.context_gate.v1",
        },
    }
    plan = {
        "status": "completed",
        "planner_version": "phase53.context_gate.v1",
        "project_id": project_id,
        "intent_class": "apply_world_model_proposal_resolution",
        "goal": "应用世界模型提案处理决策",
        "steps": [step],
        "tools": [tool],
        "trace": {
            "plan_id": plan_id,
            "source_projection_id": f"projection:world-model-resolution:{project_id}",
            "planner_version": "phase53.context_gate.v1",
            "selected_tools": ["apply_world_model_proposal_resolution"],
        },
    }
    plan["approval_contract"] = build_agent_plan_approval_contract(plan)
    return plan


def _seed_recommended_followup_source_run(db_session, canonical_followups: list[str]) -> tuple[str, WritingAgentRun]:
    project = Project(name="Recommended Followup Source")
    db_session.add(project)
    db_session.flush()
    run = WritingAgentRun(project_id=project.id, goal="生成第2章", status="success", input={})
    db_session.add(run)
    db_session.flush()
    db_session.add(
        WritingAgentStep(
            run_id=run.id,
            project_id=project.id,
            step_index=1,
            tool_name="generate_chapter",
            status="success",
            chapter_index=2,
            input={"params": {"chapter_index": 2}},
            output={
                "status": "success",
                "chapter_index": 2,
                "agent_tool_result": {
                    "recommendations": {
                        "canonical_followups": canonical_followups,
                    }
                },
            },
        )
    )
    db_session.commit()
    return project.id, run


def _seed_pending_world_proposal(
    db_session,
    *,
    project_id: str,
    claim_id: str,
    predicate: str,
    subject_ref: str,
) -> WorldProposalItem:
    profile = db_session.query(ProjectProfileVersion).filter_by(project_id=project_id).one()
    bundle = create_bundle(
        db=db_session,
        project_id=project_id,
        project_profile_version_id=profile.id,
        profile_version=profile.version,
        created_by="athena.test",
        title="待审事实",
    )
    item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="athena.test",
        candidate=ProposalCandidateFactCreate(
            project_id=project_id,
            project_profile_version_id=profile.id,
            profile_version=profile.version,
            claim_id=claim_id,
            chapter_index=1,
            subject_ref=subject_ref,
            predicate=predicate,
            object_ref_or_value="雾港调查者",
            claim_layer="truth",
            evidence_refs=["chapter:1"],
            authority_type=DERIVED,
            confidence=0.9,
            contract_version=profile.contract_version,
        ),
    )
    db_session.commit()
    return item


def _seed_confirmed_world_fact(
    db_session,
    *,
    project_id: str,
    claim_id: str,
    subject_ref: str,
    predicate: str,
    object_ref_or_value,
    chapter_index: int | None = None,
) -> WorldFactClaim:
    profile = db_session.query(ProjectProfileVersion).filter_by(project_id=project_id).one()
    claim = WorldFactClaim(
        project_id=project_id,
        project_profile_version_id=profile.id,
        profile_version=profile.version,
        claim_id=claim_id,
        chapter_index=chapter_index,
        subject_ref=subject_ref,
        predicate=predicate,
        object_ref_or_value=object_ref_or_value,
        claim_layer="truth",
        claim_status="confirmed",
        evidence_refs=[f"chapter:{chapter_index}"] if chapter_index is not None else [],
        authority_type=DERIVED,
        confidence=1.0,
        contract_version=profile.contract_version,
    )
    db_session.add(claim)
    db_session.commit()
    return claim


def _prepare_longform_batch_execution_contract(client, project_id: str) -> dict:
    preview_response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "准备把下一章加入批次队列",
            "tools": [
                {
                    "tool_name": "enqueue_longform_chapter_batch",
                    "params": {"start_chapter": 2, "batch_size": 1},
                }
            ],
        },
    )
    plan_hash = preview_response.json()["steps"][0]["output"]["plan_hash"]
    enqueue_response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "确认加入批次队列",
            "tools": [
                {
                    "tool_name": "enqueue_longform_chapter_batch",
                    "params": {
                        "start_chapter": 2,
                        "batch_size": 1,
                        "confirm_enqueue": True,
                        "plan_hash": plan_hash,
                    },
                }
            ],
        },
    )
    task_id = enqueue_response.json()["steps"][0]["output"]["task"]["id"]
    client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "预检长篇批次任务",
            "tools": [
                {
                    "tool_name": "execute_longform_chapter_batch_preflight",
                    "params": {"task_id": task_id, "max_chapters": 1, "confirm_checkpoint": True},
                }
            ],
        },
    )
    prepare_response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "准备长篇批次执行契约",
            "tools": [
                {
                    "tool_name": "prepare_longform_chapter_batch_execution",
                    "params": {"task_id": task_id, "confirm_prepare": True},
                }
            ],
        },
    )
    output = prepare_response.json()["steps"][0]["output"]
    return {
        "task_id": task_id,
        "attempt_manifest_hash": output["attempt_manifest_hash"],
        "approval_contract_hash": output["approval_contract_hash"],
        "attempt_manifest": output["attempt_manifest"],
        "approval_contract": output["approval_contract"],
        "agent_plan": output["agent_plan"],
        "agent_plan_approval_contract": output["agent_plan_approval_contract"],
        "agent_plan_approval_contract_hash": output["agent_plan_approval_contract_hash"],
    }


def _execute_approved_longform_batch_chapter(client, project_id: str, prepared: dict, monkeypatch) -> dict:
    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        assert action_type == "generate_chapter"
        assert action_params == {"chapter_index": 2}
        self.db.add(
            ChapterContent(
                project_id=project_id,
                chapter_index=2,
                title="雾港线索2",
                content="林深和苏晚晴追入记忆诊所后巷，发现雾晶核心的回声正在扩大。",
                word_count=2200,
                status="generated",
            )
        )
        self.db.commit()
        return {"status": "success", "chapter_index": 2, "trace_id": "trace-batch-chapter-2"}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)
    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "执行已批准的长篇批次",
            "tools": [
                {
                    "tool_name": "execute_longform_chapter_batch",
                    "params": {
                        "task_id": prepared["task_id"],
                        "confirm_execute": True,
                        "attempt_manifest_hash": prepared["attempt_manifest_hash"],
                        "approval_contract_hash": prepared["approval_contract_hash"],
                    },
                }
            ],
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    return response.json()["steps"][0]["output"]


def _review_executed_longform_batch_chapter(
    client,
    project_id: str,
    task_id: str,
    monkeypatch,
    *,
    status: str,
) -> dict:
    def fake_quality(db, project_id: str, chapter_index: int):
        if status == "needs_revision":
            return {
                "status": "blocked",
                "chapter_index": chapter_index,
                "finding_count": 1,
                "blocker_count": 1,
                "findings": [
                    {
                        "code": "generic_chapter_title",
                        "severity": "blocker",
                        "message": "标题仍是占位标题。",
                        "evidence": {},
                    }
                ],
                "recommended_actions": ["revise_chapter"],
            }
        return {
            "status": "ready",
            "chapter_index": chapter_index,
            "finding_count": 0,
            "blocker_count": 0,
            "findings": [],
            "recommended_actions": [],
        }

    def fake_continuity(db, project_id: str, chapter_index: int, *, lookback: int):
        return {
            "status": "ready",
            "chapter_index": chapter_index,
            "finding_count": 0,
            "blocker_count": 0,
            "findings": [],
            "recommended_actions": [],
        }

    def fake_world_model(db, project_id: str, chapter_index: int):
        return {"status": "skipped", "reason": "missing_world_model_profile", "chapter_index": chapter_index}

    monkeypatch.setattr("app.core.chapter_quality_review.review_chapter_quality", fake_quality)
    monkeypatch.setattr("app.core.chapter_continuity_review.review_chapter_continuity", fake_continuity)
    monkeypatch.setattr("app.core.athena_longform.analyze_chapter_to_world_proposals", fake_world_model)
    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "审查已执行的长篇批次",
            "tools": [
                {
                    "tool_name": "review_longform_chapter_batch_execution",
                    "params": {"task_id": task_id, "confirm_review": True},
                }
            ],
        },
    )
    assert response.status_code == 200
    expected_status = "blocked" if status == "needs_revision" else "success"
    assert response.json()["status"] == expected_status
    return response.json()["steps"][0]["output"]


def _seed_longform_project(db_session, *, outline_chapters: list[int], generated_chapters: list[int]) -> Project:
    project = Project(
        name="Preflight Novel",
        genre="都市悬疑",
        target_chapter_count=600,
        target_word_count=1200000,
    )
    db_session.add(project)
    db_session.flush()
    setup = Setup(
        project_id=project.id,
        status="generated",
        world_building={
            "background": "雾港被记忆异常和雾晶实验影响。",
            "geography": "故事发生在‘雾港’和‘旧灯塔’，地下实验室藏有‘雾晶核心’。",
            "society": "‘雾安局’控制异常档案，‘记忆诊所’收容失忆者。",
            "rules": "雾晶只能放大记忆回声，不能凭空创造真实记忆。",
        },
        characters=[
            {
                "name": "林深",
                "personality": "冷静",
                "background": "私家侦探",
                "goals": "查清十年前雾灾真相",
                "character_status": "alive",
            },
            {
                "name": "苏晚晴",
                "personality": "敏锐",
                "background": "失踪者家属",
                "goals": "找到父亲",
                "character_status": "alive",
            },
        ],
        core_concept={"theme": "记忆与真相", "hook": "雾港会回放被删除的记忆"},
    )
    db_session.add(setup)
    db_session.add(
        Storyline(
            project_id=project.id,
            status="generated",
            plotlines=[{"name": "主线", "type": "main", "summary": "追查雾港记忆异常", "milestones": []}],
            foreshadowing=[],
        )
    )
    outline = Outline(
        project_id=project.id,
        total_chapters=600,
        status="generated",
        chapters=[
            {
                "chapter_index": index,
                "title": f"雾港线索{index}",
                "summary": f"第{index}章推进雾港记忆异常调查。",
                "scenes": ["调查现场", "冲突升级"],
                "characters": ["林深", "苏晚晴"],
                "purpose": "推进主线",
            }
            for index in outline_chapters
        ],
        plotlines=[],
        foreshadowing=[],
    )
    db_session.add(outline)
    for index in generated_chapters:
        db_session.add(
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"雾港线索{index}",
                content=f"林深和苏晚晴在雾港旧灯塔调查雾晶核心。第{index}章里，雾安局巡逻队逼近，记忆诊所留下新的证词。",
                word_count=80,
                status="generated",
            )
        )
    db_session.commit()
    db_session.refresh(project)
    return project


def _seed_activation_memories(db_session, project_id: str) -> None:
    db_session.add_all(
        [
            LongformMemory(
                project_id=project_id,
                memory_type="global",
                scope_key="global",
                start_chapter_index=1,
                end_chapter_index=2,
                title="全书记忆",
                summary="林深收到空白信，苏晚晴确认雾晶会造成记忆代价。",
                status="current",
            ),
            LongformMemory(
                project_id=project_id,
                memory_type="chapter",
                scope_key="chapter:1",
                start_chapter_index=1,
                end_chapter_index=1,
                title="空白信",
                summary="空白信遇水显出黑潮门坐标。",
                status="current",
            ),
            LongformMemory(
                project_id=project_id,
                memory_type="chapter",
                scope_key="chapter:2",
                start_chapter_index=2,
                end_chapter_index=2,
                title="雾晶代价",
                summary="雾晶会吞掉短期记忆。",
                status="current",
            ),
            LongformMemory(
                project_id=project_id,
                memory_type="chapter",
                scope_key="chapter:4",
                start_chapter_index=4,
                end_chapter_index=4,
                title="未来地点",
                summary="潮下车站是未来章节才揭示的地点。",
                status="current",
            ),
        ]
    )
    storyline = db_session.query(Storyline).filter(Storyline.project_id == project_id).first()
    storyline.foreshadowing = [
        {
            "title": "空白信来源",
            "summary": "空白信来自黑潮门内部。",
            "introduced_chapter": 1,
            "expected_resolution_chapter": 5,
            "status": "open",
        },
        {
            "title": "潮下车站",
            "summary": "未来地点，不应提前泄漏。",
            "introduced_chapter": 4,
            "expected_resolution_chapter": 8,
            "status": "open",
        },
    ]
    db_session.commit()
