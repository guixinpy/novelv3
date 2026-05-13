# AI Call Context Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a transparent AI model-call trace system for Hermes chat, Athena chat, and chapter generation.

**Architecture:** Add a backend `AIModelCallTrace` persistence layer, a small trace service that snapshots actual model payloads, and a read API for list/detail views. Existing Hermes, Athena, and chapter-generation builders will emit structured `context_blocks` beside the raw OpenAI-compatible `messages`; the frontend will expose those traces through a shared drawer launched from chat replies and generated chapters.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, SQLite JSON columns, pytest, Vue 3, Pinia, Vite, Vitest.

---

## File Structure

Backend files:

- Create `backend/app/models/ai_model_call_trace.py`: SQLAlchemy trace table.
- Modify `backend/app/models/__init__.py`: export `AIModelCallTrace`.
- Create `backend/alembic/versions/20260428_add_ai_model_call_traces.py`: migration.
- Create `backend/app/schemas/model_call_trace.py`: trace list/detail response schemas.
- Create `backend/app/core/model_call_trace.py`: trace creation, sanitizing, truncation, summary helpers.
- Modify `backend/app/core/context_injection.py`: add structured context builders while preserving current string builders.
- Modify `backend/app/api/dialogs.py`: record Hermes chat traces and expose `trace_id` in chat history.
- Modify `backend/app/api/athena.py`: record Athena chat traces for real model calls.
- Modify `backend/app/api/chapters.py`: record chapter-generation traces.
- Create `backend/app/api/model_call_traces.py`: list/detail trace API.
- Modify `backend/app/api/projects.py`: delete project-scoped traces.
- Modify `backend/app/main.py`: include trace router.
- Modify `backend/app/schemas/dialog.py`: add `id` and `trace_id`.
- Modify `backend/app/schemas/chapter.py`: add `last_generation_trace_id`.
- Add tests in `backend/tests/test_model_call_traces.py`.
- Update focused tests in `backend/tests/test_athena_dialog.py`, `backend/tests/test_chapters.py`, and project deletion tests if present.

Frontend files:

- Modify `frontend/src/api/types.ts`: add trace types, `trace_id`, `id`, `last_generation_trace_id`.
- Modify `frontend/src/api/client.ts`: add trace API methods.
- Create `frontend/src/stores/modelTraces.ts`: load detail/list and drawer state.
- Modify `frontend/src/stores/chat.ts`: preserve `id` and `trace_id` on messages.
- Modify `frontend/src/stores/athena.ts`: preserve `trace_id` on sent Athena responses.
- Modify `frontend/src/components/chat/ChatMessage.vue`: emit trace open event.
- Modify `frontend/src/components/chat/ChatMessageList.vue`: forward trace open event.
- Create `frontend/src/components/modelTrace/ModelTraceDrawer.vue`.
- Create `frontend/src/components/modelTrace/TraceSummary.vue`.
- Create `frontend/src/components/modelTrace/ContextBlockList.vue`.
- Create `frontend/src/components/modelTrace/ContextSourceList.vue`.
- Create `frontend/src/components/modelTrace/RawMessagesViewer.vue`.
- Modify `frontend/src/views/HermesView.vue`: mount drawer and open chat/chapter traces.
- Modify `frontend/src/components/athena/AthenaChatPanel.vue`: mount drawer and open Athena traces.
- Add focused Vitest tests for store and drawer behavior.

---

### Task 1: Backend Trace Model, Schema, Service, and Migration

**Files:**
- Create: `backend/app/models/ai_model_call_trace.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/20260428_add_ai_model_call_traces.py`
- Create: `backend/app/schemas/model_call_trace.py`
- Create: `backend/app/core/model_call_trace.py`
- Test: `backend/tests/test_model_call_traces.py`

- [ ] **Step 1: Write failing service tests**

Add to `backend/tests/test_model_call_traces.py`:

```python
from app.core.model_call_trace import (
    build_context_block,
    sanitize_model_messages,
    truncate_text,
)


def test_sanitize_model_messages_redacts_secret_like_values():
    messages = [
        {"role": "user", "content": "Authorization: Bearer sk-secret-token\n普通内容"},
        {"role": "system", "content": "api_key=sk-another-secret"},
    ]

    sanitized = sanitize_model_messages(messages)

    joined = "\n".join(item["content"] for item in sanitized)
    assert "sk-secret-token" not in joined
    assert "sk-another-secret" not in joined
    assert "[REDACTED]" in joined
    assert "普通内容" in joined


def test_truncate_text_preserves_length_metadata():
    result = truncate_text("0123456789" * 80, max_chars=120)

    assert result["truncated"] is True
    assert result["original_char_count"] == 800
    assert len(result["content"]) <= 150
    assert "..." in result["content"]


def test_build_context_block_adds_counts_and_sources():
    block = build_context_block(
        key="facts",
        title="已确认事实",
        kind="world_fact",
        content="char.林舟.presence_count = 2",
        sources=[
            {
                "source_type": "WorldFactClaim",
                "source_id": "claim-1",
                "label": "林舟出场事实",
                "chapter_index": 1,
            }
        ],
    )

    assert block["key"] == "facts"
    assert block["kind"] == "world_fact"
    assert block["char_count"] > 0
    assert block["token_estimate"] > 0
    assert block["sources"][0]["source_id"] == "claim-1"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
cd backend && source .venv/bin/activate && pytest tests/test_model_call_traces.py -q
```

Expected: FAIL with import errors for `app.core.model_call_trace`.

- [ ] **Step 3: Add SQLAlchemy model**

Create `backend/app/models/ai_model_call_trace.py`:

```python
import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String, Text

from app.db import Base


class AIModelCallTrace(Base):
    __tablename__ = "ai_model_call_traces"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    trace_type = Column(String, nullable=False)
    status = Column(String, nullable=False, default="running")
    model = Column(String, default="")
    temperature = Column(String, default="")
    max_tokens = Column(Integer, default=0)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)
    error_message = Column(Text, default="")
    dialog_id = Column(String, ForeignKey("dialogs.id"), nullable=True)
    request_message_id = Column(String, ForeignKey("dialog_messages.id"), nullable=True)
    response_message_id = Column(String, ForeignKey("dialog_messages.id"), nullable=True)
    chapter_id = Column(String, ForeignKey("chapter_contents.id"), nullable=True)
    chapter_index = Column(Integer, nullable=True)
    messages = Column(JSON, default=list)
    context_blocks = Column(JSON, default=list)
    trace_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


Index("ix_ai_model_call_traces_project_type_created", AIModelCallTrace.project_id, AIModelCallTrace.trace_type, AIModelCallTrace.created_at)
Index("ix_ai_model_call_traces_dialog_response", AIModelCallTrace.dialog_id, AIModelCallTrace.response_message_id)
Index("ix_ai_model_call_traces_chapter", AIModelCallTrace.project_id, AIModelCallTrace.chapter_index)
```

Modify `backend/app/models/__init__.py`:

```python
from .ai_model_call_trace import AIModelCallTrace
```

- [ ] **Step 4: Add Alembic migration**

Create `backend/alembic/versions/20260428_add_ai_model_call_traces.py`:

```python
"""add ai model call traces

Revision ID: 20260428_add_ai_model_call_traces
Revises: 20260428_add_athena_retrieval_tables
Create Date: 2026-04-28
"""

from alembic import op
import sqlalchemy as sa


revision = "20260428_add_ai_model_call_traces"
down_revision = "20260428_add_athena_retrieval_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_model_call_traces",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("trace_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("temperature", sa.String(), nullable=True),
        sa.Column("max_tokens", sa.Integer(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("dialog_id", sa.String(), nullable=True),
        sa.Column("request_message_id", sa.String(), nullable=True),
        sa.Column("response_message_id", sa.String(), nullable=True),
        sa.Column("chapter_id", sa.String(), nullable=True),
        sa.Column("chapter_index", sa.Integer(), nullable=True),
        sa.Column("messages", sa.JSON(), nullable=True),
        sa.Column("context_blocks", sa.JSON(), nullable=True),
        sa.Column("trace_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapter_contents.id"]),
        sa.ForeignKeyConstraint(["dialog_id"], ["dialogs.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["request_message_id"], ["dialog_messages.id"]),
        sa.ForeignKeyConstraint(["response_message_id"], ["dialog_messages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_model_call_traces_project_type_created", "ai_model_call_traces", ["project_id", "trace_type", "created_at"])
    op.create_index("ix_ai_model_call_traces_dialog_response", "ai_model_call_traces", ["dialog_id", "response_message_id"])
    op.create_index("ix_ai_model_call_traces_chapter", "ai_model_call_traces", ["project_id", "chapter_index"])


def downgrade() -> None:
    op.drop_index("ix_ai_model_call_traces_chapter", table_name="ai_model_call_traces")
    op.drop_index("ix_ai_model_call_traces_dialog_response", table_name="ai_model_call_traces")
    op.drop_index("ix_ai_model_call_traces_project_type_created", table_name="ai_model_call_traces")
    op.drop_table("ai_model_call_traces")
```

- [ ] **Step 5: Add schemas**

Create `backend/app/schemas/model_call_trace.py`:

```python
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TraceSourceOut(BaseModel):
    source_type: str
    source_id: str | None = None
    label: str = ""
    chapter_index: int | None = None


class ContextBlockOut(BaseModel):
    key: str
    title: str
    kind: str
    content: str
    token_estimate: int = 0
    char_count: int = 0
    original_char_count: int | None = None
    truncated: bool = False
    sources: list[TraceSourceOut] = Field(default_factory=list)


class ModelCallTraceListItem(BaseModel):
    id: str
    project_id: str
    trace_type: str
    status: str
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    dialog_id: str | None = None
    request_message_id: str | None = None
    response_message_id: str | None = None
    chapter_id: str | None = None
    chapter_index: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModelCallTraceDetail(ModelCallTraceListItem):
    temperature: str = ""
    max_tokens: int = 0
    error_message: str = ""
    messages: list[dict[str, Any]] = Field(default_factory=list)
    context_blocks: list[ContextBlockOut] = Field(default_factory=list)
    trace_metadata: dict[str, Any] = Field(default_factory=dict)


class PaginatedModelCallTraces(BaseModel):
    total: int
    items: list[ModelCallTraceListItem]
```

- [ ] **Step 6: Add trace service**

Create `backend/app/core/model_call_trace.py`:

```python
import re
import time
from typing import Any

from sqlalchemy.orm import Session

from app.models import AIModelCallTrace

MAX_BLOCK_CHARS = 4000
MAX_RAW_MESSAGE_CHARS = 12000
SECRET_PATTERNS = [
    re.compile(r"(Authorization:\s*Bearer\s+)[^\s]+", re.IGNORECASE),
    re.compile(r"(api[_-]?key\s*[:=]\s*)[^\s]+", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
]


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    cjk_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    ascii_chunks = len([item for item in re.split(r"\s+", text) if item])
    return max(1, int(cjk_chars * 0.8) + ascii_chunks)


def sanitize_text(text: str) -> str:
    sanitized = text or ""
    for pattern in SECRET_PATTERNS:
        sanitized = pattern.sub(lambda m: f"{m.group(1)}[REDACTED]" if m.lastindex else "[REDACTED]", sanitized)
    return sanitized


def truncate_text(text: str, *, max_chars: int = MAX_BLOCK_CHARS) -> dict[str, Any]:
    sanitized = sanitize_text(text or "")
    original = len(sanitized)
    if original <= max_chars:
        return {"content": sanitized, "truncated": False, "original_char_count": original}
    head = max_chars // 2
    tail = max_chars - head
    content = f"{sanitized[:head]}\n...[TRUNCATED {original - max_chars} CHARS]...\n{sanitized[-tail:]}"
    return {"content": content, "truncated": True, "original_char_count": original}


def sanitize_model_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sanitized: list[dict[str, Any]] = []
    for message in messages:
        content = message.get("content", "")
        truncated = truncate_text(str(content), max_chars=MAX_RAW_MESSAGE_CHARS)
        sanitized.append({
            "role": str(message.get("role", "")),
            "content": truncated["content"],
            "truncated": truncated["truncated"],
            "original_char_count": truncated["original_char_count"],
        })
    return sanitized


def build_context_block(
    *,
    key: str,
    title: str,
    kind: str,
    content: str,
    sources: list[dict[str, Any]] | None = None,
    max_chars: int = MAX_BLOCK_CHARS,
) -> dict[str, Any]:
    truncated = truncate_text(content, max_chars=max_chars)
    return {
        "key": key,
        "title": title,
        "kind": kind,
        "content": truncated["content"],
        "token_estimate": estimate_tokens(truncated["content"]),
        "char_count": len(truncated["content"]),
        "original_char_count": truncated["original_char_count"],
        "truncated": truncated["truncated"],
        "sources": sources or [],
    }


def create_trace(
    db: Session,
    *,
    project_id: str,
    trace_type: str,
    messages: list[dict[str, Any]],
    context_blocks: list[dict[str, Any]],
    model: str,
    temperature: float,
    max_tokens: int,
    dialog_id: str | None = None,
    request_message_id: str | None = None,
    chapter_index: int | None = None,
    trace_metadata: dict[str, Any] | None = None,
) -> AIModelCallTrace:
    trace = AIModelCallTrace(
        project_id=project_id,
        trace_type=trace_type,
        status="running",
        model=model,
        temperature=str(temperature),
        max_tokens=max_tokens,
        dialog_id=dialog_id,
        request_message_id=request_message_id,
        chapter_index=chapter_index,
        messages=sanitize_model_messages(messages),
        context_blocks=context_blocks,
        trace_metadata=trace_metadata or {},
    )
    db.add(trace)
    db.commit()
    db.refresh(trace)
    return trace


def mark_trace_success(
    db: Session,
    trace: AIModelCallTrace | None,
    *,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: int,
    response_message_id: str | None = None,
    chapter_id: str | None = None,
) -> None:
    if trace is None:
        return
    trace.status = "success"
    trace.model = model
    trace.prompt_tokens = prompt_tokens
    trace.completion_tokens = completion_tokens
    trace.latency_ms = latency_ms
    trace.response_message_id = response_message_id
    trace.chapter_id = chapter_id
    db.commit()


def mark_trace_failed(db: Session, trace: AIModelCallTrace | None, *, error: Exception | str, latency_ms: int = 0) -> None:
    if trace is None:
        return
    trace.status = "failed"
    trace.latency_ms = latency_ms
    trace.error_message = sanitize_text(str(error))[:1000]
    db.commit()


def attach_trace_response(db: Session, trace_id: str | None, response_message_id: str) -> None:
    if not trace_id:
        return
    trace = db.query(AIModelCallTrace).filter(AIModelCallTrace.id == trace_id).first()
    if not trace:
        return
    trace.response_message_id = response_message_id
    db.commit()


def now_ms() -> int:
    return int(time.time() * 1000)
```

- [ ] **Step 7: Run service tests**

Run:

```bash
cd backend && source .venv/bin/activate && pytest tests/test_model_call_traces.py -q
```

Expected: PASS for the three service tests.

- [ ] **Step 8: Commit Task 1**

Run:

```bash
git add backend/app/models/ai_model_call_trace.py backend/app/models/__init__.py backend/alembic/versions/20260428_add_ai_model_call_traces.py backend/app/schemas/model_call_trace.py backend/app/core/model_call_trace.py backend/tests/test_model_call_traces.py
git commit -m "feat: add model call trace foundation"
```

---

### Task 2: Trace Read API and Project Cleanup

**Files:**
- Create: `backend/app/api/model_call_traces.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/api/projects.py`
- Test: `backend/tests/test_model_call_traces.py`

- [ ] **Step 1: Add failing API tests**

Append to `backend/tests/test_model_call_traces.py`:

```python
from app.models import AIModelCallTrace, Project


def test_list_and_get_model_call_traces(client, db_session):
    project = Project(name="Trace API", genre="悬疑")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    trace = AIModelCallTrace(
        project_id=project.id,
        trace_type="hermes_chat",
        status="success",
        model="deepseek-chat",
        prompt_tokens=12,
        completion_tokens=8,
        messages=[{"role": "user", "content": "你好"}],
        context_blocks=[
            {
                "key": "user_input",
                "title": "用户输入",
                "kind": "user_input",
                "content": "你好",
                "token_estimate": 1,
                "char_count": 2,
                "truncated": False,
                "sources": [{"source_type": "UserInput", "source_id": None, "label": "本轮输入"}],
            }
        ],
    )
    db_session.add(trace)
    db_session.commit()
    db_session.refresh(trace)

    list_response = client.get(f"/api/v1/projects/{project.id}/model-call-traces?trace_type=hermes_chat")
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert list_response.json()["items"][0]["id"] == trace.id

    detail_response = client.get(f"/api/v1/projects/{project.id}/model-call-traces/{trace.id}")
    assert detail_response.status_code == 200
    payload = detail_response.json()
    assert payload["messages"][0]["content"] == "你好"
    assert payload["context_blocks"][0]["sources"][0]["source_type"] == "UserInput"


def test_get_model_call_trace_rejects_cross_project_access(client, db_session):
    project_a = Project(name="A")
    project_b = Project(name="B")
    db_session.add_all([project_a, project_b])
    db_session.commit()
    trace = AIModelCallTrace(project_id=project_a.id, trace_type="hermes_chat", status="success")
    db_session.add(trace)
    db_session.commit()

    response = client.get(f"/api/v1/projects/{project_b.id}/model-call-traces/{trace.id}")

    assert response.status_code == 404
```

- [ ] **Step 2: Run tests to verify API failure**

Run:

```bash
cd backend && source .venv/bin/activate && pytest tests/test_model_call_traces.py::test_list_and_get_model_call_traces tests/test_model_call_traces.py::test_get_model_call_trace_rejects_cross_project_access -q
```

Expected: FAIL with 404 because router is missing.

- [ ] **Step 3: Add trace API router**

Create `backend/app/api/model_call_traces.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AIModelCallTrace, Project
from app.schemas.model_call_trace import ModelCallTraceDetail, ModelCallTraceListItem, PaginatedModelCallTraces

router = APIRouter(prefix="/api/v1/projects/{project_id}/model-call-traces", tags=["model-call-traces"])


def _require_project(db: Session, project_id: str) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("", response_model=PaginatedModelCallTraces)
def list_model_call_traces(
    project_id: str,
    trace_type: str | None = None,
    chapter_index: int | None = None,
    dialog_id: str | None = None,
    limit: int = 30,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    _require_project(db, project_id)
    query = db.query(AIModelCallTrace).filter(AIModelCallTrace.project_id == project_id)
    if trace_type:
        query = query.filter(AIModelCallTrace.trace_type == trace_type)
    if chapter_index is not None:
        query = query.filter(AIModelCallTrace.chapter_index == chapter_index)
    if dialog_id:
        query = query.filter(AIModelCallTrace.dialog_id == dialog_id)
    total = query.count()
    items = (
        query
        .order_by(AIModelCallTrace.created_at.desc())
        .offset(max(offset, 0))
        .limit(min(max(limit, 1), 100))
        .all()
    )
    return PaginatedModelCallTraces(
        total=total,
        items=[ModelCallTraceListItem.model_validate(item) for item in items],
    )


@router.get("/{trace_id}", response_model=ModelCallTraceDetail)
def get_model_call_trace(project_id: str, trace_id: str, db: Session = Depends(get_db)):
    _require_project(db, project_id)
    trace = (
        db.query(AIModelCallTrace)
        .filter(AIModelCallTrace.project_id == project_id, AIModelCallTrace.id == trace_id)
        .first()
    )
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return ModelCallTraceDetail.model_validate(trace)
```

Modify `backend/app/main.py` imports and router registration:

```python
from app.api import (
    athena,
    background_tasks_api,
    chapter_revisions,
    chapters,
    config,
    consistency,
    dialogs,
    export,
    model_call_traces,
    outlines,
    preferences,
    projects,
    setups,
    storylines,
    topologies,
    versions,
    world_model,
    writing,
)

app.include_router(model_call_traces.router)
```

- [ ] **Step 4: Add project deletion cleanup**

Modify `backend/app/api/projects.py` imports:

```python
from app.models import (
    AIModelCallTrace,
    BackgroundTask,
    ...
)
```

Modify `PROJECT_SCOPED_MODELS` so trace rows are removed before dialogs, chapters, and world-model records:

```python
PROJECT_SCOPED_MODELS = (
    AIModelCallTrace,
    RetrievalEmbedding,
    RetrievalChunk,
    RetrievalDocument,
    ...
)
```

Add trace deletion before dialog rows because traces reference dialog messages:

```python
    if AIModelCallTrace.__tablename__ in existing_tables:
        db.execute(delete(AIModelCallTrace).where(AIModelCallTrace.project_id == project_id))
```

Place it immediately after `existing_tables` is computed and before `dialog_ids`.

- [ ] **Step 5: Run API tests**

Run:

```bash
cd backend && source .venv/bin/activate && pytest tests/test_model_call_traces.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 2**

Run:

```bash
git add backend/app/api/model_call_traces.py backend/app/main.py backend/app/api/projects.py backend/tests/test_model_call_traces.py
git commit -m "feat: expose model call trace api"
```

---

### Task 3: Structured Context Blocks for Chat Builders

**Files:**
- Modify: `backend/app/core/context_injection.py`
- Modify: `backend/app/api/dialogs.py`
- Test: `backend/tests/test_athena_dialog.py`

- [ ] **Step 1: Add failing context-block test**

Add to `backend/tests/test_athena_dialog.py`:

```python
from app.core.context_injection import build_athena_world_context_blocks
from app.models import WorldCharacter, WorldFactClaim


def test_athena_world_context_blocks_include_record_sources(db_session):
    project, profile = _seed_project(db_session, with_profile=True)
    character = WorldCharacter(
        project_id=project.id,
        project_profile_version_id=profile.id,
        profile_version=profile.version,
        character_id="char.linzhou",
        canonical_id="char.linzhou",
        name="林舟",
        primary_alias="林舟",
        contract_version="world.contract.v1",
    )
    fact = WorldFactClaim(
        project_id=project.id,
        project_profile_version_id=profile.id,
        profile_version=profile.version,
        claim_id="claim.linzhou.presence",
        chapter_index=1,
        intra_chapter_seq=0,
        subject_ref="char.linzhou",
        predicate="presence_count",
        object_ref_or_value={"count": 1},
        claim_layer="truth",
        claim_status="confirmed",
        authority_type="derived",
        confidence=0.9,
        contract_version="world.contract.v1",
    )
    db_session.add_all([character, fact])
    db_session.commit()

    blocks = build_athena_world_context_blocks(db_session, project.id)

    assert any(block["kind"] == "world_entity" for block in blocks)
    fact_block = next(block for block in blocks if block["kind"] == "world_fact")
    assert fact_block["sources"][0]["source_type"] == "WorldFactClaim"
    assert fact_block["sources"][0]["source_id"] == fact.id
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
cd backend && source .venv/bin/activate && pytest tests/test_athena_dialog.py::test_athena_world_context_blocks_include_record_sources -q
```

Expected: FAIL because `build_athena_world_context_blocks` is missing.

- [ ] **Step 3: Add structured builders**

Modify `backend/app/core/context_injection.py` by importing the trace block helper:

```python
from app.core.model_call_trace import build_context_block
```

Add `build_athena_world_context_blocks()`:

```python
def build_athena_world_context_blocks(db: Session, project_id: str) -> list[dict]:
    profile = _get_current_profile(db, project_id)
    if profile is None:
        setup = db.query(Setup).filter(Setup.project_id == project_id).first()
        if setup is None:
            return [build_context_block(
                key="athena_setup_missing",
                title="世界模型状态",
                kind="setup",
                content="当前项目尚未建立正式 world-model profile，也没有可参考的 Setup 草稿。",
                sources=[{"source_type": "Project", "source_id": project_id, "label": "项目"}],
            )]
        return [build_context_block(
            key="athena_setup_fallback",
            title="Setup 草稿",
            kind="setup",
            content=build_athena_world_context(db, project_id),
            sources=[{"source_type": "Setup", "source_id": setup.id, "label": "Setup 草稿"}],
        )]

    blocks: list[dict] = []
    characters = db.query(WorldCharacter).filter(WorldCharacter.project_id == project_id).limit(20).all()
    locations = db.query(WorldLocation).filter(WorldLocation.project_id == project_id).limit(10).all()
    factions = db.query(WorldFaction).filter(WorldFaction.project_id == project_id).limit(10).all()
    entity_lines = []
    entity_sources = []
    for c in characters:
        entity_lines.append(f"- 角色：{c.name}（{getattr(c, 'role', '未知')}）")
        entity_sources.append({"source_type": "WorldCharacter", "source_id": c.id, "label": c.name})
    for loc in locations:
        entity_lines.append(f"- 地点：{loc.name}")
        entity_sources.append({"source_type": "WorldLocation", "source_id": loc.id, "label": loc.name})
    for f in factions:
        entity_lines.append(f"- 阵营：{f.name}")
        entity_sources.append({"source_type": "WorldFaction", "source_id": f.id, "label": f.name})
    if entity_lines:
        blocks.append(build_context_block(
            key="athena_world_entities",
            title="世界实体",
            kind="world_entity",
            content="\n".join(entity_lines),
            sources=entity_sources,
        ))

    facts = (
        db.query(WorldFactClaim)
        .filter(
            WorldFactClaim.project_id == project_id,
            WorldFactClaim.claim_status == "confirmed",
            WorldFactClaim.claim_layer == "truth",
        )
        .limit(50)
        .all()
    )
    if facts:
        blocks.append(build_context_block(
            key="athena_confirmed_facts",
            title="当前确认事实",
            kind="world_fact",
            content="\n".join(f"- {f.subject_ref}.{f.predicate} = {f.object_ref_or_value}" for f in facts),
            sources=[
                {
                    "source_type": "WorldFactClaim",
                    "source_id": f.id,
                    "label": f.claim_id,
                    "chapter_index": f.chapter_index,
                }
                for f in facts
            ],
        ))
    return blocks
```

Add `build_hermes_world_context_blocks()`:

```python
def build_hermes_world_context_blocks(db: Session, project_id: str, chapter_index: int | None = None) -> list[dict]:
    content = build_hermes_world_context(db, project_id, chapter_index)
    if not content:
        return []
    return [build_context_block(
        key="hermes_world_context",
        title="Hermes 世界摘要",
        kind="world_fact",
        content=content,
        sources=[{"source_type": "Project", "source_id": project_id, "label": "Hermes 世界上下文"}],
    )]
```

- [ ] **Step 4: Update chat payload builder signature**

In `backend/app/api/dialogs.py`, add a payload helper without changing behavior:

```python
def _build_chat_call_payload(
    db: Session,
    dialog_id: str,
    project: Project,
    diagnosis: ProjectDiagnosisOut,
    dialog_type: str = "hermes",
) -> dict:
    messages = _build_chat_messages(db, dialog_id, project, diagnosis, dialog_type=dialog_type)
    if dialog_type == "athena":
        from app.core.context_injection import build_athena_world_context_blocks
        blocks = build_athena_world_context_blocks(db, project.id)
    else:
        from app.core.context_injection import build_hermes_world_context_blocks
        blocks = build_hermes_world_context_blocks(db, project.id)
    blocks.append({
        "key": "dialog_messages",
        "title": "对话历史",
        "kind": "dialog_history",
        "content": "\n".join(f"{m['role']}: {m['content']}" for m in messages[1:]),
        "token_estimate": 0,
        "char_count": sum(len(m.get("content", "")) for m in messages[1:]),
        "truncated": False,
        "sources": [{"source_type": "Dialog", "source_id": dialog_id, "label": "当前对话"}],
    })
    return {"messages": messages, "context_blocks": blocks}
```

The next task will wire this helper into trace persistence.

- [ ] **Step 5: Run focused tests**

Run:

```bash
cd backend && source .venv/bin/activate && pytest tests/test_athena_dialog.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 3**

Run:

```bash
git add backend/app/core/context_injection.py backend/app/api/dialogs.py backend/tests/test_athena_dialog.py
git commit -m "feat: structure chat context blocks"
```

---

### Task 4: Trace Hermes and Athena Chat Calls

**Files:**
- Modify: `backend/app/api/dialogs.py`
- Modify: `backend/app/api/athena.py`
- Modify: `backend/app/schemas/dialog.py`
- Test: `backend/tests/test_model_call_traces.py`
- Test: `backend/tests/test_athena_dialog.py`

- [ ] **Step 1: Add failing chat trace tests**

Append to `backend/tests/test_model_call_traces.py`:

```python
from unittest.mock import AsyncMock, patch

from app.api import dialogs
from app.models import AIModelCallTrace, DialogMessage


@patch("app.api.dialogs.load_api_key", return_value="sk-test")
@patch("app.api.dialogs.ai_service.complete", new_callable=AsyncMock)
def test_hermes_chat_creates_trace_and_returns_trace_id(mock_complete, mock_key, client):
    project_id = client.post("/api/v1/projects", json={"name": "Trace Chat"}).json()["id"]
    mock_complete.return_value.content = "可以，从第一章开始。"
    mock_complete.return_value.model = "deepseek-chat"
    mock_complete.return_value.prompt_tokens = 30
    mock_complete.return_value.completion_tokens = 12

    response = client.post("/api/v1/dialog/chat", json={"project_id": project_id, "input_type": "text", "text": "帮我规划第一章"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["trace_id"]
    trace_response = client.get(f"/api/v1/projects/{project_id}/model-call-traces/{payload['trace_id']}")
    assert trace_response.status_code == 200
    trace = trace_response.json()
    assert trace["trace_type"] == "hermes_chat"
    assert trace["status"] == "success"
    assert trace["prompt_tokens"] == 30
    assert trace["messages"][0]["role"] == "system"


@patch("app.api.dialogs.load_api_key", return_value="sk-test")
@patch("app.api.dialogs.ai_service.complete", new_callable=AsyncMock)
def test_athena_chat_creates_trace_for_real_model_call(mock_complete, mock_key, client):
    project_id = client.post("/api/v1/projects", json={"name": "Athena Trace"}).json()["id"]
    mock_complete.return_value.content = "当前世界模型还没有正式档案。"
    mock_complete.return_value.model = "deepseek-chat"
    mock_complete.return_value.prompt_tokens = 28
    mock_complete.return_value.completion_tokens = 9

    response = client.post(
        f"/api/v1/projects/{project_id}/athena/dialog/chat",
        json={"project_id": project_id, "input_type": "text", "text": "这个世界里有哪些规则？"},
    )

    assert response.status_code == 200
    trace_id = response.json()["trace_id"]
    assert trace_id
    trace = client.get(f"/api/v1/projects/{project_id}/model-call-traces/{trace_id}").json()
    assert trace["trace_type"] == "athena_chat"
    assert any(block["kind"] in ("setup", "world_fact", "world_entity") for block in trace["context_blocks"])


def test_athena_world_update_short_circuit_does_not_create_trace(client, db_session, monkeypatch):
    from app.models import GenreProfile, Project, ProjectProfileVersion

    monkeypatch.setattr(dialogs, "load_api_key", lambda: True)
    project = Project(name="Athena Trace Short Circuit", genre="悬疑")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    genre_profile = GenreProfile(
        canonical_id=f"trace-short-circuit-{project.id}",
        display_name="通用",
        contract_version="world.contract.v1",
    )
    db_session.add(genre_profile)
    db_session.commit()
    profile = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=genre_profile.id,
        version=1,
        contract_version="world.contract.v1",
        profile_payload={},
    )
    db_session.add(profile)
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/athena/dialog/chat",
        json={"project_id": project.id, "input_type": "text", "text": "请更新世界模型：林舟是守夜人"},
    )

    assert response.status_code == 200
    assert response.json()["trace_id"] is None
    assert db_session.query(AIModelCallTrace).count() == 0
```

- [ ] **Step 2: Run chat trace tests to verify failure**

Run:

```bash
cd backend && source .venv/bin/activate && pytest tests/test_model_call_traces.py::test_hermes_chat_creates_trace_and_returns_trace_id tests/test_model_call_traces.py::test_athena_chat_creates_trace_for_real_model_call -q
```

Expected: FAIL because `trace_id` is absent.

- [ ] **Step 3: Update dialog schemas**

Modify `backend/app/schemas/dialog.py`:

```python
class ChatMessageOut(BaseModel):
    id: str
    role: str
    message_type: str = "plain"
    content: str
    meta: dict | None = None
    action_result: dict | None = None
    trace_id: str | None = None
    created_at: datetime
```

Modify `ChatOut`:

```python
class ChatOut(BaseModel):
    message: str
    pending_action: PendingActionOut | None = None
    ui_hint: UiHintOut | None = None
    refresh_targets: list[str] = Field(default_factory=list)
    project_diagnosis: ProjectDiagnosisOut
    message_type: str | None = None
    meta: dict | None = None
    trace_id: str | None = None
```

- [ ] **Step 4: Return `trace_id` in message history**

In `backend/app/api/dialogs.py`, after loading `msgs`, fetch trace ids by response message id:

```python
from app.models import AIModelCallTrace
```

Inside `get_messages()`:

```python
    trace_by_response_id = {
        response_message_id: trace_id
        for trace_id, response_message_id in db.query(
            AIModelCallTrace.id,
            AIModelCallTrace.response_message_id,
        )
        .filter(AIModelCallTrace.response_message_id.in_([m.id for m in msgs]))
        .all()
        if response_message_id
    }
```

When building each message dict:

```python
            "id": message.id,
            "trace_id": trace_by_response_id.get(message.id),
```

- [ ] **Step 5: Trace `_free_chat_reply()`**

Change `_free_chat_reply()` to return both reply and trace id:

```python
async def _free_chat_reply(
    db: Session,
    dialog: Dialog,
    project: Project,
    diagnosis: ProjectDiagnosisOut,
    dialog_type: str = "hermes",
    request_message_id: str | None = None,
) -> tuple[str, str | None]:
```

Inside it:

```python
    from app.core.model_call_trace import create_trace, mark_trace_failed, mark_trace_success, now_ms
```

Replace model-call block with:

```python
    trace = None
    started = now_ms()
    model_name = project.ai_model or "deepseek-chat"
    try:
        payload = _build_chat_call_payload(db, dialog.id, project, diagnosis, dialog_type=dialog_type)
        trace = create_trace(
            db,
            project_id=project.id,
            trace_type="athena_chat" if dialog_type == "athena" else "hermes_chat",
            messages=payload["messages"],
            context_blocks=payload["context_blocks"],
            model=model_name,
            temperature=0.7,
            max_tokens=900,
            dialog_id=dialog.id,
            request_message_id=request_message_id,
            trace_metadata={"dialog_type": dialog_type},
        )
        result = await ai_service.complete(
            payload["messages"],
            temperature=0.7,
            max_tokens=900,
            model=model_name,
        )
        content = (result.content or "").strip()
        if content:
            mark_trace_success(
                db,
                trace,
                model=result.model,
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                latency_ms=now_ms() - started,
            )
            return content, trace.id
        mark_trace_failed(db, trace, error="模型返回了空内容", latency_ms=now_ms() - started)
    except Exception as exc:
        if trace:
            mark_trace_failed(db, trace, error=exc, latency_ms=now_ms() - started)
        return _chat_unavailable_reply(diagnosis, f"模型调用失败：{str(exc)}"), trace.id if trace else None

    return _chat_unavailable_reply(diagnosis, "模型返回了空内容"), trace.id if trace else None
```

After saving the assistant message in each caller, call `attach_trace_response()` so the trace points to the persisted assistant message without overwriting token usage.

- [ ] **Step 6: Wire Hermes chat caller**

In `chat()`, capture user message id:

```python
    request_message = None
    if (payload.input_type == "text" and payload.text) or (payload.input_type == "command" and effective_text):
        request_message = _save_message(db, dialog.id, "user", effective_text)
```

At the free-chat branch:

```python
    from app.core.model_call_trace import attach_trace_response

    reply, trace_id = await _free_chat_reply(db, dialog, project, diagnosis, dialog_type="hermes", request_message_id=request_message.id if request_message else None)
    assistant_message = _save_message(db, dialog.id, "assistant", reply)
    attach_trace_response(db, trace_id, assistant_message.id)
```

Return:

```python
        trace_id=trace_id,
```

- [ ] **Step 7: Wire Athena caller**

In `backend/app/api/athena.py`, short-circuit proposal responses return:

```python
trace_id=None,
```

For normal Athena chat:

```python
    from app.core.model_call_trace import attach_trace_response

    reply, trace_id = await _free_chat_reply(db, dialog, project, diagnosis, dialog_type="athena", request_message_id=request_message.id if request_message else None)
    assistant_message = _save_message(db, dialog.id, "assistant", reply)
    attach_trace_response(db, trace_id, assistant_message.id)
```

Return:

```python
        trace_id=trace_id,
```

- [ ] **Step 8: Run focused tests**

Run:

```bash
cd backend && source .venv/bin/activate && pytest tests/test_model_call_traces.py tests/test_athena_dialog.py -q
```

Expected: PASS.

- [ ] **Step 9: Commit Task 4**

Run:

```bash
git add backend/app/api/dialogs.py backend/app/api/athena.py backend/app/schemas/dialog.py backend/tests/test_model_call_traces.py backend/tests/test_athena_dialog.py
git commit -m "feat: trace chat model calls"
```

---

### Task 5: Trace Chapter Generation Calls

**Files:**
- Modify: `backend/app/api/chapters.py`
- Modify: `backend/app/schemas/chapter.py`
- Test: `backend/tests/test_chapters.py`
- Test: `backend/tests/test_model_call_traces.py`

- [ ] **Step 1: Add failing chapter trace test**

Append to `backend/tests/test_chapters.py`:

```python
@patch("app.api.chapters.load_api_key", return_value="sk-test")
@patch("app.api.chapters.ai_service.complete", new_callable=AsyncMock)
def test_generate_chapter_creates_model_call_trace(mock_complete, mock_key, client):
    project_id = client.post("/api/v1/projects", json={"name": "Trace Chapter"}).json()["id"]
    with patch("app.api.setups.load_api_key", return_value="sk-test"), \
         patch("app.api.setups.ai_service.complete", new_callable=AsyncMock) as setup_complete, \
         patch("app.api.setups.ai_service.parse_json") as parse_json:
        setup_complete.return_value.content = '{"world_building": {"background": "雾港"}, "characters": [{"name": "林舟"}], "core_concept": {}}'
        parse_json.return_value = {"world_building": {"background": "雾港"}, "characters": [{"name": "林舟"}], "core_concept": {}}
        client.post(f"/api/v1/projects/{project_id}/setup/generate")

    mock_complete.return_value.content = "第一章正文内容"
    mock_complete.return_value.model = "deepseek-chat"
    mock_complete.return_value.prompt_tokens = 123
    mock_complete.return_value.completion_tokens = 45

    response = client.post(f"/api/v1/projects/{project_id}/chapters/1/generate")

    assert response.status_code == 200
    trace_id = response.json()["last_generation_trace_id"]
    assert trace_id
    trace = client.get(f"/api/v1/projects/{project_id}/model-call-traces/{trace_id}").json()
    assert trace["trace_type"] == "chapter_generation"
    assert trace["chapter_index"] == 1
    assert trace["prompt_tokens"] == 123
    assert any(block["kind"] == "setup" for block in trace["context_blocks"])
    assert any(block["kind"] == "chapter_context" for block in trace["context_blocks"])
```

- [ ] **Step 2: Run chapter trace test to verify failure**

Run:

```bash
cd backend && source .venv/bin/activate && pytest tests/test_chapters.py::test_generate_chapter_creates_model_call_trace -q
```

Expected: FAIL because `last_generation_trace_id` is absent.

- [ ] **Step 3: Add `last_generation_trace_id` to chapter schema**

Modify `backend/app/schemas/chapter.py`:

```python
class ChapterOut(BaseModel):
    id: str
    project_id: str
    chapter_index: int
    title: str
    content: str
    word_count: int
    status: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    generation_time: int
    temperature: float
    last_generation_trace_id: str | None = None
    created_at: datetime
    updated_at: datetime
```

Because this field is not on `ChapterContent`, update chapter responses to inject it through a serializer helper in `backend/app/api/chapters.py` while keeping route `response_model=ChapterOut`:

```python
def _chapter_out(db: Session, chapter: ChapterContent) -> dict:
    from app.models import AIModelCallTrace
    trace = (
        db.query(AIModelCallTrace)
        .filter(
            AIModelCallTrace.project_id == chapter.project_id,
            AIModelCallTrace.chapter_id == chapter.id,
            AIModelCallTrace.trace_type == "chapter_generation",
        )
        .order_by(AIModelCallTrace.created_at.desc())
        .first()
    )
    data = ChapterOut.model_validate(chapter).model_dump()
    data["last_generation_trace_id"] = trace.id if trace else None
    return data
```

Keep `@router.post("/{chapter_index}/generate", response_model=ChapterOut)` and `@router.get("/{chapter_index}", response_model=ChapterOut)`. Return the computed dict:

```python
    return _chapter_out(db, chapter)
```

- [ ] **Step 4: Build structured chapter payload**

In `backend/app/api/chapters.py`, import:

```python
from app.core.model_call_trace import build_context_block
```

Add helper:

```python
def _build_chapter_call_payload(
    db: Session,
    project: Project,
    setup: Setup,
    chapter_index: int,
    extra_feedback: str,
) -> dict:
    context = _build_chapter_context(db, project.id, chapter_index, setup)
    blocks = [
        build_context_block(
            key="setup_world_building",
            title="Setup 世界观",
            kind="setup",
            content=json.dumps(setup.world_building, ensure_ascii=False),
            sources=[{"source_type": "Setup", "source_id": setup.id, "label": "Setup.world_building"}],
        ),
        build_context_block(
            key="setup_characters",
            title="Setup 角色",
            kind="setup",
            content=json.dumps(setup.characters, ensure_ascii=False),
            sources=[{"source_type": "Setup", "source_id": setup.id, "label": "Setup.characters"}],
        ),
        build_context_block(
            key="chapter_context",
            title="章节上下文",
            kind="chapter_context",
            content=context,
            sources=[{"source_type": "Project", "source_id": project.id, "label": f"第{chapter_index}章上下文", "chapter_index": chapter_index}],
        ),
    ]
    pm = PromptManager()
    prompt = pm.load(
        "generate_chapter",
        {
            "world_building": json.dumps(setup.world_building, ensure_ascii=False),
            "characters": json.dumps(setup.characters, ensure_ascii=False),
            "core_concept": json.dumps(setup.core_concept, ensure_ascii=False),
            "language": project.language,
        },
    )
    blocks.append(build_context_block(
        key="generate_chapter_template",
        title="章节生成提示词模板",
        kind="prompt_template",
        content=prompt,
        sources=[{"source_type": "PromptTemplate", "source_id": "generate_chapter", "label": "generate_chapter.txt"}],
    ))
    prompt = f"{prompt}\n\n【章节上下文】\n{context}"
    if extra_feedback:
        prompt = f"{prompt}\n\n【用户修订反馈】\n{extra_feedback}"
        blocks.append(build_context_block(
            key="revision_feedback",
            title="用户修订反馈",
            kind="revision_feedback",
            content=extra_feedback,
            sources=[{"source_type": "UserInput", "source_id": None, "label": "修订反馈"}],
        ))
        word_range = _extract_word_range(extra_feedback)
        if word_range:
            length_text = f"正文长度控制在{word_range[0]}-{word_range[1]}字，不要为了解释设定而扩写，优先保证剧情推进和章节钩子。"
            prompt = f"{prompt}\n\n【长度约束】\n{length_text}"
            blocks.append(build_context_block(
                key="length_constraint",
                title="长度约束",
                kind="system_instruction",
                content=length_text,
                sources=[{"source_type": "UserInput", "source_id": None, "label": "字数约束"}],
            ))
    prompt = prompt_optimizer.optimize(prompt, project.style_config)
    if project.style_config:
        blocks.append(build_context_block(
            key="style_config",
            title="风格偏好",
            kind="style_rule",
            content=json.dumps(project.style_config, ensure_ascii=False),
            sources=[{"source_type": "Project", "source_id": project.id, "label": "style_config"}],
        ))
    from app.core.few_shot_library import FewShotExampleLibrary
    fsl = FewShotExampleLibrary()
    examples = fsl.select_examples("chapter", project.genre)
    if examples:
        few_shot_text = fsl.format_for_prompt(examples)
        prompt += "\n\n" + few_shot_text
        blocks.append(build_context_block(
            key="few_shot_examples",
            title="Few-shot 示例",
            kind="few_shot",
            content=few_shot_text,
            sources=[{"source_type": "FewShotExample", "source_id": str(item.get("id", "")), "label": str(item.get("title", "示例"))} for item in examples],
        ))
    return {
        "messages": [{"role": "user", "content": prompt}],
        "context_blocks": blocks,
        "max_tokens": _chapter_max_tokens(extra_feedback),
    }
```

- [ ] **Step 5: Record trace around chapter model call**

In `create_or_replace_chapter()` replace direct prompt construction with:

```python
    payload = _build_chapter_call_payload(db, project, setup, chapter_index, extra_feedback)
    from app.core.model_call_trace import create_trace, mark_trace_failed, mark_trace_success, now_ms

    trace = create_trace(
        db,
        project_id=project_id,
        trace_type="chapter_generation",
        messages=payload["messages"],
        context_blocks=payload["context_blocks"],
        model=project.ai_model or "deepseek-chat",
        temperature=0.7,
        max_tokens=payload["max_tokens"],
        chapter_index=chapter_index,
        trace_metadata={"chapter_index": chapter_index},
    )
    started = now_ms()
    try:
        result = await ai_service.complete(
            payload["messages"],
            temperature=0.7,
            max_tokens=payload["max_tokens"],
            model=project.ai_model or "deepseek-chat",
        )
    except Exception as exc:
        mark_trace_failed(db, trace, error=exc, latency_ms=now_ms() - started)
        raise
    elapsed = now_ms() - started
```

After `db.refresh(chapter)`, call:

```python
    mark_trace_success(
        db,
        trace,
        model=result.model,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        latency_ms=elapsed,
        chapter_id=chapter.id,
    )
```

Make the route return `_chapter_out(db, chapter)`.

- [ ] **Step 6: Run focused chapter tests**

Run:

```bash
cd backend && source .venv/bin/activate && pytest tests/test_chapters.py tests/test_model_call_traces.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit Task 5**

Run:

```bash
git add backend/app/api/chapters.py backend/app/schemas/chapter.py backend/tests/test_chapters.py backend/tests/test_model_call_traces.py
git commit -m "feat: trace chapter generation calls"
```

---

### Task 6: Frontend Trace Types, API, Store, and Drawer Components

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/api/client.ts`
- Create: `frontend/src/stores/modelTraces.ts`
- Create: `frontend/src/components/modelTrace/ModelTraceDrawer.vue`
- Create: `frontend/src/components/modelTrace/TraceSummary.vue`
- Create: `frontend/src/components/modelTrace/ContextBlockList.vue`
- Create: `frontend/src/components/modelTrace/ContextSourceList.vue`
- Create: `frontend/src/components/modelTrace/RawMessagesViewer.vue`
- Test: `frontend/src/stores/modelTraces.test.ts`
- Test: `frontend/src/components/modelTrace/ModelTraceDrawer.test.ts`

- [ ] **Step 1: Add failing store test**

Create `frontend/src/stores/modelTraces.test.ts`:

```ts
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useModelTracesStore } from './modelTraces'
import { api } from '../api/client'

vi.mock('../api/client', () => ({
  api: {
    getModelCallTrace: vi.fn(),
    listModelCallTraces: vi.fn(),
  },
}))

describe('model trace store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('opens a trace drawer after loading detail', async () => {
    vi.mocked(api.getModelCallTrace).mockResolvedValue({
      id: 'trace-1',
      project_id: 'project-1',
      trace_type: 'hermes_chat',
      status: 'success',
      model: 'deepseek-chat',
      temperature: '0.7',
      max_tokens: 900,
      prompt_tokens: 10,
      completion_tokens: 5,
      latency_ms: 1200,
      error_message: '',
      dialog_id: 'dialog-1',
      request_message_id: 'msg-user',
      response_message_id: 'msg-ai',
      chapter_id: null,
      chapter_index: null,
      messages: [{ role: 'user', content: '你好' }],
      context_blocks: [],
      trace_metadata: {},
      created_at: '2026-04-28T10:00:00Z',
    })
    const store = useModelTracesStore()

    await store.openTrace('project-1', 'trace-1')

    expect(store.open).toBe(true)
    expect(store.current?.id).toBe('trace-1')
    expect(api.getModelCallTrace).toHaveBeenCalledWith('project-1', 'trace-1')
  })
})
```

- [ ] **Step 2: Add types and API methods**

Modify `frontend/src/api/types.ts`:

```ts
export interface TraceSource {
  source_type: string
  source_id?: string | null
  label: string
  chapter_index?: number | null
}

export interface ModelTraceContextBlock {
  key: string
  title: string
  kind: string
  content: string
  token_estimate: number
  char_count: number
  original_char_count?: number | null
  truncated: boolean
  sources: TraceSource[]
}

export interface ModelCallTraceListItem {
  id: string
  project_id: string
  trace_type: 'hermes_chat' | 'athena_chat' | 'chapter_generation' | string
  status: 'running' | 'success' | 'failed' | string
  model: string
  prompt_tokens: number
  completion_tokens: number
  latency_ms: number
  dialog_id?: string | null
  request_message_id?: string | null
  response_message_id?: string | null
  chapter_id?: string | null
  chapter_index?: number | null
  created_at: string
}

export interface ModelCallTraceDetail extends ModelCallTraceListItem {
  temperature: string
  max_tokens: number
  error_message: string
  messages: Array<{ role: string; content: string; truncated?: boolean; original_char_count?: number }>
  context_blocks: ModelTraceContextBlock[]
  trace_metadata: Record<string, unknown>
}

export interface PaginatedModelCallTraces {
  total: number
  items: ModelCallTraceListItem[]
}
```

Extend existing types:

```ts
export interface ChatResponse {
  ...
  trace_id?: string | null
}

export interface ChatHistoryMessage {
  id: string
  ...
  trace_id?: string | null
}

export interface ChapterContent {
  ...
  last_generation_trace_id?: string | null
}
```

Modify `frontend/src/api/client.ts` imports and methods:

```ts
  ModelCallTraceDetail,
  PaginatedModelCallTraces,
```

```ts
  listModelCallTraces: (id: string, params?: { trace_type?: string; chapter_index?: number; dialog_id?: string; limit?: number; offset?: number }) => {
    const query = new URLSearchParams()
    if (params?.trace_type) query.set('trace_type', params.trace_type)
    if (params?.chapter_index !== undefined) query.set('chapter_index', String(params.chapter_index))
    if (params?.dialog_id) query.set('dialog_id', params.dialog_id)
    if (params?.limit !== undefined) query.set('limit', String(params.limit))
    if (params?.offset !== undefined) query.set('offset', String(params.offset))
    const qs = query.toString()
    return request<PaginatedModelCallTraces>(`/projects/${id}/model-call-traces${qs ? `?${qs}` : ''}`)
  },
  getModelCallTrace: (id: string, traceId: string) =>
    request<ModelCallTraceDetail>(`/projects/${id}/model-call-traces/${traceId}`),
```

- [ ] **Step 3: Add store**

Create `frontend/src/stores/modelTraces.ts`:

```ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api/client'
import type { ModelCallTraceDetail } from '../api/types'

export const useModelTracesStore = defineStore('modelTraces', () => {
  const open = ref(false)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const current = ref<ModelCallTraceDetail | null>(null)

  async function openTrace(projectId: string, traceId: string) {
    loading.value = true
    error.value = null
    open.value = true
    try {
      current.value = await api.getModelCallTrace(projectId, traceId)
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err)
      current.value = null
    } finally {
      loading.value = false
    }
  }

  function close() {
    open.value = false
  }

  return { open, loading, error, current, openTrace, close }
})
```

- [ ] **Step 4: Add drawer components**

Create `frontend/src/components/modelTrace/TraceSummary.vue`:

```vue
<script setup lang="ts">
import type { ModelCallTraceDetail } from '../../api/types'
defineProps<{ trace: ModelCallTraceDetail }>()
</script>

<template>
  <dl class="trace-summary">
    <div><dt>类型</dt><dd>{{ trace.trace_type }}</dd></div>
    <div><dt>状态</dt><dd>{{ trace.status }}</dd></div>
    <div><dt>模型</dt><dd>{{ trace.model || 'unknown' }}</dd></div>
    <div><dt>Token</dt><dd>{{ trace.prompt_tokens }} / {{ trace.completion_tokens }}</dd></div>
    <div><dt>耗时</dt><dd>{{ trace.latency_ms }}ms</dd></div>
  </dl>
</template>
```

Create `frontend/src/components/modelTrace/ContextSourceList.vue`:

```vue
<script setup lang="ts">
import type { TraceSource } from '../../api/types'
defineProps<{ sources: TraceSource[] }>()
</script>

<template>
  <ul v-if="sources.length" class="trace-sources">
    <li v-for="(source, index) in sources" :key="`${source.source_type}-${source.source_id || index}`">
      <span>{{ source.source_type }}</span>
      <span v-if="source.label"> · {{ source.label }}</span>
      <span v-if="source.chapter_index"> · 第{{ source.chapter_index }}章</span>
    </li>
  </ul>
</template>
```

Create `frontend/src/components/modelTrace/ContextBlockList.vue`:

```vue
<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ModelTraceContextBlock } from '../../api/types'
import ContextSourceList from './ContextSourceList.vue'

const props = defineProps<{ blocks: ModelTraceContextBlock[] }>()
const query = ref('')
const filteredBlocks = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return props.blocks
  return props.blocks.filter((block) =>
    `${block.title} ${block.kind} ${block.content}`.toLowerCase().includes(q),
  )
})
</script>

<template>
  <section class="context-blocks">
    <input v-model="query" class="context-blocks__search" placeholder="搜索上下文" />
    <details v-for="block in filteredBlocks" :key="block.key" class="context-block" open>
      <summary>
        <strong>{{ block.title }}</strong>
        <span>{{ block.kind }} · {{ block.token_estimate }} tokens</span>
      </summary>
      <pre>{{ block.content }}</pre>
      <p v-if="block.truncated" class="context-block__hint">内容已截断，原始长度 {{ block.original_char_count }} 字符。</p>
      <ContextSourceList :sources="block.sources" />
    </details>
  </section>
</template>
```

Create `frontend/src/components/modelTrace/RawMessagesViewer.vue`:

```vue
<script setup lang="ts">
defineProps<{ messages: Array<{ role: string; content: string; truncated?: boolean; original_char_count?: number }> }>()
</script>

<template>
  <details class="raw-messages">
    <summary>Raw messages</summary>
    <article v-for="(message, index) in messages" :key="index" class="raw-message">
      <h4>{{ message.role }}</h4>
      <pre>{{ message.content }}</pre>
      <p v-if="message.truncated">已截断，原始长度 {{ message.original_char_count }} 字符。</p>
    </article>
  </details>
</template>
```

Create `frontend/src/components/modelTrace/ModelTraceDrawer.vue`:

```vue
<script setup lang="ts">
import { useModelTracesStore } from '../../stores/modelTraces'
import BaseModal from '../base/BaseModal.vue'
import ContextBlockList from './ContextBlockList.vue'
import RawMessagesViewer from './RawMessagesViewer.vue'
import TraceSummary from './TraceSummary.vue'

const store = useModelTracesStore()
</script>

<template>
  <BaseModal :open="store.open" title="调用上下文" width="760px" @close="store.close">
    <div v-if="store.loading">加载中...</div>
    <div v-else-if="store.error">{{ store.error }}</div>
    <div v-else-if="store.current" class="model-trace">
      <TraceSummary :trace="store.current" />
      <ContextBlockList :blocks="store.current.context_blocks" />
      <RawMessagesViewer :messages="store.current.messages" />
    </div>
  </BaseModal>
</template>
```

- [ ] **Step 5: Add minimal styling**

Add scoped styles in the components above:

```css
.trace-summary { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--space-2); margin-bottom: var(--space-4); }
.trace-summary div { padding: var(--space-2); border: 1px solid var(--color-border); border-radius: var(--radius-sm); }
.trace-summary dt { font-size: var(--text-xs); color: var(--color-text-tertiary); }
.trace-summary dd { font-size: var(--text-sm); color: var(--color-text-primary); }
.context-blocks { display: flex; flex-direction: column; gap: var(--space-3); }
.context-blocks__search { width: 100%; padding: var(--space-2); border: 1px solid var(--color-border); border-radius: var(--radius-sm); }
.context-block { border: 1px solid var(--color-border); border-radius: var(--radius-sm); padding: var(--space-3); }
.context-block summary { cursor: pointer; display: flex; justify-content: space-between; gap: var(--space-2); }
.context-block pre, .raw-message pre { white-space: pre-wrap; font-size: var(--text-xs); line-height: var(--leading-relaxed); overflow-x: auto; }
.trace-sources { margin-top: var(--space-2); color: var(--color-text-secondary); font-size: var(--text-xs); }
```

- [ ] **Step 6: Run frontend tests**

Run:

```bash
cd frontend && npm run test:unit -- modelTraces
```

Expected: PASS.

- [ ] **Step 7: Commit Task 6**

Run:

```bash
git add frontend/src/api/types.ts frontend/src/api/client.ts frontend/src/stores/modelTraces.ts frontend/src/stores/modelTraces.test.ts frontend/src/components/modelTrace
git commit -m "feat: add model trace drawer"
```

---

### Task 7: Hook Trace UI Into Hermes, Athena, and Chapters

**Files:**
- Modify: `frontend/src/stores/chat.ts`
- Modify: `frontend/src/stores/athena.ts`
- Modify: `frontend/src/components/chat/ChatMessage.vue`
- Modify: `frontend/src/components/chat/ChatMessageList.vue`
- Modify: `frontend/src/components/athena/AthenaChatPanel.vue`
- Modify: `frontend/src/views/HermesView.vue`
- Test: `frontend/src/components/chat/ChatMessage.test.ts`
- Test: `frontend/src/stores/chat.workspace.test.ts`

- [ ] **Step 1: Add failing chat button test**

Modify `frontend/src/components/chat/ChatMessage.test.ts`:

```ts
it('emits open-trace when a traced assistant message clicks context button', async () => {
  const wrapper = mount(ChatMessage, {
    props: {
      msg: {
        role: 'assistant',
        content: '回答内容',
        trace_id: 'trace-1',
      },
      isLatest: false,
      loading: false,
    },
  })

  await wrapper.find('[data-testid="open-trace"]').trigger('click')

  expect(wrapper.emitted('open-trace')?.[0]).toEqual(['trace-1'])
})
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
cd frontend && npm run test:unit -- ChatMessage
```

Expected: FAIL because the button and event are missing.

- [ ] **Step 3: Preserve trace ids in stores**

Modify `frontend/src/stores/chat.ts`:

```ts
export interface ChatMessage {
  id?: string
  role: 'user' | 'assistant' | 'system'
  content: string
  ...
  trace_id?: string | null
}
```

Update `toChatMessage()`:

```ts
    id: message.id,
    trace_id: message.trace_id || null,
```

When pushing assistant messages from `sendText()`, `sendButtonAction()`, and `sendCommand()`:

```ts
        trace_id: res.trace_id || null,
```

Modify `frontend/src/stores/athena.ts` in `sendChat()` so returned assistant messages preserve `trace_id`:

```ts
    messages.value.push({
      role: 'assistant',
      content: res.message,
      trace_id: res.trace_id || null,
      message_type: res.message_type || null,
      meta: res.meta || null,
    } as ChatHistoryMessage)
```

- [ ] **Step 4: Add chat message event**

Modify `frontend/src/components/chat/ChatMessage.vue` emits:

```ts
const emit = defineEmits<{
  decide: [decision: string, comment?: string]
  openTrace: [traceId: string]
}>()
```

Add function:

```ts
function openTrace() {
  if (props.msg.trace_id) emit('openTrace', props.msg.trace_id)
}
```

Add button in the assistant bubble after content:

```vue
      <button
        v-if="msg.trace_id && msg.role === 'assistant'"
        data-testid="open-trace"
        class="chat-msg__trace"
        type="button"
        @click="openTrace"
      >
        上下文
      </button>
```

Add scoped style:

```css
.chat-msg__trace { margin-top: var(--space-2); font-size: var(--text-xs); color: var(--color-brand); border: 1px solid var(--color-border); border-radius: var(--radius-sm); padding: var(--space-1) var(--space-2); background: var(--color-bg-white); }
.chat-msg__trace:hover { border-color: var(--color-brand); }
```

- [ ] **Step 5: Forward event from list**

Modify `frontend/src/components/chat/ChatMessageList.vue`:

```ts
const emit = defineEmits<{
  decide: [decision: string, comment?: string]
  openTrace: [traceId: string]
}>()
```

Template:

```vue
      @open-trace="(traceId) => emit('openTrace', traceId)"
```

- [ ] **Step 6: Mount drawer in Hermes**

Modify `frontend/src/views/HermesView.vue` imports:

```ts
import ModelTraceDrawer from '../components/modelTrace/ModelTraceDrawer.vue'
import { useModelTracesStore } from '../stores/modelTraces'
```

Add store:

```ts
const modelTraces = useModelTracesStore()
```

Add handler:

```ts
function openTrace(traceId: string) {
  void modelTraces.openTrace(pid.value, traceId)
}
```

Update `ChatMessageList`:

```vue
        @open-trace="openTrace"
```

Mount drawer near modals:

```vue
    <ModelTraceDrawer />
```

- [ ] **Step 7: Mount drawer in Athena chat**

Modify `frontend/src/components/athena/AthenaChatPanel.vue`:

```ts
import ModelTraceDrawer from '../modelTrace/ModelTraceDrawer.vue'
import { useModelTracesStore } from '../../stores/modelTraces'

const modelTraces = useModelTracesStore()

function openTrace(traceId: string) {
  void modelTraces.openTrace(props.projectId, traceId)
}
```

Preserve `trace_id` in mapped messages:

```ts
    trace_id: m.trace_id || null,
```

Update `ChatMessageList`:

```vue
          @open-trace="openTrace"
```

Mount:

```vue
        <ModelTraceDrawer />
```

- [ ] **Step 8: Add chapter generation context entry**

In `frontend/src/views/HermesView.vue`, add computed:

```ts
const selectedChapterTraceId = computed(() => project.chapter?.last_generation_trace_id || null)
```

Add handler:

```ts
function openSelectedChapterTrace() {
  if (!selectedChapterTraceId.value) return
  void modelTraces.openTrace(pid.value, selectedChapterTraceId.value)
}
```

Add a compact button near the content panel trigger area. If no dedicated chapter detail component exists in Hermes main view, place it in the subnav below `ProjectDashboard`:

```vue
        <button
          v-if="selectedChapterTraceId"
          class="hermes-subnav__trace"
          type="button"
          @click="openSelectedChapterTrace"
        >
          生成上下文
        </button>
```

Add style:

```css
.hermes-subnav__trace { width: calc(100% - var(--space-4)); margin: var(--space-2); padding: var(--space-2); border: 1px solid var(--color-border); border-radius: var(--radius-sm); color: var(--color-brand); background: var(--color-bg-white); font-size: var(--text-sm); }
.hermes-subnav__trace:hover { border-color: var(--color-brand); }
```

- [ ] **Step 9: Run frontend focused tests**

Run:

```bash
cd frontend && npm run test:unit -- ChatMessage modelTraces
```

Expected: PASS.

- [ ] **Step 10: Commit Task 7**

Run:

```bash
git add frontend/src/stores/chat.ts frontend/src/stores/athena.ts frontend/src/components/chat/ChatMessage.vue frontend/src/components/chat/ChatMessageList.vue frontend/src/components/athena/AthenaChatPanel.vue frontend/src/views/HermesView.vue frontend/src/components/chat/ChatMessage.test.ts
git commit -m "feat: surface model call traces in ui"
```

---

### Task 8: Full Verification and Browser Check

**Files:**
- No source files unless verification finds a defect.

- [ ] **Step 1: Run backend migration on local DB**

Run:

```bash
cd backend && source .venv/bin/activate && alembic upgrade head
```

Expected: migration reaches `20260428_add_ai_model_call_traces`.

- [ ] **Step 2: Run backend tests**

Run:

```bash
cd backend && source .venv/bin/activate && pytest -q
```

Expected: all tests pass.

- [ ] **Step 3: Run frontend tests**

Run:

```bash
cd frontend && npm run test:unit
```

Expected: all tests pass.

- [ ] **Step 4: Run frontend build**

Run:

```bash
cd frontend && npm run build
```

Expected: build completes and writes `backend/static/`.

- [ ] **Step 5: Manual API smoke with mocked-safe expectations**

Use the already running backend/frontend or start them:

```bash
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev -- --host 0.0.0.0
```

Then use a temporary project:

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/projects \
  -H 'Content-Type: application/json' \
  -d '{"name":"Trace Smoke","genre":"悬疑"}'
```

Expected: response includes project id.

- [ ] **Step 6: Browser check with agent-browser**

Run:

```bash
agent-browser --help
```

Use the installed command syntax to:

- Open `http://127.0.0.1:5173`.
- Enter a project.
- Send one Hermes message.
- Open the “上下文” button on the assistant reply.
- Confirm drawer shows summary, blocks, and raw messages.
- Enter Athena chat and repeat.
- Generate or open a generated chapter and confirm “生成上下文” opens the chapter trace.

Expected: no console errors and no visibly broken layout.

- [ ] **Step 7: Commit verification fixes**

If verification required code fixes, commit them:

```bash
git status --short
git add <changed files>
git commit -m "fix: stabilize model call trace flow"
```

If verification required no code fixes, do not create an empty commit.
