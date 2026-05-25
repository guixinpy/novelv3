# Phase 6 Agent Safety Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the next safety gates needed before continuing `《雾港回声》` Chapter 4: historical outline gap detection, deterministic outline backfill, duplicate Athena-analysis skipping, and structured repeated length-drift blocking.

**Architecture:** Phase 6 keeps the Agent loop thin. It adds deterministic preflight diagnostics and same-run tool guards around existing tools instead of introducing a new planner or rewriting chapter generation.

**Tech Stack:** FastAPI service layer, SQLAlchemy, existing outline JSON storage, Writing Agent run service, pytest, runtime dogfood through Agent API.

---

## Phase Metadata

- **Phase:** 6
- **Date:** 2026-05-18
- **Verification Tier:** T1 for service/API tests; T2 for runtime dogfood backfill and Chapter 4 preflight/generation.
- **Primary Output:** Safer Agent preflight and tool sequencing.
- **Dogfood Output:** Backfill the missing Chapter 2 outline, run Chapter 4 preflight, and do not generate Chapter 4 if repeated length drift or quality findings require review.
- **Secret Handling:** Do not write API keys to docs, commits, or `.env`.

## Phase 6 Success Criteria

- Agent preflight detects generated chapters that are missing outline entries before the target chapter.
- The missing Chapter 2 outline in `《雾港回声》` is fixed through deterministic outline backfill from existing chapter content.
- Agent skips `analyze_chapter_world_model` when the same run already generated and auto-analyzed that chapter.
- Chapter length diagnostics include repeated over-target drift and a concrete policy recommendation.
- Agent preflight blocks Chapter 4 when repeated length drift requires review.
- Targeted backend tests pass.
- Runtime dogfood records preflight, generation, proposal queue, length-policy, and next issues in the phase report.

## Explicit Non-Goals

- Do not build a full autonomous planner in this phase.
- Do not auto-rewrite overlong chapters yet.
- Do not auto-approve Athena world-model proposals.
- Do not add frontend UI.
- Do not change the project-wide word target without an explicit later decision.
- Do not generate Chapter 4 if the new gates report blockers.

## Files

- Modify: `backend/app/core/outline_lookup.py`
- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-18-phase6-agent-safety-gates.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-18-phase6-agent-safety-gates.md`

## Task 1: Historical Outline Gap Detection

**Files:**
- Modify: `backend/app/core/outline_lookup.py`
- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: Add failing preflight test**

Add:

```python
def test_agent_preflight_blocks_when_generated_chapter_outline_gap_exists(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 3, 4], generated_chapters=[1, 2, 3])
    import_setup_to_world_model(db_session, project.id)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第4章是否可写",
            "tools": [{"tool_name": "preflight_writing", "params": {"chapter_index": 4}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert output["checks"]["historical_outline_gaps"]["status"] == "missing"
    assert output["checks"]["historical_outline_gaps"]["chapter_indexes"] == [2]
    assert output["issues"][0]["code"] == "missing_historical_outline_chapters"
    assert output["issues"][0]["suggested_tool"] == "backfill_outline_gaps"
```

- [x] **Step 2: Add outline lookup helpers**

Add helpers to `backend/app/core/outline_lookup.py`:

```python
def outline_chapter_indexes(db: Session, project_id: str) -> set[int]:
    ...

def generated_chapter_indexes(db: Session, project_id: str, *, before_chapter: int | None = None) -> list[int]:
    ...

def generated_chapters_missing_outline(
    db: Session,
    project_id: str,
    *,
    before_chapter: int | None = None,
) -> list[int]:
    ...
```

Required behavior:

- `outline_chapter_indexes` reads chapter indexes from `outlines.chapters` using SQLite JSON functions.
- `generated_chapter_indexes` returns generated chapter indexes in ascending order.
- `generated_chapters_missing_outline` returns generated chapter indexes absent from outline coverage.

- [x] **Step 3: Wire preflight coverage check**

In `WritingAgentRunService._preflight_writing`:

- Add `checks["historical_outline_gaps"]`.
- Use `generated_chapters_missing_outline(..., before_chapter=chapter_index)`.
- If non-empty, append blocker issue:

```python
_issue(
    "missing_historical_outline_chapters",
    "blocker",
    "已生成章节中第2章缺少章节大纲，请先回填大纲。",
    extra={
        "chapter_indexes": [2],
        "suggested_tool": "backfill_outline_gaps",
        "suggested_params": {"before_chapter": 4},
    },
)
```

- [x] **Step 4: Run targeted test**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_preflight_blocks_when_generated_chapter_outline_gap_exists -q
```

Expected: pass.

## Task 2: Deterministic Outline Backfill Tool

**Files:**
- Modify: `backend/app/core/outline_lookup.py`
- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: Add failing backfill test**

Add:

```python
def test_agent_backfill_outline_gaps_uses_existing_chapter_content_then_preflight_ready(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1, 3, 4], generated_chapters=[1, 2, 3])
    import_setup_to_world_model(db_session, project.id)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "回填历史大纲缺口并检查第4章",
            "tools": [
                {"tool_name": "backfill_outline_gaps", "params": {"before_chapter": 4}},
                {"tool_name": "preflight_writing", "params": {"chapter_index": 4}},
            ],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["steps"][0]["output"]["backfilled_chapter_indexes"] == [2]
    assert payload["steps"][1]["output"]["status"] == "ready"
    outline = db_session.query(Outline).filter(Outline.project_id == project.id).one()
    assert [chapter["chapter_index"] for chapter in outline.chapters] == [1, 2, 3, 4]
    chapter_two = next(chapter for chapter in outline.chapters if chapter["chapter_index"] == 2)
    assert chapter_two["title"] == "雾港线索2"
    assert chapter_two["purpose"] == "根据已生成正文自动回填章节大纲。"
```

- [x] **Step 2: Add backfill helper**

Add helper in `backend/app/core/outline_lookup.py`:

```python
def backfill_missing_outline_chapters_from_content(
    db: Session,
    project_id: str,
    *,
    before_chapter: int | None = None,
) -> dict[str, Any]:
    ...
```

Required behavior:

- Find latest outline for project.
- Find generated chapters before `before_chapter` whose indexes are missing from the outline.
- Append deterministic outline entries from `ChapterContent.title/content`.
- Use a short content-derived summary.
- Keep `scenes=[]`, `characters=[]`, `purpose="根据已生成正文自动回填章节大纲。"`.
- Sort chapters by `chapter_index`.
- Return `status`, `outline_id`, `backfilled_chapter_indexes`, and `missing_before`.

- [x] **Step 3: Add Agent tool**

Add `backfill_outline_gaps` to `ALLOWED_TOOLS`, `INTERNAL_TOOLS`, `_target_type_for_tool`, and `_execute_tool`.

Parameters:

```json
{"before_chapter": 4}
```

- [x] **Step 4: Run targeted test**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_backfill_outline_gaps_uses_existing_chapter_content_then_preflight_ready -q
```

Expected: pass.

## Task 3: Skip Same-Run Duplicate Athena Analysis

**Files:**
- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: Add failing duplicate-analysis test**

Add:

```python
def test_agent_skips_analyze_when_generate_step_already_auto_analyzed_same_chapter(...):
    ...
```

Test setup:

- Patch `ActionExecutionService.execute` so `generate_chapter` returns:

```python
{
    "status": "success",
    "chapter_index": 4,
    "trace_id": trace.id,
    "athena_analysis": {
        "status": "completed",
        "chapter_index": 4,
        "proposal_bundle_id": "bundle-4",
        "created": {"proposal_items": 3},
        "updated": {"proposal_items": 0},
    },
}
```

- Patch `app.core.athena_longform.analyze_chapter_to_world_proposals` to raise if called.
- Run a two-step Agent sequence:
  - `generate_chapter`, chapter 4.
  - `analyze_chapter_world_model`, chapter 4.

Expected:

- run status is `success`.
- second step status is `success`.
- second step output:

```json
{
  "status": "skipped",
  "reason": "chapter_already_analyzed_in_run",
  "chapter_index": 4,
  "source_step_id": "<generate step id>",
  "proposal_bundle_id": "bundle-4"
}
```

- [x] **Step 2: Pass run id into internal tool execution**

Change `_execute_tool` signature:

```python
async def _execute_tool(self, project_id: str, tool: WritingAgentToolRequest, *, run_id: str) -> dict[str, Any]:
    ...
```

Update the caller in `execute_run`.

- [x] **Step 3: Add same-run analysis lookup**

Add helper in `run_service.py`:

```python
def _same_run_completed_chapter_analysis(
    db: Session,
    *,
    run_id: str,
    project_id: str,
    chapter_index: int,
) -> dict[str, Any] | None:
    ...
```

It should inspect successful `generate_chapter` steps in the same run for the same chapter and return the nested `athena_analysis` if its `status` is `completed`.

- [x] **Step 4: Return skipped output**

Before calling `analyze_chapter_to_world_proposals`, return:

```python
{
    "status": "skipped",
    "reason": "chapter_already_analyzed_in_run",
    "chapter_index": chapter_index,
    "source_step_id": source_step_id,
    "proposal_bundle_id": analysis.get("proposal_bundle_id"),
    "created": analysis.get("created", {"proposal_items": 0}),
    "updated": analysis.get("updated", {"proposal_items": 0}),
}
```

- [x] **Step 5: Run targeted test**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_skips_analyze_when_generate_step_already_auto_analyzed_same_chapter -q
```

Expected: pass.

## Task 4: Repeated Length-Drift Diagnostics And Preflight Block

**Files:**
- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: Add failing length-policy output test**

Add:

```python
def test_agent_chapter_length_decision_flags_repeated_over_target_drift(...):
    ...
```

Seed:

- project target: 600 chapters, 1,200,000 words.
- generated chapters 1, 2, 3 with word count above target max.
- trace for generated chapter 3 with `chapter_word_target.status == "over"`.

Expected:

```python
decision = output["chapter_length_decision"]
assert decision["status"] == "over"
assert decision["decision"] == "requires_policy_review"
assert decision["severity"] == "warning"
assert decision["repeated_drift_count"] == 3
assert "revise_or_adjust_project_target" in decision["recommended_actions"]
```

- [x] **Step 2: Add failing preflight length-policy block test**

Add:

```python
def test_agent_preflight_blocks_when_repeated_over_target_drift_requires_review(...):
    project = _seed_longform_project(db_session, outline_chapters=[1, 2, 3, 4], generated_chapters=[1, 2, 3])
    for chapter in db_session.query(ChapterContent).filter(ChapterContent.project_id == project.id):
        chapter.word_count = 3000
    db_session.commit()
    import_setup_to_world_model(db_session, project.id)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第4章是否可写",
            "tools": [{"tool_name": "preflight_writing", "params": {"chapter_index": 4}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    assert response.json()["status"] == "blocked"
    assert output["checks"]["length_policy"]["status"] == "blocked"
    assert output["checks"]["length_policy"]["reason"] == "repeated_over_target"
    assert output["issues"][0]["code"] == "repeated_chapter_length_drift"
```

- [x] **Step 3: Extend `_chapter_length_decision`**

Add:

- `severity`.
- `repeated_drift_count`.
- `recommended_actions`.
- `policy_reason`.

Policy:

- `within` -> `decision="accept"`, severity `info`.
- single `under` or `over` -> `decision="accept_with_warning"`, severity `warning`.
- repeated same-direction drift count >= 3 -> `decision="requires_policy_review"`, severity `warning`.
- unknown/untracked -> current fallback behavior.

Use `get_longform_maintenance_diagnostics(db, project_id, limit=10)` to read `word_target`.

- [x] **Step 4: Add preflight length policy check**

In `WritingAgentRunService._preflight_writing`, add `checks["length_policy"]`.

Policy:

- no repeated drift -> status `ready`.
- repeated same-direction drift count >= 3 -> status `blocked`, reason `repeated_over_target` or `repeated_under_target`.
- append blocker issue `repeated_chapter_length_drift`.

- [x] **Step 5: Update existing exact assertion test**

Update `test_agent_run_records_chapter_length_and_world_model_diagnostics` to assert the new fields without depending on unrelated defaults.

- [x] **Step 6: Run writing-agent tests**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q
```

Expected: pass.

## Task 5: Runtime Dogfood Chapter 4 Gate

**Files:**
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-18-phase6-agent-safety-gates.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-18-phase6-agent-safety-gates.md`

- [x] **Step 1: Run focused verification**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_outlines.py -q
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references
```

Expected: tests pass, no whitespace errors, no secrets.

- [x] **Step 2: Backfill Chapter 2 outline**

Use Agent run:

```json
{
  "goal": "回填《雾港回声》第2章大纲缺口，为第4章继续写作做准备。",
  "tools": [
    {
      "tool_name": "backfill_outline_gaps",
      "params": {
        "before_chapter": 4
      }
    }
  ]
}
```

Expected: outline coverage contains Chapter 1, 2, 3, 4, 5, 6, 7, 8.

- [x] **Step 3: Preflight Chapter 4**

Use Agent run:

```json
{
  "goal": "检查《雾港回声》第4章是否可写。",
  "tools": [
    {"tool_name": "preflight_writing", "params": {"chapter_index": 4}}
  ]
}
```

Expected:

- outline coverage has no historical missing generated chapters.
- repeated length drift appears as a policy blocker.
- Chapter 4 is not generated in this phase if the blocker appears.

- [x] **Step 4: Do not generate Chapter 4 when blocked**

If preflight returns `ready`, generate Chapter 4 through the Agent gated path:

```json
{
  "goal": "在preflight通过后生成《雾港回声》第4章，并避免重复世界模型分析。",
  "tools": [
    {"tool_name": "preflight_writing", "params": {"chapter_index": 4}},
    {
      "tool_name": "generate_chapter",
      "command_args": "请生成《雾港回声》第4章，承接前三章，保持都市悬疑轻科幻风格，正文不少于2000字；注意延续雾中童谣和顾衍警告线索。",
      "params": {"chapter_index": 4}
    },
    {"tool_name": "analyze_chapter_world_model", "params": {"chapter_index": 4}}
  ]
}
```

Expected if ready:

- preflight step is ready.
- Chapter 4 is generated.
- generate step records length decision and proposal diagnostic.
- analyze step is skipped if generate step already auto-analyzed Chapter 4.

Expected if blocked:

- record the blocker in the phase report.
- do not generate Chapter 4.
- recommend Phase 7 quality-review and revision work before continuing the manuscript.

- [x] **Step 5: Write Phase 6 report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-18-phase6-agent-safety-gates.md` with:

```markdown
# Phase 6 Agent Safety Gates

## Runtime
## Implementation
## Dogfood Backfill
## Chapter 4 Gate And Generation
## Quality Review
## Issues Found
## Issues Fixed
## Verification
## Next Phase Recommendation
```

## Task 6: Commit Phase 6

- [x] **Step 1: Commit code**

```powershell
git add backend/app/core/outline_lookup.py backend/app/services/writing_agent/run_service.py backend/tests/test_writing_agent_runs.py
git commit -m "feat: add writing agent safety gates"
```

- [x] **Step 2: Commit docs**

```powershell
git add docs/superpowers/plans/long-memory-agent/2026-05-18-phase6-agent-safety-gates.md docs/superpowers/notes/long-memory-agent/2026-05-18-phase6-agent-safety-gates.md
git commit -m "docs: record long memory agent phase 6"
```

## Self-Review

- Spec coverage: This phase continues the real dogfood novel and adds Agent orchestration safety around outline, review, length, and trace output.
- Placeholder scan: No `TBD` markers.
- Scope check: The plan does not introduce a broad planner, task queue, frontend, or auto-revision system.
