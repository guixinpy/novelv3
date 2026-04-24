from typing import Any


def format_revision_feedback(annotations: list[dict[str, Any]], corrections: list[dict[str, Any]]) -> str:
    parts: list[str] = []

    if annotations:
        parts.append("【用户批注】")
        for index, item in enumerate(annotations, start=1):
            paragraph = item.get("paragraph_index", 0)
            selected_text = item.get("selected_text", "")
            comment = item.get("comment", "")
            parts.append(f"{index}. 第{paragraph + 1}段《{selected_text}》：{comment}")

    if corrections:
        parts.append("【用户修正】")
        for index, item in enumerate(corrections, start=1):
            paragraph = item.get("paragraph_index", 0)
            original_text = item.get("original_text", "")
            corrected_text = item.get("corrected_text", "")
            parts.append(f"{index}. 第{paragraph + 1}段：{original_text} -> {corrected_text}")

    if not parts:
        return ""

    return "\n".join(parts)
