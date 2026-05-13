# Longform Scale Phase 6 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a repeatable local longform scale smoke test that proves thousand-chapter synthetic projects can seed data, rebuild layered memory, index retrieval, assemble bounded context, and report resumable range-task progress.

**Architecture:** Keep this phase as a CLI/test harness around existing services. Create synthetic data through SQLAlchemy, reuse `rebuild_longform_memory`, `reindex_project_retrieval`, `build_longform_context_package`, and `BackgroundTaskService`, and emit a compact JSON report for manual 1000-chapter runs.

**Tech Stack:** Python CLI, SQLAlchemy, existing backend app services, pytest.

---

## File Structure

- Create `backend/app/core/longform_scale_smoke.py`: reusable smoke-test runner that accepts a SQLAlchemy session and returns a JSON-serializable report.
- Create `scripts/longform_scale_smoke.py`: local CLI entrypoint for manual 100/300/1000 chapter runs.
- Modify `backend/tests/test_longform_scale.py`: add a lightweight smoke test against 120 synthetic chapters.
- Create or modify docs only in this plan file for Phase 6 tracking.

## Success Criteria

- The smoke runner seeds a project with configurable chapter count and words per chapter.
- The runner creates a chapter-range background task, records progress checkpoints, rebuilds longform memory, reindexes retrieval, assembles context for the target chapter, and marks the task completed.
- The report includes project id, chapter count, target chapter, total words, memory counts, retrieval diagnostics, context section keys, range progress, and elapsed milliseconds.
- A pytest case runs a 120-chapter version without external API calls.
- Manual CLI can run `--chapters 1000 --words-per-chapter 1000` and print JSON.

## Task 1: Smoke Runner Contract

**Files:**
- Create: `backend/app/core/longform_scale_smoke.py`
- Modify: `backend/tests/test_longform_scale.py`

- [ ] **Step 1: Write failing test**

Add `test_longform_scale_smoke_reports_memory_retrieval_and_resume_progress` that calls `run_longform_scale_smoke(db_session, chapter_count=120, words_per_chapter=1000, target_chapter_index=120, query="星环钥匙")`.

Expected assertions:

- `report["chapter_count"] == 120`
- `report["total_words"] == 120000`
- `report["memory"]["counts_by_type"] == {"chapter": 120, "arc": 6, "volume": 2, "global": 1}`
- `report["retrieval"]["documents_by_source_type"]["chapter"] == 120`
- `report["retrieval"]["documents_by_source_type"]["longform_memory"] == 129`
- `"query_aware_retrieval"` is in `report["context"]["section_keys"]`
- `report["task"]["progress"]["completed_count"] == 120`
- `report["task"]["status"] == "completed"`

- [ ] **Step 2: Run focused test to verify RED**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_scale_smoke_reports_memory_retrieval_and_resume_progress -v
```

Expected: FAIL because `app.core.longform_scale_smoke` does not exist.

- [ ] **Step 3: Implement runner**

Create `run_longform_scale_smoke(db, chapter_count, words_per_chapter, target_chapter_index, query)` and helper functions to seed deterministic Chinese chapter content, create range progress, rebuild memory, reindex retrieval, build context, mark completion, and return the report.

- [ ] **Step 4: Run focused test to verify GREEN**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_scale_smoke_reports_memory_retrieval_and_resume_progress -v
```

Expected: PASS.

## Task 2: CLI Entrypoint

**Files:**
- Create: `scripts/longform_scale_smoke.py`
- Modify: `backend/tests/test_longform_scale.py`

- [ ] **Step 1: Write import-level CLI guard test**

Add a test that imports `scripts/longform_scale_smoke.py` with `importlib.util.spec_from_file_location` and asserts it exposes `main`.

- [ ] **Step 2: Run focused test to verify RED**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_scale_smoke_cli_exposes_main -v
```

Expected: FAIL because the script does not exist.

- [ ] **Step 3: Implement CLI**

The script must:

- Add `backend` to `sys.path`.
- Create database tables with `Base.metadata.create_all(bind=engine)`.
- Open `SessionLocal`.
- Parse `--chapters`, `--words-per-chapter`, `--target-chapter`, and `--query`.
- Call `run_longform_scale_smoke`.
- Print `json.dumps(report, ensure_ascii=False, indent=2)`.

- [ ] **Step 4: Run focused test**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_scale_smoke_cli_exposes_main -v
```

Expected: PASS.

## Task 3: Verification and Commit

- [ ] **Step 1: Run longform scale tests**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py -v
```

- [ ] **Step 2: Run a small CLI smoke**

```powershell
.\backend\.venv\Scripts\python.exe scripts\longform_scale_smoke.py --chapters 30 --words-per-chapter 1000 --target-chapter 30 --query 星环钥匙
```

Expected: JSON with `"chapter_count": 30`, `"total_words": 30000`, and completed task progress.

- [ ] **Step 3: Run backend tests**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests -v
```

- [ ] **Step 4: Check hygiene**

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9_-]{20,}" backend docs frontend scripts
git status --short
```

Expected: diff check passes, secret pattern scan returns no matches, and only Phase 6 files are staged.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/core/longform_scale_smoke.py backend/tests/test_longform_scale.py scripts/longform_scale_smoke.py docs/superpowers/plans/2026-05-13-longform-scale-phase6.md
git commit -m "feat: add longform scale smoke runner"
```
