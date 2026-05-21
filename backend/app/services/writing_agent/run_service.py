from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.outline_lookup import (
    find_outline_chapter,
    generated_chapters_missing_outline,
)
from app.core.world_proposal_review_queue import build_proposal_review_queue
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
from app.services.writing_agent.chapter_generation_tool import (
    _length_drift_policy,
    _length_policy_check,
    _previous_chapter_state_card,
)
from app.services.writing_agent.tool_executor import (
    WritingAgentToolContext,
    execute_writing_agent_tool,
    writing_agent_tool_adapter_metadata,
)
from app.services.writing_agent.recovery_policy import build_writing_agent_recovery
from app.services.writing_agent.tool_registry import (
    allowed_tool_names,
    internal_tool_names,
    non_blocking_report_tool_names,
    target_type_for_tool,
)

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

AGENT_TOOL_RESULT_VERSION = "phase42.tool_result.v1"
ALLOWED_TOOLS = allowed_tool_names()
CHAPTER_TOOL_NAME = "generate_chapter"
INTERNAL_TOOLS = internal_tool_names()
NON_BLOCKING_REPORT_TOOLS = non_blocking_report_tool_names()


class WritingAgentRunService:
    def __init__(self, db: Session):
        self.db = db

    def create_run(
        self,
        project_id: str,
        payload: WritingAgentRunCreate,
        *,
        effective_tools: list[WritingAgentToolRequest] | None = None,
        planner_output: dict[str, Any] | None = None,
        dialog_id: str | None = None,
        request_message_id: str | None = None,
        response_message_id: str | None = None,
        background_task_id: str | None = None,
    ) -> WritingAgentRun:
        self._require_project(project_id)
        tools = effective_tools if effective_tools is not None else payload.tools
        run_input = {
            **(payload.input or {}),
            "tools": [tool.model_dump() for tool in tools],
        }
        if planner_output is not None:
            run_input["planner"] = planner_output
        run = WritingAgentRun(
            project_id=project_id,
            goal=payload.goal,
            status=RUN_PENDING,
            entrypoint=payload.entrypoint or "api",
            input=run_input,
            dialog_id=dialog_id,
            request_message_id=request_message_id,
            response_message_id=response_message_id,
            background_task_id=background_task_id,
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def build_auto_plan_tools(
        self,
        project_id: str,
        payload: WritingAgentRunCreate,
    ) -> tuple[list[WritingAgentToolRequest], dict[str, Any] | None]:
        run_input = payload.input or {}
        if payload.tools or run_input.get("auto_plan") is not True:
            return payload.tools, None
        from app.services.writing_agent.planner import build_writing_agent_run_plan, tools_from_plan

        recovery_run_id = str(run_input.get("recovery_run_id") or "").strip() or None
        if recovery_run_id:
            from app.services.writing_agent.recovery_planner import build_recovery_tool_plan

            if run_input.get("execute_recovery") is not True:
                return _recovery_preview_auto_plan(recovery_run_id)

            plan = build_recovery_tool_plan(self.db, project_id, recovery_run_id)
            expected_hash = str(run_input.get("recovery_plan_hash") or "").strip()
            confirmed = run_input.get("confirm_execute") is True
            actual_hash = str(plan.get("plan_hash") or "")
            if not confirmed or not expected_hash or expected_hash != actual_hash or plan.get("can_execute") is not True:
                status = "confirmation_required"
                if expected_hash and expected_hash != actual_hash:
                    status = "hash_mismatch"
                elif plan.get("can_execute") is not True:
                    status = str(((plan.get("execution_policy") or {}).get("status")) or "not_executable")
                return _recovery_preview_auto_plan(recovery_run_id, status=status)

            plan = dict(plan)
            plan["mode"] = "execute"
            plan["preview_only"] = False
            plan["execution_policy"] = {
                **(plan.get("execution_policy") or {}),
                "mode": "execute",
                "status": "confirmed",
                "confirmed": True,
                "requires_confirmation": True,
                "requires_plan_hash": True,
            }
            tools = [WritingAgentToolRequest(**tool) for tool in plan.get("tools", []) if isinstance(tool, dict)]
            return tools, plan

        chapter_index = _optional_int(run_input.get("chapter_index"))
        intent = str(run_input.get("intent") or "").strip() or None
        plan = build_writing_agent_run_plan(
            self.db,
            project_id,
            goal=payload.goal,
            chapter_index=chapter_index,
            intent=intent,
        )
        return tools_from_plan(plan), plan

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

        total_steps = len(tools)
        for step_index, tool in enumerate(tools, start=1):
            step = self._start_step(run, step_index, tool)
            if tool.tool_name not in ALLOWED_TOOLS:
                self._fail_step_and_run(run, step, f"Unsupported writing agent tool: {tool.tool_name}")
                return run

            result = await self._execute_tool(run.project_id, tool, run_id=run.id)
            if not isinstance(result, dict):
                result = {"status": "failed", "error": "Tool returned non-dict result"}
            if result.get("status") == RUN_BLOCKED and tool.tool_name not in NON_BLOCKING_REPORT_TOOLS:
                self._block_step_and_run(run, step, _block_message(result), output=result)
                return run
            if result.get("status") == "failed":
                self._fail_step_and_run(run, step, str(result.get("error") or "Tool execution failed"), output=result)
                return run

            output = self._enrich_step_output(run.project_id, tool=tool, result=result)
            self._complete_step(step, output)
            next_tool_name = tools[step_index].tool_name if step_index < total_steps else None
            if _should_stop_after_report(
                tool,
                output,
                step_index=step_index,
                total_steps=total_steps,
                next_tool_name=next_tool_name,
            ):
                self._block_run_after_successful_report(run, _successful_report_block_message(tool.tool_name))
                return run

        run.status = RUN_SUCCESS
        run.error = None
        run.finished_at = _now()
        run.updated_at = run.finished_at
        run.output = self._run_output(run.id)
        self.db.commit()
        self.db.refresh(run)
        return run

    async def _execute_tool(self, project_id: str, tool: WritingAgentToolRequest, *, run_id: str) -> dict[str, Any]:
        execution = await execute_writing_agent_tool(
            WritingAgentToolContext(db=self.db, project_id=project_id, run_id=run_id),
            tool,
            preflight_writing=self._preflight_writing,
        )
        if execution.handled:
            if execution.output is not None:
                return execution.output
            return {"status": "failed", "error": "Tool executor returned empty output"}

        if tool.tool_name not in INTERNAL_TOOLS:
            return await ActionExecutionService(self.db).execute(
                tool.tool_name,
                project_id,
                command_args=tool.command_args,
                action_params=tool.params,
            )
        if tool.tool_name == "import_setup_world_model":
            from app.core.athena_longform import import_setup_to_world_model

            return import_setup_to_world_model(db=self.db, project_id=project_id)
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
        if tool.tool_name == "seed_continuity_anchor_proposals":
            from app.core.continuity_anchor_proposals import seed_continuity_anchor_proposals

            return seed_continuity_anchor_proposals(self.db, project_id)
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
        step_input = {"command_args": tool.command_args, "params": tool.params}
        if tool.planner:
            step_input["planner"] = tool.planner
        step = WritingAgentStep(
            run_id=run.id,
            project_id=run.project_id,
            step_index=step_index,
            tool_name=tool.tool_name,
            status=STEP_RUNNING,
            input=step_input,
            started_at=_now(),
        )
        self.db.add(step)
        self.db.commit()
        self.db.refresh(step)
        return step

    def _complete_step(self, step: WritingAgentStep, output: dict[str, Any]) -> None:
        trace_id = _optional_existing_trace_id(self.db, step.project_id, output.get("trace_id"))
        finished_at = _now()
        output = dict(output)
        output["agent_tool_result"] = _agent_tool_result_envelope(step, output, STEP_SUCCESS, finished_at=finished_at)
        step.status = STEP_SUCCESS
        step.output = output
        step.error = None
        step.trace_id = trace_id
        step.target_type = _target_type_for_tool(step.tool_name)
        step.chapter_index = _optional_int(output.get("chapter_index"))
        step.target_id = self._find_target_id(step)
        step.finished_at = finished_at
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
        output = dict(output) if output is not None else {"status": STEP_FAILED, "error": error}
        output["agent_tool_result"] = _agent_tool_result_envelope(step, output, STEP_FAILED, finished_at=now)
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
        output = dict(output) if output is not None else {"status": STEP_BLOCKED, "error": error}
        output["agent_tool_result"] = _agent_tool_result_envelope(step, output, STEP_BLOCKED, finished_at=now)
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

    def _block_run_after_successful_report(self, run: WritingAgentRun, error: str) -> None:
        now = _now()
        run.status = RUN_BLOCKED
        run.error = error
        run.output = self._run_output(run.id)
        run.finished_at = now
        run.updated_at = now
        self.db.commit()
        self.db.refresh(run)

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

        historical_outline_gaps = generated_chapters_missing_outline(
            self.db,
            project_id,
            before_chapter=chapter_index,
        )
        checks["historical_outline_gaps"] = (
            {"status": "missing", "chapter_indexes": historical_outline_gaps}
            if historical_outline_gaps
            else {"status": "ready", "chapter_indexes": []}
        )
        if historical_outline_gaps:
            issues.append(
                _issue(
                    "missing_historical_outline_chapters",
                    "blocker",
                    f"已生成章节中第{_chapter_index_list_label(historical_outline_gaps)}章缺少章节大纲，请先回填大纲。",
                    extra={
                        "chapter_indexes": historical_outline_gaps,
                        "suggested_tool": "backfill_outline_gaps",
                        "suggested_params": {"before_chapter": chapter_index},
                    },
                )
            )

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
        checks["previous_chapter_state_card"] = _previous_chapter_state_card(self.db, project_id, chapter_index)

        checks["longform_maintenance"] = _longform_maintenance_check(self.db, project_id)
        checks["length_policy"] = _length_policy_check(self.db, project_id)
        length_policy_status = checks["length_policy"].get("status")
        if length_policy_status == "blocked":
            issues.append(
                _issue(
                    "repeated_chapter_length_drift",
                    "blocker",
                    str(checks["length_policy"].get("message") or "章节字数连续偏离目标，请先复核策略。"),
                    extra={
                        "reason": checks["length_policy"].get("reason"),
                        "recommended_actions": checks["length_policy"].get("recommended_actions", []),
                    },
                )
            )
        elif length_policy_status == "review_required":
            issues.append(
                _issue(
                    "repeated_chapter_length_drift",
                    "warning",
                    str(checks["length_policy"].get("message") or "章节字数连续偏离目标，后续生成需复核策略。"),
                    extra={
                        "reason": checks["length_policy"].get("reason"),
                        "recommended_actions": checks["length_policy"].get("recommended_actions", []),
                    },
                )
            )
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
        if step.tool_name == "create_revision_draft":
            output = step.output if isinstance(step.output, dict) else {}
            revision_id = output.get("revision_id")
            return str(revision_id) if revision_id else None
        return None

    def _run_output(self, run_id: str) -> dict[str, Any]:
        run = self.db.query(WritingAgentRun).filter(WritingAgentRun.id == run_id).first()
        steps = (
            self.db.query(WritingAgentStep)
            .filter(WritingAgentStep.run_id == run_id)
            .order_by(WritingAgentStep.step_index.asc(), WritingAgentStep.id.asc())
            .all()
        )
        statuses = [step.status for step in steps]
        return {
            "step_count": len(statuses),
            "successful_step_count": sum(1 for status in statuses if status == STEP_SUCCESS),
            "failed_step_count": sum(1 for status in statuses if status == STEP_FAILED),
            "blocked_step_count": sum(1 for status in statuses if status == STEP_BLOCKED),
            "continuation_state": _continuation_state(run, steps) if run is not None else None,
        }


def detail_payload(detail: dict[str, Any]) -> dict[str, Any]:
    run = detail["run"]
    steps = detail["steps"]
    return {
        **_model_dict(run),
        "steps": steps,
    }


def _continuation_state(run: WritingAgentRun, steps: list[WritingAgentStep]) -> dict[str, Any]:
    recovery = _latest_recommended_recovery_from_steps(steps)
    blocked_step = _blocked_or_failed_step(run, steps)
    last_successful_step = _last_step_with_status(steps, STEP_SUCCESS)
    next_planned_tool = _next_planned_tool(run, steps)
    next_expected_tool = recovery.get("next_tool") if recovery.get("status") == "recommended" else next_planned_tool
    status = _continuation_status(run.status)
    return {
        "version": "phase56.continuation_state.v1",
        "status": status,
        "active_task": {
            "goal": run.goal,
            "entrypoint": run.entrypoint,
            "auto_plan": bool((run.input or {}).get("auto_plan") is True) if isinstance(run.input, dict) else False,
            "planner_mode": _planner_mode(run),
        },
        "target_chapter_index": _continuation_target_chapter(run, steps),
        "progress": {
            "planned_step_count": _planned_step_count(run),
            "executed_step_count": len(steps),
            "successful_step_count": sum(1 for step in steps if step.status == STEP_SUCCESS),
            "failed_step_count": sum(1 for step in steps if step.status == STEP_FAILED),
            "blocked_step_count": sum(1 for step in steps if step.status == STEP_BLOCKED),
        },
        "last_successful_tool": _step_marker(last_successful_step),
        "blocked_tool": _step_marker(blocked_step),
        "next_expected_tool": next_expected_tool,
        "recovery": recovery,
        "failure": _failure_state(run, blocked_step),
        "consumed": _consumed_state(steps),
        "resume_hint": _resume_hint(status, next_expected_tool, recovery),
    }


def _continuation_status(status: str) -> str:
    if status == RUN_SUCCESS:
        return "completed"
    return status


def _planner_mode(run: WritingAgentRun) -> str | None:
    run_input = run.input if isinstance(run.input, dict) else {}
    planner = run_input.get("planner") if isinstance(run_input.get("planner"), dict) else {}
    mode = str(planner.get("mode") or "").strip()
    return mode or None


def _planned_step_count(run: WritingAgentRun) -> int:
    run_input = run.input if isinstance(run.input, dict) else {}
    tools = run_input.get("tools") if isinstance(run_input.get("tools"), list) else []
    return len(tools)


def _next_planned_tool(run: WritingAgentRun, steps: list[WritingAgentStep]) -> str | None:
    run_input = run.input if isinstance(run.input, dict) else {}
    tools = run_input.get("tools") if isinstance(run_input.get("tools"), list) else []
    if len(steps) >= len(tools):
        return None
    candidate = tools[len(steps)]
    if not isinstance(candidate, dict):
        return None
    value = str(candidate.get("tool_name") or "").strip()
    return value or None


def _continuation_target_chapter(run: WritingAgentRun, steps: list[WritingAgentStep]) -> int | None:
    for step in reversed(steps):
        chapter_index = _optional_int(step.chapter_index)
        if chapter_index:
            return chapter_index
        output = step.output if isinstance(step.output, dict) else {}
        chapter_index = _optional_int(output.get("chapter_index"))
        if chapter_index:
            return chapter_index
        step_input = step.input if isinstance(step.input, dict) else {}
        params = step_input.get("params") if isinstance(step_input.get("params"), dict) else {}
        chapter_index = _optional_int(params.get("chapter_index") or params.get("start_chapter") or params.get("before_chapter"))
        if chapter_index:
            return chapter_index
    run_input = run.input if isinstance(run.input, dict) else {}
    chapter_index = _optional_int(run_input.get("chapter_index"))
    if chapter_index:
        return chapter_index
    planner = run_input.get("planner") if isinstance(run_input.get("planner"), dict) else {}
    return _optional_int(planner.get("chapter_index"))


def _last_step_with_status(steps: list[WritingAgentStep], status: str) -> WritingAgentStep | None:
    for step in reversed(steps):
        if step.status == status:
            return step
    return None


def _blocked_or_failed_step(run: WritingAgentRun, steps: list[WritingAgentStep]) -> WritingAgentStep | None:
    for step in reversed(steps):
        if step.status in {STEP_BLOCKED, STEP_FAILED}:
            return step
    if run.status == RUN_BLOCKED and steps:
        latest = steps[-1]
        output = latest.output if isinstance(latest.output, dict) else {}
        if output.get("should_generate_next_chapter") is False:
            return latest
    return None


def _step_marker(step: WritingAgentStep | None) -> dict[str, Any] | None:
    if step is None:
        return None
    return {
        "step_index": step.step_index,
        "tool_name": step.tool_name,
        "status": step.status,
        "chapter_index": step.chapter_index,
        "target_type": step.target_type,
        "target_id": step.target_id,
    }


def _latest_recommended_recovery_from_steps(steps: list[WritingAgentStep]) -> dict[str, Any]:
    for step in reversed(steps):
        output = step.output if isinstance(step.output, dict) else {}
        envelope = output.get("agent_tool_result") if isinstance(output.get("agent_tool_result"), dict) else {}
        recovery = envelope.get("recovery") if isinstance(envelope.get("recovery"), dict) else {}
        if recovery.get("status") == "recommended":
            return {
                "status": "recommended",
                "source_step_index": step.step_index,
                "source_tool": recovery.get("source_tool") or step.tool_name,
                "reason_code": recovery.get("reason_code"),
                "next_tool": recovery.get("next_tool"),
                "affected_chapter_indexes": recovery.get("affected_chapter_indexes", []),
            }
    return {"status": "none"}


def _failure_state(run: WritingAgentRun, blocked_step: WritingAgentStep | None) -> dict[str, Any] | None:
    if run.status not in {RUN_BLOCKED, RUN_FAILED}:
        return None
    output = blocked_step.output if blocked_step is not None and isinstance(blocked_step.output, dict) else {}
    decision = output.get("decision") if isinstance(output.get("decision"), dict) else {}
    return {
        "status": run.status,
        "tool_name": blocked_step.tool_name if blocked_step is not None else None,
        "reason_code": decision.get("reason") or output.get("reason") or output.get("error"),
        "message": run.error or decision.get("message") or output.get("error"),
    }


def _consumed_state(steps: list[WritingAgentStep]) -> dict[str, bool]:
    successful_tools = {step.tool_name for step in steps if step.status == STEP_SUCCESS}
    return {
        "longform_maintenance": "repair_longform_maintenance" in successful_tools,
        "longform_context": "summarize_longform_context" in successful_tools,
        "preflight": "preflight_writing" in successful_tools,
        "generated_chapter": CHAPTER_TOOL_NAME in successful_tools,
        "quality_review": "review_chapter_quality" in successful_tools,
        "continuity_review": "review_chapter_continuity" in successful_tools,
        "review_findings": bool({"review_chapter_quality", "review_chapter_continuity"} & successful_tools),
        "world_model_proposals": "analyze_chapter_world_model" in successful_tools,
    }


def _resume_hint(status: str, next_expected_tool: str | None, recovery: dict[str, Any]) -> str:
    if status == "completed":
        return "当前 Agent run 已完成，无需恢复。"
    if recovery.get("status") == "recommended" and next_expected_tool:
        return f"建议通过恢复预览确认后执行 {next_expected_tool}。"
    if next_expected_tool:
        return f"下一步应继续执行 {next_expected_tool}。"
    return "没有可自动推断的下一步工具。"


def _recovery_preview_auto_plan(
    recovery_run_id: str,
    *,
    status: str = "preview_required",
) -> tuple[list[WritingAgentToolRequest], dict[str, Any]]:
    preview_tool = WritingAgentToolRequest(
        tool_name="plan_recovery_tools",
        params={"run_id": recovery_run_id},
        planner={
            "mode": "preview",
            "reason": "预览上一轮阻塞的恢复工具链，不直接执行写操作。",
            "on_missing": "stop",
            "on_failure": "stop",
            "expected_output": "恢复工具链预览。",
            "post_generation": False,
            "planner_version": "phase50.recovery_preview_gate.v1",
        },
    )
    planner_output = {
        "status": "preview_required",
        "mode": "preview",
        "source_run_id": recovery_run_id,
        "preview_only": True,
        "tools": [preview_tool.model_dump()],
        "trace": {"selected_tools": ["plan_recovery_tools"], "rejected_tools": []},
        "execution_policy": {
            "status": status,
            "mode": "preview",
            "requires_confirmation": True,
            "requires_plan_hash": True,
        },
    }
    return [preview_tool], planner_output


def _model_dict(model: Any) -> dict[str, Any]:
    return {column.name: getattr(model, column.name) for column in model.__table__.columns}


def _target_type_for_tool(tool_name: str) -> str | None:
    return target_type_for_tool(tool_name)


def _agent_tool_result_envelope(
    step: WritingAgentStep,
    output: dict[str, Any],
    step_status: str,
    *,
    finished_at: datetime,
) -> dict[str, Any]:
    planner = {}
    if isinstance(step.input, dict) and isinstance(step.input.get("planner"), dict):
        planner = step.input["planner"]
    result_status = str(output.get("status") or step_status)
    output_keys = sorted(str(key) for key in output if key != "agent_tool_result")
    return {
        "version": AGENT_TOOL_RESULT_VERSION,
        "tool_name": step.tool_name,
        "step_index": step.step_index,
        "step_status": step_status,
        "result_status": result_status,
        "is_error": step_status in {STEP_FAILED, STEP_BLOCKED} or result_status in {"failed", "blocked"},
        "trace_id": str(output.get("trace_id") or "") or None,
        "planner": planner,
        "adapter": writing_agent_tool_adapter_metadata(step.tool_name),
        "elapsed_ms": _elapsed_ms(step.started_at, finished_at),
        "output_size_bytes": _output_size_bytes(output),
        "recovery": build_writing_agent_recovery(
            tool_name=step.tool_name,
            step_status=step_status,
            output=output,
            planner=planner,
        ),
        "output_keys": output_keys,
    }


def _elapsed_ms(started_at: datetime | None, finished_at: datetime) -> int:
    if started_at is None:
        return 0
    try:
        delta = finished_at - started_at
    except TypeError:
        normalized_started = started_at if started_at.tzinfo else started_at.replace(tzinfo=UTC)
        normalized_finished = finished_at if finished_at.tzinfo else finished_at.replace(tzinfo=UTC)
        delta = normalized_finished - normalized_started
    return max(0, round(delta.total_seconds() * 1000))


def _output_size_bytes(output: dict[str, Any]) -> int:
    try:
        serialized = json.dumps(output, ensure_ascii=False, default=str, sort_keys=True)
    except (TypeError, ValueError):
        serialized = str(output)
    return len(serialized.encode("utf-8"))


def _should_stop_after_report(
    tool: WritingAgentToolRequest,
    output: dict[str, Any],
    *,
    step_index: int,
    total_steps: int,
    next_tool_name: str | None = None,
) -> bool:
    if tool.tool_name not in {
        "plan_chapter_revision",
        "create_revision_draft",
        "apply_planner_revision_patch",
        "expand_chapter_to_target",
        "compress_chapter_to_target",
        "summarize_longform_context",
        "review_world_model_proposals",
        "plan_world_model_proposal_resolution",
        "preview_world_model_proposal_resolution",
        "apply_world_model_proposal_resolution",
        "draft_world_model_proposal_resolution_decisions",
        "draft_high_value_world_proposal_resolution_decisions",
        "seed_continuity_anchor_proposals",
    }:
        return False
    if step_index >= total_steps:
        return False
    if _allowed_report_followup(tool.tool_name, next_tool_name):
        return False
    return output.get("should_generate_next_chapter") is False


def _allowed_report_followup(tool_name: str, next_tool_name: str | None) -> bool:
    return (tool_name, next_tool_name) in {
        ("create_revision_draft", "apply_planner_revision_patch"),
        ("apply_planner_revision_patch", "review_chapter_quality"),
        ("expand_chapter_to_target", "review_chapter_quality"),
        ("compress_chapter_to_target", "review_chapter_quality"),
        ("review_world_model_proposals", "plan_world_model_proposal_resolution"),
        ("plan_world_model_proposal_resolution", "preview_world_model_proposal_resolution"),
        ("preview_world_model_proposal_resolution", "apply_world_model_proposal_resolution"),
        ("draft_world_model_proposal_resolution_decisions", "apply_world_model_proposal_resolution"),
        ("draft_high_value_world_proposal_resolution_decisions", "apply_world_model_proposal_resolution"),
        ("seed_continuity_anchor_proposals", "apply_world_model_proposal_resolution"),
    }


def _successful_report_block_message(tool_name: str) -> str:
    return {
        "summarize_longform_context": "长篇上下文维护未就绪，已停止后续写作工具。",
        "review_world_model_proposals": "世界模型提案队列仍有待审项，已停止后续写作工具。",
        "plan_world_model_proposal_resolution": "世界模型提案尚未解决，已停止后续写作工具。",
        "preview_world_model_proposal_resolution": "世界模型提案解决决策尚未执行，已停止后续写作工具。",
        "apply_world_model_proposal_resolution": "世界模型提案队列仍未清空，已停止后续写作工具。",
        "draft_world_model_proposal_resolution_decisions": "世界模型提案决策草案尚未确认应用，已停止后续写作工具。",
        "draft_high_value_world_proposal_resolution_decisions": "高价值世界模型提案决策草案尚未确认应用，已停止后续写作工具。",
        "seed_continuity_anchor_proposals": "稳定连续性锚点提案尚未审批，已停止后续写作工具。",
        "plan_chapter_revision": "修订计划未通过，已停止后续写作工具。",
        "create_revision_draft": "修订草稿未通过，已停止后续写作工具。",
        "apply_planner_revision_patch": "修订补丁应用后尚未复审，已停止后续写作工具。",
        "expand_chapter_to_target": "章节扩写后尚未复审，已停止后续写作工具。",
        "compress_chapter_to_target": "章节压缩后尚未复审，已停止后续写作工具。",
    }.get(tool_name, "报告未通过，已停止后续写作工具。")


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
    policy = _length_drift_policy(db, project_id, status=status)
    if status == "within":
        decision = "accept"
        severity = "info"
    elif status in {"under", "over"} and policy["status"] == "blocked":
        decision = "requires_policy_review"
        severity = "warning"
    elif status in {"under", "over"}:
        decision = "accept_with_warning"
        severity = "warning"
    else:
        decision = "requires_revision"
        severity = "warning"
    return {
        "status": status,
        "decision": decision,
        "severity": severity,
        "actual_word_count": word_target.get("actual_word_count"),
        "target_min_word_count": word_target.get("target_min_word_count"),
        "target_average_word_count": word_target.get("target_average_word_count"),
        "target_max_word_count": word_target.get("target_max_word_count"),
        "repeated_drift_count": policy["repeated_drift_count"],
        "policy_reason": policy["reason"],
        "recommended_actions": policy["recommended_actions"],
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


def _issue(code: str, severity: str, message: str, *, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"code": code, "severity": severity, "message": message, **(extra or {})}


def _chapter_index_list_label(chapter_indexes: list[int]) -> str:
    if not chapter_indexes:
        return ""
    if len(chapter_indexes) == 1:
        return str(chapter_indexes[0])
    return "、".join(str(index) for index in chapter_indexes)


def _block_message(output: dict[str, Any]) -> str:
    issues = output.get("issues")
    if isinstance(issues, list):
        for issue in issues:
            if isinstance(issue, dict) and issue.get("severity") == "blocker":
                return str(issue.get("message") or "Agent run blocked")
    return str(output.get("error") or "Agent run blocked")


def _now() -> datetime:
    return datetime.now(UTC)
