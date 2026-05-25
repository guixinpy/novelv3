# Phase104 Dialog Route Unification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让自然语言 intent、按钮 action 和斜杠命令共享同一套 Writing Agent route projection，减少旧对话入口的并行边界。

**Architecture:** 新增通用 dialog agent route helper，以 action type 为核心映射到 Agent action/tool。`/` 命令只作为一种输入语法，text intent 和 button action 也写入同形态 `agent_route` 元数据。确认执行时继续剥离控制面元数据，具体工具只接收业务参数。

**Tech Stack:** FastAPI dialog API、IntentRouter、PendingAction JSON params、Writing Agent dialog control plane、pytest。

---

## Context

Phase103 已将 `/setup`、`/storyline`、`/outline`、`/chapter` 投影为 Agent 可见 route，并新增只读自查工具。但当前自然语言 intent 与 button action 仍各自直接创建 pending action，容易继续固化旧入口边界。长期目标要求“对话仍是入口，Agent 是主脑”，因此 Phase104 要把三类对话入口统一到同一 route 契约。

## Files

- Create: `backend/app/core/dialog_agent_routes.py`
  - 提供 action type -> Agent action/tool 的通用 route helper。
- Modify: `backend/app/core/chat_commands.py`
  - 斜杠命令 route 改为复用通用 route helper。
- Modify: `backend/app/api/dialogs.py`
  - command/text/button 创建 pending action 时均写入同形态 `agent_route`。
- Modify: `backend/app/services/writing_agent/slash_command_route.py`
  - 使用通用 route version；继续保留 slash route 自查输出。
- Modify: `backend/app/services/writing_agent/tool_registry.py`
  - 注册通用 dialog route projection 检查工具。
- Modify: `backend/app/services/writing_agent/tool_executor.py`
  - 执行通用 dialog route projection 检查工具。
- Modify: `backend/tests/test_dialogs.py`
  - 覆盖 text intent 和 button action 的 `agent_route`。
  - 覆盖确认执行后 `agent_route` 不进入 tool params。
- Modify: `docs/superpowers/notes/long-memory-agent/2026-05-22-phase104-dialog-route-unification.md`
  - 阶段报告。

## Success Criteria

- `/chapter` route 仍可用，并带 `source=slash_command`。
- text intent 创建 `preview_setup` 或 `preview_chapter` pending action 时带 `agent_route.source=text_intent`。
- button action 创建 pending action 时带 `agent_route.source=button_action`。
- confirmed Writing Agent run 的 tool params 不包含 `agent_route`。
- Agent 可通过 `inspect_agent_dialog_route_projection` 同时看到 slash/text/button 三类入口的 route projection。
- 不改变用户可见确认流程。
- 使用 T1 聚焦验证，不跑完整前后端测试。

## Tasks

### Task 1: Write failing tests for text/button route metadata

**Files:**
- Modify: `backend/tests/test_dialogs.py`

- [ ] Add assertions for text intent pending action route metadata.
- [ ] Add assertions for text intent confirmed run params isolation.
- [ ] Add assertions for button action route metadata.
- [ ] Run focused pytest and confirm failure before production changes.

Verification:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_dialogs.py -k "text_intent_creates_pending_setup_action or text_intent_confirm_routes_to_agent_run or chat_button_action_merges_project_id_with_extra_params or chat_command_registry_helpers_cover_expected_commands" -q
```

### Task 2: Implement common dialog route helper

**Files:**
- Create: `backend/app/core/dialog_agent_routes.py`
- Modify: `backend/app/core/chat_commands.py`

- [ ] Add `DIALOG_AGENT_ROUTE_VERSION`.
- [ ] Add explicit preview/generate action route mapping.
- [ ] Add `dialog_action_to_agent_tool_name()`.
- [ ] Add `build_dialog_agent_route()`.
- [ ] Make slash command route reuse the common helper.
- [ ] Re-run Task 1 focused tests.

### Task 3: Attach route metadata to text and button pending actions

**Files:**
- Modify: `backend/app/api/dialogs.py`

- [ ] Add `agent_route` to button action pending params when action is Agent-routable.
- [ ] Add `agent_route` to natural-language intent pending params when candidate is Agent-routable.
- [ ] Preserve existing `command_args`, `chapter_index`, and project id behavior.
- [ ] Re-run focused dialog tests.

### Task 4: Add unified route projection inspection

**Files:**
- Modify: `backend/app/services/writing_agent/slash_command_route.py`
- Modify: `backend/app/services/writing_agent/tool_registry.py`
- Modify: `backend/app/services/writing_agent/tool_executor.py`
- Modify: `backend/tests/test_writing_agent_tool_executor.py`

- [ ] Add failing test for `inspect_agent_dialog_route_projection`.
- [ ] Implement projection across `slash_command`, `text_intent`, and `button_action`.
- [ ] Include tool registration and execution backend health for each route.
- [ ] Re-run focused tool executor tests.

### Task 5: Verify and report

**Files:**
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-22-phase104-dialog-route-unification.md`

- [ ] Run T1 focused validation.
- [ ] Run `git diff --check`.
- [ ] Run targeted secret scan.
- [ ] Incorporate reference-project read-only subagent findings if available.
- [ ] Write phase report.
- [ ] Commit and push `main`.

Verification:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_dialogs.py backend/tests/test_writing_agent_tool_executor.py -k "command or slash_command or text_intent or chat_button_action or agent_control_plane or inspect_agent_slash_command_route" -q
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```
