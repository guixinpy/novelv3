from __future__ import annotations

from typing import Any


def build_approval_verification_event(verification: dict[str, Any]) -> dict[str, Any]:
    drift = verification.get("drift") if isinstance(verification.get("drift"), dict) else {}
    current_contract = (
        verification.get("current_contract") if isinstance(verification.get("current_contract"), dict) else {}
    )
    status = str(verification.get("status") or "").strip()
    return {
        "event_type": "contract_verified" if status == "ready" else "contract_blocked",
        "status": status,
        "reason": str(verification.get("reason") or "").strip(),
        "approval_contract_bound": bool(drift.get("expected_approval_contract_hash")),
        "approval_contract_version": current_contract.get("version"),
        "write_step_count": drift.get("write_step_count"),
        "tool_contract_drift_count": drift.get("tool_contract_drift_count"),
    }
