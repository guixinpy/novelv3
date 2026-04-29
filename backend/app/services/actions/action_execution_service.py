from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.intent_router import parse_chapter_index
from app.models import AIModelCallTrace


def chapter_action_params(command_args: str | None = None, candidate_params: dict | None = None) -> dict:
    params = dict(candidate_params or {})
    chapter_index = params.get("chapter_index") or parse_chapter_index(command_args) or 1
    params["chapter_index"] = int(chapter_index)
    return params


def action_label(action_type: str, result: dict | None = None, command_args: str | None = None, action_params: dict | None = None) -> str:
    label_map = {"generate_setup": "设定", "generate_storyline": "故事线", "generate_outline": "大纲"}
    if action_type == "generate_chapter":
        chapter_index = (result or {}).get("chapter_index") or chapter_action_params(command_args, action_params).get("chapter_index", 1)
        return f"第{chapter_index}章正文"
    return label_map.get(action_type, action_type)


class ActionExecutionService:
    def __init__(self, db: Session):
        self.db = db

    async def execute(
        self,
        action_type: str,
        project_id: str,
        *,
        command_args: str | None = None,
        action_params: dict | None = None,
    ) -> dict:
        if not project_id:
            return {"status": "failed", "error": "缺少项目 ID"}
        try:
            if action_type == "generate_setup":
                from app.api.setups import generate_setup

                await generate_setup(project_id, self.db, command_args=command_args)
                result = {"status": "success"}
                if trace_id := self.latest_trace_id(project_id=project_id, trace_type="setup_generation"):
                    result["trace_id"] = trace_id
                return result
            if action_type == "generate_storyline":
                from app.api.storylines import generate_storyline

                await generate_storyline(project_id, self.db, command_args=command_args)
                result = {"status": "success"}
                if trace_id := self.latest_trace_id(project_id=project_id, trace_type="storyline_generation"):
                    result["trace_id"] = trace_id
                return result
            if action_type == "generate_outline":
                from app.api.outlines import generate_outline

                await generate_outline(project_id, self.db, command_args=command_args)
                result = {"status": "success"}
                if trace_id := self.latest_trace_id(project_id=project_id, trace_type="outline_generation"):
                    result["trace_id"] = trace_id
                return result
            if action_type == "generate_chapter":
                from app.api.chapters import create_or_replace_chapter

                chapter_index = chapter_action_params(command_args, action_params).get("chapter_index", 1)
                await create_or_replace_chapter(
                    self.db,
                    project_id,
                    int(chapter_index),
                    extra_feedback=(command_args or "").strip(),
                )
                result = {"status": "success", "chapter_index": int(chapter_index)}
                trace_id = self.latest_trace_id(
                    project_id=project_id,
                    trace_type="chapter_generation",
                    chapter_index=int(chapter_index),
                )
                if trace_id:
                    result["trace_id"] = trace_id
                return result
            return {"status": "success"}
        except HTTPException as exc:
            return {"status": "failed", "error": exc.detail}
        except Exception as exc:
            return {"status": "failed", "error": str(exc)}

    def latest_trace_id(
        self,
        *,
        project_id: str,
        trace_type: str,
        chapter_index: int | None = None,
    ) -> str | None:
        query = self.db.query(AIModelCallTrace).filter(
            AIModelCallTrace.project_id == project_id,
            AIModelCallTrace.trace_type == trace_type,
        )
        if chapter_index is not None:
            query = query.filter(AIModelCallTrace.chapter_index == chapter_index)
        trace = query.order_by(AIModelCallTrace.created_at.desc(), AIModelCallTrace.id.desc()).first()
        return trace.id if trace else None

