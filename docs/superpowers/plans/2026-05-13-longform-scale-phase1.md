# Longform Scale Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first scalable foundation for thousand-chapter projects: authoritative word-count reconciliation, deterministic layered memory summaries, future-chapter-safe context packages, and a 100-chapter pressure test.

**Architecture:** Keep `Project` as the long-form work container and add a small `LongformMemory` table for chapter/arc/volume/global summaries. Rebuild memory deterministically from existing chapters and outline data first, then expose diagnostics and context APIs under Athena without changing the generation pipeline yet.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite/Postgres-compatible models, pytest, existing Athena retrieval/world-model services.

---

## File Structure

- Create `backend/app/models/longform_memory.py`: SQLAlchemy model for chapter, arc, volume, and global memory rows.
- Modify `backend/app/models/__init__.py`: export `LongformMemory`.
- Create `backend/alembic/versions/20260513_add_longform_memories.py`: migration for persistent deployments.
- Create `backend/app/core/project_stats.py`: authoritative project word-count reconciliation from `ChapterContent`.
- Modify `backend/app/api/projects.py`: return reconciled `current_word_count` for get/list/update flows and delete longform memory with the project.
- Create `backend/app/core/longform_memory.py`: deterministic rebuild, diagnostics, and context package assembly.
- Create `backend/app/schemas/longform_memory.py`: response schemas for rebuild, diagnostics, and context package.
- Create `backend/app/api/athena_longform.py`: Athena endpoints for memory rebuild, diagnostics, and context package.
- Modify `backend/app/api/athena.py`: include `athena_longform.router`.
- Create `backend/tests/test_longform_scale.py`: Phase 1 regression and scale tests.

## Success Criteria

- `GET /api/v1/projects/{project_id}` returns `current_word_count` equal to generated chapter word-count sum, even if the stored project field is stale.
- Rebuilding memory for a 100-chapter project creates 100 chapter rows, 5 arc rows, 1 volume row, and 1 global row with deterministic summaries.
- Chapter context for chapter N includes global/current-volume/current-arc/recent-history sections but excludes chapters after N.
- Athena retrieval remains future-chapter-safe through `max_chapter_index`.
- Verification commands pass:
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py -v`
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests -v`

## Tasks

### Task 1: Project Word-Count Reconciliation

**Files:**
- Create: `backend/app/core/project_stats.py`
- Modify: `backend/app/api/projects.py`
- Test: `backend/tests/test_longform_scale.py`

- [ ] **Step 1: Write failing test**

Add this test to `backend/tests/test_longform_scale.py`:

```python
from app.models import ChapterContent, Project


def test_get_project_reconciles_current_word_count_from_chapters(client, db_session):
    project = Project(name="Longform Stats", current_word_count=1)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    db_session.add_all(
        [
            ChapterContent(project_id=project.id, chapter_index=1, title="一", content="正文一", word_count=1200, status="generated"),
            ChapterContent(project_id=project.id, chapter_index=2, title="二", content="正文二", word_count=1300, status="generated"),
        ]
    )
    db_session.commit()

    response = client.get(f"/api/v1/projects/{project.id}")

    assert response.status_code == 200
    assert response.json()["current_word_count"] == 2500
    db_session.refresh(project)
    assert project.current_word_count == 2500
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_get_project_reconciles_current_word_count_from_chapters -v
```

Expected: FAIL because `backend/tests/test_longform_scale.py` or reconciliation does not exist yet.

- [ ] **Step 3: Implement project stats service**

Create `backend/app/core/project_stats.py`:

```python
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import ChapterContent, Project


def chapter_word_count_sum(db: Session, project_id: str) -> int:
    total = (
        db.query(func.coalesce(func.sum(ChapterContent.word_count), 0))
        .filter(ChapterContent.project_id == project_id)
        .scalar()
    )
    return int(total or 0)


def reconcile_project_word_count(db: Session, project: Project, *, commit: bool = True) -> Project:
    total = chapter_word_count_sum(db, project.id)
    if (project.current_word_count or 0) != total:
        project.current_word_count = total
        if commit:
            db.commit()
            db.refresh(project)
        else:
            db.flush()
    return project
```

- [ ] **Step 4: Use reconciliation in project API**

In `backend/app/api/projects.py`, import `reconcile_project_word_count` and call it before returning project payloads:

```python
from app.core.project_stats import reconcile_project_word_count
```

For `list_projects`, reconcile each project with `commit=False`, then commit once if any value changed:

```python
projects = db.query(Project).order_by(Project.created_at.desc()).all()
changed = False
for project in projects:
    before = project.current_word_count or 0
    reconcile_project_word_count(db, project, commit=False)
    changed = changed or (project.current_word_count or 0) != before
if changed:
    db.commit()
return projects
```

For `get_project` and `update_project`, call:

```python
return reconcile_project_word_count(db, project)
```

- [ ] **Step 5: Run test to verify it passes**

Run:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_get_project_reconciles_current_word_count_from_chapters -v
```

Expected: PASS.

### Task 2: Longform Memory Model and Migration

**Files:**
- Create: `backend/app/models/longform_memory.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/20260513_add_longform_memories.py`
- Modify: `backend/app/api/projects.py`
- Test: `backend/tests/test_longform_scale.py`

- [ ] **Step 1: Write model shape test**

Append:

```python
from app.models import LongformMemory


def test_longform_memory_model_supports_scope_layers(db_session):
    project = Project(name="Memory Model")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    memory = LongformMemory(
        project_id=project.id,
        memory_type="arc",
        scope_key="arc:1-20",
        start_chapter_index=1,
        end_chapter_index=20,
        title="第一剧情弧",
        summary="主角进入核心冲突。",
        status="current",
        memory_metadata={"chapter_count": 20},
    )
    db_session.add(memory)
    db_session.commit()

    row = db_session.query(LongformMemory).filter_by(project_id=project.id, scope_key="arc:1-20").one()
    assert row.memory_type == "arc"
    assert row.memory_metadata["chapter_count"] == 20
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_memory_model_supports_scope_layers -v
```

Expected: FAIL because `LongformMemory` is not defined.

- [ ] **Step 3: Add model**

Create `backend/app/models/longform_memory.py`:

```python
import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint

from app.db import Base


class LongformMemory(Base):
    __tablename__ = "longform_memories"
    __table_args__ = (
        UniqueConstraint("project_id", "memory_type", "scope_key", name="uq_longform_memories_scope"),
        Index("ix_longform_memories_project_type", "project_id", "memory_type"),
        Index("ix_longform_memories_project_range", "project_id", "start_chapter_index", "end_chapter_index"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    memory_type = Column(String, nullable=False)
    scope_key = Column(String, nullable=False)
    start_chapter_index = Column(Integer, nullable=True)
    end_chapter_index = Column(Integer, nullable=True)
    title = Column(String, default="")
    summary = Column(Text, default="")
    status = Column(String, default="current")
    memory_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
```

Export from `backend/app/models/__init__.py`:

```python
from .longform_memory import LongformMemory
```

- [ ] **Step 4: Add migration**

Create `backend/alembic/versions/20260513_add_longform_memories.py` with a single-table upgrade and downgrade for `longform_memories`, including the unique constraint and two indexes from the model.

- [ ] **Step 5: Add project delete cleanup**

Add `LongformMemory` to `PROJECT_SCOPED_MODELS` in `backend/app/api/projects.py`.

- [ ] **Step 6: Run model test**

Run:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_memory_model_supports_scope_layers -v
```

Expected: PASS.

### Task 3: Deterministic Memory Rebuild and Diagnostics

**Files:**
- Create: `backend/app/core/longform_memory.py`
- Create: `backend/app/schemas/longform_memory.py`
- Create: `backend/app/api/athena_longform.py`
- Modify: `backend/app/api/athena.py`
- Modify: `backend/app/schemas/__init__.py`
- Test: `backend/tests/test_longform_scale.py`

- [ ] **Step 1: Write failing rebuild test**

Append:

```python
def test_rebuild_longform_memory_creates_chapter_arc_volume_and_global_layers(client, db_session):
    project = Project(name="Hundred Chapter Memory")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    for index in range(1, 101):
        db_session.add(
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章",
                content=f"第{index}章正文。主角推进第{(index - 1) // 20 + 1}段剧情。" * 8,
                word_count=1000 + index,
                status="generated",
            )
        )
    db_session.commit()

    response = client.post(f"/api/v1/projects/{project.id}/athena/longform/memory/rebuild")
    diagnostics = client.get(f"/api/v1/projects/{project.id}/athena/longform/memory/diagnostics")

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["counts_by_type"] == {"chapter": 100, "arc": 5, "volume": 1, "global": 1}
    assert diagnostics.status_code == 200
    assert diagnostics.json()["counts_by_type"]["chapter"] == 100
    assert diagnostics.json()["current_word_count"] == sum(1000 + index for index in range(1, 101))
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_rebuild_longform_memory_creates_chapter_arc_volume_and_global_layers -v
```

Expected: FAIL because endpoint/service does not exist.

- [ ] **Step 3: Implement rebuild service**

`backend/app/core/longform_memory.py` should:

- require the project exists;
- delete existing `LongformMemory` rows for the project;
- create one chapter memory per `ChapterContent`;
- group arcs by `arc_size=20`;
- group volumes by `volume_size=100`;
- create one global memory row;
- call `reconcile_project_word_count`;
- return `counts_by_type`.

- [ ] **Step 4: Implement schemas and API**

Expose:

```python
POST /api/v1/projects/{project_id}/athena/longform/memory/rebuild
GET /api/v1/projects/{project_id}/athena/longform/memory/diagnostics
```

Both endpoints should return plain, schema-validated JSON and no model API calls.

- [ ] **Step 5: Run rebuild test**

Run:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_rebuild_longform_memory_creates_chapter_arc_volume_and_global_layers -v
```

Expected: PASS.

### Task 4: Future-Chapter-Safe Context Package

**Files:**
- Modify: `backend/app/core/longform_memory.py`
- Modify: `backend/app/api/athena_longform.py`
- Test: `backend/tests/test_longform_scale.py`

- [ ] **Step 1: Write failing future-isolation test**

Append:

```python
def test_longform_context_for_chapter_excludes_future_chapters(client, db_session):
    project = Project(name="Future Boundary")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    for index in range(1, 8):
        db_session.add(
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章",
                content=f"第{index}章正文。{'未来秘密只在第7章揭露。' if index == 7 else '普通线索。'}",
                word_count=1000,
                status="generated",
            )
        )
    db_session.commit()
    client.post(f"/api/v1/projects/{project.id}/athena/longform/memory/rebuild")

    response = client.get(f"/api/v1/projects/{project.id}/athena/longform/context/chapters/5")

    assert response.status_code == 200
    payload = response.json()
    assert payload["chapter_index"] == 5
    assert "第4章" in payload["prompt_context"]
    assert "第7章" not in payload["prompt_context"]
    assert "未来秘密" not in payload["prompt_context"]
    assert all(
        item.get("end_chapter_index") is None or item["end_chapter_index"] <= 5
        for section in payload["sections"]
        for item in section["items"]
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_context_for_chapter_excludes_future_chapters -v
```

Expected: FAIL until context endpoint exists.

- [ ] **Step 3: Implement context package**

Context for chapter N should include:

- global memory row;
- volume row where `start_chapter_index <= N <= end_chapter_index`;
- arc row where `start_chapter_index <= N <= end_chapter_index`;
- recent chapter memory rows with `chapter_index < N`, ordered ascending, limited to the latest 3;
- retrieval evidence from `build_chapter_retrieval_context`, which already uses `max_chapter_index=chapter_index - 1`.

- [ ] **Step 4: Run future-isolation test**

Run:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_context_for_chapter_excludes_future_chapters -v
```

Expected: PASS.

### Task 5: Phase Verification and Commit

**Files:**
- All files changed in Tasks 1-4.

- [ ] **Step 1: Run focused Phase 1 tests**

Run:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py -v
```

Expected: all tests PASS.

- [ ] **Step 2: Run backend suite**

Run:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests -v
```

Expected: all tests PASS.

- [ ] **Step 3: Check diff hygiene**

Run:

```powershell
git diff --check
git status --short
```

Expected: no whitespace errors; only intended Phase 1 files changed.

- [ ] **Step 4: Commit Phase 1**

Run:

```powershell
git add backend\app backend\tests backend\alembic\versions docs\superpowers\plans\2026-05-13-longform-scale-phase1.md
git commit -m "feat: add longform scale memory foundation"
```

Expected: commit succeeds on `codex/longform-scale`.
