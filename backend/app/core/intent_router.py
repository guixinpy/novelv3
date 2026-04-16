import re
from app.schemas import ProjectDiagnosisOut


class ActionCandidate:
    def __init__(self, type: str, params: dict | None = None):
        self.type = type
        self.params = params or {}


class IntentRouter:
    def resolve(
        self,
        user_input: str,
        dialog_state: str,
        pending_action_id: str | None,
        diagnosis: ProjectDiagnosisOut,
    ) -> ActionCandidate | None:
        text = user_input.strip().lower()

        if pending_action_id:
            return self._resolve_confirmation(text)

        return self._resolve_action_candidate(text, diagnosis)

    def _resolve_confirmation(self, text: str) -> ActionCandidate | None:
        confirm_patterns = [r"^好的?$", r"^可以$", r"^同意$", r"^行$", r"^ok$", r"^没问题$", r"^搞吧$", r"^那就这样吧$"]
        cancel_patterns = [r"^算了$", r"^先不要$", r"^等等$", r"^不对$", r"^先别$", r"^我还没想好$", r"^换一个$"]
        revise_patterns = [r"改一下", r"先把", r"换成", r"改成"]

        for p in confirm_patterns:
            if re.search(p, text):
                return ActionCandidate("confirm")
        for p in cancel_patterns:
            if re.search(p, text):
                return ActionCandidate("cancel")
        for p in revise_patterns:
            if re.search(p, text):
                return ActionCandidate("revise", {"comment": text})
        return None

    def _resolve_action_candidate(self, text: str, diagnosis: ProjectDiagnosisOut) -> ActionCandidate | None:
        if re.search(r"创建.*(主角|人物|设定|世界观)", text) or re.search(r"生成.*设定", text):
            if "setup" in diagnosis.missing_items or "setup" in diagnosis.completed_items:
                return ActionCandidate("preview_setup", {"project_id": ""})

        if re.search(r"创建.*(主枝干|故事线)", text) or re.search(r"生成.*故事线", text):
            if "storyline" in diagnosis.missing_items:
                return ActionCandidate("preview_storyline", {"project_id": ""})

        if re.search(r"写第.*章大纲|生成章节大纲|生成.*大纲", text):
            if "outline" in diagnosis.missing_items:
                return ActionCandidate("preview_outline", {"project_id": ""})

        if re.search(r"还有什么要设定的|接下来做什么|然后呢", text):
            return ActionCandidate("query_diagnosis", {"project_id": ""})

        return None
