from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import Project
from app.services.writing_agent.agent_step_binding import build_agent_step_binding, verify_resource_binding_target
from app.services.writing_agent.approval_contract import (
    build_agent_plan_approval_contract,
    verify_agent_plan_approval_contract,
)
from app.services.writing_agent.approval_verification_event import build_approval_verification_event
from app.services.writing_agent.chapter_compression_tool import compress_chapter_to_target_tool
from app.services.writing_agent.chapter_expansion_tool import expand_chapter_to_target_tool
from app.services.writing_agent.mutation_fingerprint import build_mutation_fingerprint

PREPARE_EXPAND_CHAPTER_TO_TARGET_EXECUTION_VERSION = "phase196.chapter_expansion_execution_prepare.v1"
EXECUTE_EXPAND_CHAPTER_TO_TARGET_WITH_APPROVAL_VERSION = "phase196.chapter_expansion_with_approval_execute.v1"
EXPAND_CHAPTER_APPROVAL_GATE_VERSION = "phase196.chapter_expansion_agent_plan_approval.v1"
PREPARE_COMPRESS_CHAPTER_TO_TARGET_EXECUTION_VERSION = "phase197.chapter_compression_execution_prepare.v1"
EXECUTE_COMPRESS_CHAPTER_TO_TARGET_WITH_APPROVAL_VERSION = "phase197.chapter_compression_with_approval_execute.v1"
COMPRESS_CHAPTER_APPROVAL_GATE_VERSION = "phase197.chapter_compression_agent_plan_approval.v1"


def prepare_expand_chapter_to_target_execution(
    db: Session,
    project_id: str,
    *,
    chapter_index: int,
    min_word_count: int | None = None,
    extra_instruction: str = "",
) -> dict[str, Any]:
    project = db.query(Project.id).filter(Project.id == project_id).first()
    if project is None:
        return {"status": "failed", "error": "Project not found", "project_id": project_id}

    params = _expand_params(
        chapter_index=chapter_index,
        min_word_count=min_word_count,
        extra_instruction=extra_instruction,
    )
    agent_plan = _direct_chapter_revision_agent_plan(
        project_id,
        tool_name="expand_chapter_to_target",
        approval_executor_tool_name="execute_expand_chapter_to_target_with_approval",
        chapter_index=chapter_index,
        params=params,
        reason="扩写章节正文并写入新章节版本。",
        planner_version=PREPARE_EXPAND_CHAPTER_TO_TARGET_EXECUTION_VERSION,
    )
    return _prepare_output(
        project_id=project_id,
        chapter_index=chapter_index,
        tool_name="expand_chapter_to_target",
        prepare_tool_name="prepare_expand_chapter_to_target_execution",
        execute_tool_name="execute_expand_chapter_to_target_with_approval",
        prepare_version=PREPARE_EXPAND_CHAPTER_TO_TARGET_EXECUTION_VERSION,
        approval_gate_version=EXPAND_CHAPTER_APPROVAL_GATE_VERSION,
        agent_plan=agent_plan,
    )


async def execute_expand_chapter_to_target_with_approval(
    db: Session,
    project_id: str,
    *,
    chapter_index: int,
    min_word_count: int | None = None,
    extra_instruction: str = "",
    confirm_execute: bool,
    approval_contract_hash: str | None,
    approval_contract: dict[str, Any] | None,
    approval_tool_metadata_provider,
) -> dict[str, Any]:
    params = _expand_params(
        chapter_index=chapter_index,
        min_word_count=min_word_count,
        extra_instruction=extra_instruction,
    )
    agent_plan = _direct_chapter_revision_agent_plan(
        project_id,
        tool_name="expand_chapter_to_target",
        approval_executor_tool_name="execute_expand_chapter_to_target_with_approval",
        chapter_index=chapter_index,
        params=params,
        reason="扩写章节正文并写入新章节版本。",
        planner_version=PREPARE_EXPAND_CHAPTER_TO_TARGET_EXECUTION_VERSION,
    )
    ready = _verify_execution_ready(
        db,
        project_id,
        chapter_index=chapter_index,
        tool_name="expand_chapter_to_target",
        execute_tool_name="execute_expand_chapter_to_target_with_approval",
        execute_version=EXECUTE_EXPAND_CHAPTER_TO_TARGET_WITH_APPROVAL_VERSION,
        approval_gate_version=EXPAND_CHAPTER_APPROVAL_GATE_VERSION,
        agent_plan=agent_plan,
        confirm_execute=confirm_execute,
        approval_contract_hash=approval_contract_hash,
        approval_contract=approval_contract,
        approval_tool_metadata_provider=approval_tool_metadata_provider,
    )
    if ready.get("status") != "ready":
        return ready

    result = await expand_chapter_to_target_tool(
        db,
        project_id,
        chapter_index=chapter_index,
        min_word_count=min_word_count,
        extra_instruction=str(extra_instruction or ""),
    )
    return _approved_output(
        result,
        project_id=project_id,
        tool_name="expand_chapter_to_target",
        execute_tool_name="execute_expand_chapter_to_target_with_approval",
        execute_version=EXECUTE_EXPAND_CHAPTER_TO_TARGET_WITH_APPROVAL_VERSION,
        approval_gate_version=EXPAND_CHAPTER_APPROVAL_GATE_VERSION,
        verification=ready["agent_plan_approval_verification"],
        binding_check=ready["execution_resource_binding"],
    )


def prepare_compress_chapter_to_target_execution(
    db: Session,
    project_id: str,
    *,
    chapter_index: int,
    target_max_word_count: int | None = None,
    extra_instruction: str = "",
    forbidden_terms: list[str] | None = None,
) -> dict[str, Any]:
    project = db.query(Project.id).filter(Project.id == project_id).first()
    if project is None:
        return {"status": "failed", "error": "Project not found", "project_id": project_id}

    params = _compress_params(
        chapter_index=chapter_index,
        target_max_word_count=target_max_word_count,
        extra_instruction=extra_instruction,
        forbidden_terms=forbidden_terms,
    )
    agent_plan = _direct_chapter_revision_agent_plan(
        project_id,
        tool_name="compress_chapter_to_target",
        approval_executor_tool_name="execute_compress_chapter_to_target_with_approval",
        chapter_index=chapter_index,
        params=params,
        reason="压缩章节正文并写入新章节版本。",
        planner_version=PREPARE_COMPRESS_CHAPTER_TO_TARGET_EXECUTION_VERSION,
    )
    return _prepare_output(
        project_id=project_id,
        chapter_index=chapter_index,
        tool_name="compress_chapter_to_target",
        prepare_tool_name="prepare_compress_chapter_to_target_execution",
        execute_tool_name="execute_compress_chapter_to_target_with_approval",
        prepare_version=PREPARE_COMPRESS_CHAPTER_TO_TARGET_EXECUTION_VERSION,
        approval_gate_version=COMPRESS_CHAPTER_APPROVAL_GATE_VERSION,
        agent_plan=agent_plan,
    )


async def execute_compress_chapter_to_target_with_approval(
    db: Session,
    project_id: str,
    *,
    chapter_index: int,
    target_max_word_count: int | None = None,
    extra_instruction: str = "",
    forbidden_terms: list[str] | None = None,
    confirm_execute: bool,
    approval_contract_hash: str | None,
    approval_contract: dict[str, Any] | None,
    approval_tool_metadata_provider,
) -> dict[str, Any]:
    params = _compress_params(
        chapter_index=chapter_index,
        target_max_word_count=target_max_word_count,
        extra_instruction=extra_instruction,
        forbidden_terms=forbidden_terms,
    )
    agent_plan = _direct_chapter_revision_agent_plan(
        project_id,
        tool_name="compress_chapter_to_target",
        approval_executor_tool_name="execute_compress_chapter_to_target_with_approval",
        chapter_index=chapter_index,
        params=params,
        reason="压缩章节正文并写入新章节版本。",
        planner_version=PREPARE_COMPRESS_CHAPTER_TO_TARGET_EXECUTION_VERSION,
    )
    ready = _verify_execution_ready(
        db,
        project_id,
        chapter_index=chapter_index,
        tool_name="compress_chapter_to_target",
        execute_tool_name="execute_compress_chapter_to_target_with_approval",
        execute_version=EXECUTE_COMPRESS_CHAPTER_TO_TARGET_WITH_APPROVAL_VERSION,
        approval_gate_version=COMPRESS_CHAPTER_APPROVAL_GATE_VERSION,
        agent_plan=agent_plan,
        confirm_execute=confirm_execute,
        approval_contract_hash=approval_contract_hash,
        approval_contract=approval_contract,
        approval_tool_metadata_provider=approval_tool_metadata_provider,
    )
    if ready.get("status") != "ready":
        return ready

    result = await compress_chapter_to_target_tool(
        db,
        project_id,
        chapter_index=chapter_index,
        target_max_word_count=target_max_word_count,
        extra_instruction=str(extra_instruction or ""),
        forbidden_terms=params["forbidden_terms"],
    )
    return _approved_output(
        result,
        project_id=project_id,
        tool_name="compress_chapter_to_target",
        execute_tool_name="execute_compress_chapter_to_target_with_approval",
        execute_version=EXECUTE_COMPRESS_CHAPTER_TO_TARGET_WITH_APPROVAL_VERSION,
        approval_gate_version=COMPRESS_CHAPTER_APPROVAL_GATE_VERSION,
        verification=ready["agent_plan_approval_verification"],
        binding_check=ready["execution_resource_binding"],
    )


def _direct_chapter_revision_agent_plan(
    project_id: str,
    *,
    tool_name: str,
    approval_executor_tool_name: str,
    chapter_index: int,
    params: dict[str, Any],
    reason: str,
    planner_version: str,
) -> dict[str, Any]:
    plan_id = f"direct-{tool_name.replace('_', '-')}:{project_id}:chapter:{chapter_index}"
    mutation_fingerprint = build_mutation_fingerprint(project_id, tool_name, params)
    step = {
        "step_index": 1,
        "step_id": plan_id,
        "tool_name": tool_name,
        "approval_executor_tool_name": approval_executor_tool_name,
        "params": params,
        "mutability": "guarded_write",
        "requires_confirmation": True,
        "mutation_fingerprint": mutation_fingerprint,
        "reason": reason,
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
        "intent_class": f"direct_{tool_name}",
        "chapter_index": chapter_index,
        "trace": {
            "plan_id": plan_id,
            "source_projection_id": None,
            "planner_version": planner_version,
        },
        "steps": [step],
    }


def _prepare_output(
    *,
    project_id: str,
    chapter_index: int,
    tool_name: str,
    prepare_tool_name: str,
    execute_tool_name: str,
    prepare_version: str,
    approval_gate_version: str,
    agent_plan: dict[str, Any],
) -> dict[str, Any]:
    approval_contract = build_agent_plan_approval_contract(agent_plan)
    approval_hash = str(((approval_contract.get("approval") or {}).get("approval_contract_hash")) or "")
    first_step = agent_plan["steps"][0]
    return {
        "status": "approval_required",
        "prepare_version": prepare_version,
        "project_id": project_id,
        "chapter_index": chapter_index,
        "target_type": "chapter_revision_adjustment",
        "mutation_fingerprint": first_step.get("mutation_fingerprint"),
        "tool_call_id": first_step.get("tool_call_id"),
        "resource_binding": first_step.get("resource_binding"),
        "agent_plan": agent_plan,
        "agent_plan_approval_contract": approval_contract,
        "agent_plan_approval_contract_hash": approval_hash,
        "required_confirmation": {
            "confirm_execute": True,
            "approval_contract_hash": approval_hash,
        },
        "side_effects": {"executed": [], "skipped": [tool_name]},
        "recommended_next_tools": [execute_tool_name],
        "trace": {
            "selected_tools": [prepare_tool_name],
            "rejected_tools": [{"tool_name": tool_name, "reason": "approval_required_before_write"}],
            "approval_gate_version": approval_gate_version,
        },
    }


def _verify_execution_ready(
    db: Session,
    project_id: str,
    *,
    chapter_index: int,
    tool_name: str,
    execute_tool_name: str,
    execute_version: str,
    approval_gate_version: str,
    agent_plan: dict[str, Any],
    confirm_execute: bool,
    approval_contract_hash: str | None,
    approval_contract: dict[str, Any] | None,
    approval_tool_metadata_provider,
) -> dict[str, Any]:
    project = db.query(Project.id).filter(Project.id == project_id).first()
    if project is None:
        return {"status": "failed", "error": "Project not found", "project_id": project_id}
    if confirm_execute is not True:
        return _blocked_output(
            project_id,
            chapter_index,
            tool_name=tool_name,
            execute_tool_name=execute_tool_name,
            execute_version=execute_version,
            approval_gate_version=approval_gate_version,
            reason="confirmation_required",
        )
    if not approval_contract_hash or not isinstance(approval_contract, dict):
        return _blocked_output(
            project_id,
            chapter_index,
            tool_name=tool_name,
            execute_tool_name=execute_tool_name,
            execute_version=execute_version,
            approval_gate_version=approval_gate_version,
            reason="approval_contract_required",
        )
    if approval_tool_metadata_provider is None:
        return _blocked_output(
            project_id,
            chapter_index,
            tool_name=tool_name,
            execute_tool_name=execute_tool_name,
            execute_version=execute_version,
            approval_gate_version=approval_gate_version,
            reason="agent_plan_tool_metadata_missing",
        )

    verification = verify_agent_plan_approval_contract(
        agent_plan,
        approval_contract_hash=approval_contract_hash,
        approval_contract=approval_contract,
        project_id=project_id,
        tool_metadata_by_name=approval_tool_metadata_provider(agent_plan),
    )
    if verification.get("status") != "ready":
        return _blocked_output(
            project_id,
            chapter_index,
            tool_name=tool_name,
            execute_tool_name=execute_tool_name,
            execute_version=execute_version,
            approval_gate_version=approval_gate_version,
            reason=str(verification.get("reason") or "agent_plan_approval_not_ready"),
            extra={
                "agent_plan_approval_verification": verification,
                "approval_verification_event": build_approval_verification_event(verification),
            },
        )

    binding_check = verify_resource_binding_target(
        verification,
        tool_name=tool_name,
        target_type="chapter_revision_adjustment",
        target_id=_chapter_revision_adjustment_target_id(tool_name, chapter_index),
    )
    if binding_check.get("status") != "ready":
        return _blocked_output(
            project_id,
            chapter_index,
            tool_name=tool_name,
            execute_tool_name=execute_tool_name,
            execute_version=execute_version,
            approval_gate_version=approval_gate_version,
            reason=str(binding_check.get("reason") or "resource_binding_target_mismatch"),
            extra={
                "agent_plan_approval_verification": verification,
                "approval_verification_event": build_approval_verification_event(verification),
                "execution_resource_binding": binding_check,
            },
        )

    return {
        "status": "ready",
        "agent_plan_approval_verification": verification,
        "execution_resource_binding": binding_check,
    }


def _approved_output(
    result: dict[str, Any],
    *,
    project_id: str,
    tool_name: str,
    execute_tool_name: str,
    execute_version: str,
    approval_gate_version: str,
    verification: dict[str, Any],
    binding_check: dict[str, Any],
) -> dict[str, Any]:
    return {
        **result,
        "execute_version": execute_version,
        "project_id": project_id,
        "target_type": "chapter_revision_adjustment",
        "agent_plan_approval_verification": verification,
        "approval_verification_event": build_approval_verification_event(verification),
        "execution_resource_binding": binding_check,
        "evidence": {
            "agent_plan_approval_verified": True,
            "legacy_action": tool_name,
            "execution_route": "static_adapter",
        },
        "side_effects": {"executed": [tool_name], "skipped": []},
        "trace": {
            "selected_tools": [execute_tool_name],
            "approval_gate_version": approval_gate_version,
        },
    }


def _blocked_output(
    project_id: str,
    chapter_index: int,
    *,
    tool_name: str,
    execute_tool_name: str,
    execute_version: str,
    approval_gate_version: str,
    reason: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    output = {
        "status": "blocked",
        "execute_version": execute_version,
        "project_id": project_id,
        "chapter_index": chapter_index,
        "target_type": "chapter_revision_adjustment",
        "reason": reason,
        "side_effects": {"executed": [], "skipped": [tool_name]},
        "recommended_next_tools": [f"prepare_{tool_name}_execution"],
        "trace": {
            "selected_tools": [execute_tool_name],
            "rejected_tools": [{"tool_name": tool_name, "reason": reason}],
            "approval_gate_version": approval_gate_version,
        },
    }
    if extra:
        output.update(extra)
    return output


def _expand_params(*, chapter_index: int, min_word_count: int | None, extra_instruction: str) -> dict[str, Any]:
    return {
        "chapter_index": chapter_index,
        "min_word_count": min_word_count,
        "extra_instruction": str(extra_instruction or ""),
    }


def _compress_params(
    *,
    chapter_index: int,
    target_max_word_count: int | None,
    extra_instruction: str,
    forbidden_terms: list[str] | None,
) -> dict[str, Any]:
    return {
        "chapter_index": chapter_index,
        "target_max_word_count": target_max_word_count,
        "extra_instruction": str(extra_instruction or ""),
        "forbidden_terms": _normalised_forbidden_terms(forbidden_terms),
    }


def _normalised_forbidden_terms(forbidden_terms: list[str] | None) -> list[str]:
    return [str(item).strip() for item in (forbidden_terms or []) if str(item).strip()]


def _chapter_revision_adjustment_target_id(tool_name: str, chapter_index: int) -> str:
    return f"chapter_revision_adjustment:{tool_name}:{chapter_index}"
