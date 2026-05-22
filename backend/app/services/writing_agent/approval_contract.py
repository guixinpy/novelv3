from __future__ import annotations

import hashlib
import json
from typing import Any

APPROVAL_CONTRACT_VERSION = "phase108.agent_plan_approval_contract.v1"
_WRITE_MUTABILITY = {"write", "guarded_write"}


def build_agent_plan_approval_contract(plan: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(plan, dict):
        return _invalid_contract("plan_not_object")

    trace = plan.get("trace") if isinstance(plan.get("trace"), dict) else {}
    steps = plan.get("steps") if isinstance(plan.get("steps"), list) else []
    write_steps = [_approval_step(step) for step in steps if _step_requires_approval(step)]
    payload = {
        "contract_version": APPROVAL_CONTRACT_VERSION,
        "project_id": plan.get("project_id"),
        "plan_id": trace.get("plan_id") or plan.get("plan_id"),
        "source_projection_id": trace.get("source_projection_id") or plan.get("source_projection_id"),
        "planner_version": trace.get("planner_version") or plan.get("planner_version"),
        "intent_class": plan.get("intent_class"),
        "write_steps": write_steps,
    }
    contract_hash = _hash_payload(payload)
    approval_required = bool(write_steps)
    return {
        "status": "requires_confirmation" if approval_required else "not_required",
        "version": APPROVAL_CONTRACT_VERSION,
        "project_id": payload["project_id"],
        "plan_id": payload["plan_id"],
        "source_projection_id": payload["source_projection_id"],
        "write_step_count": len(write_steps),
        "write_steps": write_steps,
        "approval": {
            "required": approval_required,
            "confirmation_param": "approval_contract_hash",
            "approval_contract_hash": contract_hash,
            "hash_algorithm": "sha256",
        },
        "trace": {
            "reason": "approval_preview_only",
            "planner_version": payload["planner_version"],
            "intent_class": payload["intent_class"],
            "write_step_ids": [step.get("step_id") for step in write_steps],
        },
    }


def _invalid_contract(reason: str) -> dict[str, Any]:
    return {
        "status": "invalid_plan",
        "version": APPROVAL_CONTRACT_VERSION,
        "project_id": None,
        "plan_id": None,
        "source_projection_id": None,
        "write_step_count": 0,
        "write_steps": [],
        "approval": {
            "required": False,
            "confirmation_param": "approval_contract_hash",
            "approval_contract_hash": None,
            "hash_algorithm": "sha256",
        },
        "trace": {"reason": reason},
    }


def _step_requires_approval(step: object) -> bool:
    if not isinstance(step, dict):
        return False
    mutability = str(step.get("mutability") or "")
    return step.get("requires_confirmation") is True or mutability in _WRITE_MUTABILITY


def _approval_step(step: dict[str, Any]) -> dict[str, Any]:
    approval_step = {
        "step_index": step.get("step_index"),
        "step_id": step.get("step_id"),
        "tool_name": step.get("tool_name"),
        "params": step.get("params") if isinstance(step.get("params"), dict) else {},
        "mutability": step.get("mutability"),
        "requires_confirmation": step.get("requires_confirmation") is True,
        "reason": str(step.get("reason") or ""),
    }
    if step.get("command_args"):
        approval_step["command_args"] = str(step["command_args"])
    return approval_step


def _hash_payload(payload: dict[str, Any]) -> str:
    normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return f"approval:{hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:16]}"
