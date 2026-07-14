"""/api/v2 会话接口：创建会话、发消息（SSE 流）、审批（M1 最小实现 + M2 审批门）。"""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agent.approval import ApprovalGate
from app.agent.events import (
    ApprovalPending,
    AssistantDelta,
    AssistantMessage,
    LoopEvent,
    ToolCallFinished,
    ToolCallStarted,
    TurnEnded,
)
from app.agent.harness import AgentHarness, HarnessConfig
from app.agent.providers.base import Provider
from app.agent.providers.deepseek import DeepSeekProvider
from app.agent.tooling import ToolContext
from app.config import load_api_key
from app.db import DATA_DIR, get_db
from app.models import Project
from app.tools.registry import build_default_registry

router = APIRouter(prefix="/api/v2", tags=["agent-sessions"])

SESSIONS_DIR = Path(DATA_DIR) / "agent_sessions"

SYSTEM_PROMPT = (
    "你是一位长篇网文创作助手，通过调用工具了解和操作当前小说项目。"
    "回答要基于工具返回的真实数据，不要编造项目内容。"
    "\n\n"
    "【跨会话记忆 (P3)】"
    "\n每次新会话开始时，务必先用 query_memory 回顾项目状态："
    "\n- memory_type='arc_summary' 查看已完成的弧线摘要（上限 3 条）"
    "\n- memory_type='plotline' 查看开放的情节线（上限 5 条）"
    "\n- keyword='角色名' 查看特定人物的历史状态（上限 3 条）"
    "\n这可以让你在不同写作会话之间保持对故事进展的感知，避免重复已完成的工作。"
    "\n\n"
    "【长程写作规范】"
    "\n1. 开始写作前，用 plan_arc define 定义弧线（指定起始和结束章节），规划好每弧线的章节数。"
    "\n2. 每章写完后，用 plan_arc progress 检查弧线进度。当弧线还剩 3 章时，提前规划下一弧线。"
    "\n3. 每章写完后，用 check_quality_trend 检查最近 10 章的字数趋势。如果发现下滑，立即分析原因并调整。"
    "\n4. 每章写完后，用 check_chapter_quality 自检，用 track_plotline 维护情节线。"
    "\n5. 坚决避免生成番外、后记、致读者等填充内容。始终聚焦主线剧情推进。"
    "\n6. 如果弧线完成且不知写什么，先用 plan_arc define 规划新弧线再继续，不要盲目填充。"
    "\n7. 人物一致性检查：用 derive_entity_relations 检查关键人物是否有合理的共现关系。"
    "\n8. 区分记忆来源：author_explicit（作者设定）可信度高于 agent_inferred（Agent 推理）。推理内容需在写作前交叉验证。"
)

# 持有活跃会话的审批门实例，供 approve/reject 端点查找
_active_gates: dict[str, ApprovalGate] = {}


def build_provider() -> Provider:
    key = load_api_key()
    if not key:
        raise HTTPException(status_code=503, detail="DeepSeek API key 未配置")
    return DeepSeekProvider(api_key=key)


def _meta_path(session_id: str) -> Path:
    return SESSIONS_DIR / f"{session_id}.meta.json"


def _load_meta(session_id: str) -> dict | None:
    path = _meta_path(session_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


class CreateSessionResponse(BaseModel):
    session_id: str
    project_id: str


class SendMessageRequest(BaseModel):
    content: str


class ApprovalResponse(BaseModel):
    ok: bool
    detail: str = ""


@router.post("/projects/{project_id}/sessions", response_model=CreateSessionResponse)
def create_session(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    session_id = str(uuid.uuid4())
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    _meta_path(session_id).write_text(
        json.dumps({"session_id": session_id, "project_id": project_id}, ensure_ascii=False),
        encoding="utf-8",
    )
    return CreateSessionResponse(session_id=session_id, project_id=project_id)


@router.get("/projects/{project_id}/sessions")
def list_sessions(project_id: str):
    sessions = []
    if SESSIONS_DIR.exists():
        for meta_file in SESSIONS_DIR.glob("*.meta.json"):
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            if meta.get("project_id") == project_id:
                sessions.append(meta)
    return {"sessions": sessions}


@router.get("/sessions/{session_id}")
def get_session(session_id: str):
    meta = _load_meta(session_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="session not found")
    log_path = SESSIONS_DIR / f"{session_id}.jsonl"
    messages: list[dict] = []
    if log_path.exists():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            if entry.get("type") == "message":
                messages.append(entry["data"])
    return {**meta, "messages": messages}


_EVENT_NAMES: list[tuple[type, str]] = [
    (AssistantDelta, "assistant_delta"),
    (AssistantMessage, "assistant_message"),
    (ToolCallStarted, "tool_call_started"),
    (ToolCallFinished, "tool_call_finished"),
    (ApprovalPending, "approval_pending"),
    (TurnEnded, "turn_ended"),
]


def _sse_frame(event: LoopEvent) -> str:
    name = next((n for t, n in _EVENT_NAMES if isinstance(event, t)), "unknown")
    return f"event: {name}\ndata: {json.dumps(asdict(event), ensure_ascii=False)}\n\n"


@router.post("/sessions/{session_id}/messages")
def send_message(
    session_id: str,
    request: SendMessageRequest,
    db: Session = Depends(get_db),
):
    meta = _load_meta(session_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="session not found")

    registry = build_default_registry()
    gate = ApprovalGate(registry=registry)
    _active_gates[session_id] = gate

    harness = AgentHarness(
        session_id=session_id,
        session_dir=SESSIONS_DIR,
        provider=build_provider(),
        registry=registry,
        tool_context=ToolContext(project_id=meta["project_id"], session_id=session_id, db=db),
        config=HarnessConfig(system_prompt=SYSTEM_PROMPT),
        before_tool_call=gate.before_tool_call,
        approval_gate=gate,
    )

    async def event_stream():
        try:
            async for event in harness.send(request.content):
                yield _sse_frame(event)
        finally:
            _active_gates.pop(session_id, None)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


class ApproveOrRejectRequest(BaseModel):
    reason: str = ""


@router.post("/sessions/{session_id}/approve", response_model=ApprovalResponse)
def approve_tool(session_id: str):
    gate = _active_gates.get(session_id)
    if gate is None:
        return ApprovalResponse(ok=False, detail="没有待审批的工具调用")
    ok = gate.approve()
    return ApprovalResponse(
        ok=ok,
        detail="已批准" if ok else "没有待审批的工具调用",
    )


@router.post("/sessions/{session_id}/reject", response_model=ApprovalResponse)
def reject_tool(session_id: str, request: ApproveOrRejectRequest = ApproveOrRejectRequest()):
    gate = _active_gates.get(session_id)
    if gate is None:
        return ApprovalResponse(ok=False, detail="没有待审批的工具调用")
    ok = gate.reject(reason=request.reason)
    return ApprovalResponse(
        ok=ok,
        detail="已拒绝" if ok else "没有待审批的工具调用",
    )
