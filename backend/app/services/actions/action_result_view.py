TYPE_LABELS = {
    "generate_setup": "生成设定",
    "generate_storyline": "生成故事线",
    "generate_outline": "生成大纲",
    "generate_chapter": "生成正文",
    "preview_setup": "生成设定",
    "preview_storyline": "生成故事线",
    "preview_outline": "生成大纲",
    "preview_chapter": "生成正文",
}

GENERATING_LABELS = {
    "generate_setup": "设定",
    "generate_storyline": "故事线",
    "generate_outline": "大纲",
    "generate_chapter": "正文",
    "preview_setup": "设定",
    "preview_storyline": "故事线",
    "preview_outline": "大纲",
    "preview_chapter": "正文",
}


def action_result_view(action_result: dict | None) -> dict | None:
    if not action_result:
        return None
    action_type = str(action_result.get("type") or "").strip()
    status = str(action_result.get("status") or "").strip()
    if not action_type or not status:
        return None

    label = _label(action_type, status)
    view = {
        "type": action_type,
        "status": status,
        "label": label,
        "variant": _variant(status),
    }
    detail_items = _detail_items(action_result)
    if detail_items:
        view["detail_items"] = detail_items
    return view


def _label(action_type: str, status: str) -> str:
    label = TYPE_LABELS.get(action_type, action_type)
    if status in {"success", "completed"}:
        return f"{label}执行成功"
    if status == "cancelled":
        return "操作已取消"
    if status == "revised":
        return "已收到修改意见"
    if status in {"generating", "running"}:
        return f"{GENERATING_LABELS.get(action_type, label)}生成中..."
    if status == "approval_required":
        return f"{label}等待确认"
    if status == "failed":
        return f"{label}失败"
    return f"{label}: {status}"


def _variant(status: str) -> str:
    if status in {"success", "completed"}:
        return "success"
    if status == "failed":
        return "error"
    return "neutral"


def _detail_items(action_result: dict) -> list[dict[str, str]]:
    data = action_result.get("data") if isinstance(action_result.get("data"), dict) else {}
    approval_decision = data.get("approval_decision") if isinstance(data.get("approval_decision"), dict) else None
    if not approval_decision:
        return []

    items = []
    decision = str(approval_decision.get("decision") or "").strip()
    if decision:
        items.append({"label": "用户决策", "value": _decision_label(decision)})

    approval_mode = str(approval_decision.get("approval_mode") or "").strip()
    if approval_mode == "single":
        items.append({"label": "审批模式", "value": "单次确认"})

    if str(approval_decision.get("approval_contract_hash") or "").strip():
        items.append({"label": "审批契约", "value": "已绑定"})

    return items


def _decision_label(decision: str) -> str:
    if decision == "confirm":
        return "已确认"
    if decision == "cancel":
        return "已取消"
    if decision == "revise":
        return "要求修改"
    return decision
