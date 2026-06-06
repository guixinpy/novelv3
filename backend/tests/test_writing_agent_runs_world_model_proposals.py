from app.core.athena_longform import import_setup_to_world_model
from app.models import WorldFactClaim, WorldProposalItem, WorldProposalReview
from test_support.writing_agent_run_helpers import (
    approved_generate_chapter_tool,
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
