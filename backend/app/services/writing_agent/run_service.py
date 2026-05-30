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
from app.services.writing_agent.approval_contract import verify_agent_plan_approval_contract
from app.services.writing_agent.approval_tool_metadata import build_approval_tool_metadata_by_name
from app.services.writing_agent.agent_step_binding import summarize_resource_binding
from app.services.writing_agent.agent_loop_risk import build_agent_loop_risk
from app.services.writing_agent.agent_stop_hooks import evaluate_agent_stop_hooks
from app.services.writing_agent.memory_activation import build_memory_activation_plan
from app.services.writing_agent.tool_adapter_types import WritingAgentToolContext
from app.services.writing_agent.tool_executor import (
    execute_writing_agent_tool,
    writing_agent_tool_adapter_metadata,
    writing_agent_tool_adapter_metadata_by_name,
)
from app.services.writing_agent.tool_policy import should_stop_after_report, successful_report_block_message
from app.services.writing_agent.tool_recommendations import normalize_tool_recommendations
from app.services.writing_agent.tool_contracts import agent_tool_execution_metadata
from app.services.writing_agent.tool_request_validation import validate_writing_agent_tool_request
from app.services.writing_agent.command_contract_projection import command_contracts_from_run_input
from app.services.writing_agent.control_plane_readiness_projection import control_plane_readiness_from_run_input
from app.services.writing_agent.recommended_followup_planner import (
    FOLLOWUP_PLANNER_VERSION,
    build_recommended_followup_tool_plan,
    latest_recommended_followup_state,
)
from app.services.writing_agent.recovery_policy import build_writing_agent_recovery
from app.services.writing_agent.agent_tool_surface_policy import build_agent_profile_definition
from app.services.writing_agent.tool_registry import (
    allowed_tool_names,
    get_agent_tool_descriptor,
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
TOOL_LIFECYCLE_HOOKS_OUTPUT_KEY = "_tool_lifecycle_hooks"
ALLOWED_TOOLS = allowed_tool_names()
CHAPTER_TOOL_NAME = "generate_chapter"
APPROVED_CHAPTER_TOOL_NAME = "execute_generate_chapter_with_approval"
CHAPTER_GENERATION_TOOL_NAMES = {CHAPTER_TOOL_NAME, APPROVED_CHAPTER_TOOL_NAME}
INTERNAL_TOOLS = internal_tool_names()
NON_BLOCKING_REPORT_TOOLS = non_blocking_report_tool_names()
AGENT_TOOL_DISCOVERY_PROJECTION_VERSION = "phase210.agent_tool_discovery_projection.v1"
AGENT_LOOP_CONTRACT_VERSION = "phase219.agent_loop_contract.v1"


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
            tools = [
                WritingAgentToolRequest(**tool)
                for tool in _tools_with_execution_confirmation(plan.get("tools", []))
            ]
            return tools, plan

        recommended_followup_run_id = str(run_input.get("recommended_followup_run_id") or "").strip() or None
        if recommended_followup_run_id:
            if run_input.get("execute_recommended_followups") is not True:
                return _recommended_followup_preview_auto_plan(recommended_followup_run_id)

            plan = build_recommended_followup_tool_plan(self.db, project_id, recommended_followup_run_id)
            expected_hash = str(run_input.get("recommended_followup_plan_hash") or "").strip()
            confirmed = run_input.get("confirm_execute") is True
            actual_hash = str(plan.get("plan_hash") or "")
            executable = bool(plan.get("tools")) and plan.get("status") == "completed"
            if not confirmed or not expected_hash or expected_hash != actual_hash or not executable:
                status = "confirmation_required"
                if expected_hash and expected_hash != actual_hash:
                    status = "hash_mismatch"
                elif not executable:
                    status = str(
                        ((plan.get("execution_policy") or {}).get("status"))
                        or plan.get("status")
                        or "not_executable"
                    )
                return _recommended_followup_preview_auto_plan(recommended_followup_run_id, status=status)

            plan = dict(plan)
            plan["mode"] = "execute"
            plan["preview_only"] = False
            plan["can_execute"] = True
            plan["execution_policy"] = {
                **(plan.get("execution_policy") or {}),
                "mode": "execute",
                "status": "confirmed",
                "confirmed": True,
                "requires_confirmation": True,
                "requires_plan_hash": True,
            }
            tools = [
                WritingAgentToolRequest(**tool)
                for tool in _tools_with_execution_confirmation(plan.get("tools", []))
            ]
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

            planner_continuation_gate = _planner_continuation_approval_gate(run, tool)
            if planner_continuation_gate and planner_continuation_gate.get("status") == RUN_BLOCKED:
                self._block_step_and_run(
                    run,
                    step,
                    "Planner continuation requires approval",
                    output=planner_continuation_gate["output"],
                )
                return run

            validation = validate_writing_agent_tool_request(tool.tool_name, tool.params)
            if validation.get("status") == "failed":
                self._fail_step_and_run(
                    run,
                    step,
                    "Tool input validation failed",
                    output={
                        "status": "failed",
                        "error": "Tool input validation failed",
                        "validation": validation,
                    },
                )
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
            if planner_continuation_gate and planner_continuation_gate.get("status") == "ready":
                output["planner_continuation_approval"] = planner_continuation_gate["approval"]
            self._complete_step(step, output)
            next_tool_name = tools[step_index].tool_name if step_index < total_steps else None
            if should_stop_after_report(
                tool.tool_name,
                output,
                step_index=step_index,
                total_steps=total_steps,
                next_tool_name=next_tool_name,
            ):
                self._block_run_after_successful_report(run, successful_report_block_message(tool.tool_name))
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
                return _attach_tool_lifecycle_hooks(execution.output, execution.lifecycle_hooks)
            return {"status": "failed", "error": "Tool executor returned empty output"}

        if tool.tool_name not in INTERNAL_TOOLS:
            return await ActionExecutionService(self.db).execute(
                tool.tool_name,
                project_id,
                command_args=tool.command_args,
                action_params=tool.params,
            )
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
        lifecycle_hooks = _extract_tool_lifecycle_hooks(output)
        output["agent_tool_result"] = _agent_tool_result_envelope(
            step,
            output,
            STEP_SUCCESS,
            finished_at=finished_at,
            tool_lifecycle_hooks=lifecycle_hooks,
        )
        step.status = STEP_SUCCESS
        step.output = output
        step.error = None
        step.trace_id = trace_id
        step.target_type = _target_type_for_tool(step.tool_name)
        step.chapter_index = _optional_int(output.get("chapter_index"))
        step.target_id = self._find_target_id(step)
        resource_binding = _extract_step_resource_binding(output)
        step.resource_binding = resource_binding
        step.tool_call_id = _resource_binding_tool_call_id(resource_binding)
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
        lifecycle_hooks = _extract_tool_lifecycle_hooks(output)
        output["agent_tool_result"] = _agent_tool_result_envelope(
            step,
            output,
            STEP_FAILED,
            finished_at=now,
            tool_lifecycle_hooks=lifecycle_hooks,
        )
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
        lifecycle_hooks = _extract_tool_lifecycle_hooks(output)
        output["agent_tool_result"] = _agent_tool_result_envelope(
            step,
            output,
            STEP_BLOCKED,
            finished_at=now,
            tool_lifecycle_hooks=lifecycle_hooks,
        )
        step.status = STEP_BLOCKED
        step.error = error
        step.output = output
        step.target_type = _target_type_for_tool(step.tool_name)
        step.chapter_index = _optional_int((output or {}).get("chapter_index"))
        resource_binding = _extract_step_resource_binding(output)
        step.resource_binding = resource_binding
        step.tool_call_id = _resource_binding_tool_call_id(resource_binding)
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
        if tool.tool_name not in CHAPTER_GENERATION_TOOL_NAMES:
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

        checks["memory_activation"] = _memory_activation_check(self.db, project_id, chapter_index)
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
        if step.tool_name in {"generate_setup", "execute_generate_setup_with_approval"}:
            row = (
                self.db.query(Setup.id)
                .filter(Setup.project_id == step.project_id)
                .order_by(Setup.created_at.desc(), Setup.id.desc())
                .first()
            )
            return row.id if row else None
        if step.tool_name in {"generate_storyline", "execute_generate_storyline_with_approval"}:
            row = (
                self.db.query(Storyline.id)
                .filter(Storyline.project_id == step.project_id)
                .order_by(Storyline.created_at.desc(), Storyline.id.desc())
                .first()
            )
            return row.id if row else None
        if step.tool_name in {"generate_outline", "execute_generate_outline_with_approval"}:
            row = (
                self.db.query(Outline.id)
                .filter(Outline.project_id == step.project_id)
                .order_by(Outline.created_at.desc(), Outline.id.desc())
                .first()
            )
            return row.id if row else None
        if step.tool_name in {"import_setup_world_model", "execute_import_setup_world_model_with_approval"}:
            row = (
                self.db.query(ProjectProfileVersion.id)
                .filter(ProjectProfileVersion.project_id == step.project_id)
                .order_by(ProjectProfileVersion.version.desc(), ProjectProfileVersion.created_at.desc())
                .first()
            )
            return row.id if row else None
        if step.tool_name in CHAPTER_GENERATION_TOOL_NAMES and step.chapter_index is not None:
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
        **_agent_profile_projection(run, steps),
        "agent_profile_policy_audit": _agent_profile_policy_audit_from_steps(steps),
        "agent_command_contracts": command_contracts_from_run_input(run.input),
        "agent_control_plane_readiness": control_plane_readiness_from_run_input(run.input),
        "steps": steps,
    }


def _agent_profile_projection(run: WritingAgentRun, steps: list[WritingAgentStep]) -> dict[str, Any]:
    scope = _agent_profile_scope_from_steps(steps)
    requested_profile, source = _agent_profile_from_run_input(run)
    if requested_profile is None:
        requested_profile, source = _agent_profile_from_step_input(steps)
    profile = requested_profile
    if isinstance(scope, dict):
        scoped_profile = _non_empty_string(scope.get("agent_profile"))
        if scoped_profile:
            profile = scoped_profile
    return {
        "agent_profile": profile,
        "agent_profile_scope": scope,
        "agent_tool_discovery": _agent_tool_discovery_projection(requested_profile, profile, scope),
        "agent_profile_definition": build_agent_profile_definition(profile, source=source),
    }


def _agent_tool_discovery_projection(
    requested_profile: str | None,
    effective_profile: str | None,
    scope: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not requested_profile and not scope:
        return None

    status = _non_empty_string(scope.get("status")) if isinstance(scope, dict) else None
    visible_tool_count = _optional_int(scope.get("allowed_visible_tool_count")) if isinstance(scope, dict) else None
    filtered_count = (
        _optional_int(scope.get("profile_filtered_visible_tool_count")) if isinstance(scope, dict) else None
    )
    hidden_tool_count = _optional_int(scope.get("allowed_hidden_tool_count")) if isinstance(scope, dict) else None
    candidate_visible_tool_count = (
        visible_tool_count + filtered_count
        if visible_tool_count is not None and filtered_count is not None
        else None
    )
    scope_source = "agent_profile" if requested_profile or effective_profile else "none"
    return {
        "version": AGENT_TOOL_DISCOVERY_PROJECTION_VERSION,
        "status": status or "not_available",
        "scope_applied": status == "applied",
        "scope_source": scope_source,
        "requested_profile": requested_profile,
        "effective_profile": effective_profile,
        "visible_tool_count": visible_tool_count,
        "filtered_by_profile_count": filtered_count,
        "hidden_tool_count": hidden_tool_count,
        "candidate_visible_tool_count": candidate_visible_tool_count,
        "filter_stages": ["profile"] if status == "applied" else [],
        "warnings": _agent_tool_discovery_warnings(status, requested_profile, scope),
    }


def _agent_tool_discovery_warnings(
    status: str | None,
    requested_profile: str | None,
    scope: dict[str, Any] | None,
) -> list[str]:
    if scope is None:
        return ["missing_describe_agent_tools_scope"] if requested_profile else []
    if status == "unknown_profile":
        return ["unknown_profile"]
    if status == "not_requested" and requested_profile:
        return ["profile_scope_not_requested"]
    return []


def _agent_profile_from_run_input(run: WritingAgentRun) -> tuple[str | None, str | None]:
    run_input = run.input if isinstance(run.input, dict) else {}
    planner = run_input.get("planner") if isinstance(run_input.get("planner"), dict) else {}
    trace = planner.get("trace") if isinstance(planner.get("trace"), dict) else {}
    profile = _non_empty_string(planner.get("agent_profile"))
    if profile:
        return profile, "planner"
    profile = _non_empty_string(trace.get("agent_profile"))
    if profile:
        return profile, "planner_trace"

    tools = run_input.get("tools") if isinstance(run_input.get("tools"), list) else []
    profile = _agent_profile_from_tool_rows(tools)
    if profile:
        return profile, "run_input_tools"
    return None, None


def _agent_profile_from_step_input(steps: list[WritingAgentStep]) -> tuple[str | None, str | None]:
    for step in steps:
        if step.tool_name != "describe_agent_tools":
            continue
        step_input = step.input if isinstance(step.input, dict) else {}
        params = step_input.get("params") if isinstance(step_input.get("params"), dict) else {}
        profile = _non_empty_string(params.get("agent_profile"))
        if profile:
            return profile, "describe_agent_tools_input"
    return None, None


def _agent_profile_from_tool_rows(tools: list[object]) -> str | None:
    for tool in tools:
        if not isinstance(tool, dict) or tool.get("tool_name") != "describe_agent_tools":
            continue
        params = tool.get("params") if isinstance(tool.get("params"), dict) else {}
        profile = _non_empty_string(params.get("agent_profile"))
        if profile:
            return profile
    return None


def _agent_profile_scope_from_steps(steps: list[WritingAgentStep]) -> dict[str, Any] | None:
    for step in steps:
        if step.tool_name != "describe_agent_tools":
            continue
        output = step.output if isinstance(step.output, dict) else {}
        scope = output.get("agent_profile_scope")
        if isinstance(scope, dict):
            return dict(scope)
    return None


def _agent_profile_policy_audit_from_steps(steps: list[WritingAgentStep]) -> dict[str, Any] | None:
    for step in reversed(steps):
        if step.tool_name != "describe_agent_tools":
            continue
        output = step.output if isinstance(step.output, dict) else {}
        projection = (
            output.get("agent_profile_tool_projection")
            if isinstance(output.get("agent_profile_tool_projection"), dict)
            else {}
        )
        audit = projection.get("consistency_audit")
        if isinstance(audit, dict):
            return dict(audit)
    return None


def _non_empty_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _planner_continuation_approval_gate(
    run: WritingAgentRun,
    tool: WritingAgentToolRequest,
) -> dict[str, Any] | None:
    run_input = run.input if isinstance(run.input, dict) else {}
    if run.entrypoint != "ui_planner_continuation_execute" and run_input.get("planner_continuation") is not True:
        return None

    planner = run_input.get("planner") if isinstance(run_input.get("planner"), dict) else {}
    approval_contract = (
        planner.get("approval_contract")
        if isinstance(planner.get("approval_contract"), dict)
        else {}
    )
    approval_status = _non_empty_string(approval_contract.get("status")) or "missing"
    planner_metadata = tool.planner if isinstance(tool.planner, dict) else {}
    execution_metadata = agent_tool_execution_metadata(
        get_agent_tool_descriptor(tool.tool_name),
        writing_agent_tool_adapter_metadata(tool.tool_name),
    )
    execution_mutability = _non_empty_string(execution_metadata.get("mutability")) or "unclassified"
    planner_mutability = _non_empty_string(planner_metadata.get("mutability"))
    requires_confirmation = (
        execution_metadata.get("requires_confirmation") is True
        or execution_mutability in {"write", "guarded_write"}
        or (
            execution_mutability == "unclassified"
            and (
                planner_metadata.get("requires_confirmation") is True
                or planner_mutability in {"write", "guarded_write"}
            )
        )
    )
    if not requires_confirmation:
        return None

    source_plan_id = _non_empty_string(run_input.get("source_plan_id")) or _non_empty_string(planner_metadata.get("plan_id"))
    block_output = {
        "status": RUN_BLOCKED,
        "reason": "planner_continuation_requires_approval",
        "message": "Planner continuation includes a write or confirmation-required tool.",
        "source_run_id": _non_empty_string(run_input.get("source_run_id")),
        "source_plan_id": source_plan_id,
        "blocked_tool": tool.tool_name,
        "approval_contract_status": approval_status,
        "tool_execution_metadata": {
            "mutability": execution_metadata.get("mutability"),
            "requires_confirmation": execution_metadata.get("requires_confirmation") is True,
        },
        "recommended_next_tools": [
            "preview_agent_plan_approval_contract",
            "verify_agent_plan_approval_contract",
        ],
    }
    if run_input.get("confirm_execute") is not True:
        return {"status": RUN_BLOCKED, "output": block_output}

    plan = _planner_continuation_plan(planner)
    approval_contract = _planner_continuation_approval_contract(run_input, planner, plan)
    verification = verify_agent_plan_approval_contract(
        plan,
        approval_contract_hash=_non_empty_string(run_input.get("approval_contract_hash")),
        approval_contract=approval_contract,
        project_id=run.project_id,
        tool_metadata_by_name=build_approval_tool_metadata_by_name(
            plan,
            adapter_metadata_by_name=writing_agent_tool_adapter_metadata_by_name(),
        ),
    )
    if verification.get("status") != "ready":
        block_output["approval_verification"] = verification
        return {"status": RUN_BLOCKED, "output": block_output}

    approval_hash = (verification.get("drift") or {}).get("actual_approval_contract_hash")
    return {
        "status": "ready",
        "approval": {
            "status": "ready",
            "reason": str(verification.get("reason") or "approval_contract_verified"),
            "approval_contract_hash": _non_empty_string(approval_hash),
            "source_plan_id": source_plan_id,
            "blocked_tool": None,
        },
    }


def _planner_continuation_plan(planner: dict[str, Any]) -> dict[str, Any] | None:
    nested_plan = planner.get("plan") if isinstance(planner.get("plan"), dict) else None
    if nested_plan and (
        isinstance(nested_plan.get("steps"), list)
        or isinstance(nested_plan.get("tools"), list)
        or isinstance(nested_plan.get("trace"), dict)
    ):
        return nested_plan
    return planner


def _planner_continuation_approval_contract(
    run_input: dict[str, Any],
    planner: dict[str, Any],
    plan: dict[str, Any] | None,
) -> dict[str, Any] | None:
    for source in (
        run_input.get("approval_contract"),
        planner.get("approval_contract"),
        plan.get("approval_contract") if isinstance(plan, dict) else None,
    ):
        if isinstance(source, dict):
            return source
    return None


def _continuation_state(run: WritingAgentRun, steps: list[WritingAgentStep]) -> dict[str, Any]:
    recovery = _latest_recommended_recovery_from_steps(steps)
    if recovery.get("status") == "recommended":
        recommended_followups = {
            "version": FOLLOWUP_PLANNER_VERSION,
            "status": "suppressed",
            "reason": "recovery_required",
            "recovery_next_tool": recovery.get("next_tool"),
        }
    else:
        recommended_followups = latest_recommended_followup_state(steps)
    blocked_step = _blocked_or_failed_step(run, steps)
    last_successful_step = _last_step_with_status(steps, STEP_SUCCESS)
    next_planned_tool = _next_planned_tool(run, steps)
    next_expected_tool = recovery.get("next_tool") if recovery.get("status") == "recommended" else next_planned_tool
    status = _continuation_status(run.status)
    agent_loop = _agent_loop_contract(
        run,
        steps,
        status=status,
        next_expected_tool=next_expected_tool,
        recovery=recovery,
    )
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
        "agent_loop": agent_loop,
        "memory_provenance": _latest_memory_provenance_from_steps(steps),
        "profile_policy_health": _profile_policy_health(steps),
        "recommended_followups": recommended_followups,
        "recovery": recovery,
        "failure": _failure_state(run, blocked_step),
        "consumed": _consumed_state(steps),
        "resume_hint": _resume_hint(status, next_expected_tool, recovery),
    }


def _agent_loop_contract(
    run: WritingAgentRun,
    steps: list[WritingAgentStep],
    *,
    status: str,
    next_expected_tool: str | None,
    recovery: dict[str, Any],
) -> dict[str, Any]:
    planned_step_count = _planned_step_count(run)
    used_iterations = len(steps)
    max_iterations = max(planned_step_count, used_iterations)
    exit_reason = _agent_loop_exit_reason(run.status)
    latest_output = _latest_step_output(steps)
    return {
        "version": AGENT_LOOP_CONTRACT_VERSION,
        "loop_kind": "sequential_tool_plan",
        "status": status,
        "budget": {
            "max_iterations": max_iterations,
            "used_iterations": used_iterations,
            "remaining_iterations": max(0, max_iterations - used_iterations),
        },
        "exit_reason": exit_reason,
        "requires_user_action": exit_reason in {"blocked", "tool_failed", "cancelled"},
        "loop_risk": build_agent_loop_risk(
            steps,
            planned_tools=_planned_tool_rows(run),
            known_tool_names=ALLOWED_TOOLS,
        ),
        "stop_hooks": evaluate_agent_stop_hooks(run, steps, latest_output),
        "next_action": _agent_loop_next_action(
            status=status,
            exit_reason=exit_reason,
            next_expected_tool=next_expected_tool,
            recovery=recovery,
        ),
        "tool_call_sequence": [_agent_loop_step_marker(step) for step in steps],
    }


def _latest_step_output(steps: list[WritingAgentStep]) -> dict[str, Any]:
    if not steps:
        return {}
    output = steps[-1].output
    return output if isinstance(output, dict) else {}


def _agent_loop_exit_reason(run_status: str) -> str:
    if run_status == RUN_SUCCESS:
        return "completed"
    if run_status == RUN_FAILED:
        return "tool_failed"
    if run_status == RUN_BLOCKED:
        return "blocked"
    if run_status == RUN_CANCELLED:
        return "cancelled"
    if run_status == RUN_RUNNING:
        return "running"
    if run_status == RUN_PENDING:
        return "pending"
    return str(run_status or "unknown")


def _agent_loop_next_action(
    *,
    status: str,
    exit_reason: str,
    next_expected_tool: str | None,
    recovery: dict[str, Any],
) -> dict[str, Any]:
    if status == "completed":
        return {"kind": "none", "tool_name": None, "requires_confirmation": False}
    if recovery.get("status") == "recommended":
        requires_input = recovery.get("requires_user_input") is True
        action = str(recovery.get("action") or "").strip()
        return {
            "kind": "request_input" if requires_input or action == "ask_user" else "recover",
            "tool_name": _non_empty_string(recovery.get("next_tool")),
            "requires_confirmation": requires_input or action in {"ask_user", "review_policy"},
        }
    if next_expected_tool:
        return {"kind": "continue", "tool_name": next_expected_tool, "requires_confirmation": False}
    if exit_reason == "tool_failed":
        return {
            "kind": "inspect_failure",
            "tool_name": "inspect_agent_health_projection",
            "requires_confirmation": False,
        }
    if exit_reason == "blocked":
        return {
            "kind": "resolve_blocker",
            "tool_name": "inspect_agent_health_projection",
            "requires_confirmation": False,
        }
    return {"kind": "none", "tool_name": None, "requires_confirmation": False}


def _agent_loop_step_marker(step: WritingAgentStep) -> dict[str, Any]:
    return {
        "step_index": step.step_index,
        "tool_name": step.tool_name,
        "status": step.status,
        "tool_call_id": step.tool_call_id,
        "target_type": step.target_type,
        "chapter_index": step.chapter_index,
    }


def _planned_tool_rows(run: WritingAgentRun) -> list[dict[str, Any]]:
    run_input = run.input if isinstance(run.input, dict) else {}
    tools = run_input.get("tools") if isinstance(run_input.get("tools"), list) else []
    return [tool for tool in tools if isinstance(tool, dict)]


def _profile_policy_health(steps: list[WritingAgentStep]) -> dict[str, Any]:
    audit = _agent_profile_policy_audit_from_steps(steps)
    if not isinstance(audit, dict):
        return {
            "status": "unknown",
            "reason": "missing_agent_profile_policy_audit",
            "issue_count": 0,
            "recommended_tools": ["describe_agent_tools"],
        }
    summary = audit.get("summary") if isinstance(audit.get("summary"), dict) else {}
    issue_count = _optional_int(summary.get("issues")) or 0
    status = _non_empty_string(audit.get("status")) or "unknown"
    if status == "passed":
        return {
            "status": "passed",
            "reason": "agent_profile_policy_passed",
            "issue_count": issue_count,
            "recommended_tools": [],
        }
    return {
        "status": status,
        "reason": "agent_profile_policy_needs_attention",
        "issue_count": issue_count,
        "recommended_tools": ["inspect_agent_health_projection", "describe_agent_tools"],
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
        chapter_index = _chapter_index_from_tool_list(output.get("post_approval_continuation_tools"))
        if chapter_index:
            return chapter_index
        step_input = step.input if isinstance(step.input, dict) else {}
        params = step_input.get("params") if isinstance(step_input.get("params"), dict) else {}
        chapter_index = _optional_int(params.get("chapter_index") or params.get("start_chapter") or params.get("before_chapter"))
        if chapter_index:
            return chapter_index
        chapter_index = _chapter_index_from_tool_list(params.get("post_approval_continuation_tools"))
        if chapter_index:
            return chapter_index
    run_input = run.input if isinstance(run.input, dict) else {}
    chapter_index = _optional_int(run_input.get("chapter_index"))
    if chapter_index:
        return chapter_index
    planner = run_input.get("planner") if isinstance(run_input.get("planner"), dict) else {}
    return _optional_int(planner.get("chapter_index"))


def _chapter_index_from_tool_list(value: object) -> int | None:
    if not isinstance(value, list):
        return None
    for item in value:
        if not isinstance(item, dict):
            continue
        params = item.get("params") if isinstance(item.get("params"), dict) else {}
        chapter_index = _optional_int(params.get("chapter_index") or params.get("start_chapter") or params.get("before_chapter"))
        if chapter_index:
            return chapter_index
    return None


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
        "tool_call_id": step.tool_call_id,
        "resource_binding": summarize_resource_binding(step.resource_binding),
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
                "action": recovery.get("action"),
                "next_tool": recovery.get("next_tool"),
                "next_params": recovery.get("next_params") if isinstance(recovery.get("next_params"), dict) else {},
                "requires_user_input": recovery.get("requires_user_input") is True,
                "affected_chapter_indexes": recovery.get("affected_chapter_indexes", []),
                "memory_provenance_status": recovery.get("memory_provenance_status"),
                "memory_provenance_recovery_status": recovery.get("memory_provenance_recovery_status"),
                "memory_source_count": recovery.get("memory_source_count"),
            }
    return {"status": "none"}


def _latest_memory_provenance_from_steps(steps: list[WritingAgentStep]) -> dict[str, Any]:
    for step in reversed(steps):
        output = step.output if isinstance(step.output, dict) else {}
        provenance = output.get("memory_provenance") if isinstance(output.get("memory_provenance"), dict) else None
        if provenance is None:
            continue
        recovery = provenance.get("recovery") if isinstance(provenance.get("recovery"), dict) else {}
        prompt_context = (
            provenance.get("prompt_context") if isinstance(provenance.get("prompt_context"), dict) else None
        )
        return {
            "version": provenance.get("version"),
            "source_step_index": step.step_index,
            "source_tool": step.tool_name,
            "status": provenance.get("status"),
            "source_count": provenance.get("source_count"),
            "prompt_context": prompt_context,
            "recovery": {
                "status": recovery.get("status"),
                "reason": recovery.get("reason"),
                "next_tools": recovery.get("next_tools") if isinstance(recovery.get("next_tools"), list) else [],
            },
        }
    return {"status": "unavailable", "reason": "no_memory_provenance_seen"}


def _failure_state(run: WritingAgentRun, blocked_step: WritingAgentStep | None) -> dict[str, Any] | None:
    if run.status not in {RUN_BLOCKED, RUN_FAILED}:
        return None
    output = blocked_step.output if blocked_step is not None and isinstance(blocked_step.output, dict) else {}
    decision = output.get("decision") if isinstance(output.get("decision"), dict) else {}
    return {
        "status": run.status,
        "tool_name": blocked_step.tool_name if blocked_step is not None else None,
        "tool_call_id": blocked_step.tool_call_id if blocked_step is not None else None,
        "resource_binding": summarize_resource_binding(blocked_step.resource_binding) if blocked_step is not None else None,
        "reason_code": decision.get("reason") or output.get("reason") or output.get("error"),
        "message": run.error or decision.get("message") or output.get("error"),
    }


def _consumed_state(steps: list[WritingAgentStep]) -> dict[str, bool]:
    successful_tools = {step.tool_name for step in steps if step.status == STEP_SUCCESS}
    return {
        "longform_maintenance": bool(
            {"repair_longform_maintenance", "execute_repair_longform_maintenance_with_approval"} & successful_tools
        ),
        "longform_context": "summarize_longform_context" in successful_tools,
        "preflight": "preflight_writing" in successful_tools,
        "generated_chapter": bool(CHAPTER_GENERATION_TOOL_NAMES & successful_tools),
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


def _recommended_followup_preview_auto_plan(
    recommended_followup_run_id: str,
    *,
    status: str = "preview_required",
) -> tuple[list[WritingAgentToolRequest], dict[str, Any]]:
    preview_tool = WritingAgentToolRequest(
        tool_name="plan_recommended_followups",
        params={"run_id": recommended_followup_run_id},
        planner={
            "mode": "preview",
            "reason": "预览上一轮运行时推荐的后继工具链，不直接执行。",
            "on_missing": "stop",
            "on_failure": "stop",
            "expected_output": "推荐后继工具链预览。",
            "post_generation": False,
            "planner_version": "phase102.recommended_followup_preview_gate.v1",
        },
    )
    planner_output = {
        "status": "preview_required",
        "mode": "preview",
        "source_run_id": recommended_followup_run_id,
        "preview_only": True,
        "tools": [preview_tool.model_dump()],
        "trace": {"selected_tools": ["plan_recommended_followups"], "rejected_tools": []},
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


def _tools_with_execution_confirmation(tools: object) -> list[dict[str, Any]]:
    confirmed_tools: list[dict[str, Any]] = []
    if not isinstance(tools, list):
        return confirmed_tools
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        confirmed_tool = dict(tool)
        tool_name = str(confirmed_tool.get("tool_name") or "").strip()
        if tool_name in {"expand_outline_window", "backfill_outline_gaps"}:
            params = confirmed_tool.get("params") if isinstance(confirmed_tool.get("params"), dict) else {}
            confirmed_tool["params"] = {**params, "confirm_execute": True}
        confirmed_tools.append(confirmed_tool)
    return confirmed_tools


def _extract_step_resource_binding(output: object) -> dict[str, Any] | None:
    if not isinstance(output, dict):
        return None

    execution_binding = output.get("execution_resource_binding")
    if isinstance(execution_binding, dict):
        summary = summarize_resource_binding(execution_binding.get("resource_binding"))
        if summary:
            return summary

    summary = summarize_resource_binding(output.get("resource_binding"))
    if summary:
        return summary

    verification_event = output.get("approval_verification_event")
    resource_bindings = (
        verification_event.get("resource_bindings")
        if isinstance(verification_event, dict) and isinstance(verification_event.get("resource_bindings"), list)
        else []
    )
    for item in resource_bindings:
        summary = summarize_resource_binding(item)
        if summary:
            return summary
    return None


def _resource_binding_tool_call_id(resource_binding: dict[str, Any] | None) -> str | None:
    if not resource_binding:
        return None
    tool_call_id = str(resource_binding.get("tool_call_id") or "").strip()
    return tool_call_id or None


def _target_type_for_tool(tool_name: str) -> str | None:
    return target_type_for_tool(tool_name)


def _agent_tool_result_envelope(
    step: WritingAgentStep,
    output: dict[str, Any],
    step_status: str,
    *,
    finished_at: datetime,
    tool_lifecycle_hooks: dict[str, Any] | None = None,
) -> dict[str, Any]:
    planner = {}
    if isinstance(step.input, dict) and isinstance(step.input.get("planner"), dict):
        planner = step.input["planner"]
    result_status = str(output.get("status") or step_status)
    output_keys = sorted(str(key) for key in output if key != "agent_tool_result")
    adapter = writing_agent_tool_adapter_metadata(step.tool_name)
    envelope = {
        "version": AGENT_TOOL_RESULT_VERSION,
        "tool_name": step.tool_name,
        "step_index": step.step_index,
        "step_status": step_status,
        "result_status": result_status,
        "is_error": step_status in {STEP_FAILED, STEP_BLOCKED} or result_status in {"failed", "blocked"},
        "trace_id": str(output.get("trace_id") or "") or None,
        "planner": planner,
        "adapter": adapter,
        "execution_route": _execution_route_for_tool(step.tool_name, adapter),
        "elapsed_ms": _elapsed_ms(step.started_at, finished_at),
        "output_size_bytes": _output_size_bytes(output),
        "recovery": build_writing_agent_recovery(
            tool_name=step.tool_name,
            step_status=step_status,
            output=output,
            planner=planner,
        ),
        "recommendations": normalize_tool_recommendations(step.tool_name, output),
        "output_keys": output_keys,
    }
    if tool_lifecycle_hooks is not None:
        envelope["tool_lifecycle_hooks"] = tool_lifecycle_hooks
    return envelope


def _attach_tool_lifecycle_hooks(output: dict[str, Any], lifecycle_hooks: dict[str, Any] | None) -> dict[str, Any]:
    if lifecycle_hooks is None:
        return output
    return {**output, TOOL_LIFECYCLE_HOOKS_OUTPUT_KEY: lifecycle_hooks}


def _extract_tool_lifecycle_hooks(output: dict[str, Any]) -> dict[str, Any] | None:
    lifecycle_hooks = output.pop(TOOL_LIFECYCLE_HOOKS_OUTPUT_KEY, None)
    return lifecycle_hooks if isinstance(lifecycle_hooks, dict) else None


def _execution_route_for_tool(tool_name: str, adapter_metadata: dict[str, Any] | None) -> str:
    if adapter_metadata:
        adapter_type = str(adapter_metadata.get("adapter_type") or "adapter")
        return f"{adapter_type}_adapter"
    descriptor = get_agent_tool_descriptor(tool_name)
    if descriptor is None:
        return "unsupported"
    if descriptor.internal:
        return "unsupported_internal"
    return "legacy_action_fallback"


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


def _memory_activation_check(db: Session, project_id: str, chapter_index: int) -> dict[str, Any]:
    try:
        plan = build_memory_activation_plan(db, project_id, chapter_index=chapter_index)
        coverage = plan.get("coverage") if isinstance(plan.get("coverage"), dict) else {}
        risks = plan.get("risks") if isinstance(plan.get("risks"), list) else []
        prompt_block = str(plan.get("prompt_block") or "")
        return {
            "status": str(plan.get("status") or "unknown"),
            "activated_counts": coverage.get("activated_counts")
            if isinstance(coverage.get("activated_counts"), dict)
            else {},
            "memory_coverage_debt": (
                coverage.get("memory_coverage_debt") if isinstance(coverage.get("memory_coverage_debt"), dict) else {}
            ),
            "risk_codes": [str(risk.get("code") or "") for risk in risks if isinstance(risk, dict)],
            "recommended_next_tools": plan.get("recommended_next_tools")
            if isinstance(plan.get("recommended_next_tools"), list)
            else [],
            "prompt_preview": prompt_block[:500],
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
