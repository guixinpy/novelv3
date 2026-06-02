import json

from app.services.writing_agent.tool_recommendations import normalize_tool_recommendations


def test_normalize_tool_recommendations_keeps_tool_followups_and_non_tool_actions_separate():
    result = normalize_tool_recommendations(
        "generate_chapter",
        {
            "recommended_next_tools": ["review_chapter_quality", "review_chapter_quality"],
            "recommended_actions": ["revise_chapter", "apply_world_model_proposal_resolution"],
        },
        allowed_tools={"review_chapter_quality", "apply_world_model_proposal_resolution"},
    )

    assert result["source_fields"] == ["recommended_next_tools", "recommended_actions"]
    assert result["raw_recommendations"] == [
        "review_chapter_quality",
        "revise_chapter",
        "apply_world_model_proposal_resolution",
    ]
    assert result["runtime_followups"] == ["review_chapter_quality", "apply_world_model_proposal_resolution"]
    assert result["non_tool_recommendations"] == ["revise_chapter"]
    assert result["policy_followups"] == []
    assert result["canonical_followups"] == ["review_chapter_quality", "apply_world_model_proposal_resolution"]


def test_normalize_tool_recommendations_merges_policy_followups_once():
    result = normalize_tool_recommendations(
        "seed_continuity_anchor_proposals",
        {"recommended_actions": ["apply_world_model_proposal_resolution"]},
        allowed_tools={"apply_world_model_proposal_resolution"},
    )

    assert result["source_fields"] == ["recommended_actions"]
    assert result["runtime_followups"] == ["apply_world_model_proposal_resolution"]
    assert result["policy_followups"] == ["apply_world_model_proposal_resolution"]
    assert result["canonical_followups"] == ["apply_world_model_proposal_resolution"]


def test_normalize_tool_recommendations_extracts_structured_action_tool_names():
    result = normalize_tool_recommendations(
        "inspect_agent_trace_audit",
        {
            "recommended_actions": [
                {"tool_name": "inspect_agent_memory_route", "reason_code": "no_matching_run"},
                {"tool_name": "plan_recovery_tools", "reason_code": "agent_run_blocked"},
                {"action": "revise_chapter"},
                {"tool_name": "inspect_agent_memory_route"},
            ]
        },
        allowed_tools={"inspect_agent_memory_route", "plan_recovery_tools"},
    )

    assert result["source_fields"] == ["recommended_actions"]
    assert result["raw_recommendations"] == [
        "inspect_agent_memory_route",
        "plan_recovery_tools",
        "revise_chapter",
    ]
    assert result["runtime_followups"] == ["inspect_agent_memory_route", "plan_recovery_tools"]
    assert result["non_tool_recommendations"] == ["revise_chapter"]
    assert result["canonical_followups"] == ["inspect_agent_memory_route", "plan_recovery_tools"]
    json.dumps(result, ensure_ascii=False)


def test_normalize_tool_recommendations_separates_provenance_read_and_write_tools():
    result = normalize_tool_recommendations(
        "inspect_agent_memory_route",
        {
            "memory_provenance": {
                "recovery": {
                    "next_tools": ["inspect_agent_memory_route", "prepare_repair_longform_maintenance"],
                    "tools": [
                        {
                            "tool_name": "inspect_agent_memory_route",
                            "params": {
                                "chapter_index": 13,
                                "query": "检索索引为空，诊断第13章长篇记忆与检索覆盖。",
                                "include_context_summary": False,
                            },
                        }
                    ],
                    "write_tools": [{"tool_name": "prepare_repair_longform_maintenance", "params": {}}],
                }
            }
        },
        allowed_tools={"inspect_agent_memory_route", "prepare_repair_longform_maintenance"},
    )

    assert result["source_fields"] == [
        "memory_provenance.recovery.tools",
        "memory_provenance.recovery.write_tools",
    ]
    assert result["runtime_followups"] == ["inspect_agent_memory_route"]
    assert result["canonical_followups"] == ["inspect_agent_memory_route"]
    assert result["provenance_recovery_tools"] == [
        {
            "tool_name": "inspect_agent_memory_route",
            "params": {
                "chapter_index": 13,
                "query": "检索索引为空，诊断第13章长篇记忆与检索覆盖。",
                "include_context_summary": False,
            },
        }
    ]
    assert result["provenance_write_tools"] == [{"tool_name": "prepare_repair_longform_maintenance", "params": {}}]


def test_normalize_tool_recommendations_preserves_confirmation_required_tool_calls_for_audit():
    execute_call = {
        "tool_name": "execute_apply_pending_action_route_approval_opt_in_with_approval",
        "visibility": "agent_internal",
        "requires_confirmation": True,
        "params": {
            "pending_action_id": "pending-route-1",
            "confirm_execute": True,
            "route_apply_approval_contract_hash": "approval:route",
            "route_apply_approval_contract": {"status": "requires_confirmation"},
            "agent_plan_approval_contract_hash": "approval:agent",
            "agent_plan_approval_contract": {"status": "requires_confirmation"},
        },
    }

    result = normalize_tool_recommendations(
        "prepare_apply_pending_action_route_approval_opt_in",
        {"recommended_next_tools": ["execute_apply_pending_action_route_approval_opt_in_with_approval"], "recommended_next_tool_calls": [execute_call]},
        allowed_tools={"execute_apply_pending_action_route_approval_opt_in_with_approval"},
    )

    assert result["source_fields"] == ["recommended_next_tools", "recommended_next_tool_calls"]
    assert result["runtime_followups"] == ["execute_apply_pending_action_route_approval_opt_in_with_approval"]
    assert result["canonical_followups"] == ["execute_apply_pending_action_route_approval_opt_in_with_approval"]
    assert result["recommended_next_tool_calls"] == [execute_call]
