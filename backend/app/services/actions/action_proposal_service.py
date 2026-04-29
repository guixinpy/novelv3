def preview_action_to_execution(action_type: str) -> str:
    if action_type.startswith("preview_"):
        return action_type.replace("preview_", "generate_")
    return action_type

