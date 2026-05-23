# Phase192 Dialog Control Plane Approval Opt-In Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 dialog pending action 增加显式 opt-in 路由，让 setup/storyline/outline 可以在不改变默认行为的前提下切到 Agent approval prepare wrapper。

**Architecture:** 在 `dialog_control_plane.py` 中新增只读控制参数 `use_agent_approval_chain`，由 `_tool_name_for_action` 在显式启用时选择 `APPROVED_DIALOG_CONTROL_PLANE_CHAINS[action_type][0]`。该控制参数必须从最终 tool params 中剥离，避免传到底层生成工具；默认行为保持 legacy action tool 不变。

**Tech Stack:** Python 3、pytest、Writing Agent service layer、dialog pending action control plane。

---

## Files

- Modify: `backend/app/services/writing_agent/dialog_control_plane.py`
- Modify: `backend/tests/test_dialogs.py`
- Add: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase192-dialog-control-plane-approval-opt-in.md`

## Success Criteria

- `generate_setup` 默认确认仍 dispatch 到 `generate_setup`。
- `generate_setup` 显式 `use_agent_approval_chain=True` 时 dispatch 到 `prepare_generate_setup_execution`。
- `generate_storyline` 显式 opt-in 时 dispatch 到 `prepare_generate_storyline_execution`。
- `generate_outline` 显式 opt-in 时 dispatch 到 `prepare_generate_outline_execution`。
- `use_agent_approval_chain` 不出现在 `run.input["tools"][0]["params"]` 或 task payload tool params 中。
- `generate_chapter` 现有 prepare/execute 逻辑不变。

## Non-Scope

- 不默认切换 setup/storyline/outline 的 runtime 路由。
- 不修改前端 pending action UI。
- 不执行真实生成。
- 不改变 approval wrapper 工具自身行为。

## Tasks

### Task 1: RED Dialog Control Plane Tests

- [x] Add direct service-level tests in `backend/tests/test_dialogs.py`:
  - default setup route remains `generate_setup`
  - opt-in setup route uses `prepare_generate_setup_execution`
  - opt-in storyline route uses `prepare_generate_storyline_execution`
  - opt-in outline route uses `prepare_generate_outline_execution`
  - control param is stripped from run/task params.
- [x] Run expected RED:

```powershell
pytest backend/tests/test_dialogs.py -k "approval_chain_opt_in" -q
```

Expected: opt-in tests fail because `use_agent_approval_chain` is not implemented and route remains legacy.

### Task 2: Implement Minimal Opt-In Dispatch

- [x] Add control param constant:

```python
APPROVAL_CHAIN_OPT_IN_PARAM = "use_agent_approval_chain"
```

- [x] Add it to `CONTROL_PLANE_PARAM_KEYS`.
- [x] Update `_tool_name_for_action` to:
  - keep chapter approval execute contract first
  - return recommended prepare wrapper only when opt-in is true and recommended chain exists
  - otherwise return existing `SUPPORTED_DIALOG_ACTION_TO_TOOL[action_type]`.

### Task 3: GREEN Targeted Verification

- [x] Run:

```powershell
pytest backend/tests/test_dialogs.py -k "approval_chain_opt_in" -q
pytest backend/tests/test_dialogs.py -k "agent_control_plane_routes_confirmed_setup_through_writing_agent_run or resolve_chapter_action_confirm_dispatches_prepare_tool or chapter_approval_followup_dispatches_execute_tool" -q
python -m compileall backend/app/services/writing_agent
```

### Task 4: T2 Regression Slice

- [x] Run:

```powershell
pytest backend/tests/test_dialogs.py -q
pytest backend/tests/test_writing_agent_tool_executor.py -k "dialog_control_plane_projection or route_preference_projection or prepare_generate_setup_execution or prepare_generate_storyline_execution or prepare_generate_outline_execution" -q
```

### Task 5: Report, Hygiene, Commit, Push

- [x] Run:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

- [x] Write report:

```text
docs/superpowers/notes/long-memory-agent/2026-05-23-phase192-dialog-control-plane-approval-opt-in.md
```

- [ ] Commit and push:

```powershell
git add backend/app/services/writing_agent/dialog_control_plane.py backend/tests/test_dialogs.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase192-dialog-control-plane-approval-opt-in.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase192-dialog-control-plane-approval-opt-in.md
git commit -m "feat: opt in dialog approval routes"
git push origin main
```
