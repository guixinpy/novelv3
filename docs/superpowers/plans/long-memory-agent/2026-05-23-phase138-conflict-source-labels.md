# Phase138 Conflict Source Labels Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Label chapter target conflicts by source type so users can distinguish pending action, single chapter task, and batch range task collisions.

**Architecture:** Convert reservation scanning from a set of occupied indexes to an index-source map. Preserve existing occupied set behavior by deriving indexes from the map, and enrich `chapter_target_conflict` with `source` and `source_label`. The frontend warning reads the label when available and falls back to the generic text.

**Tech Stack:** FastAPI dialog endpoint, action descriptions, Vue 3, Vitest, pytest.

---

## Scope

This phase improves explainability only. It does not change conflict detection semantics, target selection, task cancellation, or confirmation behavior.

## Files

- Modify: `backend/app/api/dialogs.py`
- Modify: `backend/app/services/actions/descriptions.py`
- Modify: `backend/tests/test_dialogs.py`
- Modify: `frontend/src/components/chat/ActionCard.vue`
- Modify: `frontend/src/components/chat/ChatMessage.test.ts`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase138-conflict-source-labels.md`

## Validation Level

T1:

- Backend targeted test for range task source labeling.
- Frontend targeted test for source label warning.
- Dialog regression and ChatMessage component regression.
- Frontend build because a Vue component changed.

Commands:

- Backend targeted RED/GREEN:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_chapter_command_explicit_range_reserved_target_labels_conflict_source -q`
- Frontend targeted RED/GREEN:
  - `npm run test:unit -- src/components/chat/ChatMessage.test.ts -t "renders pending chapter conflict source labels"`
- Regression:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py -q`
  - `npm run test:unit -- src/components/chat/ChatMessage.test.ts`
  - `npm run build`
- Hygiene:
  - `git diff --check`
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`

## Task 1: Failing Tests

- [ ] **Step 1: Add backend source-label test**

Add to `backend/tests/test_dialogs.py`:

```python
def test_chapter_command_explicit_range_reserved_target_labels_conflict_source(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    db_session.add(BackgroundTask(
        project_id=pid,
        task_type="generate_chapter_range",
        status="running",
        payload={"chapter_range": {"start": 2, "end": 3}},
    ))
    db_session.commit()

    r2 = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "command",
        "command_name": "chapter",
        "command_args": "2",
    })

    assert r2.status_code == 200
    pending = r2.json()["pending_action"]
    assert pending["params"]["chapter_target_conflict"] == {
        "status": "reserved",
        "chapter_index": 2,
        "reason": "pending_or_running_generation",
        "source": "range_task",
        "source_label": "批量生成任务",
    }
    assert "已有批量生成任务" in pending["description"]
```

- [ ] **Step 2: Add frontend source-label test**

Add to `frontend/src/components/chat/ChatMessage.test.ts`:

```ts
it('renders pending chapter conflict source labels', () => {
  const wrapper = mount(ChatMessage, {
    props: {
      msg: {
        role: 'assistant',
        content: '准备生成章节。',
        pending_action: {
          id: 'pending-1',
          type: 'preview_chapter',
          description: '我可以生成第2章正文，完成后会进入 Calliope 和正文进度。 注意：第2章已有批量生成任务，请确认是否仍要继续。',
          params: {
            chapter_index: 2,
            chapter_target_conflict: {
              status: 'reserved',
              chapter_index: 2,
              reason: 'pending_or_running_generation',
              source: 'range_task',
              source_label: '批量生成任务',
            },
          },
        },
      },
      isLatest: true,
      loading: false,
    },
  })

  const warning = wrapper.get('[data-testid="chapter-target-conflict"]')
  expect(warning.text()).toContain('第2章已有批量生成任务')
  expect(wrapper.get('.action-card__copy').text()).not.toContain('注意：')
})
```

- [ ] **Step 3: Run RED**

Expected:

- Backend conflict lacks `source/source_label`.
- Frontend warning still says generic `待确认或运行中的生成任务`.

## Task 2: Minimal Implementation

- [ ] **Step 1: Add source labels in `dialogs.py`**

Add constants:

```python
CHAPTER_TARGET_SOURCE_LABELS = {
    "pending_action": "待确认操作",
    "single_task": "单章生成任务",
    "range_task": "批量生成任务",
}
```

- [ ] **Step 2: Introduce source map helpers**

Add `_reserved_chapter_index_sources(...) -> dict[int, str]` that merges pending action sources first, then task sources.

Add `_pending_chapter_action_index_sources(...) -> dict[int, str]`.

Add `_active_chapter_task_index_sources(...) -> dict[int, str]`.

Add `_chapter_index_sources_from_task_payload(payload) -> dict[int, str]`:

- chapter ranges map to `range_task`.
- direct chapter indexes and tool params map to `single_task`.

Keep `_reserved_chapter_indexes(...)` returning `set(_reserved_chapter_index_sources(...))`.

- [ ] **Step 3: Enrich conflict object**

Change `_chapter_target_conflict(chapter_index, source)` to include:

```python
"source": source,
"source_label": CHAPTER_TARGET_SOURCE_LABELS.get(source, "占用目标")
```

When explicit chapter conflicts are detected, pass the source from `_reserved_chapter_index_sources`.

- [ ] **Step 4: Update description warning**

In `action_description(...)`, use `source_label`:

```python
source_label = str(conflict.get("source_label") or "待确认或运行中的生成任务").strip()
return f"{description} 注意：第{chapter_index}章已有{source_label}，请确认是否仍要继续。"
```

- [ ] **Step 5: Update frontend warning**

In `ActionCard.vue`, return `sourceLabel` from `chapterTargetConflict` and render:

```vue
第{{ chapterTargetConflict.chapterIndex }}章已有{{ chapterTargetConflict.sourceLabel }}，确认前请检查是否要继续覆盖同一章节。
```

Update the copy-cleaning regex to strip any conflict warning sentence:

```ts
return copy.replace(/\s*注意：第\d+章已有.+?，请确认是否仍要继续。\s*$/, '').trim()
```

## Task 3: Verify, Document, Commit

- [ ] Run targeted backend and frontend tests.
- [ ] Run backend dialog regression.
- [ ] Run ChatMessage component regression.
- [ ] Run frontend build.
- [ ] Run hygiene checks.
- [ ] Write phase report with RED/GREEN evidence.
- [ ] Commit and push:

```powershell
git add backend/app/api/dialogs.py backend/app/services/actions/descriptions.py backend/tests/test_dialogs.py frontend/src/components/chat/ActionCard.vue frontend/src/components/chat/ChatMessage.test.ts docs/superpowers/plans/long-memory-agent/2026-05-23-phase138-conflict-source-labels.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase138-conflict-source-labels.md
git commit -m "feat: label chapter conflict sources"
git push origin main
```
