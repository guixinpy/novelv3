from __future__ import annotations

from collections.abc import Mapping

REPORT_STOP_TOOLS = frozenset(
    {
        "plan_chapter_revision",
        "create_revision_draft",
        "execute_create_revision_draft_with_approval",
        "apply_planner_revision_patch",
        "execute_apply_planner_revision_patch_with_approval",
        "expand_chapter_to_target",
        "execute_expand_chapter_to_target_with_approval",
        "compress_chapter_to_target",
        "execute_compress_chapter_to_target_with_approval",
        "summarize_longform_context",
        "review_world_model_proposals",
        "plan_world_model_proposal_resolution",
        "preview_world_model_proposal_resolution",
        "apply_world_model_proposal_resolution",
        "draft_world_model_proposal_resolution_decisions",
        "draft_high_value_world_proposal_resolution_decisions",
        "seed_continuity_anchor_proposals",
    }
)

ALLOWED_REPORT_FOLLOWUPS = frozenset(
    {
        ("create_revision_draft", "apply_planner_revision_patch"),
        ("execute_create_revision_draft_with_approval", "apply_planner_revision_patch"),
        ("apply_planner_revision_patch", "review_chapter_quality"),
        ("execute_apply_planner_revision_patch_with_approval", "review_chapter_quality"),
        ("expand_chapter_to_target", "review_chapter_quality"),
        ("execute_expand_chapter_to_target_with_approval", "review_chapter_quality"),
        ("compress_chapter_to_target", "review_chapter_quality"),
        ("execute_compress_chapter_to_target_with_approval", "review_chapter_quality"),
        ("review_world_model_proposals", "plan_world_model_proposal_resolution"),
        ("plan_world_model_proposal_resolution", "preview_world_model_proposal_resolution"),
        ("preview_world_model_proposal_resolution", "apply_world_model_proposal_resolution"),
        ("draft_world_model_proposal_resolution_decisions", "apply_world_model_proposal_resolution"),
        ("draft_high_value_world_proposal_resolution_decisions", "apply_world_model_proposal_resolution"),
        ("seed_continuity_anchor_proposals", "apply_world_model_proposal_resolution"),
    }
)

REPORT_BLOCK_MESSAGES = {
    "summarize_longform_context": "长篇上下文维护未就绪，已停止后续写作工具。",
    "review_world_model_proposals": "世界模型提案队列仍有待审项，已停止后续写作工具。",
    "plan_world_model_proposal_resolution": "世界模型提案尚未解决，已停止后续写作工具。",
    "preview_world_model_proposal_resolution": "世界模型提案解决决策尚未执行，已停止后续写作工具。",
    "apply_world_model_proposal_resolution": "世界模型提案队列仍未清空，已停止后续写作工具。",
    "draft_world_model_proposal_resolution_decisions": "世界模型提案决策草案尚未确认应用，已停止后续写作工具。",
    "draft_high_value_world_proposal_resolution_decisions": "高价值世界模型提案决策草案尚未确认应用，已停止后续写作工具。",
    "seed_continuity_anchor_proposals": "稳定连续性锚点提案尚未审批，已停止后续写作工具。",
    "plan_chapter_revision": "修订计划未通过，已停止后续写作工具。",
    "create_revision_draft": "修订草稿未通过，已停止后续写作工具。",
    "execute_create_revision_draft_with_approval": "修订草稿未通过，已停止后续写作工具。",
    "apply_planner_revision_patch": "修订补丁应用后尚未复审，已停止后续写作工具。",
    "execute_apply_planner_revision_patch_with_approval": "修订补丁应用后尚未复审，已停止后续写作工具。",
    "expand_chapter_to_target": "章节扩写后尚未复审，已停止后续写作工具。",
    "execute_expand_chapter_to_target_with_approval": "章节扩写后尚未复审，已停止后续写作工具。",
    "compress_chapter_to_target": "章节压缩后尚未复审，已停止后续写作工具。",
    "execute_compress_chapter_to_target_with_approval": "章节压缩后尚未复审，已停止后续写作工具。",
}


def allowed_report_followup(tool_name: str, next_tool_name: str | None) -> bool:
    return (tool_name, next_tool_name) in ALLOWED_REPORT_FOLLOWUPS


def should_stop_after_report(
    tool_name: str,
    output: Mapping[str, object],
    *,
    step_index: int,
    total_steps: int,
    next_tool_name: str | None = None,
) -> bool:
    if tool_name not in REPORT_STOP_TOOLS:
        return False
    if step_index >= total_steps:
        return False
    if allowed_report_followup(tool_name, next_tool_name):
        return False
    return output.get("should_generate_next_chapter") is False


def successful_report_block_message(tool_name: str) -> str:
    return REPORT_BLOCK_MESSAGES.get(tool_name, "报告未通过，已停止后续写作工具。")


def report_policy_for_tool(tool_name: str) -> dict[str, object]:
    stops_after_report = tool_name in REPORT_STOP_TOOLS
    allowed_followups = sorted(
        next_tool for current_tool, next_tool in ALLOWED_REPORT_FOLLOWUPS if current_tool == tool_name
    )
    return {
        "stop_check_required": stops_after_report,
        "stop_condition": (
            "non_terminal_step_and_should_generate_next_chapter_false_without_allowed_followup"
            if stops_after_report
            else None
        ),
        "allowed_followups": allowed_followups,
        "block_message": successful_report_block_message(tool_name) if stops_after_report else None,
    }
