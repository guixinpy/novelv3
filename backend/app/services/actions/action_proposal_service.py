_PREVIEW_ACTION_EXECUTION_OVERRIDES = {
    "preview_review": "review_chapter",
    "preview_recovery": "recover_blocked_run",
}


def preview_action_to_execution(action_type: str) -> str:
    if action_type in _PREVIEW_ACTION_EXECUTION_OVERRIDES:
        return _PREVIEW_ACTION_EXECUTION_OVERRIDES[action_type]
    if action_type.startswith("preview_"):
        return action_type.replace("preview_", "generate_")
    return action_type
