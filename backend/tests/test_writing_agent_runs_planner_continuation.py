from app.core.athena_longform import import_setup_to_world_model
from app.models import WorldProposalItem, WorldProposalReview
from test_support.writing_agent_run_helpers import (
    planner_generate_chapter_plan,
    planner_revision_patch_plan,
    planner_world_model_resolution_plan,
    prepare_apply_world_model_resolution,
    seed_longform_project,
    seed_pending_world_proposal,
)


def create_project(client, name: str) -> str:
    response = client.post("/api/v1/projects", json={"name": name})
    assert response.status_code == 200
    return response.json()["id"]


def test_planner_continuation_blocks_unapproved_write_tools(client):
    project_id = create_project(client, "Planner Continuation Guard")

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
    project_id = create_project(client, "Planner Continuation Read Guard")
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
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    calls = []

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append((action_type, project_id, command_args, action_params))
        return {"status": "success", "chapter_index": 2, "trace_id": "trace-generated-2"}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)
    plan = planner_generate_chapter_plan(db_session, project.id, chapter_index=2)
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
    assert step["tool_name"] == "execute_generate_chapter_with_approval"
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


def test_planner_continuation_executes_prepared_generate_chapter_contract(
    client,
    db_session,
    monkeypatch,
):
    from app.services.writing_agent.chapter_generation_execution import prepare_generate_chapter_execution

    project = seed_longform_project(db_session, outline_chapters=[1, 2, 3], generated_chapters=[1, 2])
    calls = []

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append((action_type, project_id, command_args, action_params))
        return {"status": "success", "chapter_index": 3, "trace_id": "trace-generated-3"}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)
    prepared = prepare_generate_chapter_execution(db_session, project.id, chapter_index=3)
    approval_hash = prepared["agent_plan_approval_contract_hash"]
    approval_contract = prepared["agent_plan_approval_contract"]
    agent_plan = prepared["agent_plan"]
    plan_id = agent_plan["trace"]["plan_id"]
    params = {
        **agent_plan["steps"][0]["params"],
        "confirm_execute": True,
        "approval_contract_hash": approval_hash,
        "approval_contract": approval_contract,
    }

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "执行已审批工具：生成正文",
            "entrypoint": "ui_planner_continuation_execute",
            "tools": [
                {
                    "tool_name": "execute_generate_chapter_with_approval",
                    "params": params,
                    "planner": {
                        "plan_id": plan_id,
                        "planner_version": prepared["prepare_version"],
                        "mutability": "write",
                        "requires_confirmation": True,
                        "reason": "确认执行已准备的写入工具。",
                    },
                }
            ],
            "input": {
                "planner_continuation": True,
                "source_run_id": "run-followup-exec",
                "source_plan_id": plan_id,
                "confirm_execute": True,
                "approval_contract_hash": approval_hash,
                "approval_contract": approval_contract,
                "planner": {
                    **agent_plan,
                    "approval_contract": approval_contract,
                },
            },
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "success"
    step = payload["steps"][0]
    assert step["tool_name"] == "execute_generate_chapter_with_approval"
    assert step["status"] == "success"
    assert step["output"]["planner_continuation_approval"]["approval_contract_hash"] == approval_hash
    assert step["output"]["agent_plan_approval_verification"]["status"] == "ready"
    assert calls
    action_type, called_project_id, command_args, action_params = calls[0]
    assert action_type == "generate_chapter"
    assert called_project_id == project.id
    assert "上一章状态卡" in command_args
    assert action_params == {"chapter_index": 3}


def test_planner_continuation_blocks_write_tool_on_approval_hash_mismatch(client, db_session, monkeypatch):
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    calls = []

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append(action_type)
        return {"status": "success", "chapter_index": 2}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)
    plan = planner_generate_chapter_plan(db_session, project.id, chapter_index=2)

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
    assert step["tool_name"] == "execute_generate_chapter_with_approval"
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
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
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
        "app.services.writing_agent.revision_patch_execution.apply_planner_revision_patch_tool",
        fake_apply_revision_patch,
    )
    plan = planner_revision_patch_plan(db_session, project.id, chapter_index=1, revision_id="revision-1")
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
    assert step["tool_name"] == "execute_apply_planner_revision_patch_with_approval"
    assert step["status"] == "success"
    assert step["output"]["planner_continuation_approval"]["approval_contract_hash"] == approval_hash
    assert step["output"]["agent_plan_approval_verification"]["status"] == "ready"
    assert calls == [(project.id, 1, "revision-1")]


def test_planner_continuation_blocks_revision_patch_when_mutation_fingerprint_missing_target(
    client,
    db_session,
    monkeypatch,
):
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    calls = []

    def fake_apply_revision_patch(db, project_id, chapter_index, *, revision_id=None):
        calls.append((project_id, chapter_index, revision_id))
        return {"status": "success", "chapter_index": chapter_index}

    monkeypatch.setattr(
        "app.services.writing_agent.revision_patch_execution.apply_planner_revision_patch_tool",
        fake_apply_revision_patch,
    )
    plan = planner_revision_patch_plan(db_session, project.id, chapter_index=1, revision_id="")
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
    assert step["tool_name"] == "execute_apply_planner_revision_patch_with_approval"
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
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    item = seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.planner.world-model.approved",
        predicate="role",
        subject_ref="char.林深",
    )
    decisions = [{"proposal_item_id": item.id, "action": "reject", "reason": "规划审批后拒绝错误事实"}]
    apply_approval = prepare_apply_world_model_resolution(client, project.id, decisions)
    plan = planner_world_model_resolution_plan(project.id, decisions=decisions, apply_approval=apply_approval)
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
    assert step["tool_name"] == "execute_apply_world_model_proposal_resolution_with_approval"
    assert step["status"] == "success"
    assert step["output"]["applied_count"] == 1
    assert step["output"]["planner_continuation_approval"]["approval_contract_hash"] == approval_hash
    assert stored_item.item_status == "rejected"
    assert [review.review_action for review in reviews] == ["reject"]


def test_planner_continuation_blocks_world_model_resolution_on_approval_hash_mismatch(client, db_session):
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    item = seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.planner.world-model.drift",
        predicate="role",
        subject_ref="char.林深",
    )
    decisions = [{"proposal_item_id": item.id, "action": "reject", "reason": "漂移审批不应执行"}]
    apply_approval = prepare_apply_world_model_resolution(client, project.id, decisions)
    plan = planner_world_model_resolution_plan(project.id, decisions=decisions, apply_approval=apply_approval)
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
    assert step["tool_name"] == "execute_apply_world_model_proposal_resolution_with_approval"
    assert step["status"] == "blocked"
    output = step["output"]
    assert output["approval_verification"]["reason"] == "approval_contract_hash_mismatch"
    assert stored_item.item_status == "pending"
    assert db_session.query(WorldProposalReview).count() == before_review_count


def test_planner_continuation_blocks_world_model_resolution_when_mutation_fingerprint_missing_target(
    client,
    db_session,
):
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    before_review_count = db_session.query(WorldProposalReview).count()
    plan = planner_world_model_resolution_plan(project.id, decisions=[])
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
