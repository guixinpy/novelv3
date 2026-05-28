# Dialog Driven Agent Orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Expand the dialog intent planning surface so a natural-language request can produce an auditable Writing Agent plan for setup, storyline, outline, chapter drafting, review, and recovery.

**Architecture:** Keep the existing `IntentRouter -> plan_dialog_intent_agent_run -> build_writing_agent_run_plan` path. Add only the missing deterministic intent candidates and planner branches, then attach a compact reference-pattern projection to the dialog plan trace so future phases can see which openclaw, hermes-agent, and openhuman patterns guided the decision.

**Tech Stack:** Python, FastAPI service layer, SQLAlchemy test fixtures, pytest.

---

### Task 1: Dialog Intent Coverage

**Files:**
- Modify: `backend/app/core/intent_router.py`
- Test: `backend/tests/test_dialogs.py`

- [x] **Step 1: Write failing tests**

Add tests asserting:

```python
def test_intent_router_review_phrase_routes_to_preview_review():
    router = IntentRouter()
    diagnosis = ProjectDiagnosisOut(
        missing_items=[],
        completed_items=["setup", "storyline", "outline", "content"],
        suggested_next_step="preview_chapter",
    )

    candidate = router.resolve("审稿第2章并给出修订计划", "chatting", None, diagnosis)

    assert candidate is not None
    assert candidate.type == "preview_review"
    assert candidate.params["chapter_index"] == 2


def test_intent_router_recovery_phrase_routes_to_preview_recovery():
    router = IntentRouter()
    diagnosis = ProjectDiagnosisOut(
        missing_items=[],
        completed_items=["setup", "storyline", "outline"],
        suggested_next_step="preview_chapter",
    )

    candidate = router.resolve("恢复上一轮阻塞的写作任务", "chatting", None, diagnosis)

    assert candidate is not None
    assert candidate.type == "preview_recovery"
```

Run: `pytest backend/tests/test_dialogs.py::test_intent_router_review_phrase_routes_to_preview_review backend/tests/test_dialogs.py::test_intent_router_recovery_phrase_routes_to_preview_recovery -q`

Expected: both tests fail because these candidates do not exist yet.

- [x] **Step 2: Implement minimal routing**

Add `review_intent` and `recovery_intent` to the rule list, match recovery before chapter/review, and match review before chapter drafting. Use `parse_chapter_index(text)` and default review chapter to `1` only when the user omits a chapter.

- [x] **Step 3: Verify**

Run the two tests above again.

Expected: both tests pass.

### Task 2: Planner Branches

**Files:**
- Modify: `backend/app/services/writing_agent/planner.py`
- Modify: `backend/app/services/writing_agent/dialog_intent_planner.py`
- Test: `backend/tests/test_writing_agent_planner.py`
- Test: `backend/tests/test_writing_agent_tool_executor.py`

- [x] **Step 1: Write failing tests**

Add planner tests asserting:

```python
def test_planner_builds_storyline_plan_after_setup(db_session):
    project = _seed_project(db_session, outline_chapters=[], generated_chapters=[])

    plan = build_writing_agent_run_plan(db_session, project.id, goal="生成故事线", intent="build_storyline")

    assert plan["intent_class"] == "build_storyline"
    assert _tool_names(plan) == ["describe_agent_tools", "prepare_generate_storyline_execution"]
    assert plan["approval_contract"]["status"] == "not_required"


def test_planner_builds_outline_plan_after_storyline(db_session):
    project = _seed_project(db_session, outline_chapters=[], generated_chapters=[])

    plan = build_writing_agent_run_plan(db_session, project.id, goal="生成大纲", intent="build_outline")

    assert plan["intent_class"] == "build_outline"
    assert _tool_names(plan) == ["describe_agent_tools", "prepare_generate_outline_execution"]
    assert plan["approval_contract"]["status"] == "not_required"
```

Add dialog tool tests asserting `preview_storyline`, `preview_outline`, `preview_review`, and `preview_recovery` map to `build_storyline`, `build_outline`, `review_chapter`, and `recover_blocked_run`.

Run: `pytest backend/tests/test_writing_agent_planner.py::test_planner_builds_storyline_plan_after_setup backend/tests/test_writing_agent_planner.py::test_planner_builds_outline_plan_after_storyline -q`

Expected: tests fail because the planner falls through to inspection.

- [x] **Step 2: Implement minimal planner support**

Add `_build_storyline_plan()` and `_build_outline_plan()` using the existing approval prepare tools. Extend `_ACTION_TO_PLANNER_INTENT` with:

```python
"preview_storyline": "build_storyline",
"preview_outline": "build_outline",
"preview_review": "review_chapter",
"preview_recovery": "recover_blocked_run",
```

- [x] **Step 3: Verify**

Run the focused planner and tool-executor tests.

Expected: new tests pass and existing setup/chapter dialog plan tests still pass.

### Task 3: Reference Pattern Trace

**Files:**
- Create: `backend/app/services/writing_agent/reference_pattern_projection.py`
- Modify: `backend/app/services/writing_agent/dialog_intent_planner.py`
- Test: `backend/tests/test_writing_agent_tool_executor.py`

- [x] **Step 1: Write failing test**

Add an assertion to a dialog plan test:

```python
patterns = result.output["trace"]["reference_patterns"]
assert [item["source"] for item in patterns] == ["hermes-agent", "openhuman", "openclaw"]
assert "tool_lifecycle_hooks" in patterns[0]["applied_patterns"]
assert "agent_definition_visible_tool_split" in patterns[1]["applied_patterns"]
assert "schema_and_audit_discipline" in patterns[2]["applied_patterns"]
```

Run: `pytest backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_handles_dialog_intent_agent_plan_for_chapter -q`

Expected: fails because `reference_patterns` is absent.

- [x] **Step 2: Implement projection**

Create a small pure function returning deterministic reference-pattern decisions. Include line-oriented source notes in the values, but no runtime file reads.

- [x] **Step 3: Verify**

Run focused tests for dialog planner and planner.

Expected: all focused tests pass.

### Task 4: Final Verification

**Files:**
- No new files unless tests expose a local issue.

- [x] **Step 1: Run focused backend tests**

Run:

```powershell
pytest backend/tests/test_dialogs.py backend/tests/test_writing_agent_planner.py backend/tests/test_writing_agent_tool_executor.py -q
```

Expected: pass.

- [x] **Step 2: Review diff**

Run:

```powershell
git diff --stat
git diff --check
```

Expected: no whitespace errors; changed files are limited to this phase.

- [x] **Step 3: Commit**

Run:

```powershell
git add backend/app/core/intent_router.py backend/app/services/writing_agent/dialog_intent_planner.py backend/app/services/writing_agent/planner.py backend/app/services/writing_agent/reference_pattern_projection.py backend/tests/test_dialogs.py backend/tests/test_writing_agent_planner.py backend/tests/test_writing_agent_tool_executor.py docs/superpowers/plans/2026-05-27-dialog-driven-agent-orchestration.md
git commit -m "Expand dialog-driven agent orchestration planning"
```
