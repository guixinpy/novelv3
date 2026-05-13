# Longform Scale Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade retrieval and context packaging so long-form chapter work uses query-aware, source-explained, future-safe evidence from chapters, world facts, and layered longform memory.

**Architecture:** Keep the existing retrieval tables and scoring pipeline. Add `LongformMemory` as another retrieval source, wrap retrieval hits with explanation metadata, and let Athena longform context endpoints accept an optional user query that is folded into the retrieval query without bypassing future-chapter isolation.

**Tech Stack:** FastAPI, SQLAlchemy, existing Athena retrieval service, existing longform memory service, pytest.

---

## File Structure

- Modify `backend/app/core/athena_retrieval.py`: index `LongformMemory`, build query-aware retrieval context, add per-hit explanation metadata.
- Modify `backend/app/core/longform_memory.py`: accept optional `user_query` and use query-aware retrieval context.
- Modify `backend/app/api/athena_longform.py`: expose `q` query parameter on longform context endpoint.
- Modify `backend/app/schemas/athena_retrieval.py`: allow source explanation fields in search items.
- Modify `backend/app/prompting/providers/dialog.py`: add a compact longform evidence-range block to both Athena and Hermes dialog payloads when longform memory exists.
- Modify `backend/tests/test_longform_scale.py`: add Phase 2 tests.

## Success Criteria

- Project reindex includes `longform_memory` documents after memory rebuild.
- Query-aware context for chapter N can retrieve relevant earlier longform memory/chapter evidence using an explicit user query.
- Each retrieval context item includes an explanation with source type, chapter range, score, and reason.
- Query-aware context still excludes future chapters and future memory ranges.
- Athena and Hermes dialog payloads include a longform evidence-range context block when longform memory exists.
- Verification commands pass:
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py -v`
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_athena_retrieval.py backend\tests\test_athena_dialog.py -v`
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests -v`

## Tasks

### Task 1: Index Longform Memory

**Files:**
- Modify: `backend/app/core/athena_retrieval.py`
- Test: `backend/tests/test_longform_scale.py`

- [ ] **Step 1: Write failing test**

Add a test that creates 40 chapters, rebuilds longform memory, reindexes retrieval, and expects `documents_by_source_type["longform_memory"]` to be greater than zero.

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_reindex_includes_longform_memory_sources -v
```

Expected: FAIL because current retrieval indexing only includes chapters and world facts.

- [ ] **Step 3: Implement source adapter**

Import `LongformMemory` in `backend/app/core/athena_retrieval.py`, include rows from `longform_memories` in `_project_sources`, and add `_longform_memory_source(memory)` with:

- `source_type="longform_memory"`
- `source_ref=f"memory:{memory.scope_key}"`
- `title=memory.title`
- `text=memory.summary`
- `chapter_index=memory.end_chapter_index`
- metadata with `memory_type`, `scope_key`, `start_chapter_index`, `end_chapter_index`.

- [ ] **Step 4: Run test**

Run the focused test again. Expected: PASS.

### Task 2: Query-Aware Retrieval Context

**Files:**
- Modify: `backend/app/core/athena_retrieval.py`
- Modify: `backend/app/core/longform_memory.py`
- Modify: `backend/app/api/athena_longform.py`
- Modify: `backend/app/schemas/athena_retrieval.py`
- Test: `backend/tests/test_longform_scale.py`

- [ ] **Step 1: Write failing test**

Add a test that creates an early “秘银钥匙” memory/chapter, later filler chapters, rebuilds memory, reindexes, then calls:

```http
GET /api/v1/projects/{project_id}/athena/longform/context/chapters/35?q=秘银钥匙
```

The test should assert:

- response contains a retrieval or query-aware retrieval section;
- at least one retrieval item mentions “秘银钥匙”;
- every retrieval item has `metadata.explanation.reason`;
- no retrieval item has `chapter_index > 34`;
- `prompt_context` includes “检索依据”.

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_query_aware_context_uses_user_query_and_explains_sources -v
```

Expected: FAIL because `q` is not accepted and explanations are not attached.

- [ ] **Step 3: Add query-aware builder**

Add `build_query_aware_retrieval_context(db, project_id, chapter_index, *, user_query=None, limit=6)` in `backend/app/core/athena_retrieval.py`.

It should:

- combine `_chapter_context_query(...)` and `user_query`;
- call `search_retrieval(..., max_chapter_index=chapter_index - 1)`;
- attach `metadata["explanation"]` to each item with `source_type`, `chapter_range`, `score`, and `reason`;
- return a section with key `query_aware_retrieval` and prompt heading `【检索依据】`.

- [ ] **Step 4: Wire longform endpoint**

Pass `q` from `backend/app/api/athena_longform.py` into `build_longform_context_package`, and pass `user_query` into the query-aware retrieval builder.

- [ ] **Step 5: Run focused test**

Run the focused test again. Expected: PASS.

### Task 3: Dialog Evidence Range Block

**Files:**
- Modify: `backend/app/prompting/providers/dialog.py`
- Test: `backend/tests/test_longform_scale.py`

- [ ] **Step 1: Write failing test**

Add a test that creates longform memory, opens both Athena and Hermes dialogs, builds both payloads, and asserts both contain a context block:

```python
block["kind"] == "longform_evidence_range"
```

The block content should include memory counts and current word count.

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_dialog_payloads_include_longform_evidence_range_block -v
```

Expected: FAIL because dialog payloads do not include this block.

- [ ] **Step 3: Implement block**

Add `build_longform_evidence_range_context_block(db, project)` in `backend/app/prompting/providers/dialog.py`.

It should use `get_longform_memory_diagnostics` and return `None` when `total_memories == 0`. When present, add it to both Athena and Hermes `context_blocks`; include it in `world_context` text for both dialog types.

- [ ] **Step 4: Run focused test**

Run the focused test again. Expected: PASS.

### Task 4: Verification and Commit

**Files:**
- All changed Phase 2 files.

- [ ] **Step 1: Run focused longform tests**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py -v
```

- [ ] **Step 2: Run related suites**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_athena_retrieval.py backend\tests\test_athena_dialog.py -v
```

- [ ] **Step 3: Run backend full suite**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests -v
```

- [ ] **Step 4: Check hygiene and secrets**

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9_-]{20,}|api_key|API_KEY" backend docs frontend .agents
git status --short
```

- [ ] **Step 5: Commit**

```powershell
git add backend docs\superpowers\plans\2026-05-13-longform-scale-phase2.md
git commit -m "feat: add query-aware longform retrieval context"
```
