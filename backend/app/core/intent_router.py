import hashlib
import re
from dataclasses import dataclass
from typing import Any

from app.core.dialog_agent_routes import build_dialog_agent_route, dialog_action_to_agent_tool_name
from app.schemas import ProjectDiagnosisOut

INTENT_PROJECTION_VERSION = "phase105.intent_projection.v1"
_INTENT_RULE_IDS = (
    "setup_intent",
    "storyline_intent",
    "outline_intent",
    "chapter_intent",
    "review_intent",
    "recovery_intent",
    "memory_tree_intent",
    "memory_route_intent",
    "memory_activation_plan_intent",
    "knowledge_base_route_intent",
    "post_chapter_memory_capture_intent",
    "world_model_route_intent",
    "world_model_proposal_review_intent",
    "world_model_proposal_resolution_plan_intent",
    "retrieval_context_intent",
    "longform_context_summary_intent",
    "context_compression_payload_intent",
    "preflight_context_budget_intent",
    "context_compression_intent",
    "worker_dispatch_intent",
    "agent_event_projection_intent",
    "agent_job_projection_intent",
    "chapter_conflict_recovery_intent",
    "trace_anomaly_long_run_samples_intent",
    "trace_anomaly_threshold_review_intent",
    "trace_anomaly_trends_intent",
    "trace_audit_intent",
    "write_gate_coverage_intent",
    "legacy_hermes_migration_intent",
    "route_approval_opt_in_plan_intent",
    "route_approval_opt_in_apply_preview_intent",
    "route_approval_opt_in_apply_contract_intent",
    "route_approval_opt_in_apply_prepare_intent",
    "tool_contracts_intent",
    "command_contracts_intent",
    "slash_command_route_intent",
    "dialog_route_projection_intent",
    "intent_projection_intent",
    "dialog_control_plane_projection_intent",
    "mutation_fingerprints_intent",
    "reference_alignment_intent",
    "dogfood_evidence_intent",
    "route_preference_intent",
    "agent_health_intent",
    "control_plane_readiness_intent",
    "query_diagnosis_intent",
)


class ActionCandidate:
    def __init__(self, type: str, params: dict | None = None):
        self.type = type
        self.params = params or {}

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "params": self.params}


@dataclass(frozen=True)
class IntentProjection:
    status: str
    normalized_text: str
    dialog_state: str
    pending_action_id: str | None
    diagnosis: ProjectDiagnosisOut
    candidate: ActionCandidate | None = None
    rule_id: str | None = None
    reason: str | None = None
    extracted_params: dict[str, Any] | None = None
    match_evidence: list[dict[str, Any]] | None = None
    preconditions: list[dict[str, Any]] | None = None
    rejected_candidates: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        agent_route = None
        if self.candidate is not None and dialog_action_to_agent_tool_name(self.candidate.type):
            agent_route = build_dialog_agent_route(self.candidate.type, source="text_intent")
        agent_tool_name = agent_route.get("agent_tool_name") if agent_route is not None else None
        input_hash = hashlib.sha256(self.normalized_text.encode("utf-8")).hexdigest()
        extracted_params = dict(self.extracted_params or {})
        decision = {
            "rule_id": self.rule_id,
            "reason_code": self.reason,
            "reason_message": _reason_message(self.reason),
            "match_evidence": list(self.match_evidence or []),
            "extracted_params": extracted_params,
        }
        diagnosis = {
            "missing_items": list(self.diagnosis.missing_items),
            "completed_items": list(self.diagnosis.completed_items),
            "suggested_next_step": self.diagnosis.suggested_next_step,
        }
        return {
            "version": INTENT_PROJECTION_VERSION,
            "status": self.status,
            "rule_id": self.rule_id,
            "reason": self.reason,
            "normalized_text": self.normalized_text,
            "dialog_state": self.dialog_state,
            "pending_action_id": self.pending_action_id,
            "input": {
                "normalized_text": self.normalized_text,
                "input_hash": input_hash,
                "excerpt": self.normalized_text[:120],
            },
            "context": {
                "dialog_state": self.dialog_state,
                "pending_action_id": self.pending_action_id,
                "diagnosis": diagnosis,
            },
            "decision": decision,
            "candidate": self.candidate.to_dict() if self.candidate is not None else None,
            "agent_route": agent_route,
            "tool_selection": {
                "selected_tool": agent_tool_name,
                "why_this_tool": (
                    f"dialog_action_to_agent_tool.{self.candidate.type}"
                    if self.candidate is not None and agent_tool_name is not None
                    else None
                ),
                "availability_checked": False,
            },
            "preconditions": list(self.preconditions or []),
            "guardrails": [],
            "rejected_candidates": list(self.rejected_candidates or []),
            "diagnosis": diagnosis,
            "extracted_params": extracted_params,
            "trace": {
                "projection_id": f"intent:{input_hash[:16]}",
                "duration_ms": 0,
            },
        }


def _reason_message(reason_code: str | None) -> str | None:
    messages = {
        "intent_rule_matched": "自然语言输入命中确定性意图规则。",
        "no_intent_rule_matched": "自然语言输入未命中确定性意图规则。",
    }
    return messages.get(reason_code or "")


_CHINESE_DIGITS = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}


def parse_chapter_index(text: str | None) -> int | None:
    value = (text or "").strip().lower()
    leading_digit_match = re.search(r"^\s*(?:第\s*)?(\d{1,3})(?:\s*章|\s|$)", value)
    if leading_digit_match:
        return int(leading_digit_match.group(1))

    leading_chinese_match = re.search(r"^\s*(?:第\s*)?([零〇一二两三四五六七八九十]{1,4})\s*章", value)
    if leading_chinese_match:
        return _parse_chinese_chapter_number(leading_chinese_match.group(1))

    matches: list[tuple[int, int]] = []
    for match in re.finditer(r"第\s*(\d{1,3})\s*章", value):
        matches.append((match.start(), int(match.group(1))))
    for match in re.finditer(r"第\s*([零〇一二两三四五六七八九十]{1,4})\s*章", value):
        parsed = _parse_chinese_chapter_number(match.group(1))
        if parsed is not None:
            matches.append((match.start(), parsed))
    if not matches:
        return None
    return min(matches, key=lambda item: item[0])[1]


def _parse_chinese_chapter_number(value: str) -> int | None:
    if not value:
        return None
    if value == "十":
        return 10
    if "十" in value:
        left, _, right = value.partition("十")
        tens = _CHINESE_DIGITS.get(left, 1) if left else 1
        ones = _CHINESE_DIGITS.get(right, 0) if right else 0
        return tens * 10 + ones
    total = 0
    for char in value:
        if char not in _CHINESE_DIGITS:
            return None
        total = total * 10 + _CHINESE_DIGITS[char]
    return total or None


class IntentRouter:
    def project(
        self,
        user_input: str,
        dialog_state: str,
        pending_action_id: str | None,
        diagnosis: ProjectDiagnosisOut,
    ) -> IntentProjection:
        text = user_input.strip().lower()

        if pending_action_id:
            return self._project_confirmation(text, dialog_state, pending_action_id, diagnosis)

        return self._project_action_candidate(text, dialog_state, pending_action_id, diagnosis)

    def resolve(
        self,
        user_input: str,
        dialog_state: str,
        pending_action_id: str | None,
        diagnosis: ProjectDiagnosisOut,
    ) -> ActionCandidate | None:
        return self.project(user_input, dialog_state, pending_action_id, diagnosis).candidate

    def _project_confirmation(
        self,
        text: str,
        dialog_state: str,
        pending_action_id: str | None,
        diagnosis: ProjectDiagnosisOut,
    ) -> IntentProjection:
        confirm_patterns = [r"^好的?$", r"^可以$", r"^同意$", r"^行$", r"^ok$", r"^没问题$", r"^搞吧$", r"^那就这样吧$"]
        cancel_patterns = [r"^算了$", r"^先不要$", r"^等等$", r"^不对$", r"^先别$", r"^我还没想好$", r"^换一个$"]
        revise_patterns = [r"改一下", r"先把", r"换成", r"改成"]

        for p in confirm_patterns:
            if re.search(p, text):
                return self._matched_projection(
                    text,
                    dialog_state,
                    pending_action_id,
                    diagnosis,
                    rule_id="confirm_pending_action",
                    candidate=ActionCandidate("confirm"),
                    match_evidence=[{"kind": "pattern", "name": "confirm_phrase"}],
                )
        for p in cancel_patterns:
            if re.search(p, text):
                return self._matched_projection(
                    text,
                    dialog_state,
                    pending_action_id,
                    diagnosis,
                    rule_id="cancel_pending_action",
                    candidate=ActionCandidate("cancel"),
                    match_evidence=[{"kind": "pattern", "name": "cancel_phrase"}],
                )
        for p in revise_patterns:
            if re.search(p, text):
                return self._matched_projection(
                    text,
                    dialog_state,
                    pending_action_id,
                    diagnosis,
                    rule_id="revise_pending_action",
                    candidate=ActionCandidate("revise", {"comment": text}),
                    extracted_params={"comment": text},
                    match_evidence=[{"kind": "pattern", "name": "revise_phrase"}],
                )
        return self._no_match_projection(text, dialog_state, pending_action_id, diagnosis)

    def _project_action_candidate(
        self,
        text: str,
        dialog_state: str,
        pending_action_id: str | None,
        diagnosis: ProjectDiagnosisOut,
    ) -> IntentProjection:
        if re.search(r"(恢复|重试|继续处理).*(阻塞|失败|中断|上一轮|上次)", text) or re.search(
            r"(上一轮|上次).*(阻塞|失败)",
            text,
        ):
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="recovery_intent",
                candidate=ActionCandidate("preview_recovery"),
                match_evidence=[{"kind": "pattern", "name": "recovery_phrase"}],
                preconditions=[{"code": "recovery_preview_available", "passed": True}],
            )

        if _is_memory_tree_intent(text):
            extracted_params = _memory_tree_params(text)
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="memory_tree_intent",
                candidate=ActionCandidate("inspect_memory_tree", extracted_params),
                extracted_params=extracted_params,
                match_evidence=[{"kind": "pattern", "name": "memory_tree_phrase"}],
                preconditions=[{"code": "memory_tree_read_available", "passed": True}],
            )

        if _is_memory_route_intent(text):
            extracted_params = _memory_route_params(text)
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="memory_route_intent",
                candidate=ActionCandidate("inspect_memory_route", extracted_params),
                extracted_params=extracted_params,
                match_evidence=[{"kind": "pattern", "name": "memory_route_phrase"}],
                preconditions=[{"code": "memory_route_read_available", "passed": True}],
            )

        if _is_memory_activation_plan_intent(text):
            extracted_params = _memory_activation_plan_params(text)
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="memory_activation_plan_intent",
                candidate=ActionCandidate("inspect_memory_activation_plan", extracted_params),
                extracted_params=extracted_params,
                match_evidence=[{"kind": "pattern", "name": "memory_activation_plan_phrase"}],
                preconditions=[{"code": "memory_activation_plan_read_available", "passed": True}],
            )

        if _is_knowledge_base_route_intent(text):
            extracted_params = _knowledge_base_route_params(text)
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="knowledge_base_route_intent",
                candidate=ActionCandidate("inspect_knowledge_base_route", extracted_params),
                extracted_params=extracted_params,
                match_evidence=[{"kind": "pattern", "name": "knowledge_base_route_phrase"}],
                preconditions=[{"code": "knowledge_base_route_read_available", "passed": True}],
            )

        if _is_post_chapter_memory_capture_intent(text):
            extracted_params = _post_chapter_memory_capture_params(text)
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="post_chapter_memory_capture_intent",
                candidate=ActionCandidate("plan_post_chapter_memory_capture", extracted_params),
                extracted_params=extracted_params,
                match_evidence=[{"kind": "pattern", "name": "post_chapter_memory_capture_phrase"}],
                preconditions=[{"code": "post_chapter_memory_capture_read_available", "passed": True}],
            )

        if _is_world_model_route_intent(text):
            extracted_params = _world_model_route_params(text)
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="world_model_route_intent",
                candidate=ActionCandidate("inspect_world_model_route", extracted_params),
                extracted_params=extracted_params,
                match_evidence=[{"kind": "pattern", "name": "world_model_route_phrase"}],
                preconditions=[{"code": "world_model_route_read_available", "passed": True}],
            )

        if _is_world_model_proposal_resolution_plan_intent(text):
            extracted_params = _world_model_proposal_queue_params(text)
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="world_model_proposal_resolution_plan_intent",
                candidate=ActionCandidate("plan_world_model_proposal_resolution", extracted_params),
                extracted_params=extracted_params,
                match_evidence=[{"kind": "pattern", "name": "world_model_proposal_resolution_plan_phrase"}],
                preconditions=[{"code": "world_model_proposal_resolution_plan_read_available", "passed": True}],
            )

        if _is_world_model_proposal_review_intent(text):
            extracted_params = _world_model_proposal_queue_params(text)
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="world_model_proposal_review_intent",
                candidate=ActionCandidate("review_world_model_proposals", extracted_params),
                extracted_params=extracted_params,
                match_evidence=[{"kind": "pattern", "name": "world_model_proposal_review_phrase"}],
                preconditions=[{"code": "world_model_proposal_review_read_available", "passed": True}],
            )

        if _is_retrieval_context_intent(text):
            extracted_params = _retrieval_context_params(text)
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="retrieval_context_intent",
                candidate=ActionCandidate("search_retrieval_context", extracted_params),
                extracted_params=extracted_params,
                match_evidence=[{"kind": "pattern", "name": "retrieval_context_phrase"}],
                preconditions=[{"code": "retrieval_context_read_available", "passed": True}],
            )

        if _is_longform_context_summary_intent(text):
            extracted_params = _longform_context_summary_params(text)
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="longform_context_summary_intent",
                candidate=ActionCandidate("summarize_longform_context", extracted_params),
                extracted_params=extracted_params,
                match_evidence=[{"kind": "pattern", "name": "longform_context_summary_phrase"}],
                preconditions=[{"code": "longform_context_summary_read_available", "passed": True}],
            )

        if _is_context_compression_payload_intent(text):
            extracted_params = _context_compression_payload_params(text)
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="context_compression_payload_intent",
                candidate=ActionCandidate("build_context_compression_payload", extracted_params),
                extracted_params=extracted_params,
                match_evidence=[{"kind": "pattern", "name": "context_compression_payload_phrase"}],
                preconditions=[{"code": "context_compression_payload_read_available", "passed": True}],
            )

        if _is_preflight_context_budget_intent(text):
            extracted_params = _preflight_context_budget_params(text)
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="preflight_context_budget_intent",
                candidate=ActionCandidate("preflight_context_budget", extracted_params),
                extracted_params=extracted_params,
                match_evidence=[{"kind": "pattern", "name": "preflight_context_budget_phrase"}],
                preconditions=[{"code": "preflight_context_budget_read_available", "passed": True}],
            )

        if _is_context_compression_intent(text):
            extracted_params = _context_compression_params(text)
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="context_compression_intent",
                candidate=ActionCandidate("inspect_context_compression", extracted_params),
                extracted_params=extracted_params,
                match_evidence=[{"kind": "pattern", "name": "context_compression_phrase"}],
                preconditions=[{"code": "context_compression_read_available", "passed": True}],
            )

        if _is_worker_dispatch_intent(text):
            extracted_params = _worker_dispatch_params(text)
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="worker_dispatch_intent",
                candidate=ActionCandidate("inspect_worker_dispatch", extracted_params),
                extracted_params=extracted_params,
                match_evidence=[{"kind": "pattern", "name": "worker_dispatch_phrase"}],
                preconditions=[{"code": "worker_dispatch_read_available", "passed": True}],
            )

        if _is_agent_event_projection_intent(text):
            extracted_params = _agent_event_projection_params(text)
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="agent_event_projection_intent",
                candidate=ActionCandidate("inspect_agent_event_projection", extracted_params),
                extracted_params=extracted_params,
                match_evidence=[{"kind": "pattern", "name": "agent_event_projection_phrase"}],
                preconditions=[{"code": "agent_event_projection_read_available", "passed": True}],
            )

        if _is_agent_job_projection_intent(text):
            extracted_params = _agent_job_projection_params(text)
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="agent_job_projection_intent",
                candidate=ActionCandidate("inspect_agent_job_projection", extracted_params),
                extracted_params=extracted_params,
                match_evidence=[{"kind": "pattern", "name": "agent_job_projection_phrase"}],
                preconditions=[{"code": "agent_job_projection_read_available", "passed": True}],
            )

        if _is_chapter_conflict_recovery_intent(text):
            extracted_params = _chapter_conflict_recovery_params(text)
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="chapter_conflict_recovery_intent",
                candidate=ActionCandidate("plan_chapter_conflict_recovery", extracted_params),
                extracted_params=extracted_params,
                match_evidence=[{"kind": "pattern", "name": "chapter_conflict_recovery_phrase"}],
                preconditions=[{"code": "chapter_conflict_recovery_read_available", "passed": True}],
            )

        if _is_legacy_hermes_migration_intent(text):
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="legacy_hermes_migration_intent",
                candidate=ActionCandidate("inspect_legacy_hermes_migration", {}),
                extracted_params={},
                match_evidence=[{"kind": "pattern", "name": "legacy_hermes_migration_phrase"}],
                preconditions=[{"code": "legacy_hermes_migration_read_available", "passed": True}],
            )

        if _is_route_approval_opt_in_apply_contract_intent(text):
            extracted_params = _route_approval_opt_in_params(text)
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="route_approval_opt_in_apply_contract_intent",
                candidate=ActionCandidate("preview_route_approval_opt_in_apply_contract", extracted_params),
                extracted_params=extracted_params,
                match_evidence=[{"kind": "pattern", "name": "route_approval_opt_in_apply_contract_phrase"}],
                preconditions=[{"code": "route_approval_opt_in_apply_contract_read_available", "passed": True}],
            )

        if _is_route_approval_opt_in_apply_prepare_intent(text):
            extracted_params = _route_approval_opt_in_params(text)
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="route_approval_opt_in_apply_prepare_intent",
                candidate=ActionCandidate("prepare_route_approval_opt_in_apply", extracted_params),
                extracted_params=extracted_params,
                match_evidence=[{"kind": "pattern", "name": "route_approval_opt_in_apply_prepare_phrase"}],
                preconditions=[{"code": "route_approval_opt_in_apply_prepare_read_available", "passed": True}],
            )

        if _is_route_approval_opt_in_apply_preview_intent(text):
            extracted_params = _route_approval_opt_in_params(text)
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="route_approval_opt_in_apply_preview_intent",
                candidate=ActionCandidate("preview_route_approval_opt_in_apply", extracted_params),
                extracted_params=extracted_params,
                match_evidence=[{"kind": "pattern", "name": "route_approval_opt_in_apply_preview_phrase"}],
                preconditions=[{"code": "route_approval_opt_in_apply_preview_read_available", "passed": True}],
            )

        if _is_route_approval_opt_in_plan_intent(text):
            extracted_params = _route_approval_opt_in_params(text)
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="route_approval_opt_in_plan_intent",
                candidate=ActionCandidate("plan_route_approval_opt_in", extracted_params),
                extracted_params=extracted_params,
                match_evidence=[{"kind": "pattern", "name": "route_approval_opt_in_plan_phrase"}],
                preconditions=[{"code": "route_approval_opt_in_plan_read_available", "passed": True}],
            )

        if _is_tool_contracts_intent(text):
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="tool_contracts_intent",
                candidate=ActionCandidate("inspect_tool_contracts", {}),
                extracted_params={},
                match_evidence=[{"kind": "pattern", "name": "tool_contracts_phrase"}],
                preconditions=[{"code": "tool_contracts_read_available", "passed": True}],
            )

        if _is_command_contracts_intent(text):
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="command_contracts_intent",
                candidate=ActionCandidate("inspect_command_contracts", {}),
                extracted_params={},
                match_evidence=[{"kind": "pattern", "name": "command_contracts_phrase"}],
                preconditions=[{"code": "command_contracts_read_available", "passed": True}],
            )

        if _is_slash_command_route_intent(text):
            extracted_params = _slash_command_route_params(text)
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="slash_command_route_intent",
                candidate=ActionCandidate("inspect_slash_command_route", extracted_params),
                extracted_params=extracted_params,
                match_evidence=[{"kind": "pattern", "name": "slash_command_route_phrase"}],
                preconditions=[{"code": "slash_command_route_read_available", "passed": True}],
            )

        if _is_dialog_route_projection_intent(text):
            extracted_params = _dialog_route_projection_params(text)
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="dialog_route_projection_intent",
                candidate=ActionCandidate("inspect_dialog_route", extracted_params),
                extracted_params=extracted_params,
                match_evidence=[{"kind": "pattern", "name": "dialog_route_projection_phrase"}],
                preconditions=[{"code": "dialog_route_projection_read_available", "passed": True}],
            )

        if _is_intent_projection_intent(text):
            extracted_params = _intent_projection_params(text)
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="intent_projection_intent",
                candidate=ActionCandidate("inspect_intent_projection", extracted_params),
                extracted_params=extracted_params,
                match_evidence=[{"kind": "pattern", "name": "intent_projection_phrase"}],
                preconditions=[{"code": "intent_projection_read_available", "passed": True}],
            )

        if _is_dialog_control_plane_projection_intent(text):
            extracted_params = _dialog_control_plane_projection_params(text)
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="dialog_control_plane_projection_intent",
                candidate=ActionCandidate("inspect_dialog_control_plane", extracted_params),
                extracted_params=extracted_params,
                match_evidence=[{"kind": "pattern", "name": "dialog_control_plane_projection_phrase"}],
                preconditions=[{"code": "dialog_control_plane_projection_read_available", "passed": True}],
            )

        if _is_mutation_fingerprints_intent(text):
            extracted_params = _mutation_fingerprints_params(text)
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="mutation_fingerprints_intent",
                candidate=ActionCandidate("inspect_mutation_fingerprints", extracted_params),
                extracted_params=extracted_params,
                match_evidence=[{"kind": "pattern", "name": "mutation_fingerprints_phrase"}],
                preconditions=[{"code": "mutation_fingerprints_read_available", "passed": True}],
            )

        if _is_reference_alignment_intent(text):
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="reference_alignment_intent",
                candidate=ActionCandidate("inspect_reference_alignment", {}),
                extracted_params={},
                match_evidence=[{"kind": "pattern", "name": "reference_alignment_phrase"}],
                preconditions=[{"code": "reference_alignment_read_available", "passed": True}],
            )

        if _is_dogfood_evidence_intent(text):
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="dogfood_evidence_intent",
                candidate=ActionCandidate("inspect_dogfood_evidence", {}),
                extracted_params={},
                match_evidence=[{"kind": "pattern", "name": "dogfood_evidence_phrase"}],
                preconditions=[{"code": "dogfood_evidence_read_available", "passed": True}],
            )

        if _is_route_preference_intent(text):
            extracted_params = _route_preference_params(text)
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="route_preference_intent",
                candidate=ActionCandidate("inspect_route_preference", extracted_params),
                extracted_params=extracted_params,
                match_evidence=[{"kind": "pattern", "name": "route_preference_phrase"}],
                preconditions=[{"code": "route_preference_read_available", "passed": True}],
            )

        if _is_control_plane_readiness_intent(text):
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="control_plane_readiness_intent",
                candidate=ActionCandidate("inspect_control_plane_readiness", {}),
                extracted_params={},
                match_evidence=[{"kind": "pattern", "name": "control_plane_readiness_phrase"}],
                preconditions=[{"code": "control_plane_readiness_read_available", "passed": True}],
            )

        if _is_trace_anomaly_long_run_samples_intent(text):
            extracted_params = _trace_anomaly_long_run_samples_params(text)
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="trace_anomaly_long_run_samples_intent",
                candidate=ActionCandidate("inspect_trace_anomaly_long_run_samples", extracted_params),
                extracted_params=extracted_params,
                match_evidence=[{"kind": "pattern", "name": "trace_anomaly_long_run_samples_phrase"}],
                preconditions=[{"code": "trace_anomaly_long_run_samples_read_available", "passed": True}],
            )

        if _is_trace_anomaly_threshold_review_intent(text):
            extracted_params = _trace_anomaly_trends_params(text)
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="trace_anomaly_threshold_review_intent",
                candidate=ActionCandidate("inspect_trace_anomaly_threshold_review", extracted_params),
                extracted_params=extracted_params,
                match_evidence=[{"kind": "pattern", "name": "trace_anomaly_threshold_review_phrase"}],
                preconditions=[{"code": "trace_anomaly_threshold_review_read_available", "passed": True}],
            )

        if _is_trace_anomaly_trends_intent(text):
            extracted_params = _trace_anomaly_trends_params(text)
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="trace_anomaly_trends_intent",
                candidate=ActionCandidate("inspect_trace_anomaly_trends", extracted_params),
                extracted_params=extracted_params,
                match_evidence=[{"kind": "pattern", "name": "trace_anomaly_trends_phrase"}],
                preconditions=[{"code": "trace_anomaly_trends_read_available", "passed": True}],
            )

        if _is_trace_audit_intent(text):
            extracted_params = _trace_audit_params(text)
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="trace_audit_intent",
                candidate=ActionCandidate("inspect_trace_audit", extracted_params),
                extracted_params=extracted_params,
                match_evidence=[{"kind": "pattern", "name": "trace_audit_phrase"}],
                preconditions=[{"code": "trace_audit_read_available", "passed": True}],
            )

        if _is_write_gate_coverage_intent(text):
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="write_gate_coverage_intent",
                candidate=ActionCandidate("inspect_write_gate_coverage", {}),
                extracted_params={},
                match_evidence=[{"kind": "pattern", "name": "write_gate_coverage_phrase"}],
                preconditions=[{"code": "write_gate_coverage_read_available", "passed": True}],
            )

        if _is_agent_health_intent(text):
            extracted_params = _agent_health_params(text)
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="agent_health_intent",
                candidate=ActionCandidate("inspect_agent_health", extracted_params),
                extracted_params=extracted_params,
                match_evidence=[{"kind": "pattern", "name": "agent_health_phrase"}],
                preconditions=[{"code": "agent_health_read_available", "passed": True}],
            )

        if re.search(r"创建.*(主角|人物|设定|世界观)", text) or re.search(r"生成.*设定", text):
            if "setup" in diagnosis.missing_items or "setup" in diagnosis.completed_items:
                return self._matched_projection(
                    text,
                    dialog_state,
                    pending_action_id,
                    diagnosis,
                    rule_id="setup_intent",
                    candidate=ActionCandidate("preview_setup", {"project_id": ""}),
                    match_evidence=[{"kind": "pattern", "name": "setup_phrase"}],
                    preconditions=[{"code": "setup_available", "passed": True}],
                )

        if re.search(r"创建.*(主枝干|故事线)", text) or re.search(r"生成.*故事线", text):
            if "storyline" in diagnosis.missing_items:
                return self._matched_projection(
                    text,
                    dialog_state,
                    pending_action_id,
                    diagnosis,
                    rule_id="storyline_intent",
                    candidate=ActionCandidate("preview_storyline", {"project_id": ""}),
                    match_evidence=[{"kind": "pattern", "name": "storyline_phrase"}],
                    preconditions=[{"code": "storyline_missing", "passed": True}],
                )

        if re.search(r"写第.*章大纲|生成章节大纲|生成.*大纲", text) and "outline" in diagnosis.missing_items:
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="outline_intent",
                candidate=ActionCandidate("preview_outline", {"project_id": ""}),
                match_evidence=[{"kind": "pattern", "name": "outline_phrase"}],
                preconditions=[{"code": "outline_missing", "passed": True}],
            )

        if re.search(r"(审稿|审查|复查|检查|修订计划|连续性|质量)", text):
            parsed_chapter_index = parse_chapter_index(text)
            chapter_index = parsed_chapter_index or 1
            chapter_index_source = "explicit_user" if parsed_chapter_index is not None else "router_default"
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="review_intent",
                candidate=ActionCandidate(
                    "preview_review",
                    {"chapter_index": chapter_index, "chapter_index_source": chapter_index_source},
                ),
                extracted_params={"chapter_index": chapter_index, "chapter_index_source": chapter_index_source},
                match_evidence=[{"kind": "pattern", "name": "review_phrase"}],
                preconditions=[{"code": "review_preview_available", "passed": True}],
            )

        if "outline" in diagnosis.completed_items and re.search(r"(开始|继续|生成|写|创作).*(正文|章节|第\s*[\d零〇一二两三四五六七八九十]+\s*章|下一章)", text):
            parsed_chapter_index = parse_chapter_index(text)
            chapter_index = parsed_chapter_index or 1
            chapter_index_source = "explicit_user" if parsed_chapter_index is not None else "router_default"
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="chapter_intent",
                candidate=ActionCandidate(
                    "preview_chapter",
                    {"chapter_index": chapter_index, "chapter_index_source": chapter_index_source},
                ),
                extracted_params={"chapter_index": chapter_index, "chapter_index_source": chapter_index_source},
                match_evidence=[{"kind": "pattern", "name": "chapter_generation_phrase"}],
                preconditions=[{"code": "outline_completed", "passed": True}],
            )

        if _is_chapter_ready(diagnosis) and _is_low_detail_chapter_continue(text):
            parsed_chapter_index = parse_chapter_index(text)
            chapter_index = parsed_chapter_index or 1
            chapter_index_source = "explicit_user" if parsed_chapter_index is not None else "router_default"
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="chapter_intent",
                candidate=ActionCandidate(
                    "preview_chapter",
                    {"chapter_index": chapter_index, "chapter_index_source": chapter_index_source},
                ),
                extracted_params={"chapter_index": chapter_index, "chapter_index_source": chapter_index_source},
                match_evidence=[{"kind": "pattern", "name": "low_detail_continue_phrase"}],
                preconditions=[{"code": "outline_completed", "passed": True}],
            )

        if re.search(r"还有什么要设定的|接下来做什么|然后呢", text):
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="query_diagnosis_intent",
                candidate=ActionCandidate("query_diagnosis", {"project_id": ""}),
                match_evidence=[{"kind": "pattern", "name": "diagnosis_query_phrase"}],
            )

        return self._no_match_projection(text, dialog_state, pending_action_id, diagnosis)

    def _matched_projection(
        self,
        text: str,
        dialog_state: str,
        pending_action_id: str | None,
        diagnosis: ProjectDiagnosisOut,
        *,
        rule_id: str,
        candidate: ActionCandidate,
        extracted_params: dict[str, Any] | None = None,
        match_evidence: list[dict[str, Any]] | None = None,
        preconditions: list[dict[str, Any]] | None = None,
    ) -> IntentProjection:
        final_preconditions = list(preconditions or [])
        if candidate.type.startswith("preview_"):
            final_preconditions.append({"code": "requires_confirmation", "passed": True})
        return IntentProjection(
            status="matched",
            rule_id=rule_id,
            reason="intent_rule_matched",
            normalized_text=text,
            dialog_state=dialog_state,
            pending_action_id=pending_action_id,
            diagnosis=diagnosis,
            candidate=candidate,
            extracted_params=extracted_params or {},
            match_evidence=match_evidence or [],
            preconditions=final_preconditions,
            rejected_candidates=_rejected_candidates(rule_id, matched=True),
        )

    def _no_match_projection(
        self,
        text: str,
        dialog_state: str,
        pending_action_id: str | None,
        diagnosis: ProjectDiagnosisOut,
    ) -> IntentProjection:
        return IntentProjection(
            status="no_match",
            reason="no_intent_rule_matched",
            normalized_text=text,
            dialog_state=dialog_state,
            pending_action_id=pending_action_id,
            diagnosis=diagnosis,
            extracted_params={},
            match_evidence=[],
            preconditions=[],
            rejected_candidates=_rejected_candidates(None, matched=False),
        )


def _is_chapter_ready(diagnosis: ProjectDiagnosisOut) -> bool:
    return "outline" in diagnosis.completed_items


def _is_low_detail_chapter_continue(text: str) -> bool:
    if re.search(r"(设定|世界观|故事线|主枝干|大纲)", text):
        return False
    return bool(
        re.search(
            r"^(继续|继续吧|继续写吧|开始写吧|开写吧|往下写|推进吧|继续推进|可以开始了|开始吧|下一章|接着写|继续下一章)$",
            text,
        )
    )


def _is_memory_tree_intent(text: str) -> bool:
    return bool(
        re.search(r"(记忆树|分层记忆|长期记忆).*(浏览|查看|搜索|检索|展开|线索)", text)
        or re.search(r"(浏览|查看|搜索|检索|展开).*(记忆树|分层记忆|长期记忆|记忆)", text)
    )


def _memory_tree_params(text: str) -> dict[str, Any]:
    query = _memory_tree_query(text)
    params: dict[str, Any] = {"query": query, "include_ancestors": True}
    level = _memory_tree_level(text)
    if level:
        params["level"] = level
    chapter_index = parse_chapter_index(text)
    if chapter_index is not None:
        params["chapter_index"] = chapter_index
    return params


def _memory_tree_query(text: str) -> str:
    query = re.sub(r"(浏览|查看|搜索|检索|展开|帮我|请|一下)", "", text).strip()
    query = re.sub(r"(记忆树|分层记忆|长期记忆|记忆)", "", query).strip()
    query = re.sub(r"^(里|中|内|关于|有关|的)+", "", query).strip()
    return query or text


def _memory_tree_level(text: str) -> str | None:
    if re.search(r"(卷级|卷)", text):
        return "volume"
    if re.search(r"(章级|章节|第\s*[\d零〇一二两三四五六七八九十]+\s*章)", text):
        return "chapter"
    if re.search(r"(场景|scene)", text):
        return "scene"
    if re.search(r"(beat|节拍|情节拍)", text):
        return "beat"
    return None


def _is_memory_route_intent(text: str) -> bool:
    memory_route_phrase = r"(长篇记忆路由|记忆路由|memory\s*route|longform\s*memory\s*route|检索维护)"
    return bool(
        re.search(rf"{memory_route_phrase}.*(检查|诊断|路由|状态|覆盖|上下文摘要|context\s*summary)", text)
        or re.search(rf"(检查|诊断|路由|状态|覆盖|上下文摘要|context\s*summary).*{memory_route_phrase}", text)
    )


def _memory_route_params(text: str) -> dict[str, Any]:
    params: dict[str, Any] = {}
    chapter_index = parse_chapter_index(text)
    if chapter_index is not None:
        params["chapter_index"] = chapter_index
    query = _labeled_query(
        text,
        r"(?:长篇记忆路由|记忆路由|memory\s*route|longform\s*memory\s*route|检索维护)",
    )
    if query:
        params["query"] = query
    if re.search(r"(包含|带上|include|with).*(上下文摘要|context\s*summary)|include_context_summary", text):
        params["include_context_summary"] = True
    return params


def _is_memory_activation_plan_intent(text: str) -> bool:
    activation_phrase = r"(记忆激活(?:计划)?|memory\s*activation(?:\s*plan)?|activation\s*plan)"
    return bool(
        re.search(rf"{activation_phrase}.*(检查|诊断|计划|生成|查看|激活)", text)
        or re.search(rf"(检查|诊断|计划|生成|查看|激活).*{activation_phrase}", text)
    )


def _memory_activation_plan_params(text: str) -> dict[str, Any]:
    params: dict[str, Any] = {}
    chapter_index = parse_chapter_index(text)
    if chapter_index is not None:
        params["chapter_index"] = chapter_index
    query = _labeled_query(
        text,
        r"(?:记忆激活(?:计划)?|memory\s*activation(?:\s*plan)?|activation\s*plan)",
    )
    if query:
        params["query"] = query
    return params


def _is_knowledge_base_route_intent(text: str) -> bool:
    knowledge_route_phrase = r"(知识库路由|知识库状态|创作记忆|knowledge\s*base\s*route|knowledge_base_route)"
    return bool(
        re.search(rf"{knowledge_route_phrase}.*(检查|诊断|路由|状态|读取|query|limit)", text)
        or re.search(rf"(检查|诊断|路由|状态|读取|query|limit).*{knowledge_route_phrase}", text)
    )


def _knowledge_base_route_params(text: str) -> dict[str, Any]:
    params: dict[str, Any] = {}
    chapter_index = parse_chapter_index(text)
    if chapter_index is not None:
        params["chapter_index"] = chapter_index
    query = _parameter_query(text) or _labeled_query(
        text,
        r"(?:知识库路由|知识库状态|创作记忆|knowledge\s*base\s*route|knowledge_base_route)",
    )
    if query:
        params["query"] = query
    limit = _numeric_option(text, r"limit|限制|最多")
    if limit is not None:
        params["limit"] = limit
    return params


def _is_post_chapter_memory_capture_intent(text: str) -> bool:
    capture_phrase = r"(写后记忆|章节后记忆|章后记忆|post[-_\s]*chapter\s*memory|memory\s*capture|记忆沉淀)"
    return bool(
        re.search(rf"{capture_phrase}.*(规划|计划|捕获|沉淀|候选|知识库|记忆)", text)
        or re.search(rf"(规划|计划|捕获|沉淀|候选|知识库|记忆).*{capture_phrase}", text)
    )


def _post_chapter_memory_capture_params(text: str) -> dict[str, Any]:
    params: dict[str, Any] = {}
    chapter_index = parse_chapter_index(text)
    if chapter_index is not None:
        params["chapter_index"] = chapter_index
    return params


def _is_world_model_route_intent(text: str) -> bool:
    world_route_phrase = r"(世界模型路由|世界模型状态|world\s*model\s*route|athena\s*route)"
    return bool(
        re.search(rf"{world_route_phrase}.*(检查|诊断|路由|状态|事实|提案|profile)", text)
        or re.search(rf"(检查|诊断|路由|状态|事实|提案|profile).*{world_route_phrase}", text)
    )


def _world_model_route_params(text: str) -> dict[str, Any]:
    params: dict[str, Any] = {}
    chapter_index = parse_chapter_index(text)
    if chapter_index is not None:
        params["chapter_index"] = chapter_index
    subject_ref = _world_model_subject_ref(text)
    if subject_ref:
        params["subject_ref"] = subject_ref
    limit = _world_model_route_limit(text)
    if limit is not None:
        params["limit"] = limit
    return params


def _world_model_subject_ref(text: str) -> str | None:
    match = re.search(r"(?:subject_ref|subject|主体|对象)\s*[:=：]?\s*([a-z][a-z0-9_-]*\.[a-z0-9_.-]+)", text)
    if match:
        return match.group(1)
    match = re.search(r"\b([a-z][a-z0-9_-]*\.[a-z0-9_.-]+)\b", text)
    if match:
        return match.group(1)
    return None


def _world_model_route_limit(text: str) -> int | None:
    match = re.search(r"(?:limit|限制|最多)\s*[:=：]?\s*(\d{1,3})", text)
    if not match:
        return None
    try:
        value = int(match.group(1))
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _is_world_model_proposal_review_intent(text: str) -> bool:
    proposal_phrase = r"(世界模型提案|athena\s*提案|world\s*model\s*proposals?|world_model_proposals?)"
    return bool(
        re.search(
            rf"{proposal_phrase}.*(检查|查看|浏览|审查|队列|待处理|冲突|摘要|review|queue|limit|offset)",
            text,
        )
        or re.search(
            rf"(检查|查看|浏览|审查|队列|待处理|冲突|摘要|review|queue|limit|offset).*{proposal_phrase}",
            text,
        )
    )


def _is_world_model_proposal_resolution_plan_intent(text: str) -> bool:
    proposal_phrase = r"(世界模型提案|athena\s*提案|world\s*model\s*proposals?|world_model_proposals?)"
    plan_phrase = r"(规划|计划|方案|plan)"
    resolution_phrase = r"(解决|处理|决议|resolution|resolve)"
    return bool(
        re.search(rf"{proposal_phrase}.*{resolution_phrase}.*{plan_phrase}", text)
        or re.search(rf"{plan_phrase}.*{proposal_phrase}.*{resolution_phrase}", text)
        or re.search(rf"{resolution_phrase}.*{proposal_phrase}.*{plan_phrase}", text)
    )


def _world_model_proposal_queue_params(text: str) -> dict[str, Any]:
    params: dict[str, Any] = {}
    offset = _numeric_option(text, r"offset|偏移")
    if offset is not None:
        params["offset"] = offset
    limit = _numeric_option(text, r"limit|限制|最多")
    if limit is not None:
        params["limit"] = limit
    return params


def _is_retrieval_context_intent(text: str) -> bool:
    retrieval_phrase = r"(检索上下文|上下文证据|检索证据|retrieval\s*context|search\s*retrieval)"
    return bool(
        re.search(rf"{retrieval_phrase}.*(检索|搜索|取证|证据|query|limit)", text)
        or re.search(rf"(检索|搜索|取证|证据|query|limit).*{retrieval_phrase}", text)
    )


def _retrieval_context_params(text: str) -> dict[str, Any]:
    params: dict[str, Any] = {}
    query = _parameter_query(text) or _labeled_query(
        text,
        r"(?:检索上下文|上下文证据|检索证据|retrieval\s*context|search\s*retrieval)",
    )
    if query:
        params["query"] = query
    limit = _numeric_option(text, r"limit|限制|最多")
    if limit is not None:
        params["limit"] = limit
    source_type = _source_type_param(text)
    if source_type:
        params["source_type"] = source_type
    max_chapter_index = _numeric_option(text, r"max_chapter_index|max\s*chapter(?:\s*index)?")
    if max_chapter_index is None and re.search(r"(前|之前|以前|以内|上限|max)", text):
        max_chapter_index = parse_chapter_index(text)
    if max_chapter_index is not None:
        params["max_chapter_index"] = max_chapter_index
    candidate_limit = _numeric_option(text, r"candidate_limit|候选")
    if candidate_limit is not None:
        params["candidate_limit"] = candidate_limit
    return params


def _is_longform_context_summary_intent(text: str) -> bool:
    summary_phrase = r"(长篇上下文(?:摘要)?|上下文摘要|longform\s*context(?:\s*summary)?|context\s*summary)"
    return bool(
        re.search(rf"{summary_phrase}.*(汇总|摘要|总结|读取|生成|query|max_chars|prompt)", text)
        or re.search(rf"(汇总|摘要|总结|读取|生成|query|max_chars|prompt).*{summary_phrase}", text)
    )


def _longform_context_summary_params(text: str) -> dict[str, Any]:
    params: dict[str, Any] = {}
    chapter_index = parse_chapter_index(text)
    if chapter_index is not None:
        params["chapter_index"] = chapter_index
    query = _parameter_query(text) or _labeled_query(
        text,
        r"(?:长篇上下文(?:摘要)?|上下文摘要|longform\s*context(?:\s*summary)?|context\s*summary)",
    )
    if query:
        params["query"] = query
    max_chars = _numeric_option(text, r"max_chars|max\s*chars|最大字符|最多字符")
    if max_chars is not None:
        params["max_chars"] = max_chars
    if re.search(r"(include_prompt_context|prompt\s*context|prompt\s*上下文|包含\s*prompt)", text):
        params["include_prompt_context"] = True
    return params


def _parameter_query(text: str) -> str | None:
    match = re.search(
        r"(?:query|查询|检索词|关键词)\s*[:=：]\s*(.+?)(?=\s+(?:limit|限制|最多|max_chars|max\s*chars|"
        r"max_chapter_index|max\s*chapter|candidate_limit|source_type|include_prompt_context|prompt\s*context)\b|$)",
        text,
    )
    if not match:
        return None
    value = match.group(1).strip().rstrip("，,；;。")
    return value or None


def _numeric_option(text: str, option_pattern: str) -> int | None:
    match = re.search(rf"(?:{option_pattern})\s*[:=：]?\s*(\d{{1,6}})", text)
    if not match:
        return None
    try:
        value = int(match.group(1))
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _source_type_param(text: str) -> str | None:
    match = re.search(r"(?:source_type|source type|来源类型)\s*[:=：]?\s*([a-z][a-z0-9_-]{2,40})", text)
    if match:
        return match.group(1)
    return None


def _labeled_query(text: str, label_pattern: str) -> str | None:
    match = re.search(rf"{label_pattern}\s*[:：]\s*(.+)$", text)
    if not match:
        return None
    value = match.group(1).strip()
    return value or None


def _is_context_compression_payload_intent(text: str) -> bool:
    return bool(
        (
            re.search(r"(上下文|context|token).*(压缩|compression)", text)
            or re.search(r"(压缩|compression).*(上下文|context|token)", text)
        )
        and re.search(
            r"(payload|dry[-_\s]*run|载荷|负载|payload\s*builder|build_agent_context_compression_payload)",
            text,
        )
        and re.search(r"(构建|生成|build|准备|创建|产出)", text)
    )


def _context_compression_payload_params(text: str) -> dict[str, Any]:
    params = _context_compression_params(text)
    failure_count = _numeric_option(
        text,
        r"context_guard_failure_count|contextguard\s*失败|context\s*guard\s*failure(?:\s*count)?|"
        r"guard\s*failure(?:s)?|失败次数",
    )
    if failure_count is not None:
        params["context_guard_failure_count"] = failure_count
    return params


def _is_preflight_context_budget_intent(text: str) -> bool:
    has_preflight = bool(re.search(r"(预检|写前检查|生成前检查|preflight)", text))
    has_context_budget = bool(
        re.search(r"(上下文|context|token).*(预算|窗口|压力|压缩|guard|断路器)", text)
        or re.search(r"(预算|窗口|压力|压缩|guard|断路器).*(上下文|context|token)", text)
    )
    return has_preflight and has_context_budget


def _preflight_context_budget_params(text: str) -> dict[str, Any]:
    params: dict[str, Any] = {}
    chapter_index = parse_chapter_index(text)
    if chapter_index is not None:
        params["chapter_index"] = chapter_index
    max_context_chars = (
        _numeric_option(
            text,
            r"max_context_chars|max\s*context\s*chars|context\s*budget|上下文预算|窗口预算|预算字符|最大上下文",
        )
        or _context_compression_max_chars(text)
    )
    if max_context_chars is not None:
        params["max_context_chars"] = max_context_chars
    failure_count = _numeric_option(
        text,
        r"context_guard_failure_count|contextguard\s*失败|context\s*guard\s*failure(?:\s*count)?|"
        r"guard\s*failure(?:s)?|失败次数",
    )
    if failure_count is not None:
        params["context_guard_failure_count"] = failure_count
    return params


def _is_context_compression_intent(text: str) -> bool:
    return bool(
        re.search(r"(上下文|context|token).*(压缩|预算|窗口|压力|断路器|guard)", text)
        or re.search(r"(压缩|预算|窗口|压力|断路器|guard).*(上下文|context|token)", text)
    )


def _context_compression_params(text: str) -> dict[str, Any]:
    params: dict[str, Any] = {}
    chapter_index = parse_chapter_index(text)
    if chapter_index is not None:
        params["chapter_index"] = chapter_index
    max_chars = _context_compression_max_chars(text)
    if max_chars is not None:
        params["max_chars"] = max_chars
    return params


def _context_compression_max_chars(text: str) -> int | None:
    patterns = [
        r"(?:上下文|窗口|预算|max_chars|max|token)\D{0,8}(\d{3,6})",
        r"(\d{3,6})\s*(?:字|字符|token).*(?:上下文|窗口|预算)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        try:
            value = int(match.group(1))
        except (TypeError, ValueError):
            continue
        if value >= 500:
            return value
    return None


_WORKER_NAMES = (
    "drafting_worker",
    "reviewer_worker",
    "revision_worker",
    "memory_worker",
    "retrieval_worker",
    "world_model_worker",
    "recovery_worker",
)


def _is_worker_dispatch_intent(text: str) -> bool:
    return bool(
        re.search(r"(worker|子代理|子agent|子 agent).*(分发|分派|调度|恢复|孤儿|孤兒|orphan|审计)", text)
        or re.search(r"(分发|分派|调度|恢复|孤儿|孤兒|orphan|审计).*(worker|子代理|子agent|子 agent)", text)
        or re.search(r"(孤儿|孤兒|orphan).*(恢复|审计|清理|recovery)", text)
    )


def _worker_dispatch_params(text: str) -> dict[str, Any]:
    params: dict[str, Any] = {"tasks": []}
    worker_name = _worker_dispatch_worker_name(text)
    if worker_name:
        params["worker_name"] = worker_name
    return params


def _worker_dispatch_worker_name(text: str) -> str | None:
    for worker_name in _WORKER_NAMES:
        if worker_name in text:
            return worker_name
    return None


def _is_agent_event_projection_intent(text: str) -> bool:
    event_phrase = r"(事件投影|事件流|agent\s*event|event\s*projection|tool\s*event|工具事件)"
    return bool(
        re.search(rf"{event_phrase}.*(检查|诊断|查看|审计|task|run|limit)", text)
        or re.search(rf"(检查|诊断|查看|审计|task|run|limit).*{event_phrase}", text)
    )


def _agent_event_projection_params(text: str) -> dict[str, Any]:
    params: dict[str, Any] = {}
    task_id = _task_queue_task_id(text)
    if task_id:
        params["task_id"] = task_id
    run_id = _trace_audit_run_id(text)
    if run_id:
        params["run_id"] = run_id
    limit = _numeric_option(text, r"limit|限制|最多")
    if limit is not None:
        params["limit"] = limit
    return params


def _is_agent_job_projection_intent(text: str) -> bool:
    job_phrase = r"(任务队列|后台任务|任务投影|job\s*projection|agent\s*job|job\s*投影|task\s*queue)"
    return bool(
        re.search(rf"{job_phrase}.*(检查|诊断|查看|状态|进度|恢复|chapter|章节|task|limit)", text)
        or re.search(rf"(检查|诊断|查看|状态|进度|恢复|chapter|章节|task|limit).*{job_phrase}", text)
        or re.search(r"(running|failed|queued|completed|blocked|cancelled).*(任务队列|后台任务|task\s*queue)", text)
    )


def _agent_job_projection_params(text: str) -> dict[str, Any]:
    params: dict[str, Any] = {}
    chapter_index = parse_chapter_index(text)
    if chapter_index is not None:
        params["chapter_index"] = chapter_index
    task_id = _task_queue_task_id(text)
    if task_id:
        params["task_id"] = task_id
    task_type = _task_queue_task_type(text)
    if task_type:
        params["task_type"] = task_type
    status = _task_queue_status(text)
    if status:
        params["status"] = status
    limit = _numeric_option(text, r"limit|限制|最多")
    if limit is not None:
        params["limit"] = limit
    return params


def _task_queue_task_id(text: str) -> str | None:
    match = re.search(r"(?:task_id|task\s*id|任务\s*id)\s*[:=：]?\s*([a-z0-9][a-z0-9_-]{2,})", text)
    if match:
        return match.group(1)
    match = re.search(r"\b(task[-_][a-z0-9_-]{2,})\b", text)
    if match:
        return match.group(1)
    return None


_TASK_QUEUE_EXCLUDED_SNAKE_CASE_TOKENS = {
    "task_id",
    "run_id",
    "source_type",
    "max_chars",
    "max_chapter_index",
    "candidate_limit",
}


def _task_queue_task_type(text: str) -> str | None:
    match = re.search(r"(?:task_type|task\s*type|任务类型)\s*[:=：]?\s*([a-z][a-z0-9_]{2,80})", text)
    if match:
        return match.group(1)
    for match in re.finditer(r"\b([a-z][a-z0-9_]{2,80})\b", text):
        token = match.group(1).strip().lower()
        if "_" in token and token not in _TASK_QUEUE_EXCLUDED_SNAKE_CASE_TOKENS:
            return token
    return None


def _task_queue_status(text: str) -> str | None:
    status_patterns = (
        ("failed", r"\bfailed\b|失败|报错"),
        ("running", r"\brunning\b|执行中|运行中|进行中"),
        ("queued", r"\bqueued\b|排队|待执行|等待中"),
        ("pending", r"\bpending\b|待处理|未开始"),
        ("completed", r"\bcompleted\b|完成|已完成"),
        ("blocked", r"\bblocked\b|阻塞"),
        ("cancelled", r"\bcancelled\b|\bcanceled\b|取消|已取消"),
    )
    for status, pattern in status_patterns:
        if re.search(pattern, text):
            return status
    return None


def _is_chapter_conflict_recovery_intent(text: str) -> bool:
    return bool(
        re.search(r"(章节冲突|章节占用|chapter\s*conflict|conflict\s*recovery).*(规划|计划|恢复|解决|检查|诊断)", text)
        or re.search(r"(规划|计划|恢复|解决|检查|诊断).*(章节冲突|章节占用|chapter\s*conflict|conflict\s*recovery)", text)
    )


def _chapter_conflict_recovery_params(text: str) -> dict[str, Any]:
    params: dict[str, Any] = {}
    chapter_index = parse_chapter_index(text)
    if chapter_index is not None:
        params["chapter_index"] = chapter_index
    return params


def _is_legacy_hermes_migration_intent(text: str) -> bool:
    legacy_phrase = r"(legacy\s*hermes|hermes\s*legacy|legacy\s*action|hermes\s*action|旧版\s*hermes|旧\s*hermes)"
    migration_phrase = r"(迁移|migration|路线图|路线|agent[-_\s]*native|审批链|approval)"
    return bool(
        re.search(rf"{legacy_phrase}.*{migration_phrase}", text)
        or re.search(rf"{migration_phrase}.*{legacy_phrase}", text)
    )


def _is_route_approval_opt_in_apply_contract_intent(text: str) -> bool:
    return _is_route_approval_opt_in_phrase(text) and bool(re.search(r"(契约|contract|hash|哈希)", text))


def _is_route_approval_opt_in_apply_preview_intent(text: str) -> bool:
    if _is_route_approval_opt_in_apply_contract_intent(text) or _is_route_approval_opt_in_apply_prepare_intent(text):
        return False
    return _is_route_approval_opt_in_phrase(text) and bool(re.search(r"(预览|preview|diff|应用|apply|patch)", text))


def _is_route_approval_opt_in_apply_prepare_intent(text: str) -> bool:
    return _is_route_approval_opt_in_phrase(text) and bool(
        re.search(r"(执行审批|计划审批|agent\s*plan|approval\s*gate|with\s*approval|prepare[-_\s]*apply|prepare\s*tool)", text)
    )


def _is_route_approval_opt_in_plan_intent(text: str) -> bool:
    if (
        _is_route_approval_opt_in_apply_contract_intent(text)
        or _is_route_approval_opt_in_apply_prepare_intent(text)
        or _is_route_approval_opt_in_apply_preview_intent(text)
    ):
        return False
    return _is_route_approval_opt_in_phrase(text) and bool(re.search(r"(规划|计划|plan|准备|检查|诊断)", text))


def _is_route_approval_opt_in_phrase(text: str) -> bool:
    approval_phrase = bool(re.search(r"(审批链|approval\s*chain|route\s*approval|agent\s*approval)", text))
    opt_in_phrase = bool(re.search(r"opt[-_\s]*in", text))
    pending_action_phrase = bool(
        re.search(r"(pending[-_\s]*action|pending_action|待处理动作|\bpending[-_][a-z0-9_-]{2,}\b)", text)
    )
    route_params_phrase = bool(
        _dialog_control_plane_action_type(text) or _dialog_route_source(text) or _slash_command_name(text)
    )
    return approval_phrase and opt_in_phrase and (pending_action_phrase or route_params_phrase)


def _route_approval_opt_in_params(text: str) -> dict[str, Any]:
    params: dict[str, Any] = {}
    pending_action_id = _pending_action_id(text)
    if pending_action_id:
        params["pending_action_id"] = pending_action_id
    action_type = _dialog_control_plane_action_type(text)
    if action_type:
        params["action_type"] = action_type
    source = _dialog_route_source(text)
    if source:
        params["source"] = source
    command_name = _slash_command_name(text)
    if command_name:
        params["command_name"] = command_name
    return params


def _pending_action_id(text: str) -> str | None:
    match = re.search(
        r"(?:pending_action_id|pending\s*action\s*id|待处理动作\s*id)\s*[:=：]?\s*([a-z0-9][a-z0-9_-]{2,})",
        text,
    )
    if match:
        return match.group(1)
    match = re.search(r"\b(pending[-_][a-z0-9_-]{2,})\b", text)
    if match:
        return match.group(1)
    return None


def _is_tool_contracts_intent(text: str) -> bool:
    if re.search(r"(控制面|control\s*plane)", text):
        return False
    return bool(
        re.search(r"(工具契约|tool\s*contract).*(覆盖|coverage|迁移|差距|gap|缺口|快照|snapshot|检查|自检|诊断)", text)
        or re.search(r"(覆盖|coverage|迁移|差距|gap|缺口|快照|snapshot|检查|自检|诊断).*(工具契约|tool\s*contract)", text)
    )


def _is_command_contracts_intent(text: str) -> bool:
    if re.search(r"(控制面|control\s*plane)", text):
        return False
    if _is_slash_command_route_intent(text):
        return False
    return bool(
        re.search(
            r"(命令契约|command\s*contract|slash\s*command|斜杠命令).*(覆盖|coverage|投影|projection|依赖|缺口|gap|快照|snapshot|检查|自检|诊断)",
            text,
        )
        or re.search(
            r"(覆盖|coverage|投影|projection|依赖|缺口|gap|快照|snapshot|检查|自检|诊断).*(命令契约|command\s*contract|slash\s*command|斜杠命令)",
            text,
        )
    )


def _is_slash_command_route_intent(text: str) -> bool:
    return bool(
        re.search(r"(斜杠命令|slash\s*command|/\w+).*(路由|route|映射)", text)
        or re.search(r"(路由|route|映射).*(斜杠命令|slash\s*command|/\w+)", text)
    )


def _slash_command_route_params(text: str) -> dict[str, Any]:
    params: dict[str, Any] = {}
    command_name = _slash_command_name(text)
    if command_name:
        params["command_name"] = command_name
    return params


def _slash_command_name(text: str) -> str | None:
    match = re.search(r"/([a-z][a-z0-9_-]{1,40})\b", text)
    if match:
        return match.group(1).lower()
    match = re.search(r"\b(continue|status|clear|compact|setup|storyline|outline|chapter)\s*(?:命令|command)\b", text)
    if match:
        return match.group(1).lower()
    return None


def _is_dialog_route_projection_intent(text: str) -> bool:
    if _is_route_preference_intent(text):
        return False
    return bool(
        re.search(
            r"(对话路由|dialog\s*route|统一路由|路由投影|route\s*projection).*(投影|检查|诊断|映射|统一)",
            text,
        )
        or re.search(
            r"(投影|检查|诊断|映射|统一).*(对话路由|dialog\s*route|统一路由|路由投影|route\s*projection)",
            text,
        )
    )


def _dialog_route_projection_params(text: str) -> dict[str, Any]:
    params: dict[str, Any] = {}
    source = _dialog_route_source(text)
    if source:
        params["source"] = source
    return params


def _is_intent_projection_intent(text: str) -> bool:
    return bool(
        re.search(r"(意图投影|意图路由投影|自然语言意图投影|intent\s*projection).*(检查|诊断|投影|解释)", text)
        or re.search(r"(检查|诊断|投影|解释).*(意图投影|意图路由投影|自然语言意图投影|intent\s*projection)", text)
    )


def _intent_projection_params(text: str) -> dict[str, Any]:
    return {"text": _intent_projection_text(text)}


def _intent_projection_text(text: str) -> str:
    match = re.search(
        r"(?:意图投影|意图路由投影|自然语言意图投影|intent\s*projection)\s*[:：]\s*(.+)$",
        text,
    )
    if match:
        return match.group(1).strip()
    return text


def _is_dialog_control_plane_projection_intent(text: str) -> bool:
    return bool(
        re.search(
            r"(对话控制面|dialog\s*control\s*plane|pending\s*action\s*control).*(投影|检查|诊断|审批链|工具链)",
            text,
        )
        or re.search(
            r"(投影|检查|诊断|审批链|工具链).*(对话控制面|dialog\s*control\s*plane|pending\s*action\s*control)",
            text,
        )
    )


def _dialog_control_plane_projection_params(text: str) -> dict[str, Any]:
    params: dict[str, Any] = {}
    action_type = _dialog_control_plane_action_type(text)
    if action_type:
        params["action_type"] = action_type
    return params


def _dialog_control_plane_action_type(text: str) -> str | None:
    for action_type in (
        "generate_setup",
        "generate_storyline",
        "generate_outline",
        "generate_chapter",
        "review_chapter",
        "recover_blocked_run",
    ):
        if action_type in text:
            return action_type
    if re.search(r"(设定|setup)", text):
        return "generate_setup"
    if re.search(r"(故事线|storyline)", text):
        return "generate_storyline"
    if re.search(r"(大纲|outline)", text):
        return "generate_outline"
    if re.search(r"(正文|章节|chapter)", text):
        return "generate_chapter"
    if re.search(r"(审稿|review)", text):
        return "review_chapter"
    if re.search(r"(恢复|recover)", text):
        return "recover_blocked_run"
    return None


_MUTATION_FINGERPRINT_EXCLUDED_TOOL_TOKENS = {
    "mutation_fingerprint",
    "mutation_fingerprints",
    "write_fingerprint",
    "write_fingerprints",
}

_MUTATION_FINGERPRINT_CHAPTER_INDEX_TOOLS = {
    "execute_generate_chapter_with_approval",
    "generate_chapter",
    "generate_chapter_range",
    "expand_outline_window",
    "execute_expand_outline_window_with_approval",
    "analyze_chapter_world_model",
    "backfill_outline_gaps",
    "create_revision_draft",
    "apply_planner_revision_patch",
    "execute_apply_planner_revision_patch_with_approval",
    "expand_chapter_to_target",
    "execute_expand_chapter_to_target_with_approval",
    "compress_chapter_to_target",
    "execute_compress_chapter_to_target_with_approval",
}


def _is_mutation_fingerprints_intent(text: str) -> bool:
    fingerprint_phrase = r"(变更指纹|写入指纹|mutation\s*fingerprints?|write\s*fingerprints?)"
    return bool(
        re.search(rf"{fingerprint_phrase}.*(检查|诊断|审计|计算|工具|tool|写入|write)", text)
        or re.search(rf"(检查|诊断|审计|计算|工具|tool|写入|write).*{fingerprint_phrase}", text)
        or re.search(r"(写入|write|mutating|工具|tool).*(指纹|fingerprint)", text)
    )


def _mutation_fingerprints_params(text: str) -> dict[str, Any]:
    tool_names = _mutation_fingerprint_tool_names(text)
    if not tool_names:
        return {}

    chapter_index = parse_chapter_index(text)
    tools: list[dict[str, Any]] = []
    for tool_name in tool_names:
        params: dict[str, Any] = {}
        if chapter_index is not None and tool_name in _MUTATION_FINGERPRINT_CHAPTER_INDEX_TOOLS:
            params["chapter_index"] = chapter_index
        tools.append({"tool_name": tool_name, "params": params})
    return {"tools": tools}


def _mutation_fingerprint_tool_names(text: str) -> list[str]:
    names: list[str] = []
    for match in re.finditer(r"\b([a-z][a-z0-9_]{2,80})\b", text):
        name = match.group(1).strip().lower()
        if "_" not in name or name in _MUTATION_FINGERPRINT_EXCLUDED_TOOL_TOKENS or name in names:
            continue
        names.append(name)
    if names:
        return names

    action_type = _dialog_control_plane_action_type(text)
    if action_type in {"generate_setup", "generate_storyline", "generate_outline", "generate_chapter"}:
        return [action_type]
    return []


def _is_reference_alignment_intent(text: str) -> bool:
    return bool(
        re.search(
            r"(参考项目|参考模式|开源项目|openclaw|hermes-agent|openhuman).*(对齐|适配|映射|alignment|pattern|模式|建议|检查|审计)",
            text,
        )
        or re.search(
            r"(对齐|适配|映射|alignment|pattern|模式|建议|检查|审计).*(参考项目|参考模式|开源项目|openclaw|hermes-agent|openhuman)",
            text,
        )
    )


def _is_dogfood_evidence_intent(text: str) -> bool:
    return bool(
        re.search(
            r"(dogfood|pressure[-\s]*test|自吃|自测|真实长篇).*(证据|覆盖|coverage|审计|检查|诊断)",
            text,
        )
        or re.search(
            r"(证据|覆盖|coverage|审计|检查|诊断).*(dogfood|pressure[-\s]*test|自吃|自测|真实长篇)",
            text,
        )
    )


def _is_route_preference_intent(text: str) -> bool:
    return bool(
        re.search(
            r"(路由偏好|route\s*preference|审批链|approval\s*chain).*(迁移|建议|投影|检查|诊断|偏好|opt[-_\s]*in)",
            text,
        )
        or re.search(
            r"(迁移|建议|投影|检查|诊断|偏好|opt[-_\s]*in).*(路由偏好|route\s*preference|审批链|approval\s*chain)",
            text,
        )
    )


def _route_preference_params(text: str) -> dict[str, Any]:
    params: dict[str, Any] = {}
    source = _dialog_route_source(text)
    if source:
        params["source"] = source
    return params


def _dialog_route_source(text: str) -> str | None:
    if re.search(r"(slash[_\s-]*command|斜杠命令|/命令)", text):
        return "slash_command"
    if re.search(r"(text[_\s-]*intent|自然语言|文本意图|文字意图)", text):
        return "text_intent"
    if re.search(r"(button[_\s-]*action|按钮|action\s*card|操作卡片)", text):
        return "button_action"
    return None


def _is_control_plane_readiness_intent(text: str) -> bool:
    return bool(
        re.search(r"(控制面|control\s*plane).*(就绪|ready|readiness|契约|contract|自检|诊断)", text)
        or re.search(r"(就绪|ready|readiness|契约|contract|自检|诊断).*(控制面|control\s*plane)", text)
        or re.search(r"(工具契约|命令契约|tool\s*contract|command\s*contract).*(就绪|缺口|自检|诊断|检查)", text)
        or re.search(r"(就绪|缺口|自检|诊断|检查).*(工具契约|命令契约|tool\s*contract|command\s*contract)", text)
    )


def _is_trace_audit_intent(text: str) -> bool:
    return bool(
        re.search(r"(trace|追踪|执行链|链路).*(审计|检查|查看|分析|失败原因)", text)
        or re.search(r"(审计|检查|查看|分析).*(trace|追踪|执行链|链路)", text)
        or re.search(r"\brun[-_\w]+\b.*(trace|追踪|审计|执行链|链路|失败原因)", text)
    )


def _is_trace_anomaly_trends_intent(text: str) -> bool:
    return bool(
        re.search(r"(trace|追踪|执行链|链路).*(异常|anomal|趋势|trend|聚合|统计)", text)
        or re.search(r"(异常|anomal|趋势|trend|聚合|统计).*(trace|追踪|执行链|链路)", text)
    )


def _is_trace_anomaly_long_run_samples_intent(text: str) -> bool:
    return bool(
        re.search(
            r"(trace|追踪|执行链|链路).*(异常|anomal).*(长跑|long[-\s]*run|dogfood|自吃|真实).*(样本|sample|采集|collection)",
            text,
        )
        or re.search(
            r"(长跑|long[-\s]*run|dogfood|自吃|真实).*(样本|sample|采集|collection).*(trace|追踪|执行链|链路).*(异常|anomal)",
            text,
        )
        or re.search(
            r"(trace|追踪|执行链|链路).*(长跑|long[-\s]*run|dogfood|自吃|真实).*(样本|sample|采集|collection)",
            text,
        )
    )


def _trace_anomaly_long_run_samples_params(text: str) -> dict[str, Any]:
    params = _trace_anomaly_trends_params(text)
    minimum_review_run_count = _minimum_review_run_count_param(text)
    if minimum_review_run_count is not None:
        params["minimum_review_run_count"] = minimum_review_run_count
    return params


def _is_trace_anomaly_threshold_review_intent(text: str) -> bool:
    return bool(
        re.search(
            r"(trace|追踪|执行链|链路).*(异常|anomal).*(阈值|threshold).*(复核|review|样本|sample|校准|固化)",
            text,
        )
        or re.search(
            r"(复核|review|样本|sample|校准|固化).*(trace|追踪|执行链|链路).*(异常|anomal).*(阈值|threshold)",
            text,
        )
        or re.search(
            r"(trace|追踪|执行链|链路).*(阈值|threshold).*(复核|review|样本|sample|校准|固化)",
            text,
        )
        or re.search(
            r"(复核|review|样本|sample|校准|固化).*(阈值|threshold).*(trace|追踪|执行链|链路)",
            text,
        )
    )


def _trace_anomaly_trends_params(text: str) -> dict[str, Any]:
    params: dict[str, Any] = {}
    chapter_index = parse_chapter_index(text)
    if chapter_index is not None:
        params["chapter_index"] = chapter_index
    limit = _limit_param(text)
    if limit is not None:
        params["limit"] = limit
    baseline_limit = _baseline_limit_param(text)
    if baseline_limit is not None:
        params["baseline_limit"] = baseline_limit
    return params


def _trace_audit_params(text: str) -> dict[str, Any]:
    params: dict[str, Any] = {}
    run_id = _trace_audit_run_id(text)
    if run_id:
        params["run_id"] = run_id
    chapter_index = parse_chapter_index(text)
    if chapter_index is not None:
        params["chapter_index"] = chapter_index
    return params


def _trace_audit_run_id(text: str) -> str | None:
    match = re.search(r"\b(run[-_a-z0-9]+)\b", text)
    if match:
        return match.group(1)
    match = re.search(r"(?:run_id|run\s*id)\s*[:=：]?\s*([a-z0-9][a-z0-9_-]{2,})", text)
    if match:
        return match.group(1)
    return None


def _limit_param(text: str) -> int | None:
    match = re.search(r"\blimit\s*[:=：]?\s*(\d+)", text, re.IGNORECASE)
    if not match:
        match = re.search(r"(?:最近|返回|前)\s*(\d+)\s*(?:个|条|次)?", text)
    if not match:
        return None
    try:
        parsed = int(match.group(1))
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def _baseline_limit_param(text: str) -> int | None:
    match = re.search(r"\b(?:baseline|base)\s*[:=：]?\s*(\d+)", text, re.IGNORECASE)
    if not match:
        match = re.search(r"(?:基线|历史|对照)\s*(\d+)\s*(?:个|条|次)?", text)
    if not match:
        return None
    try:
        parsed = int(match.group(1))
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def _minimum_review_run_count_param(text: str) -> int | None:
    match = re.search(r"\b(?:minimum_review_run_count|min_review_runs|min_samples)\s*[:=：]?\s*(\d+)", text, re.IGNORECASE)
    if not match:
        match = re.search(r"(?:最少|至少)\s*(\d+)\s*(?:个|条|次)?(?:复核)?(?:样本|run|运行)", text)
    if not match:
        return None
    try:
        parsed = int(match.group(1))
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def _is_write_gate_coverage_intent(text: str) -> bool:
    return bool(
        re.search(r"(写入|写工具|write).*(门禁|gate|审批|approval).*(覆盖|coverage|缺口|风险|检查|审计)", text)
        or re.search(r"(门禁|gate|审批|approval).*(覆盖|coverage|缺口|风险).*(写入|写工具|write)", text)
        or re.search(r"(write\s*gate|写入门禁|审批门禁).*(覆盖|coverage|缺口|自检|审计|检查)", text)
    )


def _is_agent_health_intent(text: str) -> bool:
    return bool(
        re.search(r"(agent|工具|tool|health).*(健康|自检|诊断|health)", text)
        or re.search(r"(健康|自检|诊断|health).*(agent|工具|tool)", text)
    )


def _agent_health_params(text: str) -> dict[str, Any]:
    params: dict[str, Any] = {}
    chapter_index = parse_chapter_index(text)
    if chapter_index is not None:
        params["chapter_index"] = chapter_index
    return params


def _rejected_candidates(selected_rule_id: str | None, *, matched: bool) -> list[dict[str, str]]:
    reason_code = "not_selected" if matched else "intent_pattern_not_matched"
    return [
        {"rule_id": rule_id, "reason_code": reason_code}
        for rule_id in _INTENT_RULE_IDS
        if rule_id != selected_rule_id
    ]
