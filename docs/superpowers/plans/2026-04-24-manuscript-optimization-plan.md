# Manuscript 编辑器 + 自优化反馈闭环 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 Manuscript 正文编辑器、修订提交、Hermes 重新生成入口，以及 Athena 自优化展示的可测试闭环。

**Architecture:** 后端新增修订持久化模型、Pydantic schema、API 与 Alembic 迁移；前端新增 manuscript store/API 类型与三栏编辑器组件。重新生成先用同步 API 注入用户反馈，规则提取与偏好微调用小型服务封装，Athena 通过独立 optimization endpoint 展示学习结果。

**Tech Stack:** FastAPI + SQLAlchemy + Alembic + pytest；Vue 3 + TypeScript + Pinia + Vite/Vitest。

---

## File Map

- `backend/app/models/chapter_revision.py`：修订批次、批注、修正文档三张表。
- `backend/app/schemas/chapter_revision.py`：提交修订、读取修订、自优化展示的 API 契约。
- `backend/app/api/chapter_revisions.py`：修订提交、列表、详情、重新生成入口。
- `backend/app/core/revision_feedback.py`：把批注和修正格式化成生成 prompt 可注入文本。
- `backend/app/core/self_optimization.py`：从修订反馈生成 learned prompt rules，并微调 `Project.style_config`。
- `backend/alembic/versions/*_add_chapter_revisions.py`：创建三张表和索引。
- `backend/app/api/athena.py`：增加 optimization endpoint。
- `backend/tests/test_chapter_revisions.py`：后端修订 API 行为测试。
- `backend/tests/test_self_optimization.py`：规则提取与偏好微调测试。
- `frontend/src/api/types.ts`：新增 manuscript/revision/optimization 类型。
- `frontend/src/api/client.ts`：新增修订 API 调用。
- `frontend/src/stores/manuscript.ts`：章节正文、临时批注、临时修正、提交状态。
- `frontend/src/views/ManuscriptView.vue`：替换占位页为三栏编辑器容器。
- `frontend/src/components/manuscript/*.vue`：正文编辑区、批注气泡、摘要面板、提交确认框。
- `frontend/src/stores/athena.ts`、`frontend/src/views/AthenaView.vue`：加载并展示自优化数据。

---

## Phase 1: Revision Persistence API

### Task 1: Add revision models and migration

**Files:**
- Create: `backend/app/models/chapter_revision.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/20260424_add_chapter_revisions.py`
- Test: `backend/tests/test_chapter_revisions.py`

- [ ] **Step 1: Write failing model/API test**

```python
from app.models import ChapterRevision, RevisionAnnotation, RevisionCorrection


def test_revision_models_are_importable():
    assert ChapterRevision.__tablename__ == "chapter_revisions"
    assert RevisionAnnotation.__tablename__ == "revision_annotations"
    assert RevisionCorrection.__tablename__ == "revision_corrections"
```

Run: `cd backend && pytest tests/test_chapter_revisions.py::test_revision_models_are_importable -q`
Expected: FAIL with import error.

- [ ] **Step 2: Implement models**

Create `backend/app/models/chapter_revision.py` with UUID ids, project/chapter foreign keys, `revision_index`, `status`, timestamps, and child rows for annotations/corrections.

- [ ] **Step 3: Export models**

Add `ChapterRevision`, `RevisionAnnotation`, `RevisionCorrection` imports to `backend/app/models/__init__.py`.

- [ ] **Step 4: Add Alembic migration**

Create tables `chapter_revisions`, `revision_annotations`, `revision_corrections`; add indexes on `(project_id, chapter_index)` and `revision_id`.

- [ ] **Step 5: Verify model test**

Run: `cd backend && pytest tests/test_chapter_revisions.py::test_revision_models_are_importable -q`
Expected: PASS.

### Task 2: Submit and read revisions

**Files:**
- Create: `backend/app/schemas/chapter_revision.py`
- Create: `backend/app/api/chapter_revisions.py`
- Modify: `backend/app/schemas/__init__.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_chapter_revisions.py`

- [ ] **Step 1: Write failing submit test**

```python
def test_submit_revision_persists_annotations_and_corrections(client, sample_project_with_chapter):
    project_id = sample_project_with_chapter["project_id"]
    response = client.post(f"/api/v1/projects/{project_id}/revisions", json={
        "chapter_index": 1,
        "annotations": [{"paragraph_index": 0, "start_offset": 0, "end_offset": 2, "selected_text": "开头", "comment": "节奏太慢"}],
        "corrections": [{"paragraph_index": 0, "original_text": "寒风凛冽", "corrected_text": "夜风微凉"}],
    })
    assert response.status_code == 200
    data = response.json()
    assert data["revision_index"] == 1
    assert len(data["annotations"]) == 1
    assert len(data["corrections"]) == 1
```

Run: `cd backend && pytest tests/test_chapter_revisions.py::test_submit_revision_persists_annotations_and_corrections -q`
Expected: FAIL with missing fixture or 404 route; add fixture if missing.

- [ ] **Step 2: Add schemas**

Define `RevisionAnnotationIn/Out`, `RevisionCorrectionIn/Out`, `ChapterRevisionCreate`, `ChapterRevisionOut` with Pydantic field validation for non-negative offsets and non-empty feedback.

- [ ] **Step 3: Add router**

Implement `POST /api/v1/projects/{project_id}/revisions`, `GET /api/v1/projects/{project_id}/revisions`, `GET /api/v1/projects/{project_id}/revisions/{revision_id}`. Reject unknown project/chapter with 404; reject empty annotations+corrections with 400.

- [ ] **Step 4: Register router**

Import `chapter_revisions` in `backend/app/main.py` and include router.

- [ ] **Step 5: Verify submit/read tests**

Run: `cd backend && pytest tests/test_chapter_revisions.py -q`
Expected: PASS.

---

## Phase 2: Regeneration and Self-Optimization

### Task 3: Format revision feedback for prompts

**Files:**
- Create: `backend/app/core/revision_feedback.py`
- Test: `backend/tests/test_chapter_revisions.py`

- [ ] **Step 1: Write failing formatter test**

```python
def test_revision_feedback_formats_annotations_and_corrections():
    text = format_revision_feedback(
        annotations=[{"paragraph_index": 0, "selected_text": "开头", "comment": "节奏太慢"}],
        corrections=[{"paragraph_index": 1, "original_text": "寒风凛冽", "corrected_text": "夜风微凉"}],
    )
    assert "批注" in text
    assert "节奏太慢" in text
    assert "寒风凛冽 -> 夜风微凉" in text
```

Run: `cd backend && pytest tests/test_chapter_revisions.py::test_revision_feedback_formats_annotations_and_corrections -q`
Expected: FAIL with missing function.

- [ ] **Step 2: Implement formatter**

Return deterministic Chinese sections for annotations and corrections; keep it pure and side-effect free.

- [ ] **Step 3: Verify formatter test**

Run: `cd backend && pytest tests/test_chapter_revisions.py::test_revision_feedback_formats_annotations_and_corrections -q`
Expected: PASS.

### Task 4: Add revision-based regeneration endpoint

**Files:**
- Modify: `backend/app/api/chapter_revisions.py`
- Modify: `backend/app/api/chapters.py`
- Test: `backend/tests/test_chapter_revisions.py`

- [ ] **Step 1: Write failing endpoint test**

Test `POST /api/v1/projects/{project_id}/revisions/{revision_id}/regenerate` updates revision `status` to `completed` and returns a `ChapterOut`.

- [ ] **Step 2: Extract generation helper**

Move shared chapter generation internals from `generate_chapter` into a helper that accepts optional `extra_feedback`.

- [ ] **Step 3: Implement regenerate endpoint**

Load revision, format feedback, call helper, mark revision completed, return chapter.

- [ ] **Step 4: Verify endpoint test**

Run: `cd backend && pytest tests/test_chapter_revisions.py -q`
Expected: PASS.

### Task 5: Add self-optimization service

**Files:**
- Create: `backend/app/core/self_optimization.py`
- Modify: `backend/app/api/chapter_revisions.py`
- Test: `backend/tests/test_self_optimization.py`

- [ ] **Step 1: Write failing service test**

Assert repeated "节奏太慢" feedback creates a learned `PromptRule` and lowers `style_config.description_density` only within safe min/max bounds.

- [ ] **Step 2: Implement deterministic extractor**

Use simple keyword heuristics first: 节奏太慢/描写太多/套话/对话不足. Do not call LLM in tests.

- [ ] **Step 3: Call service after submit**

After revision persistence, run optimization synchronously for now; keep method isolated for future async queue.

- [ ] **Step 4: Verify service tests**

Run: `cd backend && pytest tests/test_self_optimization.py -q`
Expected: PASS.

### Task 6: Add Athena optimization endpoint

**Files:**
- Modify: `backend/app/api/athena.py`
- Modify: `backend/app/schemas/chapter_revision.py`
- Test: `backend/tests/test_self_optimization.py`

- [ ] **Step 1: Write failing endpoint test**

Test `GET /api/v1/projects/{project_id}/athena/optimization` returns `rules`, `style_config`, and `learning_logs`.

- [ ] **Step 2: Implement endpoint**

Read learned `PromptRule` rows ordered by `created_at desc`; derive learning logs from those rows; include current `Project.style_config`.

- [ ] **Step 3: Verify endpoint test**

Run: `cd backend && pytest tests/test_self_optimization.py -q`
Expected: PASS.

---

## Phase 3: Frontend Manuscript UI

### Task 7: Add API types and manuscript store

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/api/client.ts`
- Create: `frontend/src/stores/manuscript.ts`
- Test: `frontend/src/stores/manuscript.test.ts`

- [ ] **Step 1: Write failing store test**

Test adding annotation/correction, computing dirty state, and clearing local feedback after successful submit.

- [ ] **Step 2: Add API methods**

Add `submitRevision`, `listRevisions`, `getRevision`, `regenerateRevision`, `getAthenaOptimization`.

- [ ] **Step 3: Implement store**

State: `chapter`, `annotations`, `corrections`, `selectedChapterIndex`, `submitting`, `error`. Actions: load chapter, add/update/remove annotation, add/remove correction, submit.

- [ ] **Step 4: Verify store test**

Run: `cd frontend && npx vitest run src/stores/manuscript.test.ts`
Expected: PASS.

### Task 8: Build Manuscript editor components

**Files:**
- Create: `frontend/src/components/manuscript/ManuscriptEditor.vue`
- Create: `frontend/src/components/manuscript/AnnotationBubble.vue`
- Create: `frontend/src/components/manuscript/RevisionSummaryPanel.vue`
- Create: `frontend/src/components/manuscript/RevisionSubmitModal.vue`
- Modify: `frontend/src/views/ManuscriptView.vue`

- [ ] **Step 1: Replace placeholder with three-column editor**

Use existing `Teleport to="[data-subnav-content]"`, `ChapterList`, design tokens, and no inline hardcoded theme values except semantic highlight colors documented in spec.

- [ ] **Step 2: Implement annotation selection**

On text selection inside a paragraph, show bubble; save offsets relative to that paragraph.

- [ ] **Step 3: Implement correction detection**

On paragraph blur, compare original paragraph text and current text; store one correction per paragraph.

- [ ] **Step 4: Implement submit modal**

Show all annotations/corrections and explicit hint: “确认后将跳转回 Hermes”。

- [ ] **Step 5: Verify frontend build**

Run: `cd frontend && npx vue-tsc --noEmit && npm run build`
Expected: PASS.

### Task 9: Wire Hermes handoff

**Files:**
- Modify: `frontend/src/views/ManuscriptView.vue`
- Modify: `frontend/src/views/HermesView.vue`
- Modify: `frontend/src/stores/chat.ts` if needed

- [ ] **Step 1: Add navigation after submit**

After submit, route to `/projects/{id}/hermes?revision_id={revisionId}`.

- [ ] **Step 2: Add Hermes revision banner/action**

If query has `revision_id`, show a message/action to start regeneration from revision.

- [ ] **Step 3: Trigger regenerate API**

Call `regenerateRevision`, refresh project/chapter, and append visible chat feedback.

- [ ] **Step 4: Verify build**

Run: `cd frontend && npx vue-tsc --noEmit && npm run build`
Expected: PASS.

---

## Phase 4: Athena Optimization UI

### Task 10: Display optimization state

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/stores/athena.ts`
- Modify: `frontend/src/views/AthenaView.vue`
- Create: `frontend/src/components/athena/OptimizationPanel.vue`

- [ ] **Step 1: Add Athena store state**

Add `optimization`, `loadOptimization(projectId)`, reset on project switch.

- [ ] **Step 2: Add OptimizationPanel**

Render learned rules, current style config, and learning logs with empty states.

- [ ] **Step 3: Add Athena section/tab**

Add `optimization` to section list and lazy-load data when opened.

- [ ] **Step 4: Verify build**

Run: `cd frontend && npx vue-tsc --noEmit && npm run build`
Expected: PASS.

---

## Final Verification

- [ ] Run backend tests: `cd backend && pytest`
- [ ] Run frontend tests: `cd frontend && npx vitest run`
- [ ] Run frontend type/build: `cd frontend && npx vue-tsc --noEmit && npm run build`
- [ ] Manual smoke: generate/load chapter → Manuscript add annotation/correction → submit modal → Hermes regenerate → Athena optimization shows learned data.

## Known Risks

- `contenteditable` offset mapping is fragile with nested highlights; keep paragraph DOM flat and recalculate from text nodes.
- Revision regeneration currently synchronous; if latency becomes bad, move Task 4 endpoint to background task queue.
- Heuristic self-optimization is deliberately conservative; LLM extraction should be added behind a service boundary later, not inside the API route.
