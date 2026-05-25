# Phase211 Dialog Agent Discovery View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让对话消息的 `action_result_view.detail_items` 能显示 Agent 身份与 profile-scoped tool discovery 摘要，避免用户必须打开 run drawer 才能确认本次 Agent 使用的工具面。

**Architecture:** 复用 Phase210 的 `agent_profile` / `agent_tool_discovery` 数据形状；只在后端 `action_result_view` 和前端 fallback projection 中新增中文 detail items，不改变 action result 原始数据、planner、executor 或任务队列行为。

**Tech Stack:** Python, pytest, TypeScript, Vitest.

---

## Reference Project Inputs

- OpenClaw：trace/event details 使用结构化字段，UI 读取压缩摘要；本阶段把 profile/tool discovery 转成少量 detail items。
- Hermes Agent：profile 在运行上下文中应可见；本阶段让对话消息也能看到 profile，而不是只在详情页中看到。
- OpenHuman：visible tools 与 agent identity 分离；本阶段对话视图同时显示 Agent 身份、工具面状态、可见工具数和过滤数。

## Files

- Modify: `backend/app/services/actions/action_result_view.py`
  - 新增 `agent_profile` / `agent_tool_discovery` detail item 构造。
- Modify: `backend/tests/test_dialogs.py`
  - 覆盖 server-side `action_result_view` 中的 Agent 身份与工具面摘要。
- Modify: `frontend/src/components/chat/agentRunProjection.ts`
  - 前端 fallback projection 读取同样的数据。
- Modify: `frontend/src/components/chat/agentRunProjection.test.ts`
  - 覆盖 fallback action result view 和 run execution feedback。
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-24-phase211-dialog-agent-discovery-view.md`
  - 记录 RED/GREEN、验证和参考项目转译。

## Tasks

### Task 1: RED Tests

- [x] **Step 1: Backend RED**

Add a test in `backend/tests/test_dialogs.py` using `_save_message()` with `action_result.data.agent_profile` and `action_result.data.agent_tool_discovery`, then assert `DialogMessageService.list_messages()` returns `action_result_view.detail_items` containing:

```python
{"label": "Agent 身份", "value": "创作执行者"}
{"label": "工具面", "value": "已按身份收窄"}
{"label": "可见工具", "value": "12 个"}
{"label": "已过滤", "value": "7 个"}
```

Run:

```powershell
pytest backend/tests/test_dialogs.py -k "agent_discovery_view" -q
```

Expected: FAIL because the view ignores these fields.

- [x] **Step 2: Frontend RED**

Add tests in `frontend/src/components/chat/agentRunProjection.test.ts` asserting fallback views include the same detail items when `agent_profile` and `agent_tool_discovery` are present.

Run:

```powershell
npm run test:unit -- agentRunProjection
```

Expected: FAIL because fallback projection ignores these fields.

### Task 2: Backend Projection

- [x] **Step 1: Add label helpers**

Add backend helpers:

```python
def _agent_profile_label(profile: str) -> str: ...
def _agent_tool_scope_status_label(status: str) -> str: ...
```

- [x] **Step 2: Append detail items**

Append profile/tool discovery items to `_detail_items()` for any action result whose `data` includes profile/discovery metadata. Keep existing item order for old payloads.

- [x] **Step 3: GREEN backend**

Run:

```powershell
pytest backend/tests/test_dialogs.py -k "agent_discovery_view" -q
```

Expected: PASS.

### Task 3: Frontend Fallback Projection

- [x] **Step 1: Add shared fallback helpers**

Add `agentDiscoveryDetailItems(data)` and label helpers in `agentRunProjection.ts`.

- [x] **Step 2: Use helpers**

Use helpers in recovery preview/action execution fallback views and `buildAgentRunExecutionFeedback(run)`.

- [x] **Step 3: GREEN frontend**

Run:

```powershell
npm run test:unit -- agentRunProjection
```

Expected: PASS.

### Task 4: Validation, Report, Commit

- [x] **Step 1: Targeted validation**

Run:

```powershell
pytest backend/tests/test_dialogs.py -k "agent_discovery_view or action_result_view or agent_run" -q
npm run test:unit -- agentRunProjection
npm run build
git diff --check
```

- [x] **Step 2: Report and commit**

Update phase notes and commit:

```text
feat: show agent discovery in dialog result views
```
