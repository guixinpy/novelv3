import hashlib
import re
from dataclasses import dataclass
from typing import Any

from app.core.dialog_agent_routes import build_dialog_agent_route
from app.schemas import ProjectDiagnosisOut

INTENT_PROJECTION_VERSION = "phase105.intent_projection.v1"
_INTENT_RULE_IDS = (
    "setup_intent",
    "storyline_intent",
    "outline_intent",
    "chapter_intent",
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
        if self.candidate is not None and self.candidate.type.startswith("preview_"):
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

        if "outline" in diagnosis.completed_items and re.search(r"(开始|继续|生成|写|创作).*(正文|章节|第\s*[\d零〇一二两三四五六七八九十]+\s*章|下一章)", text):
            chapter_index = parse_chapter_index(text) or 1
            return self._matched_projection(
                text,
                dialog_state,
                pending_action_id,
                diagnosis,
                rule_id="chapter_intent",
                candidate=ActionCandidate("preview_chapter", {"chapter_index": chapter_index}),
                extracted_params={"chapter_index": chapter_index},
                match_evidence=[{"kind": "pattern", "name": "chapter_generation_phrase"}],
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


def _rejected_candidates(selected_rule_id: str | None, *, matched: bool) -> list[dict[str, str]]:
    reason_code = "not_selected" if matched else "intent_pattern_not_matched"
    return [
        {"rule_id": rule_id, "reason_code": reason_code}
        for rule_id in _INTENT_RULE_IDS
        if rule_id != selected_rule_id
    ]
