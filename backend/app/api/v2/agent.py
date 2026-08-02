"""v2 agent API（arch-refactor 新 API，会话中心 + SSE 事件流）。

- POST /api/v2/agent/sessions           创建会话
- POST /api/v2/agent/sessions/{id}/messages  发送消息 → SSE 事件流
- POST /api/v2/agent/sessions/{id}/steer     生成中注入方向（steer 队列）
- POST /api/v2/agent/sessions/{id}/followup  完成后追加要求（follow-up 队列）
- GET  /api/v2/agent/sessions/{id}/events    事件重放

事件协议：agent_start → turn_start → ... → turn_end → agent_end（openclaw 风格）。
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.project_snapshot import build_project_snapshot
from app.db import get_db
from core.harness import AgentHarness, HarnessConfig
from core.loop import BeforeToolCall
from core.providers.deepseek import DeepSeekProvider
from core.tools.base import ToolContext, ToolRegistry
from domain.tools.writing_tools import register_writing_tools

router = APIRouter(prefix="/api/v2/agent", tags=["agent-v2"])

# 会话目录：data/agent_sessions/{session_id}/（与旧 agent_sessions 平级避免混淆）
_SESSIONS_DIR = Path("data") / "agent_sessions_v2"


class SessionCreate(BaseModel):
    project_id: str
    system_prompt: str = Field(
        default="你是一位擅长长篇网络小说的资深作者。使用可用工具完成写作任务。",
        max_length=4000,
    )


class MessageSend(BaseModel):
    content: str = Field(..., min_length=1, max_length=20000)
    idempotency_key: str | None = None


class QueueText(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)


# ── 会话注册表（进程内）──

_sessions: dict[str, dict] = {}


def _session_meta(session_id: str) -> dict | None:
    meta_path = _SESSIONS_DIR / session_id / "meta.json"
    if not meta_path.exists():
        return None
    with open(meta_path, encoding="utf-8") as f:
        return json.load(f)


def _load_provider():
    """真实 provider。测试注入走 harness 构造（见测试）。"""
    from app.config import load_api_key

    key = load_api_key()
    if not key:
        raise HTTPException(status_code=500, detail="DeepSeek API key 未配置")
    return DeepSeekProvider(api_key=key)


def _build_harness(session_id: str, db: Session) -> AgentHarness:
    meta = _session_meta(session_id)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在")
    registry = ToolRegistry()
    register_writing_tools(registry)
    provider = _load_provider()
    session_dir = _SESSIONS_DIR / session_id
    tool_context = ToolContext(
        project_id=meta["project_id"],
        session_id=session_id,
        db=db,
        extras={"work_dir": str(session_dir / "artifacts")},
    )
    harness = AgentHarness(
        session_id=session_id,
        session_dir=session_dir,
        provider=provider,
        registry=registry,
        tool_context=tool_context,
        config=HarnessConfig(
            system_prompt=meta["system_prompt"],
            max_iterations_per_turn=30,
            max_wall_clock_ms=600_000,
        ),
        snapshot_provider=lambda: build_project_snapshot(db, meta["project_id"]),
    )
    return harness


# ── 端点 ──

@router.post("/sessions")
def create_session(payload: SessionCreate, db: Session = Depends(get_db)):
    session_id = uuid.uuid4().hex[:16]
    session_dir = _SESSIONS_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    meta = {"session_id": session_id, "project_id": payload.project_id, "system_prompt": payload.system_prompt}
    with open(session_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    _sessions[session_id] = meta
    return meta


@router.post("/sessions/{session_id}/messages")
async def send_message(session_id: str, payload: MessageSend, db: Session = Depends(get_db)):
    harness = _build_harness(session_id, db)

    async def event_stream():
        yield "event: agent_start\ndata: {}\n\n"
        async for event in harness.send(payload.content, idempotency_key=payload.idempotency_key):
            data = json.dumps(
                {
                    "kind": event.kind.value,
                    **{k: v for k, v in event.__dict__.items() if k != "kind" and not k.startswith("_")},
                },
                ensure_ascii=False,
                default=str,
            )
            yield f"event: {event.kind.value}\ndata: {data}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/sessions/{session_id}/steer")
def steer(session_id: str, payload: QueueText, db: Session = Depends(get_db)):
    harness = _build_harness(session_id, db)
    harness.queue_steering(payload.content)
    return {"queued": "steer", "session_id": session_id}


@router.post("/sessions/{session_id}/followup")
def follow_up(session_id: str, payload: QueueText, db: Session = Depends(get_db)):
    harness = _build_harness(session_id, db)
    harness.queue_follow_up(payload.content)
    return {"queued": "followup", "session_id": session_id}


@router.get("/sessions/{session_id}/events")
def replay_events(session_id: str, db: Session = Depends(get_db)):
    """事件重放：读取 transcript JSONL，重建事件时间线。"""
    transcript_path = _SESSIONS_DIR / session_id / f"{session_id}.jsonl"
    if not transcript_path.exists():
        raise HTTPException(status_code=404, detail="会话无事件记录")
    events = []
    for line in transcript_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        events.append({"type": entry.get("type"), "data": entry.get("data")})
    return {"session_id": session_id, "events": events}
