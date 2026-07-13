"""v1 dialog 工具函数 — 从 dialogs.py 抽取，供 athena_dialog 使用。"""
from __future__ import annotations

from app.core.ui_hints import build_ui_hint
from app.schemas.workspace import ProjectDiagnosisOut


def _build_chat_idle_hint(reason: str) -> dict:
    return build_ui_hint(
        action_type="chat",
        dialog_state="CHATTING",
        status="idle",
        reason=reason,
    )


def _build_diagnosis(db, project_id: str) -> ProjectDiagnosisOut:
    from app.services.workspace.bootstrap import build_project_diagnosis
    return build_project_diagnosis(db, project_id)
