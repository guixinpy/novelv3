def _get_or_create_dialog(db: Session, project_id: str, dialog_type: str = "hermes") -> Dialog:
    return DialogSessionService(db).get_or_create(project_id, dialog_type)


def _save_message(
    db: Session,
    dialog_id: str,
    role: str,
    content: str,
    action_result: dict | None = None,
    message_type: str = "plain",
    meta: dict | None = None,
) -> DialogMessage:
    return DialogSessionService(db).save_message(
        dialog_id,
        role,
        content,
        action_result=action_result,
        message_type=message_type,
        meta=meta,
    )


    except Exception:
        db.rollback()
        reply = "压缩失败，历史未变更。"
        _save_command_feedback(
            db,
            dialog.id,
            "compact",
            reply,
            extra_meta={"compaction_failed": True},
        )
        return ChatOut(
            message=reply,
            pending_action=None,
            ui_hint=_build_chat_idle_hint("压缩失败"),
            refresh_targets=[],
            project_diagnosis=diagnosis,
        )

    reply = f"已压缩 {summary.compacted_count} 条消息。"
    return ChatOut(
        message=reply,
        pending_action=None,
        ui_hint=_build_chat_idle_hint("对话已压缩"),
        refresh_targets=[],
        project_diagnosis=diagnosis,
    )



    reply = f"已压缩 {summary.compacted_count} 条消息。"
    return ChatOut(
        message=reply,
        pending_action=None,
        ui_hint=_build_chat_idle_hint("对话已压缩"),
        refresh_targets=[],
        project_diagnosis=diagnosis,
    )


def _chat_unavailable_reply(diagnosis: ProjectDiagnosisOut, reason: str) -> str:
    return f"{reason}。我现在只能做流程诊断：{_diagnosis_summary(diagnosis)}"


def _build_chat_call_payload(
    db: Session,
    dialog_id: str,
    project: Project,
    diagnosis: ProjectDiagnosisOut,
    dialog_type: str = "hermes",
) -> dict:
    return build_dialog_call_payload(
        db,
        dialog_id,
        project,
        diagnosis,
        dialog_type=dialog_type,
        history_limit=CHAT_HISTORY_LIMIT,
    )


    *,
    error_message: str,
    latency_ms: int | None,
) -> AIModelCallTrace | None:
    if trace is None:
        return None
    try:
        mark_trace_failed(
            db,
            trace,
            error_message=error_message,
            latency_ms=latency_ms,
        )
        return trace
    except Exception:
        db.rollback()
        return None


        mark_trace_failed(
            db,
            trace,
            error_message=error_message,
            latency_ms=latency_ms,
        )
        return trace
    except Exception:
        db.rollback()
        return None


def _safe_attach_trace_response(
    db: Session,
    trace: AIModelCallTrace | None,
    response_message_id: str,
) -> str | None:
    if trace is None:
        return None
    try:
        attach_trace_response(db, trace, response_message_id=response_message_id)
        db.commit()
        return trace.id
    except Exception:
        db.rollback()
        return None


def _safe_create_chat_trace(
    db: Session,
    *,
    project_id: str,
    trace_type: str,
    messages: list[dict],
    context_blocks: list[dict],
    model: str,
    temperature: float,
    max_tokens: int,
    dialog_id: str,
    request_message_id: str | None,
    trace_metadata: dict,
) -> AIModelCallTrace | None:
    try:
        trace = create_trace(
            db,
            project_id=project_id,
            trace_type=trace_type,
            messages=messages,
            context_blocks=context_blocks,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            dialog_id=dialog_id,
            request_message_id=request_message_id,
            trace_metadata=trace_metadata,
        )
        db.commit()
        return trace
    except Exception:
        db.rollback()
        return None


async def _free_chat_reply(
    db: Session,
    dialog: Dialog,
    project: Project,
    diagnosis: ProjectDiagnosisOut,
    dialog_type: str = "hermes",
    request_message_id: str | None = None,
) -> tuple[str, AIModelCallTrace | None]:
    if not load_api_key():
        return _chat_unavailable_reply(diagnosis, "当前未配置模型 API Key，聊天还没有真实接入 AI"), None

    trace = None
    started_at = now_ms()
    model = project.ai_model or "deepseek-chat"
    temperature = 0.7
    max_tokens = 900
    try:
        payload = _build_chat_call_payload(db, dialog.id, project, diagnosis, dialog_type=dialog_type)
        messages = payload["messages"]
    except Exception as exc:
        return _chat_unavailable_reply(diagnosis, f"模型调用失败：{str(exc)}"), None

    trace = _safe_create_chat_trace(
        db,
        project_id=project.id,
        trace_type=f"{dialog_type}_chat",
        messages=messages,
        context_blocks=payload["context_blocks"],
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        dialog_id=dialog.id,
        request_message_id=request_message_id,
        trace_metadata={**payload.get("trace_metadata", {}), "dialog_type": dialog_type},
    )

    try:
        result = await ai_service.complete(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
        )
        content = (result.content or "").strip()
        if content:
            trace = _safe_mark_trace_success(
                db,
                trace,
                prompt_tokens=getattr(result, "prompt_tokens", 0),
                completion_tokens=getattr(result, "completion_tokens", 0),
                latency_ms=now_ms() - started_at,
            )
            return content, trace
        trace = _safe_mark_trace_failed(
            db,
            trace,
            error_message="模型返回了空内容",
            latency_ms=now_ms() - started_at,
        )
    except Exception as exc:
        trace = _safe_mark_trace_failed(
            db,
            trace,
            error_message=str(exc),
            latency_ms=now_ms() - started_at,
        )
        return _chat_unavailable_reply(diagnosis, f"模型调用失败：{str(exc)}"), trace

    return _chat_unavailable_reply(diagnosis, "模型返回了空内容"), trace


@router.get("/api/v1/dialog/projects/{project_id}/messages")
    LocalTaskRunner().start(
        task.id,
        build_action_background_work(
            action_type,
            project_id,
            dialog_id,
            command_args=command_args,
            action_params=action_params,
        ),
    )
    return task


        "pending_action_id": pending.id,
        "action_type": action_type,
        "pending_action_type": pending.type,
        "decision": decision,
        "decision_comment": pending.decision_comment or "",
        "resolved_at": pending.resolved_at.isoformat() if pending.resolved_at else None,
        "approval_mode": "single",
        "approval_contract_hash": params.get("approval_contract_hash"),
        "approval_contract_version": contract.get("version"),
    }
    try:
        chapter_index = int(params.get("chapter_index"))
    except (TypeError, ValueError):
        chapter_index = None
    if chapter_index is not None and chapter_index > 0:
        metadata["chapter_index"] = chapter_index
    chapter_index_source = str(params.get("chapter_index_source") or "").strip()
    if chapter_index_source:
        metadata["chapter_index_source"] = chapter_index_source
    chapter_target_conflict = _approval_chapter_target_conflict(params)
    if chapter_target_conflict is not None:
        metadata["chapter_target_conflict"] = chapter_target_conflict
    return metadata


        "decision": decision,
        "decision_comment": pending.decision_comment or "",
        "resolved_at": pending.resolved_at.isoformat() if pending.resolved_at else None,
        "approval_mode": "single",
        "approval_contract_hash": params.get("approval_contract_hash"),
        "approval_contract_version": contract.get("version"),
    }
    try:
        chapter_index = int(params.get("chapter_index"))
    except (TypeError, ValueError):
        chapter_index = None
    if chapter_index is not None and chapter_index > 0:
        metadata["chapter_index"] = chapter_index
    chapter_index_source = str(params.get("chapter_index_source") or "").strip()
    if chapter_index_source:
        metadata["chapter_index_source"] = chapter_index_source
    chapter_target_conflict = _approval_chapter_target_conflict(params)
    if chapter_target_conflict is not None:
        metadata["chapter_target_conflict"] = chapter_target_conflict
    return metadata


            "status": payload.decision,
            "decision_comment": payload.comment,
            "resolved_at": datetime.now(UTC),
        },
        synchronize_session=False,
    )
    if claimed != 1:
        existing = db.query(PendingAction.id).filter(PendingAction.id == payload.action_id).first()
        db.rollback()
        if not existing:
            raise HTTPException(status_code=404, detail="Pending action not found")
        raise HTTPException(status_code=409, detail="Pending action is no longer active")

    pending = db.query(PendingAction).filter(PendingAction.id == payload.action_id).first()
    if not pending:
        db.rollback()
        raise HTTPException(status_code=404, detail="Pending action not found")

    dialog = db.query(Dialog).filter(
        Dialog.id == pending.dialog_id,
        Dialog.pending_action_id == pending.id,
    ).first()
    if not dialog:
        db.rollback()
        raise HTTPException(status_code=409, detail="Pending action is no longer active")

    dialog.pending_action_id = None
    dialog.state = "running" if payload.decision == "confirm" else "chatting"
    db.commit()

    action_type = pending.type
    action_type = preview_action_to_execution(action_type)

    result_data = None
    if payload.decision == "confirm":
        project_id = (pending.params or {}).get("project_id", "")
        command_args = (pending.params or {}).get("command_args")
        if supports_dialog_agent_control_plane(action_type):
            dispatch = prepare_dialog_agent_run_dispatch(
                db,
                project_id=project_id,
                dialog_id=dialog.id,
                action_type=action_type,
                command_args=command_args,
                action_params=pending.params,
            )
            LocalTaskRunner().start(dispatch.task.id, dispatch.work)
            result_data = {
                "status": "generating",
                "task_id": dispatch.task.id,
                "agent_run_id": dispatch.run.id,
                "control_plane": {"version": CONTROL_PLANE_VERSION},
            }
        else:
            task = _execute_action_background(action_type, project_id, dialog.id, command_args=command_args, action_params=pending.params, db=db)
            result_data = {"status": "generating"}
            task_id = getattr(task, "id", None)
            if isinstance(task_id, str):
                result_data["task_id"] = task_id
    elif payload.decision == "cancel":
        result_data = {"status": "cancelled"}
    elif payload.decision == "revise":
        result_data = {"status": "revised", "comment": payload.comment}

    result_data["approval_decision"] = _approval_decision_metadata(pending, payload.decision, action_type)
    resolve_msg = _resolve_message(payload.decision)
    action_result = {
        "type": action_type,
        "status": result_data["status"],
        "data": result_data,
    }
    decision_message = _save_message(db, dialog.id, "system", resolve_msg, action_result)
    _link_run_request_message(db, result_data.get("agent_run_id"), decision_message.id)

    return {
        "dialog_state": "RUNNING" if payload.decision == "confirm" else "CHATTING",
        "action_result": action_result,
        "action_result_view": action_result_view(action_result),
        "message": resolve_msg,
        "ui_hint": build_ui_hint(
            action_type=action_type,
            dialog_state="RUNNING" if payload.decision == "confirm" else "CHATTING",
            status="running" if payload.decision == "confirm" else result_data["status"],
            reason="用户确认执行" if payload.decision == "confirm" else "操作已结束",
        ),
        "refresh_targets": action_to_refresh_targets(action_type, result_data["status"]),
    }


