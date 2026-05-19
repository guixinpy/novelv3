# Phase 20 Deterministic Revision Apply and Chapter 7 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Safely apply planner-owned deterministic Chapter 6 fixes, re-review blockers to zero, then continue to Chapter 7 only if the quality gate is clear.

**Architecture:** Add a small internal Writing Agent tool that applies only known planner-owned revision actions. It creates chapter versions, patches exact supported drift spans, updates word counts, marks the revision completed, and requires review before further generation.

**Tech Stack:** FastAPI backend services, SQLAlchemy models, `WritingAgentRunService`, chapter revision models, chapter quality review, pytest.

---

## Phase Metadata

- **Phase:** 20
- **Date:** 2026-05-19
- **Verification Tier:** T1 for deterministic patch behavior; T2 for dogfood Chapter 6 patch/review and optional Chapter 7 generation.
- **Dogfood Project:** `25fa2b20-5b9f-473b-918b-f4ea491cbb60`
- **Primary Output:** Chapter 6 blocker cleanup and, if safe, Chapter 7 generation.
- **Secret Handling:** Do not write API keys to docs, commits, `.env`, or logs.

## Starting State

- Generated chapters: 6
- Latest generated chapter: Chapter 6 `黑市雾晶`
- Active revision draft id: `94ee16d6-1559-4dac-b13b-138bb065ae0a`
- Draft annotations:
  - `fix_character_profile_drift`
  - `respect_ability_boundary`
- Known blockers:
  - `叶知秋` is described as formerly `雾安局` researcher.
  - `苏晚晴` uses `制造幻觉`, exceeding ability boundary.
- Chapter 7 is not generated.

## Problem

The system can now detect and plan repairs, but cannot apply planner-owned repairs. Continuing longform generation would still require manual editing or unsafe full LLM regeneration.

This phase should add a conservative patch path for deterministic, known corrections:

- Do not apply arbitrary annotations.
- Do not call LLMs for this patch.
- Do not overwrite content without version backup.
- Do not continue generation until review passes.

## Success Criteria

- Writing Agent supports `apply_planner_revision_patch`.
- The tool only applies planner-owned draft revisions.
- The tool creates a base version before patch and result version after patch.
- The tool marks the revision `completed`.
- The tool updates chapter content and word count.
- The tool returns applied replacement evidence.
- It blocks unsupported planner actions instead of guessing.
- Tests prove Chapter 6 style drift patches clear `character_profile_drift` and `ability_boundary_drift`.
- Dogfood Chapter 6 review after patch has `blocker_count=0`.
- Chapter 7 is generated only after Chapter 6 blocker count is 0.

## Explicit Non-Goals

- Do not build a general-purpose text patch engine.
- Do not apply manual user drafts.
- Do not handle LLM regeneration in this phase.
- Do not change database schema.
- Do not add frontend UI.
- Do not rewrite all of Chapter 6.

## Files

- Create: `backend/app/core/chapter_revision_apply.py`
- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-19-phase20-deterministic-revision-apply-and-chapter7.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-19-phase20-deterministic-revision-apply-and-chapter7.md`

## Task 1: Implement Deterministic Revision Patch Tool

**Files:**

- Create: `backend/app/core/chapter_revision_apply.py`
- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [ ] **Step 1: Write failing apply-patch test**

Add a test to `backend/tests/test_writing_agent_runs.py` near revision draft tests:

```python
def test_agent_apply_planner_revision_patch_updates_chapter_and_versions(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "黑市雾晶"
    chapter.content = "苏晚晴低声说，她以前是雾安局研究员。随后她制造幻觉骗过守卫。"
    chapter.word_count = 2000
    db_session.commit()

    draft = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "创建修订草稿",
            "tools": [{"tool_name": "create_revision_draft", "params": {"chapter_index": 1}}],
        },
    )
    revision_id = draft.json()["steps"][0]["output"]["revision_id"]

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "应用planner修订",
            "tools": [{"tool_name": "apply_planner_revision_patch", "params": {"chapter_index": 1}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    patched = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    revision = db_session.query(ChapterRevision).filter_by(id=revision_id).one()
    assert response.status_code == 200
    assert output["status"] == "completed"
    assert output["revision_id"] == revision_id
    assert output["applied_replacement_count"] == 2
    assert "雾安局研究员" not in patched.content
    assert "制造幻觉" not in patched.content
    assert "雾港大学神经科学教授" in patched.content
    assert "扰乱雾中感知" in patched.content
    assert patched.word_count != 2000
    assert revision.status == "completed"
    assert revision.base_version_id
    assert revision.result_version_id
    assert output["should_generate_next_chapter"] is False
```

- [ ] **Step 2: Run RED apply-patch test**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_apply_planner_revision_patch_updates_chapter_and_versions -q
```

Expected: fail because the tool is unsupported.

- [ ] **Step 3: Create `chapter_revision_apply.py`**

Implement:

- `apply_planner_revision_patch(db, project_id, chapter_index, revision_id=None)`.
- Load latest draft revision unless `revision_id` is supplied.
- Require every annotation comment to start with `[PLAN_ACTION:`.
- Parse action names from comments.
- Support only:
  - `fix_character_profile_drift`
  - `respect_ability_boundary`
- Create base version before patch.
- Apply deterministic replacements:
  - `他叫叶知秋，以前是雾安局的研究员` -> `她叫叶知秋，是雾港大学神经科学教授，曾参与政府秘密项目`
  - `以前是雾安局研究员` -> `是雾港大学神经科学教授，曾参与政府秘密项目`
  - `以前是雾安局的研究员` -> `是雾港大学神经科学教授，曾参与政府秘密项目`
  - `制造幻觉` -> `扰乱雾中感知`
- Update `chapter.word_count` with `count_words`.
- Reconcile `project.current_word_count`.
- Create result version after patch.
- Mark revision completed.

- [ ] **Step 4: Register Writing Agent tool**

In `backend/app/services/writing_agent/run_service.py`:

- Add `apply_planner_revision_patch` to allowed/internal tools.
- Add execution branch calling `apply_planner_revision_patch`.
- Add target type `revision`.
- Add report-stop behavior so generation cannot follow it directly when `should_generate_next_chapter` is false.
- Allow follow-up `review_chapter_quality`.

- [ ] **Step 5: Run GREEN apply-patch test**

Run the same test and confirm it passes.

## Task 2: Verify Patch Clears Drift Findings

**Files:**

- Modify: `backend/tests/test_writing_agent_runs.py`

- [ ] **Step 1: Write review-after-patch test**

Add:

```python
def test_agent_apply_planner_revision_patch_then_review_clears_drift_blockers(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    chapter = db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=1).one()
    chapter.title = "黑市雾晶"
    chapter.content = "苏晚晴低声说，她以前是雾安局研究员。随后她制造幻觉骗过守卫。"
    chapter.word_count = 2000
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "修订并复审",
            "tools": [
                {"tool_name": "create_revision_draft", "params": {"chapter_index": 1}},
                {"tool_name": "apply_planner_revision_patch", "params": {"chapter_index": 1}},
                {"tool_name": "review_chapter_quality", "params": {"chapter_index": 1}},
            ],
        },
    )

    review = response.json()["steps"][2]["output"]
    codes = {finding["code"] for finding in review["findings"]}
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "character_profile_drift" not in codes
    assert "ability_boundary_drift" not in codes
    assert review["blocker_count"] == 0
```

- [ ] **Step 2: Run GREEN review-after-patch test**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_apply_planner_revision_patch_then_review_clears_drift_blockers -q
```

Expected: pass after Task 1 implementation.

## Task 3: Dogfood Chapter 6 Patch and Chapter 7 Continuation

**Files:**

- Create report under `docs/superpowers/notes/long-memory-agent/`.

- [ ] **Step 1: Apply Chapter 6 planner patch**

Run Writing Agent:

```json
[
  {"tool_name": "apply_planner_revision_patch", "params": {"chapter_index": 6}}
]
```

Expected:

- revision id `94ee16d6-1559-4dac-b13b-138bb065ae0a`
- applied replacement count >= 2
- revision status `completed`
- Chapter 6 still generated and not structurally replaced.

- [ ] **Step 2: Review Chapter 6**

Run:

```json
[
  {"tool_name": "review_chapter_quality", "params": {"chapter_index": 6}}
]
```

Expected:

- `character_profile_drift` absent.
- `ability_boundary_drift` absent.
- blocker count 0.

- [ ] **Step 3: Generate Chapter 7 only if clear**

If Chapter 6 blocker count is 0, run:

```json
[
  {"tool_name": "preflight_writing", "params": {"chapter_index": 7}},
  {"tool_name": "generate_chapter", "params": {"chapter_index": 7}},
  {"tool_name": "review_chapter_quality", "params": {"chapter_index": 7}},
  {"tool_name": "analyze_chapter_world_model", "params": {"chapter_index": 7}}
]
```

Expected:

- Chapter 7 generated.
- `agent_continuity_feedback` present.
- `word_count >= 2000`.
- If review has blockers, stop and record them.

## Task 4: Verification, Report, Commit, Push

**Files:**

- Modify all Phase20 files.

- [ ] **Step 1: Run T2 verification**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_world_proposals.py -q
```

Expected: pass.

- [ ] **Step 2: Write Phase20 report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-19-phase20-deterministic-revision-apply-and-chapter7.md` with:

- code changes;
- RED/GREEN evidence;
- dogfood patch run id;
- Chapter 6 review result;
- Chapter 7 generation/review result or blocker reason;
- next phase recommendation.

- [ ] **Step 3: Hygiene checks**

Run:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references
git status --short --branch
```

Expected:

- whitespace check passes;
- secret scan returns no matches;
- only intended Phase20 files are changed.

- [ ] **Step 4: Commit and push**

Commit plan first:

```powershell
git add docs/superpowers/plans/long-memory-agent/2026-05-19-phase20-deterministic-revision-apply-and-chapter7.md
git commit -m "docs: plan long memory agent phase 20"
```

Commit implementation/report after verification:

```powershell
git add backend/app/core/chapter_revision_apply.py backend/app/services/writing_agent/run_service.py backend/tests/test_writing_agent_runs.py docs/superpowers/plans/long-memory-agent/2026-05-19-phase20-deterministic-revision-apply-and-chapter7.md docs/superpowers/notes/long-memory-agent/2026-05-19-phase20-deterministic-revision-apply-and-chapter7.md
git commit -m "feat: apply deterministic planner revisions"
git push origin main
```
