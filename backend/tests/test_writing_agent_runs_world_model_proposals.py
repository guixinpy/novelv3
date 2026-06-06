from app.core.athena_longform import import_setup_to_world_model
from app.models import WorldFactClaim, WorldProposalItem, WorldProposalReview
from test_support.writing_agent_run_helpers import (
    apply_world_model_resolution_with_approval,
    approved_apply_world_model_resolution_tool,
    approved_generate_chapter_tool,
    approved_seed_continuity_anchor_proposals_tool,
    prepare_apply_world_model_resolution,
    seed_longform_project,
    seed_pending_world_proposal,
)


def test_agent_review_world_model_proposals_reports_queue_without_reviewing_items(client, db_session):
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    item = seed_pending_world_proposal(
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
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
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
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    seed_pending_world_proposal(
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
                approved_generate_chapter_tool(db_session, project.id, chapter_index=2),
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
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    high_item = seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase11.agent.status",
        predicate="status",
        subject_ref="char.林深",
    )
    low_item_one = seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase11.agent.mentioned-one",
        predicate="mentioned_in_chapter",
        subject_ref="char.林深",
    )
    low_item_two = seed_pending_world_proposal(
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
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
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
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    seeded_item_ids = []
    for index in range(12):
        item = seed_pending_world_proposal(
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
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase11.agent.high-count",
        predicate="status",
        subject_ref="char.林深",
    )
    seed_pending_world_proposal(
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
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    seed_pending_world_proposal(
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
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    seed_pending_world_proposal(
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
                approved_generate_chapter_tool(db_session, project.id, chapter_index=2),
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
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    approve_item = seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase12.agent.approve",
        predicate="role",
        subject_ref="char.林深",
    )
    reject_item = seed_pending_world_proposal(
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
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])

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
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    valid_item = seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase12.agent.valid",
        predicate="role",
        subject_ref="char.林深",
    )
    unsupported_item = seed_pending_world_proposal(
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
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    item = seed_pending_world_proposal(
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
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
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
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    intake_item = seed_pending_world_proposal(
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
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    item = seed_pending_world_proposal(
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
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    item = seed_pending_world_proposal(
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

def test_agent_apply_world_model_proposal_resolution_allows_confirmed_continuity_anchor_approval(client, db_session):
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={"goal": "seed", "tools": [approved_seed_continuity_anchor_proposals_tool(db_session, project.id)]},
    )
    item = (
        db_session.query(WorldProposalItem)
        .filter_by(project_id=project.id, subject_ref="林深", predicate="father_name")
        .one()
    )

    response = apply_world_model_resolution_with_approval(
        client,
        project.id,
        [
            {
                "proposal_item_id": item.id,
                "action": "approve",
                "reason": "确认父亲姓名锚点",
                "evidence_refs": ["chapter:10", "chapter:11", "chapter:13"],
            }
        ],
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

def test_agent_apply_world_model_proposal_resolution_requires_confirmation_without_writes(client, db_session):
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    item = seed_pending_world_proposal(
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
    assert response.json()["status"] == "blocked"
    assert output["status"] == "blocked"
    assert output["reason"] == "approval_required_before_write"
    assert output["required_approval"] == {
        "prepare_tool": "prepare_apply_world_model_proposal_resolution",
        "execute_tool": "execute_apply_world_model_proposal_resolution_with_approval",
        "approval_scope": "agent_plan_approval",
    }
    assert output["side_effects"]["executed"] == []
    assert stored_item.item_status == "pending"
    assert db_session.query(WorldProposalReview).count() == before_review_count

def test_agent_apply_world_model_proposal_resolution_blocks_missing_profile_without_decisions(client, db_session):
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])

    output = prepare_apply_world_model_resolution(client, project.id, [])
    assert output["status"] == "missing_profile"
    assert output["profile_version"] is None
    assert output["applied_count"] == 0
    assert output["should_generate_next_chapter"] is False
    assert output["recommended_actions"] == ["import_setup_world_model"]

def test_agent_apply_world_model_proposal_resolution_applies_confirmed_non_merge_decisions(client, db_session):
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    reject_item = seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase13.agent.reject",
        predicate="role",
        subject_ref="char.林深",
    )
    uncertain_item = seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase13.agent.uncertain",
        predicate="status",
        subject_ref="char.苏晚晴",
    )
    before_fact_count = db_session.query(WorldFactClaim).count()

    response = apply_world_model_resolution_with_approval(
        client,
        project.id,
        [
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
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    item = seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase13.agent.approve-refused",
        predicate="role",
        subject_ref="char.林深",
    )
    edit_item = seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase13.agent.approve-edits-refused",
        predicate="role",
        subject_ref="char.苏晚晴",
    )
    before_review_count = db_session.query(WorldProposalReview).count()
    before_fact_count = db_session.query(WorldFactClaim).count()

    output = prepare_apply_world_model_resolution(
        client,
        project.id,
        [
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
            },
        ],
    )
    stored_item = db_session.query(WorldProposalItem).filter_by(id=item.id).one()
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
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    valid_item = seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase13.agent.rollback-valid",
        predicate="role",
        subject_ref="char.林深",
    )
    drift_item = seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase13.agent.rollback-drift",
        predicate="status",
        subject_ref="char.苏晚晴",
    )
    drift_item.contract_version = "drifted-contract-version"
    db_session.commit()
    before_review_count = db_session.query(WorldProposalReview).count()

    response = apply_world_model_resolution_with_approval(
        client,
        project.id,
        [
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
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    valid_item = seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase13.agent.valid-batch",
        predicate="role",
        subject_ref="char.林深",
    )
    before_review_count = db_session.query(WorldProposalReview).count()

    output = prepare_apply_world_model_resolution(
        client,
        project.id,
        [
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
    )
    stored_valid_item = db_session.query(WorldProposalItem).filter_by(id=valid_item.id).one()
    assert output["status"] == "blocked"
    assert output["applied_count"] == 0
    assert output["invalid_decision_count"] == 1
    assert output["invalid_decisions"][0]["code"] == "missing_item"
    assert stored_valid_item.item_status == "pending"
    assert db_session.query(WorldProposalReview).count() == before_review_count

def test_agent_preview_world_model_proposal_resolution_allows_apply_followup(client, db_session):
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    item = seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase13.agent.preview-apply",
        predicate="role",
        subject_ref="char.林深",
    )

    decisions = [
        {
            "proposal_item_id": item.id,
            "action": "reject",
            "reason": "预览后确认拒绝",
        }
    ]
    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "先预览再确认应用世界模型提案决策",
            "tools": [
                {
                    "tool_name": "preview_world_model_proposal_resolution",
                    "params": {"decisions": decisions},
                },
                approved_apply_world_model_resolution_tool(client, project.id, decisions),
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert [step["tool_name"] for step in payload["steps"]] == [
        "preview_world_model_proposal_resolution",
        "execute_apply_world_model_proposal_resolution_with_approval",
    ]
    assert payload["steps"][1]["output"]["applied_count"] == 1

def test_agent_apply_world_model_proposal_resolution_blocks_followup_generation_when_queue_remains(
    client,
    db_session,
    monkeypatch,
):
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    item_to_apply = seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase13.agent.apply-one",
        predicate="role",
        subject_ref="char.林深",
    )
    seed_pending_world_proposal(
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

    decisions = [
        {
            "proposal_item_id": item_to_apply.id,
            "action": "reject",
            "reason": "只处理一个，仍有待审项",
        }
    ]
    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "应用部分提案后尝试生成第2章",
            "tools": [
                approved_apply_world_model_resolution_tool(client, project.id, decisions),
                {"tool_name": "generate_chapter", "params": {"chapter_index": 2}},
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert payload["steps"][0]["tool_name"] == "execute_apply_world_model_proposal_resolution_with_approval"
    assert payload["steps"][0]["output"]["after_actionable_items"] == 1
    assert payload["steps"][0]["output"]["should_generate_next_chapter"] is False
    assert len(payload["steps"]) == 1
    assert calls == []

def test_agent_apply_world_model_proposal_resolution_allows_generation_when_queue_clears(
    client,
    db_session,
    monkeypatch,
):
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    item = seed_pending_world_proposal(
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

    decisions = [
        {
            "proposal_item_id": item.id,
            "action": "reject",
            "reason": "清空队列",
        }
    ]
    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "清空提案队列后生成第2章",
            "tools": [
                approved_apply_world_model_resolution_tool(client, project.id, decisions),
                approved_generate_chapter_tool(db_session, project.id, chapter_index=2),
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert [step["tool_name"] for step in payload["steps"]] == [
        "execute_apply_world_model_proposal_resolution_with_approval",
        "execute_generate_chapter_with_approval",
    ]
    assert calls == ["generate_chapter"]

def test_agent_draft_world_model_proposal_resolution_decisions_reports_without_writes(client, db_session):
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    presence_item = seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase14.agent.presence",
        predicate="presence_count",
        subject_ref="char.林深",
    )
    location_item = seed_pending_world_proposal(
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
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    seed_pending_world_proposal(
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
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    seed_pending_world_proposal(
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
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    high_item = seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase82.identifier.hypothesis",
        predicate="identifier_meaning_hypothesis",
        subject_ref="identifier.G-07",
    )
    video_item = seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase84.video.evidence",
        predicate="historical_video_evidence",
        subject_ref="chapter.26.video",
    )
    low_item = seed_pending_world_proposal(
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
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    seed_pending_world_proposal(
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
    project = seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    item = seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase14.agent.chain",
        predicate="presence_count",
        subject_ref="char.林深",
    )

    decisions = [
        {
            "proposal_item_id": item.id,
            "action": "reject",
            "reason": "presence_count 是提取元数据，不进入真相层",
        }
    ]
    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "先草拟再应用世界模型提案决策",
            "tools": [
                {"tool_name": "draft_world_model_proposal_resolution_decisions", "params": {"limit": 20}},
                approved_apply_world_model_resolution_tool(client, project.id, decisions),
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert [step["tool_name"] for step in payload["steps"]] == [
        "draft_world_model_proposal_resolution_decisions",
        "execute_apply_world_model_proposal_resolution_with_approval",
    ]
    assert payload["steps"][1]["output"]["applied_count"] == 1

def test_agent_draft_world_model_proposal_resolution_decisions_blocks_followup_generation(
    client,
    db_session,
    monkeypatch,
):
    project = seed_longform_project(db_session, outline_chapters=[1, 2], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    seed_pending_world_proposal(
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
