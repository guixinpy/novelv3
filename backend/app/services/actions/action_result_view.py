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
    "plan_recommended_followups": "推荐后继预览",
    "search_agent_retrieval_context": "检索证据",
    "plan_post_chapter_memory_capture": "写后记忆规划",
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

    data = action_result.get("data") if isinstance(action_result.get("data"), dict) else {}
    label = _label(action_type, status, data)
    view = {
        "type": action_type,
        "status": status,
        "label": label,
        "variant": _variant(action_type, status, data),
    }
    detail_items = _detail_items(action_result)
    if detail_items:
        view["detail_items"] = detail_items
    return view


def _label(action_type: str, status: str, data: dict | None = None) -> str:
    data = data or {}
    label = TYPE_LABELS.get(action_type, action_type)
    if action_type == "plan_recovery_tools":
        if status in {"success", "completed"}:
            return "恢复预览已生成"
        if status == "failed":
            return "恢复预览失败"
    if action_type == "plan_recommended_followups":
        if status in {"success", "completed"}:
            return "推荐后继预览已生成"
        if status == "failed":
            return "推荐后继预览失败"
    if action_type == "search_agent_retrieval_context":
        return _retrieval_context_label(action_result_status=status, data=data)
    if action_type == "plan_post_chapter_memory_capture":
        return _post_chapter_memory_capture_label(action_result_status=status, data=data)
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


def _variant(action_type: str, status: str, data: dict | None = None) -> str:
    data = data or {}
    if action_type == "plan_post_chapter_memory_capture":
        return _post_chapter_memory_capture_variant(str(data.get("capture_status") or "").strip(), status)
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
    if action_type == "plan_recommended_followups":
        return [
            *_recommended_followup_preview_detail_items(data),
            *_agent_discovery_detail_items(data),
        ]
    if action_type == "search_agent_retrieval_context":
        return _retrieval_context_detail_items(data)
    if action_type == "plan_post_chapter_memory_capture":
        return _post_chapter_memory_capture_detail_items(data)

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
    items.extend(_dialog_route_decision_detail_items(data))

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


def _recommended_followup_preview_detail_items(data: dict) -> list[dict[str, str]]:
    items = []
    source_run_id = str(data.get("source_run_id") or "").strip()
    if source_run_id:
        items.append({"label": "来源运行", "value": source_run_id[:8]})
    items.extend(_dialog_route_decision_detail_items(data))

    followups = data.get("recommended_followups") if isinstance(data.get("recommended_followups"), dict) else {}
    followup_status = str(followups.get("status") or "").strip()
    if followup_status:
        items.append({"label": "推荐状态", "value": _recommended_followup_status_label(followup_status)})

    tools = data.get("tools") if isinstance(data.get("tools"), list) else []
    if tools:
        items.append({"label": "自动后继", "value": f"{len(tools)} 个"})
        tool_summary = _tool_name_summary(tools)
        if tool_summary:
            items.append({"label": "后继工具", "value": tool_summary})
    pending_confirmation_calls = (
        data.get("pending_confirmation_tool_calls")
        if isinstance(data.get("pending_confirmation_tool_calls"), list)
        else []
    )
    if pending_confirmation_calls:
        items.append({"label": "待确认后继", "value": f"{len(pending_confirmation_calls)} 个工具"})
        tool_summary = _tool_name_summary(pending_confirmation_calls)
        if tool_summary:
            items.append({"label": "待确认工具", "value": tool_summary})
    items.extend(_worker_dispatch_detail_items(data))

    continuation_tools = (
        followups.get("post_approval_continuation_tools")
        if isinstance(followups.get("post_approval_continuation_tools"), list)
        else []
    )
    if continuation_tools:
        items.append({"label": "写后续跑", "value": f"{len(continuation_tools)} 个工具"})

    write_tools = followups.get("provenance_write_tools") if isinstance(followups.get("provenance_write_tools"), list) else []
    if write_tools:
        items.append({"label": "需确认修复", "value": f"{len(write_tools)} 个"})
    return items


def _worker_dispatch_detail_items(data: dict) -> list[dict[str, str]]:
    dispatch = data.get("worker_dispatch") if isinstance(data.get("worker_dispatch"), dict) else {}
    summary = dispatch.get("summary") if isinstance(dispatch.get("summary"), dict) else {}
    route_registry = dispatch.get("route_registry") if isinstance(dispatch.get("route_registry"), dict) else {}
    route_registry_summary = (
        route_registry.get("summary") if isinstance(route_registry.get("summary"), dict) else {}
    )
    items = []
    worker_count = _optional_int(summary.get("workers"))
    if worker_count is not None:
        items.append({"label": "Worker 分派", "value": f"{worker_count} 个 worker"})
    worker_summary = _worker_dispatch_summary(dispatch)
    if worker_summary:
        items.append({"label": "分派 Worker", "value": worker_summary})
    planned_tasks = _optional_int(summary.get("planned_tasks"))
    if planned_tasks is not None:
        items.append({"label": "分派任务", "value": f"{planned_tasks} 个任务"})
    blocked_tasks = _optional_int(summary.get("blocked_tasks"))
    if blocked_tasks is not None and blocked_tasks > 0:
        items.append({"label": "分派阻塞", "value": f"{blocked_tasks} 个"})
    issue_count = _optional_int(summary.get("issues"))
    if issue_count is not None and issue_count > 0:
        items.append({"label": "分派问题", "value": f"{issue_count} 个"})
    route_registry_status = str(route_registry.get("status") or "").strip()
    if route_registry_status:
        items.append({"label": "路由审计", "value": _route_registry_status_label(route_registry_status)})
    unrouted_allowed_tools = _optional_int(route_registry_summary.get("unrouted_allowed_tools"))
    if unrouted_allowed_tools is not None:
        items.append({"label": "未路由工具", "value": f"{unrouted_allowed_tools} 个"})
    route_issue_count = _optional_int(route_registry_summary.get("issues"))
    if route_issue_count is not None and route_issue_count > 0:
        items.append({"label": "路由问题", "value": f"{route_issue_count} 个"})
    return items


def _tool_name_summary(tools: list[object]) -> str:
    names = []
    for tool in tools:
        if isinstance(tool, str):
            tool_name = tool.strip()
        elif isinstance(tool, dict):
            tool_name = str(tool.get("tool_name") or "").strip()
        else:
            tool_name = ""
        if tool_name:
            names.append(tool_name)
    return _compact_unique_label(names)


def _worker_dispatch_summary(dispatch: dict) -> str:
    dispatches = dispatch.get("worker_dispatches") if isinstance(dispatch.get("worker_dispatches"), list) else []
    names = []
    for item in dispatches:
        if not isinstance(item, dict):
            continue
        worker = item.get("worker") if isinstance(item.get("worker"), dict) else {}
        worker_name = str(worker.get("name") or "").strip()
        if worker_name:
            names.append(_agent_profile_label(worker_name))
    return _compact_unique_label(names)


def _compact_unique_label(values: list[str], *, limit: int = 3) -> str:
    unique_values = list(dict.fromkeys(value for value in values if value))
    if not unique_values:
        return ""
    if len(unique_values) <= limit:
        return ", ".join(unique_values)
    return f"{', '.join(unique_values[:limit])} 等 {len(unique_values)} 个"


def _retrieval_context_detail_items(data: dict) -> list[dict[str, str]]:
    items = []
    summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    returned = _optional_int(summary.get("returned"))
    total = _optional_int(summary.get("total"))
    coverage_label = _retrieval_coverage_label(returned, total)
    if coverage_label:
        items.append({"label": "检索证据", "value": coverage_label})

    retrieval_items = data.get("items") if isinstance(data.get("items"), list) else []
    primary_source = _retrieval_primary_source_label(retrieval_items[0] if retrieval_items else None)
    if primary_source:
        items.append({"label": "首个来源", "value": primary_source})

    next_tools = data.get("recommended_next_tools") if isinstance(data.get("recommended_next_tools"), list) else []
    if next_tools:
        items.append({"label": "下一步", "value": f"{len(next_tools)} 个工具"})
    return items


def _post_chapter_memory_capture_detail_items(data: dict) -> list[dict[str, str]]:
    items = []
    chapter_index = _optional_int(data.get("chapter_index"))
    if chapter_index is not None and chapter_index > 0:
        items.append({"label": "章节", "value": f"第{chapter_index}章"})

    capture_status = str(data.get("capture_status") or "").strip()
    if capture_status:
        items.append({"label": "写后记忆", "value": _post_chapter_memory_capture_status_label(capture_status)})

    summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    candidate_count = _optional_int(summary.get("candidate_count"))
    if candidate_count is not None:
        items.append({"label": "候选", "value": f"{candidate_count} 个"})
    review_step_count = _optional_int(summary.get("review_step_count"))
    if review_step_count is not None:
        items.append({"label": "审稿证据", "value": f"{review_step_count} 个"})

    next_tools = data.get("recommended_next_tools") if isinstance(data.get("recommended_next_tools"), list) else []
    if next_tools:
        items.append({"label": "下一步", "value": f"{len(next_tools)} 个工具"})
    return items


def _dialog_route_decision_detail_items(data: dict) -> list[dict[str, str]]:
    decision = data.get("route_decision") if isinstance(data.get("route_decision"), dict) else {}
    items = []
    selected_route = str(decision.get("selected_route") or "").strip()
    if selected_route:
        items.append({"label": "继续路由", "value": _dialog_route_label(selected_route)})
    reason_code = str(decision.get("reason_code") or "").strip()
    if reason_code:
        items.append({"label": "路由原因", "value": _dialog_route_reason_label(reason_code)})
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
    items.extend(_agent_command_contract_detail_items(data))
    items.extend(_agent_control_plane_readiness_detail_items(data))
    return items


def _agent_command_contract_detail_items(data: dict) -> list[dict[str, str]]:
    contracts = data.get("agent_command_contracts") if isinstance(data.get("agent_command_contracts"), dict) else {}
    summary = contracts.get("summary") if isinstance(contracts.get("summary"), dict) else {}
    if not summary:
        return []
    items = [{"label": "命令契约", "value": "已投影"}]
    control_commands = _optional_int(summary.get("agent_control_commands"))
    if control_commands is not None:
        items.append({"label": "控制命令", "value": f"{control_commands} 个"})
    gap_count = _optional_int(summary.get("gap_count"))
    if gap_count is not None:
        items.append({"label": "契约缺口", "value": f"{gap_count} 个"})
    return items


def _agent_control_plane_readiness_detail_items(data: dict) -> list[dict[str, str]]:
    readiness = (
        data.get("agent_control_plane_readiness")
        if isinstance(data.get("agent_control_plane_readiness"), dict)
        else {}
    )
    summary = readiness.get("summary") if isinstance(readiness.get("summary"), dict) else {}
    if not summary:
        return []
    items = [{"label": "控制平面", "value": _agent_control_plane_status_label(str(readiness.get("status") or ""))}]
    total_gap_count = _optional_int(summary.get("total_gap_count"))
    if total_gap_count is not None:
        items.append({"label": "控制面缺口", "value": f"{total_gap_count} 个"})
    tool_gap_count = _optional_int(summary.get("tool_gap_count"))
    if tool_gap_count is not None:
        items.append({"label": "工具缺口", "value": f"{tool_gap_count} 个"})
    command_gap_count = _optional_int(summary.get("command_gap_count"))
    if command_gap_count is not None:
        items.append({"label": "命令缺口", "value": f"{command_gap_count} 个"})
    recommended_next_tools = (
        readiness.get("recommended_next_tools") if isinstance(readiness.get("recommended_next_tools"), list) else []
    )
    if recommended_next_tools:
        items.append({"label": "建议检查", "value": f"{len(recommended_next_tools)} 项"})
    return items


def _agent_control_plane_status_label(status: str) -> str:
    if status == "ready":
        return "可继续编排"
    if status == "degraded":
        return "需检查"
    if status == "needs_attention":
        return "需处理"
    return status or "未知"


def _route_registry_status_label(status: str) -> str:
    if status == "passed":
        return "通过"
    if status == "needs_attention":
        return "需处理"
    return status or "未知"


def _agent_profile_label(profile: str) -> str:
    if profile == "orchestrator":
        return "编排主控"
    if profile == "drafting_worker":
        return "创作执行者"
    if profile == "reviewer_worker":
        return "审稿执行者"
    if profile == "memory_worker":
        return "记忆维护者"
    if profile == "retrieval_worker":
        return "检索取证者"
    if profile == "world_model_worker":
        return "世界模型执行者"
    if profile == "revision_worker":
        return "修订执行者"
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


def _retrieval_context_label(*, action_result_status: str, data: dict) -> str:
    if action_result_status in {"success", "completed"}:
        summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
        if _optional_int(summary.get("returned")) == 0:
            return "检索证据为空"
        return "检索证据已返回"
    if action_result_status == "failed":
        return "检索证据获取失败"
    if action_result_status in {"running", "generating"}:
        return "检索证据检索中"
    return f"检索证据: {action_result_status or '未知状态'}"


def _post_chapter_memory_capture_label(*, action_result_status: str, data: dict) -> str:
    capture_status = str(data.get("capture_status") or "").strip()
    if action_result_status in {"success", "completed"}:
        if capture_status == "needs_review":
            return "写后记忆等待审稿"
        if capture_status == "missing_chapter":
            return "写后记忆缺少章节"
        return "写后记忆候选已规划"
    if action_result_status == "failed":
        return "写后记忆规划失败"
    if action_result_status in {"running", "generating"}:
        return "写后记忆规划中"
    return f"写后记忆规划: {action_result_status or '未知状态'}"


def _post_chapter_memory_capture_variant(capture_status: str, action_result_status: str) -> str:
    if action_result_status == "failed" or capture_status in {"failed", "blocked"}:
        return "error"
    if capture_status in {"needs_review", "missing_chapter", "skipped"}:
        return "neutral"
    if action_result_status in {"success", "completed"}:
        return "success"
    return "neutral"


def _post_chapter_memory_capture_status_label(status: str) -> str:
    if status == "ready":
        return "可写入候选"
    if status == "needs_review":
        return "需要审稿"
    if status == "missing_chapter":
        return "缺少章节"
    if status in {"completed", "success"}:
        return "完成"
    return status or "未知"


def _retrieval_coverage_label(returned: int | None, total: int | None) -> str:
    if returned is not None and total is not None:
        return f"返回 {returned} / 共 {total}"
    if returned is not None:
        return f"返回 {returned}"
    if total is not None:
        return f"共 {total}"
    return ""


def _retrieval_primary_source_label(item: object) -> str:
    if not isinstance(item, dict):
        return ""
    title = str(item.get("title") or item.get("source_ref") or "").strip()
    chapter_index = _optional_int(item.get("chapter_index"))
    chapter_label = f"第{chapter_index}章" if chapter_index is not None and chapter_index > 0 else ""
    source_label = _retrieval_source_type_label(str(item.get("source_type") or "").strip())
    return " · ".join(value for value in [title, chapter_label or source_label] if value)


def _retrieval_source_type_label(source_type: str) -> str:
    if source_type == "knowledge_base_candidate":
        return "知识库候选"
    if source_type == "longform_memory":
        return "长篇记忆"
    if source_type == "world_fact":
        return "世界事实"
    return ""


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


def _recommended_followup_status_label(status: str) -> str:
    if status == "recommended":
        return "已推荐"
    if status == "none":
        return "无推荐"
    return status


def _dialog_route_label(route: str) -> str:
    if route == "recover_blocked_run":
        return "恢复阻塞运行"
    if route == "recommended_followups":
        return "推荐后继"
    if route == "chapter_generation":
        return "继续章节生成"
    return route


def _dialog_route_reason_label(reason_code: str) -> str:
    if reason_code == "recoverable_run_found":
        return "发现可恢复运行"
    if reason_code == "recommended_followups_found":
        return "发现上一轮推荐后继"
    if reason_code == "no_recovery_or_followup":
        return "无恢复或后继，继续章节生成"
    return reason_code


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
