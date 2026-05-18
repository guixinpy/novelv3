from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.world_proposal_review_queue import build_proposal_review_queue
from app.core.outline_lookup import find_outline_chapter
from app.models import (
    AIModelCallTrace,
    ChapterContent,
    Outline,
    Project,
    ProjectProfileVersion,
    Setup,
    Storyline,
    WritingAgentRun,
    WritingAgentStep,
)
from app.schemas.writing_agent import WritingAgentRunCreate, WritingAgentToolRequest
from app.services.actions.action_execution_service import ActionExecutionService

RUN_PENDING = "pending"
RUN_RUNNING = "running"
RUN_SUCCESS = "success"
RUN_FAILED = "failed"
RUN_CANCELLED = "cancelled"
RUN_BLOCKED = "blocked"

STEP_PENDING = "pending"
STEP_RUNNING = "running"
STEP_SUCCESS = "success"
STEP_FAILED = "failed"
STEP_BLOCKED = "blocked"

ALLOWED_TOOLS = {
    "generate_setup",
    "generate_storyline",
    "generate_outline",
    "generate_chapter",
    "preflight_writing",
    "import_setup_world_model",
    "analyze_chapter_world_model",
    "expand_outline_window",
}
CHAPTER_TOOL_NAME = "generate_chapter"
INTERNAL_TOOLS = {"preflight_writing", "import_setup_world_model", "analyze_chapter_world_model", "expand_outline_window"}


class WritingAgentRunService:
    def __init__(self, db: Session):
        self.db = db

    def create_run(self, project_id: str, payload: WritingAgentRunCreate) -> WritingAgentRun:
        self._require_project(project_id)
        run = WritingAgentRun(
            project_id=project_id,
            goal=payload.goal,
            status=RUN_PENDING,
            entrypoint=payload.entrypoint or "api",
            input={
                **(payload.input or {}),
                "tools": [tool.model_dump() for tool in payload.tools],
            },
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    async def execute_run(self, run_id: str, tools: list[WritingAgentToolRequest]) -> WritingAgentRun:
        run = self._get_run(run_id)
        if run.status == RUN_CANCELLED:
            return run

        now = _now()
        run.status = RUN_RUNNING
        run.started_at = run.started_at or now
        run.updated_at = now
        self.db.commit()
        self.db.refresh(run)

        for step_index, tool in enumerate(tools, start=1):
            step = self._start_step(run, step_index, tool)
            if tool.tool_name not in ALLOWED_TOOLS:
                self._fail_step_and_run(run, step, f"Unsupported writing agent tool: {tool.tool_name}")
                return run

            result = await self._execute_tool(run.project_id, tool)
            if not isinstance(result, dict):
                result = {"status": "failed", "error": "Tool returned non-dict result"}
            if result.get("status") == RUN_BLOCKED:
                self._block_step_and_run(run, step, _block_message(result), output=result)
                return run
            if result.get("status") == "failed":
                self._fail_step_and_run(run, step, str(result.get("error") or "Tool execution failed"), output=result)
                return run

            output = self._enrich_step_output(run.project_id, tool=tool, result=result)
            self._complete_step(step, output)

        run.status = RUN_SUCCESS
        run.error = None
        run.finished_at = _now()
        run.updated_at = run.finished_at
        run.output = self._run_output(run.id)
        self.db.commit()
        self.db.refresh(run)
        return run

    async def _execute_tool(self, project_id: str, tool: WritingAgentToolRequest) -> dict[str, Any]:
        if tool.tool_name not in INTERNAL_TOOLS:
            return await ActionExecutionService(self.db).execute(
                tool.tool_name,
                project_id,
                command_args=tool.command_args,
                action_params=tool.params,
            )
        if tool.tool_name == "preflight_writing":
            return self._preflight_writing(project_id, tool.params)
        if tool.tool_name == "import_setup_world_model":
            from app.core.athena_longform import import_setup_to_world_model

            return import_setup_to_world_model(db=self.db, project_id=project_id)
        if tool.tool_name == "analyze_chapter_world_model":
            from app.core.athena_longform import analyze_chapter_to_world_proposals

            chapter_index = int(tool.params.get("chapter_index") or 1)
            return analyze_chapter_to_world_proposals(db=self.db, project_id=project_id, chapter_index=chapter_index)
        if tool.tool_name == "expand_outline_window":
            from app.api.outlines import expand_outline_window

            start_chapter = int(tool.params.get("start_chapter") or tool.params.get("chapter_index") or 1)
            end_chapter = int(tool.params.get("end_chapter") or start_chapter)
            command_args = str(tool.params.get("command_args") or tool.command_args or "").strip() or None
            outline = await expand_outline_window(
                project_id,
                start_chapter=start_chapter,
                end_chapter=end_chapter,
                db=self.db,
                command_args=command_args,
            )
            merge = getattr(outline, "outline_expansion_result", {}) or {}
            return {
                "status": "completed",
                "start_chapter": start_chapter,
                "end_chapter": end_chapter,
                "outline_id": outline.id,
                "total_chapters": outline.total_chapters,
                "added_chapter_count": int(merge.get("added_chapter_count") or 0),
                "merge": merge,
                "trace_id": getattr(outline, "last_expansion_trace_id", None),
            }
        return {"status": "failed", "error": f"Unsupported writing agent tool: {tool.tool_name}"}

    def list_runs(self, project_id: str, *, offset: int = 0, limit: int = 20) -> dict[str, Any]:
        self._require_project(project_id)
        clamped_limit = min(max(limit, 1), 100)
        query = self.db.query(WritingAgentRun).filter(WritingAgentRun.project_id == project_id)
        total = query.with_entities(func.count(WritingAgentRun.id)).order_by(None).scalar() or 0
        items = (
            query.order_by(WritingAgentRun.created_at.desc(), WritingAgentRun.id.desc())
            .offset(offset)
            .limit(clamped_limit)
            .all()
        )
        return {
            "total": total,
            "items": items,
            "offset": offset,
            "limit": clamped_limit,
            "has_more": offset + len(items) < total,
        }

    def get_run_detail(self, project_id: str, run_id: str) -> dict[str, Any]:
        self._require_project(project_id)
        run = (
            self.db.query(WritingAgentRun)
            .filter(WritingAgentRun.project_id == project_id, WritingAgentRun.id == run_id)
            .first()
        )
        if run is None:
            raise HTTPException(status_code=404, detail="Writing agent run not found")
        steps = (
            self.db.query(WritingAgentStep)
            .filter(WritingAgentStep.project_id == project_id, WritingAgentStep.run_id == run_id)
            .order_by(WritingAgentStep.step_index.asc(), WritingAgentStep.id.asc())
            .all()
        )
        return {"run": run, "steps": steps}

    def cancel_run(self, project_id: str, run_id: str) -> WritingAgentRun:
        detail = self.get_run_detail(project_id, run_id)
        run: WritingAgentRun = detail["run"]
        if run.status in {RUN_PENDING, RUN_RUNNING}:
            now = _now()
            run.status = RUN_CANCELLED
            run.error = "Cancelled by user"
            run.finished_at = now
            run.updated_at = now
            self.db.commit()
            self.db.refresh(run)
        return run

    def _require_project(self, project_id: str) -> Project:
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return project

    def _get_run(self, run_id: str) -> WritingAgentRun:
        run = self.db.query(WritingAgentRun).filter(WritingAgentRun.id == run_id).first()
        if run is None:
            raise HTTPException(status_code=404, detail="Writing agent run not found")
        return run

    def _start_step(
        self,
        run: WritingAgentRun,
        step_index: int,
        tool: WritingAgentToolRequest,
    ) -> WritingAgentStep:
        step = WritingAgentStep(
            run_id=run.id,
            project_id=run.project_id,
            step_index=step_index,
            tool_name=tool.tool_name,
            status=STEP_RUNNING,
            input={"command_args": tool.command_args, "params": tool.params},
            started_at=_now(),
        )
        self.db.add(step)
        self.db.commit()
        self.db.refresh(step)
        return step

    def _complete_step(self, step: WritingAgentStep, output: dict[str, Any]) -> None:
        trace_id = _optional_existing_trace_id(self.db, step.project_id, output.get("trace_id"))
        step.status = STEP_SUCCESS
        step.output = output
        step.error = None
        step.trace_id = trace_id
        step.target_type = _target_type_for_tool(step.tool_name)
        step.chapter_index = _optional_int(output.get("chapter_index"))
        step.target_id = self._find_target_id(step)
        step.finished_at = _now()
        self.db.commit()
        self.db.refresh(step)

    def _fail_step_and_run(
        self,
        run: WritingAgentRun,
        step: WritingAgentStep,
        error: str,
        *,
        output: dict[str, Any] | None = None,
    ) -> None:
        now = _now()
        step.status = STEP_FAILED
        step.error = error
        step.output = output
        step.finished_at = now
        self.db.flush()
        run.status = RUN_FAILED
        run.error = error
        run.output = self._run_output(run.id)
        run.finished_at = now
        run.updated_at = now
        self.db.commit()
        self.db.refresh(run)
        self.db.refresh(step)

    def _block_step_and_run(
        self,
        run: WritingAgentRun,
        step: WritingAgentStep,
        error: str,
        *,
        output: dict[str, Any] | None = None,
    ) -> None:
        now = _now()
        step.status = STEP_BLOCKED
        step.error = error
        step.output = output
        step.target_type = _target_type_for_tool(step.tool_name)
        step.chapter_index = _optional_int((output or {}).get("chapter_index"))
        step.finished_at = now
        self.db.flush()
        run.status = RUN_BLOCKED
        run.error = error
        run.output = self._run_output(run.id)
        run.finished_at = now
        run.updated_at = now
        self.db.commit()
        self.db.refresh(run)
        self.db.refresh(step)

    def _enrich_step_output(
        self,
        project_id: str,
        *,
        tool: WritingAgentToolRequest,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        output = dict(result)
        if tool.tool_name != CHAPTER_TOOL_NAME:
            return output

        trace_id = str(output.get("trace_id") or "") or None
        output["chapter_length_decision"] = _chapter_length_decision(self.db, project_id=project_id, trace_id=trace_id)
        output["world_model_proposal_diagnostic"] = _world_model_proposal_diagnostic(
            self.db,
            project_id=project_id,
        )
        return output

    def _preflight_writing(self, project_id: str, params: dict[str, Any]) -> dict[str, Any]:
        chapter_index = int(params.get("chapter_index") or 1)
        checks: dict[str, dict[str, Any]] = {}
        issues: list[dict[str, Any]] = []

        setup = (
            self.db.query(Setup.id)
            .filter(Setup.project_id == project_id)
            .order_by(Setup.created_at.desc(), Setup.id.desc())
            .first()
        )
        checks["setup"] = {"status": "ready", "id": setup.id} if setup else {"status": "missing"}
        if setup is None:
            issues.append(_issue("missing_setup", "blocker", "项目缺少已生成设定。"))

        outline_chapter = find_outline_chapter(self.db, project_id, chapter_index)
        checks["outline_chapter"] = (
            {"status": "ready", "chapter_index": chapter_index}
            if outline_chapter is not None
            else {"status": "missing", "chapter_index": chapter_index}
        )
        if outline_chapter is None:
            issues.append(_issue("missing_outline_chapter", "blocker", f"第{chapter_index}章缺少章节大纲。"))

        profile = (
            self.db.query(ProjectProfileVersion)
            .filter(ProjectProfileVersion.project_id == project_id)
            .order_by(ProjectProfileVersion.version.desc(), ProjectProfileVersion.created_at.desc())
            .first()
        )
        checks["world_model_profile"] = (
            {"status": "ready", "profile_version": profile.version, "project_profile_version_id": profile.id}
            if profile
            else {"status": "missing", "profile_version": None}
        )
        if profile is None:
            issues.append(_issue("missing_world_model_profile", "warning", "项目尚未导入Athena世界模型profile。"))

        if chapter_index <= 1:
            checks["previous_chapter"] = {"status": "not_required"}
        else:
            previous = (
                self.db.query(ChapterContent.id)
                .filter(
                    ChapterContent.project_id == project_id,
                    ChapterContent.chapter_index == chapter_index - 1,
                )
                .first()
            )
            checks["previous_chapter"] = (
                {"status": "ready", "chapter_index": chapter_index - 1, "id": previous.id}
                if previous
                else {"status": "missing", "chapter_index": chapter_index - 1}
            )
            if previous is None:
                issues.append(_issue("missing_previous_chapter", "blocker", f"第{chapter_index - 1}章尚未生成。"))

        checks["longform_maintenance"] = _longform_maintenance_check(self.db, project_id)
        checks["retrieval"] = _retrieval_check(self.db, project_id)

        blocker_count = sum(1 for issue in issues if issue["severity"] == "blocker")
        return {
            "status": "blocked" if blocker_count else "ready",
            "chapter_index": chapter_index,
            "checks": checks,
            "issues": issues,
        }

    def _find_target_id(self, step: WritingAgentStep) -> str | None:
        if step.tool_name == "generate_setup":
            row = (
                self.db.query(Setup.id)
                .filter(Setup.project_id == step.project_id)
                .order_by(Setup.created_at.desc(), Setup.id.desc())
                .first()
            )
            return row.id if row else None
        if step.tool_name == "generate_storyline":
            row = (
                self.db.query(Storyline.id)
                .filter(Storyline.project_id == step.project_id)
                .order_by(Storyline.created_at.desc(), Storyline.id.desc())
                .first()
            )
            return row.id if row else None
        if step.tool_name == "generate_outline":
            row = (
                self.db.query(Outline.id)
                .filter(Outline.project_id == step.project_id)
                .order_by(Outline.created_at.desc(), Outline.id.desc())
                .first()
            )
            return row.id if row else None
        if step.tool_name == CHAPTER_TOOL_NAME and step.chapter_index is not None:
            row = (
                self.db.query(ChapterContent.id)
                .filter(
                    ChapterContent.project_id == step.project_id,
                    ChapterContent.chapter_index == step.chapter_index,
                )
                .order_by(ChapterContent.updated_at.desc(), ChapterContent.id.desc())
                .first()
            )
            return row.id if row else None
        return None

    def _run_output(self, run_id: str) -> dict[str, Any]:
        rows = self.db.query(WritingAgentStep.status).filter(WritingAgentStep.run_id == run_id).all()
        statuses = [row.status for row in rows]
        return {
            "step_count": len(statuses),
            "successful_step_count": sum(1 for status in statuses if status == STEP_SUCCESS),
            "failed_step_count": sum(1 for status in statuses if status == STEP_FAILED),
            "blocked_step_count": sum(1 for status in statuses if status == STEP_BLOCKED),
        }


def detail_payload(detail: dict[str, Any]) -> dict[str, Any]:
    run = detail["run"]
    steps = detail["steps"]
    return {
        **_model_dict(run),
        "steps": steps,
    }


def _model_dict(model: Any) -> dict[str, Any]:
    return {column.name: getattr(model, column.name) for column in model.__table__.columns}


def _target_type_for_tool(tool_name: str) -> str | None:
    return {
        "generate_setup": "setup",
        "generate_storyline": "storyline",
        "generate_outline": "outline",
        "generate_chapter": "chapter",
        "preflight_writing": "preflight",
        "import_setup_world_model": "world_model",
        "analyze_chapter_world_model": "world_model",
        "expand_outline_window": "outline",
    }.get(tool_name)


def _optional_existing_trace_id(db: Session, project_id: str, trace_id: object) -> str | None:
    if not trace_id:
        return None
    value = str(trace_id)
    exists = (
        db.query(AIModelCallTrace.id)
        .filter(AIModelCallTrace.project_id == project_id, AIModelCallTrace.id == value)
        .first()
    )
    return value if exists else None


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _chapter_length_decision(db: Session, *, project_id: str, trace_id: str | None) -> dict[str, Any]:
    metadata = {}
    if trace_id:
        row = (
            db.query(AIModelCallTrace.trace_metadata)
            .filter(AIModelCallTrace.project_id == project_id, AIModelCallTrace.id == trace_id)
            .first()
        )
        metadata = row[0] if row and isinstance(row[0], dict) else {}
    word_target = metadata.get("chapter_word_target") if isinstance(metadata.get("chapter_word_target"), dict) else {}
    status = str(word_target.get("status") or "unknown")
    decision = "accept" if status == "within" else "accept_with_warning" if status in {"under", "over"} else "requires_revision"
    return {
        "status": status,
        "decision": decision,
        "actual_word_count": word_target.get("actual_word_count"),
        "target_min_word_count": word_target.get("target_min_word_count"),
        "target_average_word_count": word_target.get("target_average_word_count"),
        "target_max_word_count": word_target.get("target_max_word_count"),
    }


def _world_model_proposal_diagnostic(db: Session, *, project_id: str) -> dict[str, Any]:
    try:
        profile = (
            db.query(ProjectProfileVersion)
            .filter(ProjectProfileVersion.project_id == project_id)
            .order_by(ProjectProfileVersion.version.desc(), ProjectProfileVersion.created_at.desc())
            .first()
        )
        queue = build_proposal_review_queue(db=db, project_id=project_id, profile=profile, limit=1)
        profile_version = queue.get("profile_version")
        total_items = int(queue.get("total_items") or 0)
        if profile_version is None:
            status = "missing"
            reason = "missing_profile"
        elif total_items > 0:
            status = "ready"
            reason = "available"
        else:
            status = "empty"
            reason = "empty_queue"
        return {
            "status": status,
            "profile_version": profile_version,
            "total_items": total_items,
            "reason": reason,
        }
    except Exception as exc:
        return {
            "status": "unknown",
            "profile_version": None,
            "total_items": 0,
            "reason": "diagnostic_failed",
            "error": str(exc),
        }


def _longform_maintenance_check(db: Session, project_id: str) -> dict[str, Any]:
    try:
        from app.core.longform_memory import get_longform_maintenance_diagnostics

        diagnostics = get_longform_maintenance_diagnostics(db, project_id, limit=20)
        return {
            "status": "ready" if diagnostics.get("ready_for_writing") else "warning",
            "ready_for_writing": bool(diagnostics.get("ready_for_writing")),
            "issue_count": int(diagnostics.get("issue_count") or 0),
        }
    except Exception as exc:
        return {"status": "unknown", "error": str(exc)}


def _retrieval_check(db: Session, project_id: str) -> dict[str, Any]:
    try:
        from app.core.athena_retrieval import get_retrieval_diagnostics

        diagnostics = get_retrieval_diagnostics(db, project_id)
        return {
            "status": "ready" if int(diagnostics.get("total_documents") or 0) > 0 else "unknown",
            "total_documents": int(diagnostics.get("total_documents") or 0),
            "total_chunks": int(diagnostics.get("total_chunks") or 0),
        }
    except Exception as exc:
        return {"status": "unknown", "error": str(exc)}


def _issue(code: str, severity: str, message: str) -> dict[str, Any]:
    return {"code": code, "severity": severity, "message": message}


def _block_message(output: dict[str, Any]) -> str:
    issues = output.get("issues")
    if isinstance(issues, list):
        for issue in issues:
            if isinstance(issue, dict) and issue.get("severity") == "blocker":
                return str(issue.get("message") or "Agent run blocked")
    return str(output.get("error") or "Agent run blocked")


def _now() -> datetime:
    return datetime.now(UTC)
