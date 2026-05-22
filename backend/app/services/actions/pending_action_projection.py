from app.services.actions.action_result_view import TYPE_LABELS


def pending_action_execution_preview(params: dict | None) -> dict | None:
    if not isinstance(params, dict):
        return None
    contract = params.get("approval_contract")
    if not isinstance(contract, dict):
        return None

    write_steps = contract.get("write_steps")
    if not isinstance(write_steps, list) or not write_steps:
        return None

    steps = [_step_preview(step) for step in write_steps if isinstance(step, dict)]
    if not steps:
        return None

    approval = contract.get("approval") if isinstance(contract.get("approval"), dict) else {}
    approval_hash = params.get("approval_contract_hash") or approval.get("approval_contract_hash")
    audit = _audit_preview(contract, approval_hash)
    first_label = steps[0]["label"]
    write_step_count = len(steps)
    return {
        "kind": "approval_contract",
        "title": f"待执行：{first_label}" if write_step_count == 1 else f"待执行：{write_step_count} 个写入步骤",
        "summary": f"确认后将执行 {write_step_count} 个写入步骤。",
        "write_step_count": write_step_count,
        "approval_contract_hash": approval_hash,
        "audit": audit,
        "steps": steps,
    }


def _step_preview(step: dict) -> dict:
    tool_name = str(step.get("tool_name") or "").strip()
    params = step.get("params") if isinstance(step.get("params"), dict) else {}
    return {
        "step_id": str(step.get("step_id") or "").strip(),
        "step_index": step.get("step_index"),
        "tool_name": tool_name,
        "label": TYPE_LABELS.get(tool_name, tool_name or "未命名步骤"),
        "reason": str(step.get("reason") or "").strip(),
        "params": params,
    }


def _audit_preview(contract: dict, approval_hash: str | None) -> dict:
    trace = contract.get("trace") if isinstance(contract.get("trace"), dict) else {}
    return {
        "kind": "approval_contract",
        "approval_contract_hash": approval_hash,
        "approval_contract_version": contract.get("version"),
        "plan_id": contract.get("plan_id"),
        "source_projection_id": contract.get("source_projection_id"),
        "planner_version": trace.get("planner_version"),
        "intent_class": trace.get("intent_class"),
    }
