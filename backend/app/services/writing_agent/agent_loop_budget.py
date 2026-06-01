from __future__ import annotations

from typing import Any, Iterable

from app.services.writing_agent.tool_descriptor_types import descriptor_mutability
from app.services.writing_agent.tool_registry import get_agent_tool_descriptor

AGENT_LOOP_BUDGET_REFUND_POLICY_VERSION = "phase227.agent_loop_budget_refund.v1"
REFUNDABLE_MUTABILITY = ("read",)
REFUNDABLE_STATUSES = ("success",)


def build_agent_loop_budget(steps: Iterable[Any], *, max_iterations: int) -> dict[str, Any]:
    step_list = list(steps)
    used_iterations = len(step_list)
    refunded_iterations = sum(1 for step in step_list if _is_refundable_step(step))
    charged_iterations = max(0, used_iterations - refunded_iterations)
    return {
        "max_iterations": max_iterations,
        "used_iterations": used_iterations,
        "charged_iterations": charged_iterations,
        "refunded_iterations": refunded_iterations,
        "remaining_iterations": max(0, max_iterations - charged_iterations),
        "refund_policy": {
            "version": AGENT_LOOP_BUDGET_REFUND_POLICY_VERSION,
            "refundable_mutability": list(REFUNDABLE_MUTABILITY),
            "refundable_statuses": list(REFUNDABLE_STATUSES),
        },
    }


def _is_refundable_step(step: Any) -> bool:
    if str(getattr(step, "status", "") or "") not in REFUNDABLE_STATUSES:
        return False
    tool_name = str(getattr(step, "tool_name", "") or "")
    descriptor = get_agent_tool_descriptor(tool_name)
    if descriptor is None:
        return False
    return descriptor_mutability(descriptor) in REFUNDABLE_MUTABILITY
