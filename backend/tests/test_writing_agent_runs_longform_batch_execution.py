from app.models import BackgroundTask, ChapterContent, WritingAgentStep
from test_support.writing_agent_run_helpers import (
    prepare_longform_batch_execution_contract,
    seed_longform_project,
)


def test_agent_run_can_execute_approved_longform_chapter_batch_once(client, db_session, monkeypatch):
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    prepared = prepare_longform_batch_execution_contract(client, project.id)
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
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    prepared = prepare_longform_batch_execution_contract(client, project.id)
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
    assert continuation["recovery"]["next_tool"] == "prepare_longform_chapter_batch_execution_prepare"
    assert continuation["recovery"]["next_params"] == {"task_id": prepared["task_id"]}
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
    assert recovery_output["tools"][0]["tool_name"] == "prepare_longform_chapter_batch_execution_prepare"
    assert recovery_output["tools"][0]["params"] == {"task_id": prepared["task_id"]}
    assert recovery_output["execution_policy"]["safe_auto_execute"] is False


def test_agent_run_execute_longform_chapter_batch_recovers_missing_resource_binding(client, db_session, monkeypatch):
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    prepared = prepare_longform_batch_execution_contract(client, project.id)
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
    assert continuation["recovery"]["next_tool"] == "prepare_longform_chapter_batch_execution_prepare"
    assert continuation["recovery"]["next_params"] == {"task_id": prepared["task_id"]}
    assert calls == []


def test_agent_run_auto_plan_executes_binding_recovery_prepare_only_after_hash_confirmation(
    client,
    db_session,
    monkeypatch,
):
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    prepared = prepare_longform_batch_execution_contract(client, project.id)
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
    assert preview_output["tools"][0]["tool_name"] == "prepare_longform_chapter_batch_execution_prepare"
    assert preview_output["execution_policy"]["safe_auto_execute"] is False
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["input"]["planner"]["mode"] == "execute"
    assert payload["input"]["planner"]["plan_hash"] == plan_hash
    assert payload["input"]["tools"][0]["tool_name"] == "prepare_longform_chapter_batch_execution_prepare"
    assert [step["tool_name"] for step in payload["steps"]] == ["prepare_longform_chapter_batch_execution_prepare"]
    assert output["status"] == "approval_required"
    assert output["task"]["id"] == prepared["task_id"]
    assert output["side_effects"]["skipped"] == ["background_task_result_execution_prepare"]
    assert calls == []
    assert (
        db_session.query(ChapterContent)
        .filter(ChapterContent.project_id == project.id, ChapterContent.chapter_index == 2)
        .count()
        == 0
    )


def test_agent_run_execute_longform_chapter_batch_requires_confirmation(client, db_session):
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    prepared = prepare_longform_batch_execution_contract(client, project.id)

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
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    prepared = prepare_longform_batch_execution_contract(client, project.id)

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
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    prepared = prepare_longform_batch_execution_contract(client, project.id)
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
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    prepared = prepare_longform_batch_execution_contract(client, project.id)
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
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    prepared = prepare_longform_batch_execution_contract(client, project.id)
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
