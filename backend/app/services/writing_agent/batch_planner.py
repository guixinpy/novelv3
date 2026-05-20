from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import ChapterContent, Project, WritingAgentRun

BATCH_PLAN_VERSION = "phase57.longform_batch_plan.v1"
MAX_BATCH_SIZE = 3


def build_longform_chapter_batch_plan(
    db: Session,
    project_id: str,
    *,
    source_run_id: str | None = None,
    start_chapter: int | None = None,
    batch_size: int | None = None,
) -> dict[str, Any]:
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        return {"status": "failed", "error": "Project not found", "project_id": project_id}

    source_state = _source_continuation_state(db, project_id, source_run_id)
    if source_run_id and source_state is None:
        return {
            "status": "failed",
            "error": "source_run_id not found",
            "project_id": project_id,
            "source_run_id": source_run_id,
        }
    if source_state and source_state.get("status") in {"blocked", "failed"}:
        chapter_index = _optional_int(source_state.get("target_chapter_index"))
        return {
            "status": "blocked",
            "plan_version": BATCH_PLAN_VERSION,
            "project_id": project_id,
            "source_run_id": source_run_id,
            "source_continuation_state": source_state,
            "recommended_next_tools": ["plan_recovery_tools"],
            "batch": _batch_payload(chapter_index, 1),
            "dag": {"node_count": 0, "nodes": [], "edges": []},
            "plan_basis": {
                "source": "source_continuation_state",
                "source_run_id": source_run_id,
                "source_status": source_state.get("status"),
            },
            "execution_policy": {
                "mode": "preview",
                "can_execute": False,
                "requires_queue": True,
                "requires_recovery": True,
            },
            "trace": {
                "selected_nodes": [],
                "rejected_nodes": [{"reason": "source_run_needs_recovery"}],
            },
        }

    resolved_start = _resolve_start_chapter(db, project_id, source_state, start_chapter)
    resolved_size = _clamp_batch_size(batch_size)
    batch = _batch_payload(resolved_start, resolved_size)
    nodes = _dag_nodes(batch["chapter_indexes"])
    return {
        "status": "completed",
        "plan_version": BATCH_PLAN_VERSION,
        "project_id": project_id,
        "source_run_id": source_run_id,
        "source_continuation_state": source_state,
        "batch": batch,
        "dag": {
            "node_count": len(nodes),
            "nodes": nodes,
            "edges": _dag_edges(nodes),
        },
        "plan_basis": {
            "source": _start_chapter_source(source_state, start_chapter),
            "source_run_id": source_run_id,
            "source_status": source_state.get("status") if source_state else None,
        },
        "tools": _representative_tool_requests(batch["chapter_indexes"]),
        "execution_policy": {
            "mode": "preview",
            "can_execute": False,
            "requires_queue": True,
            "requires_recovery": False,
            "max_batch_size": MAX_BATCH_SIZE,
        },
        "trace": {
            "selected_nodes": [node["node_id"] for node in nodes],
            "rejected_nodes": [],
            "start_chapter_source": _start_chapter_source(source_state, start_chapter),
        },
    }


def _source_continuation_state(db: Session, project_id: str, source_run_id: str | None) -> dict[str, Any] | None:
    if not source_run_id:
        return None
    run = (
        db.query(WritingAgentRun)
        .filter(WritingAgentRun.project_id == project_id, WritingAgentRun.id == source_run_id)
        .first()
    )
    if run is None:
        return None
    output = run.output if isinstance(run.output, dict) else {}
    state = output.get("continuation_state")
    return state if isinstance(state, dict) else None


def _resolve_start_chapter(
    db: Session,
    project_id: str,
    source_state: dict[str, Any] | None,
    start_chapter: int | None,
) -> int:
    if start_chapter and start_chapter > 0:
        return int(start_chapter)
    if source_state and source_state.get("status") == "completed":
        chapter_index = _optional_int(source_state.get("target_chapter_index"))
        if chapter_index:
            return chapter_index + 1
    latest = (
        db.query(func.max(ChapterContent.chapter_index))
        .filter(
            ChapterContent.project_id == project_id,
            ChapterContent.content.isnot(None),
            ChapterContent.content != "",
        )
        .scalar()
    )
    return int(latest or 0) + 1


def _clamp_batch_size(batch_size: int | None) -> int:
    if batch_size is None:
        return 1
    return min(max(int(batch_size), 1), MAX_BATCH_SIZE)


def _batch_payload(start_chapter: int | None, batch_size: int) -> dict[str, Any]:
    if not start_chapter or start_chapter <= 0:
        return {"start_chapter": None, "end_chapter": None, "batch_size": 0, "chapter_indexes": []}
    chapter_indexes = list(range(start_chapter, start_chapter + batch_size))
    return {
        "start_chapter": start_chapter,
        "end_chapter": chapter_indexes[-1],
        "batch_size": len(chapter_indexes),
        "chapter_indexes": chapter_indexes,
    }


def _dag_nodes(chapter_indexes: list[int]) -> list[dict[str, Any]]:
    return [
        _node(
            "context_diagnostics",
            "summarize_longform_context",
            [chapter_indexes[0]],
            [],
            "目标章节的长篇上下文可用于生成，且硬阻塞已转入恢复流程。",
        ),
        _node(
            "preflight_gate",
            "preflight_writing",
            chapter_indexes,
            ["context_diagnostics"],
            "批次内每章均通过生成前依赖检查。",
        ),
        _node(
            "chapter_generation",
            "generate_chapter",
            chapter_indexes,
            ["preflight_gate"],
            "批次内章节生成正文而非大纲，并写入章节内容。",
        ),
        _node(
            "quality_review",
            "review_chapter_quality",
            chapter_indexes,
            ["chapter_generation"],
            "生成章节通过正文质量、完整度和弹性字数检查。",
        ),
        _node(
            "continuity_review",
            "review_chapter_continuity",
            chapter_indexes,
            ["chapter_generation"],
            "生成章节通过人物、设定、前文和伏笔连续性检查。",
        ),
        _node(
            "world_model_intake",
            "analyze_chapter_world_model",
            chapter_indexes,
            ["chapter_generation"],
            "章节新增事实被抽取为世界模型候选提案，等待审批。",
        ),
        _node(
            "batch_checkpoint",
            "plan_longform_chapter_batch",
            chapter_indexes,
            ["quality_review", "continuity_review", "world_model_intake"],
            "批次状态可被 continuation_state 或后续批次计划恢复。",
        ),
    ]


def _node(
    node_id: str,
    tool_name: str,
    chapter_indexes: list[int],
    depends_on: list[str],
    acceptance_criteria: str,
) -> dict[str, Any]:
    return {
        "node_id": node_id,
        "tool_name": tool_name,
        "chapter_indexes": chapter_indexes,
        "chapter_scope": {
            "start_chapter": chapter_indexes[0] if chapter_indexes else None,
            "end_chapter": chapter_indexes[-1] if chapter_indexes else None,
        },
        "depends_on": depends_on,
        "parallelizable": node_id in {"quality_review", "continuity_review", "world_model_intake"},
        "owned_artifacts": _owned_artifacts(node_id, chapter_indexes),
        "acceptance_criteria": acceptance_criteria,
        "validation": _validation_for_node(node_id),
        "handoff_payload": {
            "chapter_indexes": chapter_indexes,
            "tool_name": tool_name,
            "next_consumer": _next_consumer_for_node(node_id),
        },
    }


def _owned_artifacts(node_id: str, chapter_indexes: list[int]) -> list[str]:
    if node_id == "context_diagnostics":
        return [f"longform_context:{chapter_indexes[0]}"] if chapter_indexes else []
    if node_id == "preflight_gate":
        return [f"preflight:{index}" for index in chapter_indexes]
    if node_id == "chapter_generation":
        return [f"chapter:{index}" for index in chapter_indexes]
    if node_id == "quality_review":
        return [f"quality_review:{index}" for index in chapter_indexes]
    if node_id == "continuity_review":
        return [f"continuity_review:{index}" for index in chapter_indexes]
    if node_id == "world_model_intake":
        return [f"world_model_proposals:{index}" for index in chapter_indexes]
    if node_id == "batch_checkpoint":
        return ["longform_batch_checkpoint"]
    return []


def _validation_for_node(node_id: str) -> str:
    return {
        "context_diagnostics": "检查输出 should_generate_next_chapter 与 recommended_actions。",
        "preflight_gate": "检查每章 preflight status 为 ready。",
        "chapter_generation": "检查章节内容已写入，且不是大纲式占位文本。",
        "quality_review": "检查质量审查没有硬阻断项。",
        "continuity_review": "检查连续性审查没有硬阻断项。",
        "world_model_intake": "检查世界模型候选提案已生成或明确跳过原因。",
        "batch_checkpoint": "检查 continuation_state 可恢复下一批次。",
    }.get(node_id, "检查节点输出满足验收标准。")


def _next_consumer_for_node(node_id: str) -> str | None:
    return {
        "context_diagnostics": "preflight_gate",
        "preflight_gate": "chapter_generation",
        "chapter_generation": "quality_review|continuity_review|world_model_intake",
        "quality_review": "batch_checkpoint",
        "continuity_review": "batch_checkpoint",
        "world_model_intake": "batch_checkpoint",
        "batch_checkpoint": None,
    }.get(node_id)


def _dag_edges(nodes: list[dict[str, Any]]) -> list[dict[str, str]]:
    edges: list[dict[str, str]] = []
    for node in nodes:
        for dependency in node["depends_on"]:
            edges.append({"from": dependency, "to": node["node_id"]})
    return edges


def _representative_tool_requests(chapter_indexes: list[int]) -> list[dict[str, Any]]:
    if not chapter_indexes:
        return []
    first = chapter_indexes[0]
    return [
        {"tool_name": "summarize_longform_context", "params": {"chapter_index": first}},
        {"tool_name": "preflight_writing", "params": {"chapter_index": first}},
        {"tool_name": "generate_chapter", "params": {"chapter_index": first}},
        {"tool_name": "review_chapter_quality", "params": {"chapter_index": first}},
        {"tool_name": "review_chapter_continuity", "params": {"chapter_index": first}},
        {"tool_name": "analyze_chapter_world_model", "params": {"chapter_index": first}},
    ]


def _start_chapter_source(source_state: dict[str, Any] | None, start_chapter: int | None) -> str:
    if start_chapter:
        return "explicit"
    if source_state and source_state.get("status") == "completed":
        return "source_continuation_state"
    return "latest_generated_chapter"


def _optional_int(value: object) -> int | None:
    try:
        parsed = int(value or 0)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None
