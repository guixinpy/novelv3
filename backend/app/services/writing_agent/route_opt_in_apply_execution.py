import copy
from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from app.models import Dialog, PendingAction, Project
from app.services.actions.action_execution_service import SUPPORTED_ACTION_EXECUTION_TYPES
from app.services.writing_agent.agent_step_binding import build_agent_step_binding, verify_resource_binding_target
from app.services.writing_agent.approval_contract import (
    build_agent_plan_approval_contract,
    verify_agent_plan_approval_contract,
)
from app.services.writing_agent.approval_verification_event import build_approval_verification_event
from app.services.writing_agent.mutation_fingerprint import build_mutation_fingerprint
from app.services.writing_agent.slash_command_route import (
    blocked_pending_action_route_approval_opt_in_apply,
    blocked_pending_action_route_approval_opt_in_apply_preview,
    build_pending_action_route_approval_opt_in_apply_contract,
    completed_pending_action_route_approval_opt_in_apply,
    plan_agent_route_approval_opt_in,
    preview_pending_action_route_approval_opt_in_apply,
    verify_pending_action_route_approval_opt_in_apply_contract,
)

PREPARE_APPLY_ROUTE_OPT_IN_VERSION = "phase231.route_opt_in_apply_prepare.v1"
EXECUTE_APPLY_ROUTE_OPT_IN_WITH_APPROVAL_VERSION = "phase231.route_opt_in_apply_with_approval_execute.v1"
APPROVAL_GATE_VERSION = "phase231.route_opt_in_apply_agent_plan_approval.v1"
DIRECT_TOOL = "apply_pending_action_route_approval_opt_in"
PREPARE_TOOL = "prepare_apply_pending_action_route_approval_opt_in"
EXECUTE_TOOL = "execute_apply_pending_action_route_approval_opt_in_with_approval"

StaticAdapterToolNamesProvider = Callable[[], set[str]]


def prepare_apply_pending_action_route_approval_opt_in(
    db: Session,
    project_id: str,
    *,
    pending_action_id: str,
    static_adapter_tool_names_provider: StaticAdapterToolNamesProvider,
) -> dict[str, Any]:
    project = db.query(Project.id).filter(Project.id == project_id).first()
    if project is None:
        return {"status": "failed", "error": "Project not found", "project_id": project_id}

    route_contract = _build_route_apply_contract(
        db,
        project_id,
        pending_action_id=pending_action_id,
        static_adapter_tool_names_provider=static_adapter_tool_names_provider,
    )
    if route_contract.get("status") != "requires_confirmation":
        return _blocked_output(
            project_id,
            pending_action_id,
            reason=str((route_contract.get("trace") or {}).get("reason") or "route_apply_contract_not_required"),
            extra={"route_apply_contract": route_contract},
        )

    agent_plan = _apply_route_opt_in_agent_plan(project_id, pending_action_id)
    approval_contract = build_agent_plan_approval_contract(agent_plan)
    approval_hash = str(((approval_contract.get("approval") or {}).get("approval_contract_hash")) or "")
    first_step = agent_plan["steps"][0]
    return {
        "status": "approval_required",
        "prepare_version": PREPARE_APPLY_ROUTE_OPT_IN_VERSION,
        "project_id": project_id,
        "pending_action_id": pending_action_id,
        "target_type": "agent_route_approval_opt_in_apply",
        "route_apply_approval_contract": route_contract["approval_contract"],
        "route_apply_approval_contract_hash": route_contract["approval_contract_hash"],
        "route_apply_preview": route_contract.get("route_apply_preview"),
        "mutation_fingerprint": first_step.get("mutation_fingerprint"),
        "tool_call_id": first_step.get("tool_call_id"),
        "resource_binding": first_step.get("resource_binding"),
        "agent_plan": agent_plan,
        "agent_plan_approval_contract": approval_contract,
        "agent_plan_approval_contract_hash": approval_hash,
        "required_confirmation": {
            "confirm_execute": True,
            "route_apply_approval_contract_hash": route_contract["approval_contract_hash"],
            "agent_plan_approval_contract_hash": approval_hash,
        },
        "side_effects": {"executed": [], "skipped": [DIRECT_TOOL]},
        "recommended_next_tools": [EXECUTE_TOOL],
        "recommended_next_tool_calls": [
            {
                "tool_name": EXECUTE_TOOL,
                "visibility": "agent_internal",
                "requires_confirmation": True,
                "params": {
                    "pending_action_id": pending_action_id,
                    "confirm_execute": True,
                    "route_apply_approval_contract_hash": route_contract["approval_contract_hash"],
                    "route_apply_approval_contract": route_contract["approval_contract"],
                    "agent_plan_approval_contract_hash": approval_hash,
                    "agent_plan_approval_contract": approval_contract,
                },
            }
        ],
        "trace": {
            "selected_tools": [PREPARE_TOOL],
            "rejected_tools": [{"tool_name": DIRECT_TOOL, "reason": "approval_required_before_write"}],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }


def execute_apply_pending_action_route_approval_opt_in_with_approval(
    db: Session,
    project_id: str,
    *,
    pending_action_id: str,
    confirm_execute: bool,
    route_apply_approval_contract_hash: str | None,
    route_apply_approval_contract: dict[str, Any] | None,
    agent_plan_approval_contract_hash: str | None,
    agent_plan_approval_contract: dict[str, Any] | None,
    static_adapter_tool_names_provider: StaticAdapterToolNamesProvider,
    approval_tool_metadata_provider,
) -> dict[str, Any]:
    project = db.query(Project.id).filter(Project.id == project_id).first()
    if project is None:
        return {"status": "failed", "error": "Project not found", "project_id": project_id}
    if confirm_execute is not True:
        return _blocked_output(project_id, pending_action_id, reason="confirmation_required")
    if not route_apply_approval_contract_hash or not isinstance(route_apply_approval_contract, dict):
        return _blocked_output(project_id, pending_action_id, reason="route_apply_contract_required")
    if not agent_plan_approval_contract_hash or not isinstance(agent_plan_approval_contract, dict):
        return _blocked_output(project_id, pending_action_id, reason="agent_plan_approval_contract_required")
    if approval_tool_metadata_provider is None:
        return _blocked_output(project_id, pending_action_id, reason="agent_plan_tool_metadata_missing")

    route_contract = _build_route_apply_contract(
        db,
        project_id,
        pending_action_id=pending_action_id,
        static_adapter_tool_names_provider=static_adapter_tool_names_provider,
    )
    route_verification = verify_pending_action_route_approval_opt_in_apply_contract(
        approval_contract_hash=route_apply_approval_contract_hash,
        approval_contract=route_apply_approval_contract,
        recomputed_contract=route_contract,
    )
    if route_verification.get("status") != "ready":
        return _blocked_output(
            project_id,
            pending_action_id,
            reason=str(route_verification.get("reason") or "route_apply_contract_not_ready"),
            extra={
                "route_apply_preview": route_contract.get("route_apply_preview"),
                "route_apply_approval_verification": route_verification,
            },
        )

    agent_plan = _apply_route_opt_in_agent_plan(project_id, pending_action_id)
    agent_verification = verify_agent_plan_approval_contract(
        agent_plan,
        approval_contract_hash=agent_plan_approval_contract_hash,
        approval_contract=agent_plan_approval_contract,
        project_id=project_id,
        tool_metadata_by_name=approval_tool_metadata_provider(agent_plan),
    )
    if agent_verification.get("status") != "ready":
        return _blocked_output(
            project_id,
            pending_action_id,
            reason=str(agent_verification.get("reason") or "agent_plan_approval_not_ready"),
            extra={
                "route_apply_preview": route_contract.get("route_apply_preview"),
                "route_apply_approval_verification": route_verification,
                "agent_plan_approval_verification": agent_verification,
                "approval_verification_event": build_approval_verification_event(agent_verification),
            },
        )

    binding_check = verify_resource_binding_target(
        agent_verification,
        tool_name=DIRECT_TOOL,
        target_type="pending_action_route_opt_in",
        target_id=_target_id(pending_action_id),
    )
    if binding_check.get("status") != "ready":
        return _blocked_output(
            project_id,
            pending_action_id,
            reason=str(binding_check.get("reason") or "resource_binding_target_mismatch"),
            extra={
                "route_apply_preview": route_contract.get("route_apply_preview"),
                "route_apply_approval_verification": route_verification,
                "agent_plan_approval_verification": agent_verification,
                "approval_verification_event": build_approval_verification_event(agent_verification),
                "execution_resource_binding": binding_check,
            },
        )

    return _apply_route_opt_in(
        db,
        project_id,
        pending_action_id=pending_action_id,
        route_contract=route_contract,
        route_verification=route_verification,
        agent_verification=agent_verification,
        binding_check=binding_check,
    )


def blocked_apply_route_opt_in_requires_agent_plan(project_id: str, pending_action_id: str) -> dict[str, Any]:
    output = blocked_pending_action_route_approval_opt_in_apply(
        pending_action_id=pending_action_id,
        reason="approval_required_before_write",
    )
    output.update(
        {
            "project_id": project_id,
            "required_approval": {
                "prepare_tool": PREPARE_TOOL,
                "execute_tool": EXECUTE_TOOL,
                "approval_scope": "agent_plan_approval",
            },
            "side_effects": {"executed": [], "skipped": [DIRECT_TOOL]},
            "recommended_next_tools": [PREPARE_TOOL],
            "trace": {
                **(output.get("trace") if isinstance(output.get("trace"), dict) else {}),
                "selected_tools": [],
                "rejected_tools": [{"tool_name": DIRECT_TOOL, "reason": "approval_required_before_write"}],
                "source": "direct_agent_write_guard",
            },
        }
    )
    return output


def validate_direct_apply_route_opt_in_request(
    db: Session,
    project_id: str,
    *,
    pending_action_id: str,
    confirm_apply: bool,
    approval_contract_hash: str | None,
    approval_contract: dict[str, Any] | None,
    static_adapter_tool_names_provider: StaticAdapterToolNamesProvider,
) -> dict[str, Any]:
    if confirm_apply is not True:
        return blocked_pending_action_route_approval_opt_in_apply(
            pending_action_id=pending_action_id,
            reason="confirmation_required",
        )
    if not approval_contract_hash:
        return blocked_pending_action_route_approval_opt_in_apply(
            pending_action_id=pending_action_id,
            reason="approval_contract_hash_required",
        )
    if not isinstance(approval_contract, dict):
        return blocked_pending_action_route_approval_opt_in_apply(
            pending_action_id=pending_action_id,
            reason="approval_contract_required",
        )

    pending = db.query(PendingAction).filter(PendingAction.id == pending_action_id).first()
    if pending is None:
        return blocked_pending_action_route_approval_opt_in_apply(
            pending_action_id=pending_action_id,
            reason="pending_action_not_found",
        )
    dialog = db.query(Dialog).filter(Dialog.id == pending.dialog_id).first()
    if dialog is None or dialog.project_id != project_id:
        return blocked_pending_action_route_approval_opt_in_apply(
            pending_action_id=pending_action_id,
            reason="pending_action_not_found",
        )
    if pending.status != "pending" or pending.resolved_at is not None:
        return blocked_pending_action_route_approval_opt_in_apply(
            pending_action_id=pending.id,
            reason="pending_action_not_pending",
        )

    route_contract = _build_route_apply_contract(
        db,
        project_id,
        pending_action_id=pending.id,
        static_adapter_tool_names_provider=static_adapter_tool_names_provider,
    )
    route_verification = verify_pending_action_route_approval_opt_in_apply_contract(
        approval_contract_hash=approval_contract_hash,
        approval_contract=approval_contract,
        recomputed_contract=route_contract,
    )
    if route_verification.get("status") != "ready":
        return blocked_pending_action_route_approval_opt_in_apply(
            pending_action_id=pending.id,
            reason=str(route_verification.get("reason") or "approval_contract_not_ready"),
            route_apply_preview=route_contract.get("route_apply_preview"),
            approval_verification=route_verification,
        )
    route_apply_preview = route_contract.get("route_apply_preview")
    params_after = route_apply_preview.get("params_after") if isinstance(route_apply_preview, dict) else None
    params_diff = route_apply_preview.get("params_diff") if isinstance(route_apply_preview, dict) else None
    if not isinstance(params_after, dict) or not isinstance(params_diff, dict) or not params_diff:
        return blocked_pending_action_route_approval_opt_in_apply(
            pending_action_id=pending.id,
            reason="route_apply_contract_not_required",
            route_apply_preview=route_apply_preview if isinstance(route_apply_preview, dict) else None,
            approval_verification=route_verification,
        )
    return blocked_apply_route_opt_in_requires_agent_plan(project_id, pending.id)


def _apply_route_opt_in(
    db: Session,
    project_id: str,
    *,
    pending_action_id: str,
    route_contract: dict[str, Any],
    route_verification: dict[str, Any],
    agent_verification: dict[str, Any],
    binding_check: dict[str, Any],
) -> dict[str, Any]:
    pending = db.query(PendingAction).filter(PendingAction.id == pending_action_id).first()
    if pending is None:
        return _blocked_output(project_id, pending_action_id, reason="pending_action_not_found")
    dialog = db.query(Dialog).filter(Dialog.id == pending.dialog_id).first()
    if dialog is None or dialog.project_id != project_id:
        return _blocked_output(project_id, pending_action_id, reason="pending_action_not_found")
    if pending.status != "pending" or pending.resolved_at is not None:
        return _blocked_output(project_id, pending.id, reason="pending_action_not_pending")

    route_apply_preview = route_contract.get("route_apply_preview")
    params_after = route_apply_preview.get("params_after") if isinstance(route_apply_preview, dict) else None
    params_diff = route_apply_preview.get("params_diff") if isinstance(route_apply_preview, dict) else None
    if not isinstance(params_after, dict) or not isinstance(params_diff, dict) or not params_diff:
        return _blocked_output(
            project_id,
            pending.id,
            reason="route_apply_contract_not_required",
            extra={
                "route_apply_preview": route_apply_preview if isinstance(route_apply_preview, dict) else None,
                "route_apply_approval_verification": route_verification,
            },
        )

    params_before = copy.deepcopy(route_apply_preview.get("params_before") or {})
    params_after = copy.deepcopy(params_after)
    updated = (
        db.query(PendingAction)
        .filter(
            PendingAction.id == pending.id,
            PendingAction.status == "pending",
            PendingAction.resolved_at.is_(None),
            PendingAction.params == params_before,
        )
        .update({"params": params_after}, synchronize_session=False)
    )
    if updated != 1:
        db.rollback()
        return _blocked_output(
            project_id,
            pending.id,
            reason="pending_action_state_changed",
            extra={
                "route_apply_preview": route_apply_preview,
                "route_apply_approval_verification": route_verification,
                "agent_plan_approval_verification": agent_verification,
                "approval_verification_event": build_approval_verification_event(agent_verification),
                "execution_resource_binding": binding_check,
            },
        )
    db.commit()
    pending = db.query(PendingAction).populate_existing().filter(PendingAction.id == pending.id).first()
    db.refresh(pending)
    output = completed_pending_action_route_approval_opt_in_apply(
        pending_action_id=pending.id,
        pending_action_type=pending.type,
        params_before=params_before,
        params_after=copy.deepcopy(pending.params if isinstance(pending.params, dict) else params_after),
        params_diff=copy.deepcopy(params_diff),
        route_apply_preview=route_apply_preview,
        approval_verification=route_verification,
    )
    output.update(
        {
            "execute_version": EXECUTE_APPLY_ROUTE_OPT_IN_WITH_APPROVAL_VERSION,
            "project_id": project_id,
            "target_type": "agent_route_approval_opt_in_apply",
            "route_apply_approval_verification": route_verification,
            "agent_plan_approval_verification": agent_verification,
            "approval_verification_event": build_approval_verification_event(agent_verification),
            "execution_resource_binding": binding_check,
            "evidence": {
                **(output.get("evidence") if isinstance(output.get("evidence"), dict) else {}),
                "agent_plan_approval_verified": True,
                "route_apply_contract_verified": True,
                "execution_route": "static_adapter",
            },
            "side_effects": {"executed": [DIRECT_TOOL], "skipped": ["pending_action_execution"]},
            "trace": {
                **(output.get("trace") if isinstance(output.get("trace"), dict) else {}),
                "selected_tools": [EXECUTE_TOOL],
                "approval_gate_version": APPROVAL_GATE_VERSION,
            },
        }
    )
    return output


def _build_route_apply_contract(
    db: Session,
    project_id: str,
    *,
    pending_action_id: str,
    static_adapter_tool_names_provider: StaticAdapterToolNamesProvider,
) -> dict[str, Any]:
    pending = db.query(PendingAction).filter(PendingAction.id == pending_action_id).first()
    if pending is not None:
        dialog = db.query(Dialog).filter(Dialog.id == pending.dialog_id).first()
        if dialog is None or dialog.project_id != project_id:
            preview = blocked_pending_action_route_approval_opt_in_apply_preview(
                pending_action_id=pending_action_id,
                pending_action_type=None,
                pending_params=None,
                risk_code="pending_action_not_found",
            )
            return build_pending_action_route_approval_opt_in_apply_contract(
                project_id=project_id,
                route_apply_preview=preview,
                pending_status=None,
            )
    if pending is not None and pending.status != "pending":
        preview = blocked_pending_action_route_approval_opt_in_apply_preview(
            pending_action_id=pending.id,
            pending_action_type=pending.type,
            pending_params=pending.params if isinstance(pending.params, dict) else {},
            risk_code="pending_action_not_pending",
        )
        return build_pending_action_route_approval_opt_in_apply_contract(
            project_id=project_id,
            route_apply_preview=preview,
            pending_status=str(pending.status or ""),
        )

    preview = _route_apply_preview(
        db,
        project_id,
        pending_action_id=pending_action_id,
        static_adapter_tool_names_provider=static_adapter_tool_names_provider,
    )
    return build_pending_action_route_approval_opt_in_apply_contract(
        project_id=project_id,
        route_apply_preview=preview,
        pending_status=str(pending.status or "") if pending is not None else None,
    )


def _route_apply_preview(
    db: Session,
    project_id: str,
    *,
    pending_action_id: str,
    static_adapter_tool_names_provider: StaticAdapterToolNamesProvider,
) -> dict[str, Any]:
    pending = db.query(PendingAction).populate_existing().filter(PendingAction.id == pending_action_id).first()
    if pending is None:
        return blocked_pending_action_route_approval_opt_in_apply_preview(
            pending_action_id=pending_action_id,
            pending_action_type=None,
            pending_params=None,
            risk_code="pending_action_not_found",
        )
    dialog = db.query(Dialog).filter(Dialog.id == pending.dialog_id).first()
    if dialog is None or dialog.project_id != project_id:
        return blocked_pending_action_route_approval_opt_in_apply_preview(
            pending_action_id=pending_action_id,
            pending_action_type=pending.type,
            pending_params=None,
            risk_code="pending_action_not_found",
        )
    pending_params = pending.params if isinstance(pending.params, dict) else {}
    agent_route = pending_params.get("agent_route")
    if not isinstance(agent_route, dict):
        return blocked_pending_action_route_approval_opt_in_apply_preview(
            pending_action_id=pending.id,
            pending_action_type=pending.type,
            pending_params=pending_params,
            risk_code="pending_action_agent_route_missing",
        )
    if pending_params.get("use_agent_approval_chain") is False:
        return blocked_pending_action_route_approval_opt_in_apply_preview(
            pending_action_id=pending.id,
            pending_action_type=pending.type,
            pending_params=pending_params,
            risk_code="pending_action_top_level_override",
        )
    route_plan = plan_agent_route_approval_opt_in(
        action_type=str(pending.type or "").strip() or None,
        agent_route=agent_route,
        static_adapter_tool_names=static_adapter_tool_names_provider(),
        action_execution_tool_names=set(SUPPORTED_ACTION_EXECUTION_TYPES),
    )
    preview = preview_pending_action_route_approval_opt_in_apply(
        pending_action_id=pending.id,
        pending_action_type=pending.type,
        pending_params=pending_params,
        route_plan=route_plan,
    )
    preview["trace"] = {
        **preview.get("trace", {}),
        "pending_action_route_source": "pending_action",
    }
    return preview


def _apply_route_opt_in_agent_plan(project_id: str, pending_action_id: str) -> dict[str, Any]:
    params = {"pending_action_id": pending_action_id}
    plan_id = f"direct-apply-route-opt-in:{project_id}:pending:{pending_action_id}"
    mutation_fingerprint = build_mutation_fingerprint(project_id, DIRECT_TOOL, params)
    step = {
        "step_index": 1,
        "step_id": plan_id,
        "tool_name": DIRECT_TOOL,
        "approval_executor_tool_name": EXECUTE_TOOL,
        "params": params,
        "mutability": "guarded_write",
        "requires_confirmation": True,
        "mutation_fingerprint": mutation_fingerprint,
        "reason": "将 pending action route 切换到 Agent approval-chain opt-in。",
    }
    step.update(
        build_agent_step_binding(
            project_id=project_id,
            plan_id=plan_id,
            source_projection_id=None,
            step=step,
            mutation_fingerprint=mutation_fingerprint,
        )
    )
    return {
        "project_id": project_id,
        "intent_class": "direct_apply_route_opt_in",
        "trace": {
            "plan_id": plan_id,
            "source_projection_id": None,
            "planner_version": PREPARE_APPLY_ROUTE_OPT_IN_VERSION,
        },
        "steps": [step],
    }


def _blocked_output(
    project_id: str,
    pending_action_id: str,
    *,
    reason: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    output = blocked_pending_action_route_approval_opt_in_apply(
        pending_action_id=pending_action_id,
        reason=reason,
    )
    output.update(
        {
            "execute_version": EXECUTE_APPLY_ROUTE_OPT_IN_WITH_APPROVAL_VERSION,
            "project_id": project_id,
            "target_type": "agent_route_approval_opt_in_apply",
            "recommended_next_tools": [PREPARE_TOOL],
            "trace": {
                **(output.get("trace") if isinstance(output.get("trace"), dict) else {}),
                "selected_tools": [EXECUTE_TOOL],
                "rejected_tools": [{"tool_name": DIRECT_TOOL, "reason": reason}],
                "approval_gate_version": APPROVAL_GATE_VERSION,
            },
        }
    )
    if extra:
        output.update(extra)
    return output


def _target_id(pending_action_id: str) -> str:
    return f"pending_action_route_opt_in:{pending_action_id}"
