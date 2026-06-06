from app.models import BackgroundTask
from test_support.writing_agent_run_helpers import (
    execute_approved_longform_batch_chapter,
    prepare_longform_batch_execution_contract,
    review_executed_longform_batch_chapter,
    route_reviewed_longform_batch_after_review,
    seed_longform_project,
)


def test_agent_run_can_review_longform_chapter_batch_execution(client, db_session, monkeypatch):
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    prepared = prepare_longform_batch_execution_contract(client, project.id)
    execute_approved_longform_batch_chapter(client, project.id, prepared, monkeypatch)
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

    prepare_response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "准备审查已执行的长篇批次",
            "tools": [
                {
                    "tool_name": "prepare_longform_chapter_batch_execution_review",
                    "params": {"task_id": prepared["task_id"], "lookback": 12},
                }
            ],
        },
    )
    prepare_output = prepare_response.json()["steps"][0]["output"]

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "确认后审查已执行的长篇批次",
            "tools": [
                {
                    "tool_name": "execute_longform_chapter_batch_execution_review_with_approval",
                    "params": {
                        "task_id": prepared["task_id"],
                        "lookback": 12,
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
    task = db_session.query(BackgroundTask).filter(BackgroundTask.id == prepared["task_id"]).one()
    assert prepare_response.status_code == 200
    assert prepare_response.json()["status"] == "success"
    assert prepare_response.json()["steps"][0]["target_type"] == "background_task_post_generation_review_approval"
    assert prepare_output["status"] == "approval_required"
    assert prepare_output["review_preview"]["reason"] == "review_confirmation_required"
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["steps"][0]["target_type"] == "background_task_post_generation_review"
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


def test_agent_run_review_longform_chapter_batch_redirects_to_approval_chain(client, db_session, monkeypatch):
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    prepared = prepare_longform_batch_execution_contract(client, project.id)
    execute_approved_longform_batch_chapter(client, project.id, prepared, monkeypatch)
    calls: list[str] = []

    def fake_quality(db, project_id: str, chapter_index: int):
        calls.append("quality")
        return {"status": "ready", "chapter_index": chapter_index, "finding_count": 0, "blocker_count": 0}

    monkeypatch.setattr("app.core.chapter_quality_review.review_chapter_quality", fake_quality)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "直接审查已执行的长篇批次应重定向到审批链",
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
    assert output["reason"] == "approval_required_before_write"
    assert output["required_approval"] == {
        "prepare_tool": "prepare_longform_chapter_batch_execution_review",
        "execute_tool": "execute_longform_chapter_batch_execution_review_with_approval",
        "approval_scope": "agent_plan_approval",
    }
    assert output["recommended_next_tools"] == ["prepare_longform_chapter_batch_execution_review"]
    assert output["side_effects"]["executed"] == []
    assert calls == []
    assert "post_generation_review_result" not in (task.result or {})


def test_agent_run_review_longform_chapter_batch_requires_execution_evidence(client, db_session):
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    prepared = prepare_longform_batch_execution_contract(client, project.id)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "拒绝未执行批次的审查",
            "tools": [
                {
                    "tool_name": "prepare_longform_chapter_batch_execution_review",
                    "params": {"task_id": prepared["task_id"]},
                }
            ],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert output["status"] == "blocked"
    assert output["reason"] == "missing_batch_execution_result"


def test_agent_run_review_longform_chapter_batch_blocks_before_world_model_on_quality_blocker(
    client,
    db_session,
    monkeypatch,
):
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    prepared = prepare_longform_batch_execution_contract(client, project.id)
    execute_approved_longform_batch_chapter(client, project.id, prepared, monkeypatch)
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

    output = review_executed_longform_batch_chapter(
        client,
        project.id,
        prepared["task_id"],
        monkeypatch,
        status="needs_revision",
        calls=calls,
    )
    task = db_session.query(BackgroundTask).filter(BackgroundTask.id == prepared["task_id"]).one()
    assert output["status"] == "blocked"
    assert output["reason"] == "post_generation_review_has_blockers"
    assert output["review_gate"]["status"] == "needs_revision"
    assert output["reviews"]["world_model"]["status"] == "skipped"
    assert output["reviews"]["world_model"]["reason"] == "review_blockers_present"
    assert output["recommended_next_tools"] == ["plan_chapter_revision", "create_revision_draft", "inspect_longform_chapter_batch"]
    assert calls == ["quality", "continuity"]
    assert task.result["post_generation_review_result"]["status"] == "needs_revision"


def test_agent_run_review_longform_chapter_batch_is_idempotent(client, db_session, monkeypatch):
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    prepared = prepare_longform_batch_execution_contract(client, project.id)
    execute_approved_longform_batch_chapter(client, project.id, prepared, monkeypatch)
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

    first_output = review_executed_longform_batch_chapter(
        client,
        project.id,
        prepared["task_id"],
        monkeypatch,
        status="passed",
        calls=calls,
    )
    calls_after_first = list(calls)
    second = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "重复审查",
            "tools": [
                {
                    "tool_name": "prepare_longform_chapter_batch_execution_review",
                    "params": {"task_id": prepared["task_id"]},
                }
            ],
        },
    )

    second_output = second.json()["steps"][0]["output"]
    assert first_output["status"] == "completed"
    assert calls_after_first == ["quality", "continuity", "world_model"]
    assert second.status_code == 200
    assert second.json()["status"] == "success"
    assert second_output["status"] == "skipped"
    assert second_output["reason"] == "post_generation_review_already_recorded"
    assert second_output["post_generation_review_result"]["status"] == "passed"
    assert calls == calls_after_first


def test_agent_run_routes_passed_longform_batch_review_to_next_batch_preview(client, db_session, monkeypatch):
    project = seed_longform_project(db_session, outline_chapters=[1, 2, 3], generated_chapters=[1])
    prepared = prepare_longform_batch_execution_contract(client, project.id)
    execute_approved_longform_batch_chapter(client, project.id, prepared, monkeypatch)
    review_executed_longform_batch_chapter(client, project.id, prepared["task_id"], monkeypatch, status="passed")
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

    payload = route_reviewed_longform_batch_after_review(
        client,
        project.id,
        task_id=prepared["task_id"],
        next_batch_size=1,
    )

    output = payload["steps"][0]["output"]
    task = db_session.query(BackgroundTask).filter(BackgroundTask.id == prepared["task_id"]).one()
    assert payload["status"] == "success"
    assert payload["steps"][0]["target_type"] == "background_task_post_review_route"
    assert output["status"] == "completed"
    assert output["route_decision"]["decision"] == "continue_to_next_batch"
    assert output["route_decision"]["next_chapter_index"] == 3
    assert output["post_generation_route_result"]["next_batch_plan"]["batch"]["chapter_indexes"] == [3]
    assert output["recommended_next_tools"] == ["enqueue_longform_chapter_batch", "inspect_longform_chapter_batch"]
    assert calls == [(3, 1), (3, 1)]
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
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    prepared = prepare_longform_batch_execution_contract(client, project.id)
    execute_approved_longform_batch_chapter(client, project.id, prepared, monkeypatch)
    review_executed_longform_batch_chapter(client, project.id, prepared["task_id"], monkeypatch, status="needs_revision")
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

    payload = route_reviewed_longform_batch_after_review(
        client,
        project.id,
        task_id=prepared["task_id"],
    )

    output = payload["steps"][0]["output"]
    task = db_session.query(BackgroundTask).filter(BackgroundTask.id == prepared["task_id"]).one()
    assert payload["status"] == "success"
    assert payload["steps"][0]["target_type"] == "background_task_post_review_route"
    assert output["status"] == "completed"
    assert output["route_decision"]["decision"] == "stop_for_revision"
    assert output["post_generation_route_result"]["recovery_plan"]["revision_plan"]["revision_actions"][0]["action"] == "retitle_chapter"
    assert output["recommended_next_tools"] == ["plan_chapter_revision", "create_revision_draft", "inspect_longform_chapter_batch"]
    assert calls == [2]
    assert task.result["post_generation_route_result"]["route_decision"]["decision"] == "stop_for_revision"
    assert db_session.query(BackgroundTask).filter(BackgroundTask.project_id == project.id).count() == 1


def test_agent_run_route_longform_chapter_batch_after_review_redirects_to_approval_chain(
    client,
    db_session,
    monkeypatch,
):
    project = seed_longform_project(db_session, outline_chapters=[1, 2, 3], generated_chapters=[1])
    prepared = prepare_longform_batch_execution_contract(client, project.id)
    execute_approved_longform_batch_chapter(client, project.id, prepared, monkeypatch)
    review_executed_longform_batch_chapter(client, project.id, prepared["task_id"], monkeypatch, status="passed")

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "直接路由审查结果应重定向到审批链",
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
    assert payload["status"] == "blocked"
    assert output["status"] == "blocked"
    assert output["reason"] == "approval_required_before_write"
    assert output["required_approval"] == {
        "prepare_tool": "prepare_longform_chapter_batch_after_review_route",
        "execute_tool": "execute_longform_chapter_batch_after_review_route_with_approval",
        "approval_scope": "agent_plan_approval",
    }
    assert output["recommended_next_tools"] == ["prepare_longform_chapter_batch_after_review_route"]
    assert output["side_effects"]["executed"] == []
    assert "post_generation_route_result" not in (task.result or {})


def test_agent_run_post_review_routing_requires_phase63_review(client, db_session, monkeypatch):
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    prepared = prepare_longform_batch_execution_contract(client, project.id)
    execute_approved_longform_batch_chapter(client, project.id, prepared, monkeypatch)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "缺少审查结果时拒绝路由",
            "tools": [
                {
                    "tool_name": "prepare_longform_chapter_batch_after_review_route",
                    "params": {"task_id": prepared["task_id"]},
                }
            ],
        },
    )

    payload = response.json()
    output = payload["steps"][0]["output"]
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert output["status"] == "blocked"
    assert output["reason"] == "missing_post_generation_review_result"


def test_agent_run_post_review_routing_blocks_review_hash_mismatch(client, db_session, monkeypatch):
    project = seed_longform_project(db_session, outline_chapters=[1, 2, 3], generated_chapters=[1])
    prepared = prepare_longform_batch_execution_contract(client, project.id)
    execute_approved_longform_batch_chapter(client, project.id, prepared, monkeypatch)
    review_executed_longform_batch_chapter(client, project.id, prepared["task_id"], monkeypatch, status="passed")

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "拒绝过期审查哈希",
            "tools": [
                {
                    "tool_name": "prepare_longform_chapter_batch_after_review_route",
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
    assert payload["status"] == "success"
    assert output["status"] == "blocked"
    assert output["reason"] == "post_generation_review_hash_mismatch"


def test_agent_run_post_review_routing_is_idempotent(client, db_session, monkeypatch):
    project = seed_longform_project(db_session, outline_chapters=[1, 2, 3], generated_chapters=[1])
    prepared = prepare_longform_batch_execution_contract(client, project.id)
    execute_approved_longform_batch_chapter(client, project.id, prepared, monkeypatch)
    review_executed_longform_batch_chapter(client, project.id, prepared["task_id"], monkeypatch, status="passed")
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

    first = route_reviewed_longform_batch_after_review(client, project.id, task_id=prepared["task_id"])
    second = route_reviewed_longform_batch_after_review(client, project.id, task_id=prepared["task_id"])

    output = second["steps"][0]["output"]
    assert first["status"] == "success"
    assert second["status"] == "success"
    assert output["status"] == "skipped"
    assert output["reason"] == "post_generation_route_already_recorded"
    assert output["post_generation_route_result"]["route_decision"]["decision"] == "continue_to_next_batch"
    assert calls == [3, 3]
