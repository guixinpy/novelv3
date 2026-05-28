def action_description(action_type: str, params: dict | None = None) -> str:
    action_params = params or {}
    if action_type == "preview_chapter":
        chapter_index = action_params.get("chapter_index")
        if chapter_index:
            return _append_chapter_conflict_warning(
                f"我可以生成第{chapter_index}章正文，完成后会进入 Calliope 和正文进度。",
                action_params,
            )
        return _append_chapter_conflict_warning("我可以生成下一章正文，完成后会进入 Calliope 和正文进度。", action_params)
    if action_type == "generate_chapter":
        chapter_index = action_params.get("chapter_index")
        chapter_label = f"第{chapter_index}章正文" if chapter_index else "正文"
        if action_params.get("confirm_execute") is True and action_params.get("approval_contract_hash"):
            return _append_chapter_conflict_warning(f"{chapter_label}已准备好审批，确认后将正式写入正文。", action_params)
        return _append_chapter_conflict_warning(f"我可以生成{chapter_label}，完成后会进入 Calliope 和正文进度。", action_params)
    if action_type == "preview_review":
        chapter_index = action_params.get("chapter_index")
        chapter_label = f"第{chapter_index}章" if chapter_index else "目标章节"
        return f"我可以审查{chapter_label}并生成修订计划。"
    if action_type == "preview_recovery":
        return "我可以为上一轮阻塞或失败的 Agent 运行规划恢复工具链。"
    mapping = {
        "preview_setup": "我建议先为项目生成设定，这样后续创作更有基础。",
        "preview_storyline": "基于已有设定，我可以生成故事线。",
        "preview_outline": "故事线已就绪，接下来可以生成完整大纲。",
        "query_diagnosis": "让我看看项目当前状态...",
    }
    return mapping.get(action_type, "已准备好执行操作。")


def _append_chapter_conflict_warning(description: str, params: dict) -> str:
    conflict = params.get("chapter_target_conflict") if isinstance(params.get("chapter_target_conflict"), dict) else None
    if not conflict or conflict.get("status") != "reserved":
        return description
    chapter_index = conflict.get("chapter_index") or params.get("chapter_index")
    if not chapter_index:
        return description
    source_label = str(conflict.get("source_label") or "待确认或运行中的生成任务").strip()
    return f"{description} 注意：第{chapter_index}章已有{source_label}，请确认是否仍要继续。"
