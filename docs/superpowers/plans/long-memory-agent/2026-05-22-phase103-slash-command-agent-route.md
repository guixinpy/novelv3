# Phase103 Slash Command Agent Route Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有 `/setup`、`/storyline`、`/outline`、`/chapter` 从旧式对话命令投影为 Writing Agent 可检查、可调度的工具路由。

**Architecture:** 斜杠命令仍保留为用户入口，但命令解析结果必须携带稳定的 Agent route 元数据。确认执行时，元数据只用于控制面审计和路由判断，不应泄漏到具体工具参数。Writing Agent 还需要提供一个只读检查工具，让 Agent 能自查当前可用的斜杠命令到工具映射。

**Tech Stack:** FastAPI dialog API、SQLAlchemy PendingAction JSON params、Writing Agent tool registry/executor、pytest。

---

## Context

本 goal 的重点不是让操作者手动写小说，而是把 novelv3 升级为专精网络小说创作的长期记忆 Agent。斜杠命令是当前对话入口的重要遗留边界，如果继续只把它看成 UI 快捷命令，就会阻碍 Agent 自主编排。因此本阶段处理一个小而关键的切面：让斜杠命令先具备 Agent 可见的工具路由契约。

## Files

- Modify: `backend/app/core/chat_commands.py`
  - 为生成类命令补充 Agent 工具名和 Agent action type。
  - 暴露 route 投影 helper。
- Modify: `backend/app/api/dialogs.py`
  - 创建 pending action 时写入 `agent_route` 元数据。
- Modify: `backend/app/services/writing_agent/dialog_control_plane.py`
  - 将 `agent_route` 等控制面元数据从工具 params 中剥离，避免污染工具输入。
- Create: `backend/app/services/writing_agent/slash_command_route.py`
  - 生成 Writing Agent 可读取的斜杠命令路由投影。
- Modify: `backend/app/services/writing_agent/tool_registry.py`
  - 注册只读检查工具 `inspect_agent_slash_command_route`。
- Modify: `backend/app/services/writing_agent/tool_executor.py`
  - 执行该检查工具。
- Modify: `backend/tests/test_dialogs.py`
  - 覆盖 route helper、pending action 元数据和确认执行参数隔离。
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
  - 覆盖 Writing Agent 对斜杠命令路由投影的自查能力。
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-22-phase103-slash-command-agent-route.md`
  - 阶段报告。

## Success Criteria

- `/setup`、`/storyline`、`/outline`、`/chapter` 都能映射到对应 Writing Agent tool。
- `/clear`、`/compact` 这类非生成命令不暴露为 Agent 生成工具。
- pending action params 包含可审计的 `agent_route`。
- confirmed action 派发到 Writing Agent run 时，实际 tool params 不包含 `agent_route`。
- Agent 可通过 `inspect_agent_slash_command_route` 获取当前 route 投影。
- 使用 T1 聚焦验证，不跑完整前后端测试。

## Tasks

### Task 1: Write failing tests for route projection

**Files:**
- Modify: `backend/tests/test_dialogs.py`

- [ ] Add assertions that generation commands expose Agent route metadata.
- [ ] Add assertions that non-generation commands do not expose Agent tool names.
- [ ] Run focused pytest and confirm the new assertions fail before implementation.

Verification:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_dialogs.py -k "chat_command_registry_helpers_cover_expected_commands" -q
```

### Task 2: Implement chat command route helpers

**Files:**
- Modify: `backend/app/core/chat_commands.py`

- [ ] Extend command specs with `agent_action_type` and `agent_tool_name`.
- [ ] Add `CHAT_COMMAND_AGENT_ROUTE_VERSION`.
- [ ] Add `command_to_agent_tool_name()`.
- [ ] Add `command_agent_route()`.
- [ ] Add `agent_slash_command_routes()`.
- [ ] Re-run Task 1 test and confirm green.

### Task 3: Persist route metadata and keep tool params clean

**Files:**
- Modify: `backend/tests/test_dialogs.py`
- Modify: `backend/app/api/dialogs.py`
- Modify: `backend/app/services/writing_agent/dialog_control_plane.py`

- [ ] Add failing assertion that pending slash actions include `agent_route`.
- [ ] Add failing assertion that confirmed Writing Agent tool params strip `agent_route`.
- [ ] Populate `agent_route` during command pending-action creation.
- [ ] Strip control metadata in dialog control plane before building `WritingAgentToolRequest`.
- [ ] Re-run focused dialog tests.

### Task 4: Add Agent self-inspection tool

**Files:**
- Create: `backend/app/services/writing_agent/slash_command_route.py`
- Modify: `backend/app/services/writing_agent/tool_registry.py`
- Modify: `backend/app/services/writing_agent/tool_executor.py`
- Modify: `backend/tests/test_writing_agent_tool_executor.py`

- [ ] Add failing test for `inspect_agent_slash_command_route`.
- [ ] Implement route projection service.
- [ ] Register descriptor with conservative read-only schema.
- [ ] Add executor branch.
- [ ] Re-run focused executor test.

### Task 5: Stage report and verification

**Files:**
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-22-phase103-slash-command-agent-route.md`

- [ ] Run T1 focused validation.
- [ ] Run `git diff --check`.
- [ ] Run a targeted secret scan.
- [ ] Write phase report with implementation, verification evidence, and next phase suggestion.
- [ ] Commit and push `main`.

Verification:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_dialogs.py backend/tests/test_writing_agent_tool_executor.py -k "command or slash_command or agent_control_plane or inspect_agent_slash_command_route" -q
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```
