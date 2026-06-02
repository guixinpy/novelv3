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
    "context_compression_intent",
    "worker_dispatch_intent",
    "trace_audit_intent",
    "write_gate_coverage_intent",
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
