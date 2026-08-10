"""v2 agent API（arch-refactor 新 API，会话中心 + SSE 事件流）。

- POST /api/v2/projects                   创建项目（写入前置）
- POST /api/v2/agent/sessions             创建会话
- POST /api/v2/agent/sessions/{id}/messages  发送消息 → SSE 事件流
- POST /api/v2/agent/sessions/{id}/steer     生成中注入方向（steer 队列）
- POST /api/v2/agent/sessions/{id}/followup  完成后追加要求（follow-up 队列）
- POST /api/v2/agent/sessions/{id}/approve|reject  工具审批（write 工具拦截）
- GET  /api/v2/agent/sessions/{id}/events    事件重放

事件协议：agent_start → turn_start → ... → turn_end → agent_end（openclaw 风格），
事件带稳定 id（{session_id}-evt-{offset}）。
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from core.approval import ApprovalGate
from core.harness import AgentHarness, HarnessConfig
from core.providers.deepseek import DeepSeekProvider
from core.tools.base import ToolContext, ToolRegistry
from domain.memory.project_snapshot import build_project_snapshot
from domain.tools.memory_tools import register_memory_tools
from domain.tools.retrieval_tools import register_retrieval_tools
from domain.tools.writing_tools import register_writing_tools

logger = logging.getLogger(__name__)

# per-book 自优化开关（09 定稿"config 可关"——code-review #13：生产路径曾硬编码
# always-on，用户无法关闭每章自省的 LLM 成本；NOVELV3_SELF_OPTIMIZE=0 关闭）
SELF_OPTIMIZE_ENABLED = os.environ.get("NOVELV3_SELF_OPTIMIZE", "1") != "0"

router = APIRouter(prefix="/api/v2", tags=["agent-v2"])

# 会话目录：data/agent_sessions_v2/{session_id}/
_SESSIONS_DIR = Path("data") / "agent_sessions_v2"

# 单会话回合总数上限（follow-up 链逃生阀，P1-7）
MAX_TURNS_PER_SEND = 5


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    genre: str = Field(default="", max_length=50)


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


class RejectBody(BaseModel):
    reason: str = Field(default="", max_length=500)


# ── 会话注册表（进程内，会话持有 harness 实例——修复每请求重建缺陷）──
# 空闲淘汰（R8）：超过 SESSION_IDLE_TTL 未访问的会话惰性清理，防长跑进程内存无界增长

SESSION_IDLE_TTL_SECONDS = 3600.0


def _now() -> float:
    import time

    return time.monotonic()


_sessions: dict[str, dict] = {}


def _evict_idle_sessions() -> None:
    """惰性淘汰：清理超过 TTL 未访问的会话（send/steer 等访问时顺带扫描）。"""
    cutoff = _now() - SESSION_IDLE_TTL_SECONDS
    for sid in [s for s, entry in _sessions.items() if entry.get("last_used", 0) < cutoff]:
        _sessions.pop(sid, None)


def _touch(session: dict) -> None:
    session["last_used"] = _now()


def _load_provider() -> DeepSeekProvider:
    """真实 provider。测试注入 monkeypatch 本函数。"""
    from app.config import load_api_key

    key = load_api_key()
    if not key:
        raise HTTPException(status_code=500, detail="DeepSeek API key 未配置")
    return DeepSeekProvider(api_key=key)


def _build_registry() -> ToolRegistry:
    """全量工具注册（writing + memory + retrieval，P0-2）。"""
    registry = ToolRegistry()
    register_writing_tools(registry)
    register_memory_tools(registry)
    register_retrieval_tools(registry)
    return registry


def _create_harness(session_id: str, meta: dict, db: Session, gate: ApprovalGate | None = None) -> AgentHarness:
    registry = _build_registry()
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
        provider=_load_provider(),
        registry=registry,
        tool_context=tool_context,
        config=HarnessConfig(
            system_prompt=meta["system_prompt"],
            max_iterations_per_turn=30,
            max_wall_clock_ms=600_000,
        ),
        before_tool_call=gate.before_tool_call if gate is not None else None,
        approval_gate=gate,
        # include_experience 接 SELF_OPTIMIZE 开关（吸收核查：此前开关只挡自省
        # 调用，快照经验段仍无条件注入——半接线）
        snapshot_provider=lambda: build_project_snapshot(
            db, meta["project_id"], include_experience=SELF_OPTIMIZE_ENABLED
        ),
        # 压缩后状态重注入（code-review 三轮 #13：injection_provider 曾是无生产
        # 消费方的死扩展点——压缩摘要永不携带设定/大纲，跨压缩存活特性静默失效）
        injection_provider=lambda: build_project_snapshot(
            db, meta["project_id"], include_experience=SELF_OPTIMIZE_ENABLED
        ),
    )
    return harness


# 每次 send 最多自省的章数（code-review 三轮：存量书首次 send 全书串行追补
# 曾阻塞 SSE 数分钟；后台任务 + 分批，成本分散到后续 send）
_INTROSPECT_BATCH_SIZE = 3


async def _introspect_after_send(db: Session, session: dict) -> None:
    """生产路径触发点（09 定稿触发点 2）：harness 回合结束后自省未自省的章（fail-open）。

    后台任务执行（BackgroundTasks）——不阻塞 SSE 流、不受客户端断开影响
    （code-review 三轮：此前在 event_stream 生成器内同步执行，按 10 号契约
    断开连接的客户端会取消自省，且存量书首次 send 全书串行追补挂起数分钟）。
    复用请求 db（FastAPI 保证 background 在依赖 teardown 之前执行）。

    - 差集推导（code-review 三轮 #2）：全部章号 - 已自省章号（introspect_log），
      乱序写章（先写 Ch5 再写 Ch4）不漏检；每次最多 _INTROSPECT_BATCH_SIZE 章
    - plan_context：从大纲取章节摘要（锚定章纲）
    - 幂等由 introspect_and_record 内部保证；失败仅记日志（fail-open）。
    """
    if not SELF_OPTIMIZE_ENABLED:
        return
    try:
        from app.models import ChapterContent, LongformMemory, Outline
        from domain.memory.memory_service import aggregate_pending_arc_summaries
        from domain.memory.writing_experience import INTROSPECT_LOG_TYPE, introspect_and_record

        harness: AgentHarness = session["harness"]
        project_id = session["meta"]["project_id"]
        all_chapters = (
            db.query(ChapterContent.chapter_index)
            .filter(ChapterContent.project_id == project_id)
            .all()
        )
        if not all_chapters:
            return
        logged = {
            r[0]
            for r in db.query(LongformMemory.start_chapter_index)
            .filter(
                LongformMemory.project_id == project_id,
                LongformMemory.memory_type == INTROSPECT_LOG_TYPE,
            )
            .all()
            if r[0] is not None
        }
        pending = sorted({c[0] for c in all_chapters} - logged)[:_INTROSPECT_BATCH_SIZE]
        if not pending:
            return
        outline = db.query(Outline).filter(Outline.project_id == project_id).first()
        outline_summaries: dict[int, str] = {}
        if outline is not None:
            for ch in outline.chapters or []:
                if isinstance(ch, dict) and isinstance(ch.get("chapter_index"), int):
                    outline_summaries[int(ch["chapter_index"])] = str(ch.get("summary") or "")
        for chapter_index in pending:
            chapter = (
                db.query(ChapterContent)
                .filter(
                    ChapterContent.project_id == project_id,
                    ChapterContent.chapter_index == chapter_index,
                )
                .first()
            )
            if chapter is None:
                continue
            await introspect_and_record(
                db,
                project_id,
                chapter_index,
                provider=harness.provider,
                plan_context=outline_summaries.get(chapter_index, ""),
                chapter_text=chapter.content,
                review_reasons="",
            )
        # B4（openhuman 封箱聚合）：仅在确有新章自省时顺带聚合（纯讨论回合
        # 不触发——code-review 三轮 #7：此前每次 send 都触发并无限重试）
        await aggregate_pending_arc_summaries(db, project_id, provider=harness.provider)
    except Exception:  # noqa: BLE001 - fail-open：自省失败不阻塞写作流程
        logger.exception("章末自省失败（fail-open 已跳过）")


def _get_session(session_id: str, db: Session) -> dict:
    """取会话（进程内 registry；重启后按磁盘 meta 懒重建）。"""
    _evict_idle_sessions()
    session = _sessions.get(session_id)
    if session is None:
        meta_path = _SESSIONS_DIR / session_id / "meta.json"
        if not meta_path.exists():
            raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在")
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
        gate = ApprovalGate(_build_registry())
        harness = _create_harness(session_id, meta, db, gate=gate)
        session = {"meta": meta, "harness": harness, "gate": gate}
        _sessions[session_id] = session
    _touch(session)
    return session


# ── 端点 ──

@router.post("/projects")
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    """创建项目（v2 会话的写入前置；修复无创建入口缺陷）。"""
    from app.models import Project

    project = Project(name=payload.name, genre=payload.genre)
    db.add(project)
    db.commit()
    db.refresh(project)
    return {"id": project.id, "name": project.name, "genre": project.genre}


@router.post("/agent/sessions")
def create_session(payload: SessionCreate, db: Session = Depends(get_db)):
    from app.models import Project

    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail=f"项目 {payload.project_id} 不存在")
    session_id = uuid.uuid4().hex[:16]
    session_dir = _SESSIONS_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    meta = {"session_id": session_id, "project_id": payload.project_id, "system_prompt": payload.system_prompt}
    with open(session_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    # 构建并持有 harness（含审批门）
    gate = ApprovalGate(_build_registry())
    harness = _create_harness(session_id, meta, db, gate=gate)
    _sessions[session_id] = {"meta": meta, "harness": harness, "gate": gate}
    return meta


@router.post("/agent/sessions/{session_id}/messages")
async def send_message(
    session_id: str,
    payload: MessageSend,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None,  # type: ignore[assignment]  # FastAPI 特殊参数，非响应字段
):
    session = _get_session(session_id, db)
    harness: AgentHarness = session["harness"]
    harness.max_turns_per_send = MAX_TURNS_PER_SEND

    # 09 定稿触发点 2（生产路径）：自省注册为后台任务——SSE 流立即结束、
    # 客户端按 10 号契约收到 agent_end 即可关闭连接（code-review 三轮 #1：
    # 此前自省在生成器内同步执行，按契约断开的客户端 CancelledError 取消自省，
    # 存量书首次 send 全书串行追补挂起数分钟且每轮重复烧成本）
    if background_tasks is not None:
        background_tasks.add_task(_introspect_after_send, db, session)

    async def event_stream():
        async for event in harness.send(payload.content, idempotency_key=payload.idempotency_key):
            # R6：会话级递增（跨 send 不重置），事件 id 全局唯一
            harness.event_offset += 1
            event_id = f"{session_id}-evt-{harness.event_offset}"
            data = json.dumps(
                {
                    "kind": event.kind.value,
                    "event_id": event_id,
                    **{k: v for k, v in event.__dict__.items() if k != "kind" and not k.startswith("_")},
                },
                ensure_ascii=False,
                default=str,
            )
            yield f"event: {event.kind.value}\ndata: {data}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/agent/sessions/{session_id}/steer")
def steer(session_id: str, payload: QueueText, db: Session = Depends(get_db)):
    session = _get_session(session_id, db)
    session["harness"].queue_steering(payload.content)
    return {"queued": "steer", "session_id": session_id}


@router.post("/agent/sessions/{session_id}/followup")
def follow_up(session_id: str, payload: QueueText, db: Session = Depends(get_db)):
    session = _get_session(session_id, db)
    session["harness"].queue_follow_up(payload.content)
    return {"queued": "followup", "session_id": session_id}


@router.post("/agent/sessions/{session_id}/approve")
def approve(session_id: str, call_id: str, db: Session = Depends(get_db)):
    session = _get_session(session_id, db)
    if not session["gate"].approve(call_id):
        raise HTTPException(status_code=404, detail=f"审批请求 {call_id} 不存在或已处理")
    return {"approved": True, "call_id": call_id}


@router.post("/agent/sessions/{session_id}/reject")
def reject(session_id: str, call_id: str, payload: RejectBody = RejectBody(), db: Session = Depends(get_db)):
    session = _get_session(session_id, db)
    if not session["gate"].reject(call_id, payload.reason):
        raise HTTPException(status_code=404, detail=f"审批请求 {call_id} 不存在或已处理")
    return {"approved": False, "call_id": call_id}


@router.get("/agent/sessions/{session_id}/pending-approvals")
def pending_approvals(session_id: str, db: Session = Depends(get_db)):
    session = _get_session(session_id, db)
    return {"session_id": session_id, "pending": session["gate"].pending_requests()}


@router.get("/agent/sessions/{session_id}/events")
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
