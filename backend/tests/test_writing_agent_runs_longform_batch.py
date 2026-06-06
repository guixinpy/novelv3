from app.models import BackgroundTask, ChapterContent
from test_support.writing_agent_run_helpers import (
    enqueue_longform_batch_with_approval,
    preflight_longform_batch_with_approval,
    prepare_enqueue_longform_batch,
    seed_longform_project,
)


def test_agent_run_can_plan_longform_chapter_batch(client, db_session):
    project = seed_longform_project(db_session, outline_chapters=[1, 2, 3], generated_chapters=[1])

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
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])

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
    project = seed_longform_project(db_session, outline_chapters=[1, 2, 3], generated_chapters=[1])

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "准备把接下来两章加入批次队列",
            "tools": [
                {
                    "tool_name": "prepare_enqueue_longform_chapter_batch",
                    "params": {"start_chapter": 2, "batch_size": 2},
                }
            ],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["steps"][0]["target_type"] == "background_task_enqueue_approval"
    assert output["status"] == "approval_required"
    assert output["plan_hash"]
    assert output["required_confirmation"] == {
        "confirm_execute": True,
        "approval_contract_hash": output["agent_plan_approval_contract_hash"],
    }
    preview = output["enqueue_preview"]
    assert preview["preview_only"] is True
    assert preview["can_enqueue"] is True
    assert preview["batch"]["chapter_indexes"] == [2, 3]
    assert preview["queue_policy"]["starts_runner"] is False
    assert db_session.query(BackgroundTask).filter(BackgroundTask.project_id == project.id).count() == 0


def test_agent_run_rejects_longform_chapter_batch_enqueue_approval_hash_mismatch(client, db_session):
    project = seed_longform_project(db_session, outline_chapters=[1, 2, 3], generated_chapters=[1])
    prepared = prepare_enqueue_longform_batch(client, project.id, start_chapter=2, batch_size=2)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "尝试执行过期批次计划",
            "tools": [
                {
                    "tool_name": "execute_enqueue_longform_chapter_batch_with_approval",
                    "params": {
                        "start_chapter": 2,
                        "batch_size": 2,
                        "plan_hash": prepared["plan_hash"],
                        "confirm_execute": True,
                        "approval_contract_hash": "stale",
                        "approval_contract": prepared["agent_plan_approval_contract"],
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
    assert output["reason"] == "approval_contract_hash_mismatch"
    assert db_session.query(BackgroundTask).filter(BackgroundTask.project_id == project.id).count() == 0


def test_agent_run_confirms_longform_chapter_batch_enqueue(client, db_session):
    project = seed_longform_project(db_session, outline_chapters=[1, 2, 3], generated_chapters=[1])
    prepared = prepare_enqueue_longform_batch(client, project.id, start_chapter=2, batch_size=2)
    plan_hash = prepared["plan_hash"]

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "确认加入批次队列",
            "tools": [
                {
                    "tool_name": "execute_enqueue_longform_chapter_batch_with_approval",
                    "params": {
                        "start_chapter": 2,
                        "batch_size": 2,
                        "confirm_execute": True,
                        "plan_hash": plan_hash,
                        "approval_contract_hash": prepared["agent_plan_approval_contract_hash"],
                        "approval_contract": prepared["agent_plan_approval_contract"],
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
                    "tool_name": "execute_enqueue_longform_chapter_batch_with_approval",
                    "params": {
                        "start_chapter": 2,
                        "batch_size": 2,
                        "confirm_execute": True,
                        "plan_hash": plan_hash,
                        "approval_contract_hash": prepared["agent_plan_approval_contract_hash"],
                        "approval_contract": prepared["agent_plan_approval_contract"],
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
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])

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
                    "tool_name": "prepare_enqueue_longform_chapter_batch",
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
    assert output["can_enqueue"] is False
    assert output["recommended_next_tools"] == ["plan_recovery_tools"]
    assert db_session.query(BackgroundTask).filter(BackgroundTask.project_id == project.id).count() == 0


def test_agent_run_inspects_longform_chapter_batch_queue(client, db_session):
    project = seed_longform_project(db_session, outline_chapters=[1, 2, 3], generated_chapters=[1])
    enqueue_output = enqueue_longform_batch_with_approval(client, project.id, start_chapter=2, batch_size=2)
    plan_hash = enqueue_output["plan_hash"]
    task_id = enqueue_output["task"]["id"]

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
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])

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
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    enqueue_output = enqueue_longform_batch_with_approval(client, project.id, start_chapter=2, batch_size=1)
    task_id = enqueue_output["task"]["id"]

    payload = preflight_longform_batch_with_approval(client, project.id, task_id, max_chapters=1)
    output = payload["steps"][0]["output"]
    task = db_session.query(BackgroundTask).filter(BackgroundTask.id == task_id).one()
    assert payload["status"] == "success"
    assert payload["steps"][0]["target_type"] == "background_task_checkpoint"
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


def test_agent_run_preflight_longform_chapter_batch_requires_agent_approval(client, db_session):
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    enqueue_output = enqueue_longform_batch_with_approval(client, project.id, start_chapter=2, batch_size=1)
    task_id = enqueue_output["task"]["id"]

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
    assert output["reason"] == "approval_required_before_write"
    assert output["required_approval"]["prepare_tool"] == "prepare_longform_chapter_batch_preflight"
    assert output["required_approval"]["execute_tool"] == "execute_longform_chapter_batch_preflight_with_approval"
    assert output["side_effects"]["executed"] == []
    assert "preflight_checkpoint" not in (task.result or {})
    assert (
        db_session.query(ChapterContent)
        .filter(ChapterContent.project_id == project.id, ChapterContent.chapter_index == 2)
        .count()
        == 0
    )


def test_agent_run_preflight_longform_chapter_batch_blocks_on_dependencies(client, db_session):
    project = seed_longform_project(db_session, outline_chapters=[1, 2, 3], generated_chapters=[1])
    enqueue_output = enqueue_longform_batch_with_approval(client, project.id, start_chapter=3, batch_size=1)
    task_id = enqueue_output["task"]["id"]

    payload = preflight_longform_batch_with_approval(client, project.id, task_id, max_chapters=1)
    output = payload["steps"][0]["output"]
    task = db_session.query(BackgroundTask).filter(BackgroundTask.id == task_id).one()
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


def test_agent_run_can_prepare_longform_chapter_batch_execution_manifest_with_approval(client, db_session):
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    enqueue_output = enqueue_longform_batch_with_approval(client, project.id, start_chapter=2, batch_size=1)
    plan_hash = enqueue_output["plan_hash"]
    task_id = enqueue_output["task"]["id"]
    preflight_longform_batch_with_approval(client, project.id, task_id, max_chapters=1)

    prepare_response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "准备长篇批次执行准备审批契约",
            "tools": [
                {
                    "tool_name": "prepare_longform_chapter_batch_execution_prepare",
                    "params": {"task_id": task_id},
                }
            ],
        },
    )

    prepare_payload = prepare_response.json()
    prepare_output = prepare_payload["steps"][0]["output"]
    task = db_session.query(BackgroundTask).filter(BackgroundTask.id == task_id).one()
    assert prepare_response.status_code == 200
    assert prepare_payload["status"] == "success"
    assert prepare_payload["steps"][0]["target_type"] == "background_task_execution_prepare_approval"
    assert prepare_output["status"] == "approval_required"
    assert prepare_output["task"]["id"] == task_id
    assert prepare_output["execution_prepare_preview"]["reason"] == "prepare_confirmation_required"
    assert prepare_output["recommended_next_tools"] == ["execute_longform_chapter_batch_execution_prepare_with_approval"]
    assert "attempt_manifest" not in (task.result or {})
    assert "approval_contract" not in (task.result or {})

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "确认后写入长篇批次执行契约",
            "tools": [
                {
                    "tool_name": "execute_longform_chapter_batch_execution_prepare_with_approval",
                    "params": {
                        "task_id": task_id,
                        "confirm_execute": True,
                        "approval_contract_hash": prepare_output["agent_plan_approval_contract_hash"],
                        "approval_contract": prepare_output["agent_plan_approval_contract"],
                    },
                }
            ],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    db_session.refresh(task)
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["steps"][0]["target_type"] == "background_task_execution_prepare"
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
    assert output["agent_plan_approval_verification"]["status"] == "ready"
    assert output["execution_resource_binding"]["status"] == "ready"
    assert output["evidence"]["agent_plan_approval_verified"] is True
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


def test_agent_run_prepare_longform_chapter_batch_execution_redirects_to_approval_chain(client, db_session):
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    enqueue_output = enqueue_longform_batch_with_approval(client, project.id, start_chapter=2, batch_size=1)
    task_id = enqueue_output["task"]["id"]
    preflight_longform_batch_with_approval(client, project.id, task_id, max_chapters=1)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "直接准备长篇批次执行契约应重定向到审批链",
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
    assert payload["status"] == "blocked"
    assert output["status"] == "blocked"
    assert output["reason"] == "approval_required_before_write"
    assert output["required_approval"] == {
        "prepare_tool": "prepare_longform_chapter_batch_execution_prepare",
        "execute_tool": "execute_longform_chapter_batch_execution_prepare_with_approval",
        "approval_scope": "agent_plan_approval",
    }
    assert output["recommended_next_tools"] == ["prepare_longform_chapter_batch_execution_prepare"]
    assert output["side_effects"]["executed"] == []
    assert "attempt_manifest" not in (task.result or {})
    assert "approval_contract" not in (task.result or {})


def test_agent_run_prepare_longform_chapter_batch_execution_requires_ready_preflight(client, db_session):
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    enqueue_output = enqueue_longform_batch_with_approval(client, project.id, start_chapter=2, batch_size=1)
    task_id = enqueue_output["task"]["id"]

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "尝试跳过预检准备执行",
            "tools": [{"tool_name": "prepare_longform_chapter_batch_execution_prepare", "params": {"task_id": task_id}}],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    task = db_session.query(BackgroundTask).filter(BackgroundTask.id == task_id).one()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert output["status"] == "blocked"
    assert output["reason"] == "missing_ready_preflight_checkpoint"
    assert output["recommended_next_tools"] == ["prepare_longform_chapter_batch_preflight"]
    assert "attempt_manifest" not in (task.result or {})
    assert (
        db_session.query(ChapterContent)
        .filter(ChapterContent.project_id == project.id, ChapterContent.chapter_index == 2)
        .count()
        == 0
    )
