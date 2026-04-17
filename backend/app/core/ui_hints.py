ACTION_TO_PANEL = {
    "preview_setup": "setup",
    "generate_setup": "setup",
    "preview_storyline": "storyline",
    "generate_storyline": "storyline",
    "preview_outline": "outline",
    "generate_outline": "outline",
}

ACTION_TO_REFRESH_TARGETS = {
    "generate_setup": ["setup", "versions"],
    "generate_storyline": ["storyline", "versions"],
    "generate_outline": ["outline", "versions"],
}


def action_to_panel(action_type: str | None) -> str:
    if not action_type:
        return "setup"
    return ACTION_TO_PANEL.get(action_type, "setup")


def action_to_refresh_targets(action_type: str | None, status: str | None = None) -> list[str]:
    if not action_type:
        return []
    if (status or "").lower() not in {"completed", "success"}:
        return []
    return ACTION_TO_REFRESH_TARGETS.get(action_type, [])


def task_status_to_dialog_state(status: str | None) -> str:
    status_value = (status or "").lower()
    if status_value in {"completed", "failed", "cancelled"}:
        return "CHATTING"
    if status_value in {"running", "pending"}:
        return "RUNNING"
    return "CHATTING"


def build_ui_hint(action_type: str | None, dialog_state: str, status: str, reason: str = "") -> dict:
    active_action_type = action_type or "chat"
    return {
        "dialog_state": (dialog_state or "IDLE").upper(),
        "active_action": {
            "type": active_action_type,
            "status": (status or "").lower(),
            "target_panel": action_to_panel(action_type),
            "reason": reason,
        },
    }
