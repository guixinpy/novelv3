from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any

from app.schemas.writing_agent import WritingAgentToolRequest
from app.services.writing_agent.approval_tool_metadata import build_approval_tool_metadata_by_name
from app.services.writing_agent.tool_adapter_types import WritingAgentToolAdapter, WritingAgentToolContext
from app.services.writing_agent.tool_registry import build_agent_tool_plan


AdapterMetadataByNameProvider = Callable[[], dict[str, dict[str, Any]]]
StaticAdapterToolNamesProvider = Callable[[], set[str]]


def build_agent_core_tool_adapters(
    *,
    adapter_metadata_by_name_provider: AdapterMetadataByNameProvider,
    static_adapter_tool_names_provider: StaticAdapterToolNamesProvider,
) -> dict[str, WritingAgentToolAdapter]:
    return {
        "describe_agent_tools": WritingAgentToolAdapter(
            "describe_agent_tools",
            _describe_agent_tools(adapter_metadata_by_name_provider),
            category="preflight",
            mutability="read",
        ),
        "plan_writing_agent_run": WritingAgentToolAdapter(
            "plan_writing_agent_run",
            _plan_writing_agent_run,
            category="preflight",
            mutability="read",
        ),
        "plan_dialog_intent_agent_run": WritingAgentToolAdapter(
            "plan_dialog_intent_agent_run",
            _plan_dialog_intent_agent_run,
            category="preflight",
            mutability="read",
        ),
        "preview_agent_plan_approval_contract": WritingAgentToolAdapter(
            "preview_agent_plan_approval_contract",
            _preview_agent_plan_approval_contract,
            category="preflight",
            mutability="read",
        ),
        "verify_agent_plan_approval_contract": WritingAgentToolAdapter(
            "verify_agent_plan_approval_contract",
            _verify_agent_plan_approval_contract(adapter_metadata_by_name_provider),
            category="preflight",
            mutability="read",
        ),
        "plan_recovery_tools": WritingAgentToolAdapter(
            "plan_recovery_tools",
            _plan_recovery_tools,
            category="preflight",
            mutability="read",
        ),
        "plan_recommended_followups": WritingAgentToolAdapter(
            "plan_recommended_followups",
            _plan_recommended_followups,
            category="preflight",
            mutability="read",
        ),
        "inspect_agent_slash_command_route": WritingAgentToolAdapter(
            "inspect_agent_slash_command_route",
            _inspect_agent_slash_command_route(static_adapter_tool_names_provider),
            category="preflight",
            mutability="read",
        ),
        "inspect_agent_dialog_route_projection": WritingAgentToolAdapter(
            "inspect_agent_dialog_route_projection",
            _inspect_agent_dialog_route_projection(static_adapter_tool_names_provider),
            category="preflight",
            mutability="read",
        ),
        "inspect_agent_route_preference_projection": WritingAgentToolAdapter(
            "inspect_agent_route_preference_projection",
            _inspect_agent_route_preference_projection(static_adapter_tool_names_provider),
            category="preflight",
            mutability="read",
        ),
        "plan_agent_route_approval_opt_in": WritingAgentToolAdapter(
            "plan_agent_route_approval_opt_in",
            _plan_agent_route_approval_opt_in(static_adapter_tool_names_provider),
            category="preflight",
            mutability="read",
        ),
        "preview_pending_action_route_approval_opt_in_apply": WritingAgentToolAdapter(
            "preview_pending_action_route_approval_opt_in_apply",
            _preview_pending_action_route_approval_opt_in_apply(static_adapter_tool_names_provider),
            category="preflight",
            mutability="read",
        ),
        "preview_pending_action_route_approval_opt_in_apply_contract": WritingAgentToolAdapter(
            "preview_pending_action_route_approval_opt_in_apply_contract",
            _preview_pending_action_route_approval_opt_in_apply_contract(static_adapter_tool_names_provider),
            category="preflight",
            mutability="read",
        ),
        "apply_pending_action_route_approval_opt_in": WritingAgentToolAdapter(
            "apply_pending_action_route_approval_opt_in",
            _apply_pending_action_route_approval_opt_in(static_adapter_tool_names_provider),
            category="preflight",
            mutability="write",
        ),
        "inspect_agent_dialog_control_plane_projection": WritingAgentToolAdapter(
            "inspect_agent_dialog_control_plane_projection",
            _inspect_agent_dialog_control_plane_projection,
            category="preflight",
            mutability="read",
        ),
        "inspect_agent_intent_projection": WritingAgentToolAdapter(
            "inspect_agent_intent_projection",
            _inspect_agent_intent_projection,
            category="preflight",
            mutability="read",
        ),
        "inspect_agent_tool_contracts": WritingAgentToolAdapter(
            "inspect_agent_tool_contracts",
            _inspect_agent_tool_contracts(adapter_metadata_by_name_provider),
            category="preflight",
            mutability="read",
        ),
        "inspect_legacy_hermes_action_migration": WritingAgentToolAdapter(
            "inspect_legacy_hermes_action_migration",
            _inspect_legacy_hermes_action_migration(adapter_metadata_by_name_provider),
            category="preflight",
            mutability="read",
        ),
        "inspect_agent_write_gate_coverage": WritingAgentToolAdapter(
            "inspect_agent_write_gate_coverage",
            _inspect_agent_write_gate_coverage(adapter_metadata_by_name_provider),
            category="preflight",
            mutability="read",
        ),
        "inspect_agent_mutation_fingerprints": WritingAgentToolAdapter(
            "inspect_agent_mutation_fingerprints",
            _inspect_agent_mutation_fingerprints,
            category="preflight",
            mutability="read",
        ),
    }


def _describe_agent_tools(
    adapter_metadata_by_name_provider: AdapterMetadataByNameProvider,
) -> Callable[[WritingAgentToolContext, WritingAgentToolRequest], dict[str, Any]]:
    def describe_agent_tools_adapter(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
        chapter_index = _optional_int(tool.params.get("chapter_index"))
        return build_agent_tool_plan(
            context.db,
            context.project_id,
            chapter_index=chapter_index,
            adapter_metadata_by_name=adapter_metadata_by_name_provider(),
        )

    describe_agent_tools_adapter.__name__ = "_describe_agent_tools"
    return describe_agent_tools_adapter


def _plan_writing_agent_run(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.planner import build_writing_agent_run_plan

    chapter_index = _optional_int(tool.params.get("chapter_index"))
    intent = str(tool.params.get("intent") or "").strip() or None
    goal = str(tool.params.get("goal") or tool.command_args or "").strip() or "规划下一步写作"
    return build_writing_agent_run_plan(
        context.db,
        context.project_id,
        goal=goal,
        chapter_index=chapter_index,
        intent=intent,
    )


def _plan_dialog_intent_agent_run(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.dialog_intent_planner import (
        plan_dialog_intent_agent_run,
        project_diagnosis_from_params,
    )

    text = str(tool.params.get("text") or tool.command_args or "").strip()
    return plan_dialog_intent_agent_run(
        context.db,
        context.project_id,
        text=text,
        dialog_state=str(tool.params.get("dialog_state") or "chatting"),
        pending_action_id=str(tool.params.get("pending_action_id") or "").strip() or None,
        diagnosis=project_diagnosis_from_params(tool.params),
    )


def _preview_agent_plan_approval_contract(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.approval_contract import build_agent_plan_approval_contract

    plan = tool.params.get("plan")
    return build_agent_plan_approval_contract(plan if isinstance(plan, dict) else None)


def _verify_agent_plan_approval_contract(
    adapter_metadata_by_name_provider: AdapterMetadataByNameProvider,
) -> Callable[[WritingAgentToolContext, WritingAgentToolRequest], dict[str, Any]]:
    def verify_agent_plan_approval_contract_adapter(
        context: WritingAgentToolContext,
        tool: WritingAgentToolRequest,
    ) -> dict[str, Any]:
        from app.services.writing_agent.approval_contract import verify_agent_plan_approval_contract

        plan = tool.params.get("plan")
        approval_contract = tool.params.get("approval_contract")
        tool_metadata_by_name = build_approval_tool_metadata_by_name(
            plan if isinstance(plan, dict) else None,
            adapter_metadata_by_name=adapter_metadata_by_name_provider(),
        )
        return verify_agent_plan_approval_contract(
            plan if isinstance(plan, dict) else None,
            approval_contract_hash=str(tool.params.get("approval_contract_hash") or "").strip() or None,
            approval_contract=approval_contract if isinstance(approval_contract, dict) else None,
            project_id=context.project_id,
            tool_metadata_by_name=tool_metadata_by_name,
        )

    verify_agent_plan_approval_contract_adapter.__name__ = "_verify_agent_plan_approval_contract"
    return verify_agent_plan_approval_contract_adapter


def _plan_recovery_tools(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.recovery_planner import build_recovery_tool_plan

    run_id = str(tool.params.get("run_id") or "").strip() or None
    return build_recovery_tool_plan(context.db, context.project_id, run_id)


def _plan_recommended_followups(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.recommended_followup_planner import build_recommended_followup_tool_plan

    run_id = str(tool.params.get("run_id") or "").strip() or None
    return build_recommended_followup_tool_plan(context.db, context.project_id, run_id)


def _inspect_agent_slash_command_route(
    static_adapter_tool_names_provider: StaticAdapterToolNamesProvider,
) -> Callable[[WritingAgentToolContext, WritingAgentToolRequest], dict[str, Any]]:
    def inspect_agent_slash_command_route_adapter(
        context: WritingAgentToolContext,
        tool: WritingAgentToolRequest,
    ) -> dict[str, Any]:
        from app.services.actions.action_execution_service import SUPPORTED_ACTION_EXECUTION_TYPES
        from app.services.writing_agent.slash_command_route import inspect_agent_slash_command_route

        return inspect_agent_slash_command_route(
            command_name=str(tool.params.get("command_name") or "").strip() or None,
            static_adapter_tool_names=static_adapter_tool_names_provider(),
            action_execution_tool_names=set(SUPPORTED_ACTION_EXECUTION_TYPES),
        )

    inspect_agent_slash_command_route_adapter.__name__ = "_inspect_agent_slash_command_route"
    return inspect_agent_slash_command_route_adapter


def _inspect_agent_dialog_route_projection(
    static_adapter_tool_names_provider: StaticAdapterToolNamesProvider,
) -> Callable[[WritingAgentToolContext, WritingAgentToolRequest], dict[str, Any]]:
    def inspect_agent_dialog_route_projection_adapter(
        context: WritingAgentToolContext,
        tool: WritingAgentToolRequest,
    ) -> dict[str, Any]:
        from app.services.actions.action_execution_service import SUPPORTED_ACTION_EXECUTION_TYPES
        from app.services.writing_agent.slash_command_route import inspect_agent_dialog_route_projection

        return inspect_agent_dialog_route_projection(
            source=str(tool.params.get("source") or "").strip() or None,
            static_adapter_tool_names=static_adapter_tool_names_provider(),
            action_execution_tool_names=set(SUPPORTED_ACTION_EXECUTION_TYPES),
        )

    inspect_agent_dialog_route_projection_adapter.__name__ = "_inspect_agent_dialog_route_projection"
    return inspect_agent_dialog_route_projection_adapter


def _inspect_agent_route_preference_projection(
    static_adapter_tool_names_provider: StaticAdapterToolNamesProvider,
) -> Callable[[WritingAgentToolContext, WritingAgentToolRequest], dict[str, Any]]:
    def inspect_agent_route_preference_projection_adapter(
        context: WritingAgentToolContext,
        tool: WritingAgentToolRequest,
    ) -> dict[str, Any]:
        from app.services.actions.action_execution_service import SUPPORTED_ACTION_EXECUTION_TYPES
        from app.services.writing_agent.slash_command_route import inspect_agent_route_preference_projection

        return inspect_agent_route_preference_projection(
            source=str(tool.params.get("source") or "").strip() or None,
            approval_chain_opt_in_action_types=tool.params.get("approval_chain_opt_in_action_types"),
            static_adapter_tool_names=static_adapter_tool_names_provider(),
            action_execution_tool_names=set(SUPPORTED_ACTION_EXECUTION_TYPES),
        )

    inspect_agent_route_preference_projection_adapter.__name__ = "_inspect_agent_route_preference_projection"
    return inspect_agent_route_preference_projection_adapter


def _plan_agent_route_approval_opt_in(
    static_adapter_tool_names_provider: StaticAdapterToolNamesProvider,
) -> Callable[[WritingAgentToolContext, WritingAgentToolRequest], dict[str, Any]]:
    def plan_agent_route_approval_opt_in_adapter(
        context: WritingAgentToolContext,
        tool: WritingAgentToolRequest,
    ) -> dict[str, Any]:
        from app.services.actions.action_execution_service import SUPPORTED_ACTION_EXECUTION_TYPES
        from app.services.writing_agent.slash_command_route import plan_agent_route_approval_opt_in

        pending_action_id = str(tool.params.get("pending_action_id") or "").strip()
        agent_route = tool.params.get("agent_route")
        if pending_action_id:
            from app.models import Dialog, PendingAction

            pending = context.db.query(PendingAction).filter(PendingAction.id == pending_action_id).first()
            if pending is None:
                output = plan_agent_route_approval_opt_in(
                    static_adapter_tool_names=static_adapter_tool_names_provider(),
                    action_execution_tool_names=set(SUPPORTED_ACTION_EXECUTION_TYPES),
                )
                output["risk"] = {
                    "codes": ["pending_action_not_found"],
                    "missing_preferred_tools": [],
                    "guardrails": output.get("risk", {}).get("guardrails", []),
                }
                output["trace"] = {**output.get("trace", {}), "pending_action_id": pending_action_id}
                return output
            dialog = context.db.query(Dialog).filter(Dialog.id == pending.dialog_id).first()
            if dialog is None or dialog.project_id != context.project_id:
                output = plan_agent_route_approval_opt_in(
                    static_adapter_tool_names=static_adapter_tool_names_provider(),
                    action_execution_tool_names=set(SUPPORTED_ACTION_EXECUTION_TYPES),
                )
                output["risk"] = {
                    "codes": ["pending_action_not_found"],
                    "missing_preferred_tools": [],
                    "guardrails": output.get("risk", {}).get("guardrails", []),
                }
                output["trace"] = {**output.get("trace", {}), "pending_action_id": pending_action_id}
                return output
            pending_params = pending.params if isinstance(pending.params, dict) else {}
            agent_route = pending_params.get("agent_route")
            output = plan_agent_route_approval_opt_in(
                action_type=str(pending.type or "").strip() or None,
                agent_route=agent_route if isinstance(agent_route, dict) else None,
                static_adapter_tool_names=static_adapter_tool_names_provider(),
                action_execution_tool_names=set(SUPPORTED_ACTION_EXECUTION_TYPES),
            )
            output["trace"] = {
                **output.get("trace", {}),
                "pending_action_id": pending.id,
                "pending_action_type": pending.type,
                "pending_action_route_source": "pending_action",
            }
            return output

        return plan_agent_route_approval_opt_in(
            action_type=str(tool.params.get("action_type") or "").strip() or None,
            source=str(tool.params.get("source") or "").strip() or None,
            command_name=str(tool.params.get("command_name") or "").strip() or None,
            agent_route=agent_route if isinstance(agent_route, dict) else None,
            static_adapter_tool_names=static_adapter_tool_names_provider(),
            action_execution_tool_names=set(SUPPORTED_ACTION_EXECUTION_TYPES),
        )

    plan_agent_route_approval_opt_in_adapter.__name__ = "_plan_agent_route_approval_opt_in"
    return plan_agent_route_approval_opt_in_adapter


def _preview_pending_action_route_approval_opt_in_apply(
    static_adapter_tool_names_provider: StaticAdapterToolNamesProvider,
) -> Callable[[WritingAgentToolContext, WritingAgentToolRequest], dict[str, Any]]:
    def preview_pending_action_route_approval_opt_in_apply_adapter(
        context: WritingAgentToolContext,
        tool: WritingAgentToolRequest,
    ) -> dict[str, Any]:
        from app.models import Dialog, PendingAction
        from app.services.actions.action_execution_service import SUPPORTED_ACTION_EXECUTION_TYPES
        from app.services.writing_agent.slash_command_route import (
            blocked_pending_action_route_approval_opt_in_apply_preview,
            plan_agent_route_approval_opt_in,
            preview_pending_action_route_approval_opt_in_apply,
        )

        pending_action_id = str(tool.params.get("pending_action_id") or "").strip()
        pending = (
            context.db.query(PendingAction)
            .populate_existing()
            .filter(PendingAction.id == pending_action_id)
            .first()
        )
        if pending is None:
            return blocked_pending_action_route_approval_opt_in_apply_preview(
                pending_action_id=pending_action_id,
                pending_action_type=None,
                pending_params=None,
                risk_code="pending_action_not_found",
            )
        dialog = context.db.query(Dialog).filter(Dialog.id == pending.dialog_id).first()
        if dialog is None or dialog.project_id != context.project_id:
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

    preview_pending_action_route_approval_opt_in_apply_adapter.__name__ = (
        "_preview_pending_action_route_approval_opt_in_apply"
    )
    return preview_pending_action_route_approval_opt_in_apply_adapter


def _preview_pending_action_route_approval_opt_in_apply_contract(
    static_adapter_tool_names_provider: StaticAdapterToolNamesProvider,
) -> Callable[[WritingAgentToolContext, WritingAgentToolRequest], dict[str, Any]]:
    def preview_pending_action_route_approval_opt_in_apply_contract_adapter(
        context: WritingAgentToolContext,
        tool: WritingAgentToolRequest,
    ) -> dict[str, Any]:
        from app.models import Dialog, PendingAction
        from app.services.writing_agent.slash_command_route import (
            build_pending_action_route_approval_opt_in_apply_contract,
            blocked_pending_action_route_approval_opt_in_apply_preview,
        )

        pending_action_id = str(tool.params.get("pending_action_id") or "").strip()
        pending = context.db.query(PendingAction).filter(PendingAction.id == pending_action_id).first()
        if pending is not None:
            dialog = context.db.query(Dialog).filter(Dialog.id == pending.dialog_id).first()
            if dialog is None or dialog.project_id != context.project_id:
                preview = blocked_pending_action_route_approval_opt_in_apply_preview(
                    pending_action_id=pending_action_id,
                    pending_action_type=None,
                    pending_params=None,
                    risk_code="pending_action_not_found",
                )
                return build_pending_action_route_approval_opt_in_apply_contract(
                    project_id=context.project_id,
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
                project_id=context.project_id,
                route_apply_preview=preview,
                pending_status=str(pending.status or ""),
            )

        preview = _preview_pending_action_route_approval_opt_in_apply(static_adapter_tool_names_provider)(context, tool)
        return build_pending_action_route_approval_opt_in_apply_contract(
            project_id=context.project_id,
            route_apply_preview=preview,
            pending_status=str(pending.status or "") if pending is not None else None,
        )

    preview_pending_action_route_approval_opt_in_apply_contract_adapter.__name__ = (
        "_preview_pending_action_route_approval_opt_in_apply_contract"
    )
    return preview_pending_action_route_approval_opt_in_apply_contract_adapter


def _apply_pending_action_route_approval_opt_in(
    static_adapter_tool_names_provider: StaticAdapterToolNamesProvider,
) -> Callable[[WritingAgentToolContext, WritingAgentToolRequest], dict[str, Any]]:
    def apply_pending_action_route_approval_opt_in_adapter(
        context: WritingAgentToolContext,
        tool: WritingAgentToolRequest,
    ) -> dict[str, Any]:
        from app.models import Dialog, PendingAction
        from app.services.writing_agent.slash_command_route import (
            blocked_pending_action_route_approval_opt_in_apply,
            build_pending_action_route_approval_opt_in_apply_contract,
            completed_pending_action_route_approval_opt_in_apply,
            verify_pending_action_route_approval_opt_in_apply_contract,
        )

        pending_action_id = str(tool.params.get("pending_action_id") or "").strip()
        if tool.params.get("confirm_apply") is not True:
            return blocked_pending_action_route_approval_opt_in_apply(
                pending_action_id=pending_action_id,
                reason="confirmation_required",
            )
        approval_contract_hash = str(tool.params.get("approval_contract_hash") or "").strip() or None
        if not approval_contract_hash:
            return blocked_pending_action_route_approval_opt_in_apply(
                pending_action_id=pending_action_id,
                reason="approval_contract_hash_required",
            )
        approval_contract = tool.params.get("approval_contract")
        if not isinstance(approval_contract, dict):
            return blocked_pending_action_route_approval_opt_in_apply(
                pending_action_id=pending_action_id,
                reason="approval_contract_required",
            )

        pending = context.db.query(PendingAction).filter(PendingAction.id == pending_action_id).first()
        if pending is None:
            return blocked_pending_action_route_approval_opt_in_apply(
                pending_action_id=pending_action_id,
                reason="pending_action_not_found",
            )
        dialog = context.db.query(Dialog).filter(Dialog.id == pending.dialog_id).first()
        if dialog is None or dialog.project_id != context.project_id:
            return blocked_pending_action_route_approval_opt_in_apply(
                pending_action_id=pending_action_id,
                reason="pending_action_not_found",
            )
        if pending.status != "pending" or pending.resolved_at is not None:
            return blocked_pending_action_route_approval_opt_in_apply(
                pending_action_id=pending.id,
                reason="pending_action_not_pending",
            )

        route_apply_preview = _preview_pending_action_route_approval_opt_in_apply(static_adapter_tool_names_provider)(
            context,
            tool,
        )
        recomputed_contract = build_pending_action_route_approval_opt_in_apply_contract(
            project_id=context.project_id,
            route_apply_preview=route_apply_preview,
            pending_status=str(pending.status or ""),
        )
        approval_verification = verify_pending_action_route_approval_opt_in_apply_contract(
            approval_contract_hash=approval_contract_hash,
            approval_contract=approval_contract,
            recomputed_contract=recomputed_contract,
        )
        if approval_verification.get("status") != "ready":
            return blocked_pending_action_route_approval_opt_in_apply(
                pending_action_id=pending.id,
                reason=str(approval_verification.get("reason") or "approval_contract_not_ready"),
                route_apply_preview=route_apply_preview,
                approval_verification=approval_verification,
            )
        params_after = route_apply_preview.get("params_after")
        params_diff = route_apply_preview.get("params_diff")
        if not isinstance(params_after, dict) or not isinstance(params_diff, dict) or not params_diff:
            return blocked_pending_action_route_approval_opt_in_apply(
                pending_action_id=pending.id,
                reason="route_apply_contract_not_required",
                route_apply_preview=route_apply_preview,
                approval_verification=approval_verification,
            )
        params_before = copy.deepcopy(route_apply_preview.get("params_before") or {})
        params_after = copy.deepcopy(params_after)
        updated = (
            context.db.query(PendingAction)
            .filter(
                PendingAction.id == pending.id,
                PendingAction.status == "pending",
                PendingAction.resolved_at.is_(None),
                PendingAction.params == params_before,
            )
            .update({"params": params_after}, synchronize_session=False)
        )
        if updated != 1:
            context.db.rollback()
            return blocked_pending_action_route_approval_opt_in_apply(
                pending_action_id=pending.id,
                reason="pending_action_state_changed",
                route_apply_preview=route_apply_preview,
                approval_verification=approval_verification,
            )
        context.db.commit()
        pending = (
            context.db.query(PendingAction)
            .populate_existing()
            .filter(PendingAction.id == pending.id)
            .first()
        )
        context.db.refresh(pending)
        return completed_pending_action_route_approval_opt_in_apply(
            pending_action_id=pending.id,
            pending_action_type=pending.type,
            params_before=params_before,
            params_after=copy.deepcopy(pending.params if isinstance(pending.params, dict) else params_after),
            params_diff=copy.deepcopy(params_diff),
            route_apply_preview=route_apply_preview,
            approval_verification=approval_verification,
        )

    apply_pending_action_route_approval_opt_in_adapter.__name__ = "_apply_pending_action_route_approval_opt_in"
    return apply_pending_action_route_approval_opt_in_adapter


def _inspect_agent_dialog_control_plane_projection(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.dialog_control_plane import inspect_agent_dialog_control_plane_projection

    return inspect_agent_dialog_control_plane_projection(
        action_type=str(tool.params.get("action_type") or "").strip() or None,
    )


def _inspect_agent_intent_projection(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.core.intent_router import IntentRouter
    from app.schemas import ProjectDiagnosisOut
    from app.services.workspace.bootstrap import build_project_diagnosis

    text = str(tool.params.get("text") or tool.command_args or "").strip()
    if "missing_items" in tool.params or "completed_items" in tool.params or "suggested_next_step" in tool.params:
        diagnosis = ProjectDiagnosisOut(
            missing_items=_string_list(tool.params.get("missing_items")),
            completed_items=_string_list(tool.params.get("completed_items")),
            suggested_next_step=str(tool.params.get("suggested_next_step") or "").strip() or None,
        )
    else:
        diagnosis = build_project_diagnosis(context.db, context.project_id)
    return IntentRouter().project(
        text,
        str(tool.params.get("dialog_state") or "chatting"),
        str(tool.params.get("pending_action_id") or "").strip() or None,
        diagnosis,
    ).to_dict()


def _inspect_agent_tool_contracts(
    adapter_metadata_by_name_provider: AdapterMetadataByNameProvider,
) -> Callable[[WritingAgentToolContext, WritingAgentToolRequest], dict[str, Any]]:
    def inspect_agent_tool_contracts_adapter(
        context: WritingAgentToolContext,
        tool: WritingAgentToolRequest,
    ) -> dict[str, Any]:
        from app.services.writing_agent.tool_contracts import build_agent_tool_contract_snapshot

        adapter_metadata = dict(adapter_metadata_by_name_provider())
        adapter_metadata["preflight_writing"] = _preflight_writing_adapter_metadata()
        return build_agent_tool_contract_snapshot(
            adapter_metadata_by_name=adapter_metadata,
            include_gap_details=tool.params.get("include_gap_details") is not False,
        )

    inspect_agent_tool_contracts_adapter.__name__ = "_inspect_agent_tool_contracts"
    return inspect_agent_tool_contracts_adapter


def _inspect_agent_write_gate_coverage(
    adapter_metadata_by_name_provider: AdapterMetadataByNameProvider,
) -> Callable[[WritingAgentToolContext, WritingAgentToolRequest], dict[str, Any]]:
    def inspect_agent_write_gate_coverage_adapter(
        context: WritingAgentToolContext,
        tool: WritingAgentToolRequest,
    ) -> dict[str, Any]:
        from app.services.writing_agent.write_gate_coverage import inspect_agent_write_gate_coverage

        return inspect_agent_write_gate_coverage(adapter_metadata_by_name=adapter_metadata_by_name_provider())

    inspect_agent_write_gate_coverage_adapter.__name__ = "_inspect_agent_write_gate_coverage"
    return inspect_agent_write_gate_coverage_adapter


def _inspect_legacy_hermes_action_migration(
    adapter_metadata_by_name_provider: AdapterMetadataByNameProvider,
) -> Callable[[WritingAgentToolContext, WritingAgentToolRequest], dict[str, Any]]:
    def inspect_legacy_hermes_action_migration_adapter(
        context: WritingAgentToolContext,
        tool: WritingAgentToolRequest,
    ) -> dict[str, Any]:
        from app.services.writing_agent.legacy_hermes_migration_projection import (
            inspect_legacy_hermes_action_migration,
        )

        return inspect_legacy_hermes_action_migration(
            adapter_metadata_by_name=dict(adapter_metadata_by_name_provider()),
        )

    inspect_legacy_hermes_action_migration_adapter.__name__ = "_inspect_legacy_hermes_action_migration"
    return inspect_legacy_hermes_action_migration_adapter


def _inspect_agent_mutation_fingerprints(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.mutation_fingerprint import inspect_agent_mutation_fingerprints

    return inspect_agent_mutation_fingerprints(context.project_id, tool.params.get("tools"))


def _preflight_writing_adapter_metadata() -> dict[str, Any]:
    return {
        "tool_name": "preflight_writing",
        "adapter_type": "injected",
        "category": "preflight",
        "mutability": "read",
        "handler_name": "preflight_writing",
    }


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]
