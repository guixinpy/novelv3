TYPE_LABELS = {
    "generate_setup": "生成设定",
    "generate_storyline": "生成故事线",
    "generate_outline": "生成大纲",
    "generate_chapter": "生成正文",
    "preview_setup": "生成设定",
    "preview_storyline": "生成故事线",
    "preview_outline": "生成大纲",
    "preview_chapter": "生成正文",
    "plan_recovery_tools": "恢复预览",
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
    if action_type == "plan_recovery_tools":
        if status in {"success", "completed"}:
            return "恢复预览已生成"
        if status == "failed":
            return "恢复预览失败"
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
    action_type = str(action_result.get("type") or "").strip()
    data = action_result.get("data") if isinstance(action_result.get("data"), dict) else {}
    if action_type == "plan_recovery_tools":
        return [
            *_recovery_preview_detail_items(data),
            *_agent_discovery_detail_items(data),
        ]

    approval_decision = data.get("approval_decision") if isinstance(data.get("approval_decision"), dict) else None
    if not approval_decision:
        return _agent_discovery_detail_items(data)

    items = []
    decision = str(approval_decision.get("decision") or "").strip()
    if decision:
        items.append({"label": "用户决策", "value": _decision_label(decision)})

    approval_mode = str(approval_decision.get("approval_mode") or "").strip()
    if approval_mode == "single":
        items.append({"label": "审批模式", "value": "单次确认"})

    chapter_index = approval_decision.get("chapter_index")
    if isinstance(chapter_index, int) and chapter_index > 0:
        items.append({"label": "目标章节", "value": f"第{chapter_index}章"})

    chapter_index_source = str(approval_decision.get("chapter_index_source") or "").strip()
    if chapter_index_source:
        items.append({"label": "章节来源", "value": _chapter_source_label(chapter_index_source)})

    conflict = (
        approval_decision.get("chapter_target_conflict")
        if isinstance(approval_decision.get("chapter_target_conflict"), dict)
        else None
    )
    if conflict and conflict.get("status") == "reserved":
        source_label = str(conflict.get("source_label") or "").strip()
        items.append({"label": "章节冲突", "value": source_label or "已占用"})

    if str(approval_decision.get("approval_contract_hash") or "").strip():
        items.append({"label": "审批契约", "value": "已绑定"})

    items.extend(_agent_discovery_detail_items(data))
    return items


def _decision_label(decision: str) -> str:
    if decision == "confirm":
        return "已确认"
    if decision == "cancel":
        return "已取消"
    if decision == "revise":
        return "要求修改"
    return decision


def _chapter_source_label(source: str) -> str:
    if source == "explicit_user":
        return "用户指定"
    if source == "inferred_next_unwritten":
        return "系统推断"
    if source == "router_default":
        return "默认目标"
    return source


def _recovery_preview_detail_items(data: dict) -> list[dict[str, str]]:
    items = []
    source_run_id = str(data.get("source_run_id") or "").strip()
    if source_run_id:
        items.append({"label": "来源运行", "value": source_run_id[:8]})

    recovery = data.get("recovery") if isinstance(data.get("recovery"), dict) else {}
    recovery_status = str(recovery.get("status") or "").strip()
    if recovery_status:
        items.append({"label": "恢复状态", "value": _recovery_status_label(recovery_status)})

    execution_policy = data.get("execution_policy") if isinstance(data.get("execution_policy"), dict) else {}
    policy_status = str(execution_policy.get("status") or "").strip()
    if policy_status:
        items.append({"label": "执行策略", "value": _execution_policy_label(policy_status)})

    tools = data.get("tools") if isinstance(data.get("tools"), list) else []
    if tools:
        items.append({"label": "恢复工具", "value": f"{len(tools)} 个"})
    return items


def _agent_discovery_detail_items(data: dict) -> list[dict[str, str]]:
    items = []
    definition = data.get("agent_profile_definition") if isinstance(data.get("agent_profile_definition"), dict) else {}
    profile = str(data.get("agent_profile") or "").strip()
    discovery = data.get("agent_tool_discovery") if isinstance(data.get("agent_tool_discovery"), dict) else {}
    effective_profile = str(discovery.get("effective_profile") or "").strip()
    definition_profile = str(definition.get("profile") or "").strip()
    display_name = str(definition.get("display_name") or "").strip()
    if display_name or profile or effective_profile or definition_profile:
        items.append(
            {
                "label": "Agent 身份",
                "value": display_name or _agent_profile_label(profile or effective_profile or definition_profile),
            }
        )

    role = str(definition.get("role") or "").strip()
    if role:
        items.append({"label": "Agent 角色", "value": _agent_role_label(role)})

    tier = str(definition.get("tier") or "").strip()
    if tier:
        items.append({"label": "编排层级", "value": tier})

    delegation = _delegation_label(definition.get("delegation_allowed"))
    if delegation:
        items.append({"label": "委派", "value": delegation})

    delegate_targets = definition.get("delegate_to_profiles")
    if definition.get("delegation_allowed") is True and isinstance(delegate_targets, list) and delegate_targets:
        items.append({"label": "可委派目标", "value": f"{len(delegate_targets)} 个声明"})

    status = str(discovery.get("status") or "").strip()
    if status:
        items.append({"label": "工具面", "value": _agent_tool_scope_status_label(status)})

    visible_tool_count = _optional_int(discovery.get("visible_tool_count"))
    if visible_tool_count is not None:
        items.append({"label": "可见工具", "value": f"{visible_tool_count} 个"})

    filtered_count = _optional_int(discovery.get("filtered_by_profile_count"))
    if filtered_count is not None:
        items.append({"label": "已过滤", "value": f"{filtered_count} 个"})

    policy_audit = (
        data.get("agent_profile_policy_audit") if isinstance(data.get("agent_profile_policy_audit"), dict) else {}
    )
    policy_audit_label = _profile_policy_audit_label(policy_audit)
    if policy_audit_label:
        items.append({"label": "策略审计", "value": policy_audit_label})
    return items


def _agent_profile_label(profile: str) -> str:
    if profile == "orchestrator":
        return "编排主控"
    if profile == "drafting_worker":
        return "创作执行者"
    if profile == "reviewer_worker":
        return "审稿执行者"
    if profile == "world_model_worker":
        return "世界模型执行者"
    if profile == "recovery_worker":
        return "恢复维护者"
    return profile or "未标注"


def _agent_role_label(role: str) -> str:
    if role == "orchestrator":
        return "orchestrator"
    if role == "worker":
        return "worker"
    return role or "未知"


def _delegation_label(value: object) -> str | None:
    if value is True:
        return "可委派"
    if value is False:
        return "不可委派"
    return None


def _agent_tool_scope_status_label(status: str) -> str:
    if status == "applied":
        return "已按身份收窄"
    if status == "not_requested":
        return "未请求身份收窄"
    if status == "unknown_profile":
        return "未知身份，已拒绝工具面"
    if status == "not_available":
        return "暂无工具面摘要"
    return status or "未知"


def _profile_policy_audit_label(audit: dict) -> str:
    status = str(audit.get("status") or "").strip()
    summary = audit.get("summary") if isinstance(audit.get("summary"), dict) else {}
    issue_count = _optional_int(summary.get("issues"))
    if status == "passed":
        return "通过"
    if status == "needs_attention":
        if issue_count is not None:
            return f"需关注：{issue_count} 个问题"
        return "需关注"
    return status


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _recovery_status_label(status: str) -> str:
    if status == "recommended":
        return "建议恢复"
    if status == "none":
        return "无恢复建议"
    return status


def _execution_policy_label(status: str) -> str:
    if status == "ready":
        return "可执行"
    if status == "confirmation_required":
        return "等待确认"
    if status == "not_executable":
        return "不可执行"
    if status == "repeat_failed_recovery":
        return "重复失败保护"
    return status
