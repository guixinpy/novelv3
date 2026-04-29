def action_description(action_type: str, params: dict | None = None) -> str:
    if action_type == "preview_chapter":
        chapter_index = (params or {}).get("chapter_index")
        if chapter_index:
            return f"我可以生成第{chapter_index}章正文，完成后会进入 Calliope 和正文进度。"
        return "我可以生成下一章正文，完成后会进入 Calliope 和正文进度。"
    mapping = {
        "preview_setup": "我建议先为项目生成设定，这样后续创作更有基础。",
        "preview_storyline": "基于已有设定，我可以生成故事线。",
        "preview_outline": "故事线已就绪，接下来可以生成完整大纲。",
        "query_diagnosis": "让我看看项目当前状态...",
    }
    return mapping.get(action_type, "已准备好执行操作。")

