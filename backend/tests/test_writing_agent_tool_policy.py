from app.services.writing_agent.tool_policy import (
    allowed_report_followup,
    report_policy_for_tool,
    should_stop_after_report,
    successful_report_block_message,
)


def test_agent_tool_policy_blocks_report_tools_until_allowed_followup():
    assert (
        should_stop_after_report(
            "seed_continuity_anchor_proposals",
            {"should_generate_next_chapter": False},
            step_index=1,
            total_steps=2,
            next_tool_name="generate_chapter",
        )
        is True
    )
    assert (
        should_stop_after_report(
            "seed_continuity_anchor_proposals",
            {"should_generate_next_chapter": False},
            step_index=1,
            total_steps=2,
            next_tool_name="apply_world_model_proposal_resolution",
        )
        is False
    )
    assert (
        allowed_report_followup(
            "seed_continuity_anchor_proposals",
            "apply_world_model_proposal_resolution",
        )
        is True
    )


def test_agent_tool_policy_allows_terminal_step_and_non_report_tools():
    assert (
        should_stop_after_report(
            "seed_continuity_anchor_proposals",
            {"should_generate_next_chapter": False},
            step_index=1,
            total_steps=1,
            next_tool_name=None,
        )
        is False
    )
    assert (
        should_stop_after_report(
            "generate_chapter",
            {"should_generate_next_chapter": False},
            step_index=1,
            total_steps=2,
            next_tool_name="review_chapter_quality",
        )
        is False
    )


def test_agent_tool_policy_reports_tool_specific_block_messages():
    assert (
        successful_report_block_message("seed_continuity_anchor_proposals")
        == "稳定连续性锚点提案尚未审批，已停止后续写作工具。"
    )
    assert successful_report_block_message("unknown_tool") == "报告未通过，已停止后续写作工具。"


def test_agent_tool_policy_projects_report_policy_for_planner():
    assert report_policy_for_tool("seed_continuity_anchor_proposals") == {
        "stop_check_required": True,
        "stop_condition": "non_terminal_step_and_should_generate_next_chapter_false_without_allowed_followup",
        "allowed_followups": ["apply_world_model_proposal_resolution"],
        "block_message": "稳定连续性锚点提案尚未审批，已停止后续写作工具。",
    }
    assert report_policy_for_tool("generate_chapter") == {
        "stop_check_required": False,
        "stop_condition": None,
        "allowed_followups": [],
        "block_message": None,
    }
