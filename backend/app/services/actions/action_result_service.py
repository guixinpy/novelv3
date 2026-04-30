from sqlalchemy.orm import Session

from app.models import AIModelCallTrace, Dialog, DialogMessage
from app.services.actions.action_execution_service import action_label


class ActionResultService:
    def __init__(self, db: Session):
        self.db = db

    def record_completion(
        self,
        *,
        action_type: str,
        project_id: str,
        dialog_id: str,
        result: dict,
        command_args: str | None = None,
        action_params: dict | None = None,
    ) -> DialogMessage | None:
        label = action_label(action_type, result, command_args, action_params)
        dialog = self.db.query(Dialog).filter(Dialog.id == dialog_id).first()
        if dialog:
            dialog.state = "chatting"

        if result.get("status") == "success":
            message = DialogMessage(
                dialog_id=dialog_id,
                role="system",
                content=f"{label}生成完成。{_athena_analysis_notice(result)}",
                action_result={"type": action_type, "status": "success", "data": result},
            )
            self.db.add(message)
            self.db.flush()
            self._attach_trace(project_id=project_id, dialog_id=dialog_id, message_id=message.id, trace_id=result.get("trace_id"))
        else:
            message = DialogMessage(
                dialog_id=dialog_id,
                role="system",
                content=f"{label}生成失败：{result.get('error', '未知错误')}",
                action_result={"type": action_type, "status": "failed"},
            )
            self.db.add(message)

        self.db.commit()
        self.db.refresh(message)
        return message

    def _attach_trace(self, *, project_id: str, dialog_id: str, message_id: str, trace_id: str | None) -> None:
        if not trace_id:
            return
        trace = self.db.query(AIModelCallTrace).filter(
            AIModelCallTrace.id == trace_id,
            AIModelCallTrace.project_id == project_id,
        ).first()
        if trace:
            trace.dialog_id = dialog_id
            trace.response_message_id = message_id


def _athena_analysis_notice(result: dict) -> str:
    analysis = result.get("athena_analysis")
    if not isinstance(analysis, dict):
        return ""
    if analysis.get("status") == "skipped" and analysis.get("reason") == "missing_world_model_profile":
        return "Athena 世界模型尚未导入，已跳过本章世界事实分析；请先在雅典娜导入 Setup 后重新分析章节。"
    return ""
