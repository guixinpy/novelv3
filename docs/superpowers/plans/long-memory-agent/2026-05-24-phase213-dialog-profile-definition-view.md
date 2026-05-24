# Phase213 Dialog Profile Definition View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 Phase212 的 `agent_profile_definition` 接入对话 `action_result_view.detail_items` 和前端 fallback projection，让对话消息直接显示 Agent 角色、层级和委派边界。

**Architecture:** 复用 Phase212 的 definition 数据形状；只扩展投影展示，不改变 action result 原始业务语义、planner、executor、任务队列或审批行为。后端和前端使用相同的中文字段：`Agent 角色`、`编排层级`、`委派`。

**Tech Stack:** Python, pytest, TypeScript, Vitest.

---

## Reference Project Inputs

- OpenHuman：agent definition 中的 `agent_tier/subagents` 应能被运行视图观察；本阶段把 `tier/delegation_allowed` 显示到对话层。
- Hermes Agent：orchestrator/leaf role 边界应在进度事件里可见；本阶段用 `Agent 角色` 与 `委派` 暴露边界。
- OpenClaw：effective inventory 与 profile/policy 需要结构化 details；本阶段继续只展示摘要，不输出完整工具 schema。

## Files

- Modify: `backend/app/services/actions/action_result_view.py`
  - `_agent_discovery_detail_items()` 读取 `agent_profile_definition` 并追加角色、层级、委派状态。
- Modify: `backend/tests/test_dialogs.py`
  - 扩展 `test_get_messages_includes_agent_discovery_view_detail_items`。
- Modify: `frontend/src/components/chat/agentRunProjection.ts`
  - `agentDiscoveryDetailItems()` 读取 `agent_profile_definition`。
- Modify: `frontend/src/components/chat/agentRunProjection.test.ts`
  - 扩展 recovery preview fallback 与 execution feedback 用例。
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-24-phase213-dialog-profile-definition-view.md`
  - 记录 RED/GREEN、验证、参考项目转译。

## Tasks

### Task 1: RED Tests

- [x] **Step 1: Backend RED**

Extend `backend/tests/test_dialogs.py::test_get_messages_includes_agent_discovery_view_detail_items` with `agent_profile_definition` and assert detail items contain:

```python
{"label": "Agent 角色", "value": "worker"}
{"label": "编排层级", "value": "worker"}
{"label": "委派", "value": "不可委派"}
```

Run:

```powershell
pytest backend/tests/test_dialogs.py -k "agent_discovery_view" -q
```

Expected: FAIL because the view ignores profile definition fields.

- [x] **Step 2: Frontend RED**

Extend `frontend/src/components/chat/agentRunProjection.test.ts` recovery preview and execution feedback tests with `agent_profile_definition`, then assert the same detail items.

Run:

```powershell
npm run test:unit -- agentRunProjection
```

Expected: FAIL because fallback projection ignores profile definition fields.

### Task 2: Backend Projection

- [x] **Step 1: Add backend helpers**

Add helpers:

```python
def _agent_role_label(role: str) -> str: ...
def _delegation_label(value: object) -> str | None: ...
```

- [x] **Step 2: Append definition items**

In `_agent_discovery_detail_items()`, read:

```python
definition = data.get("agent_profile_definition") if isinstance(..., dict) else {}
```

Append:

- `Agent 角色`
- `编排层级`
- `委派`

- [x] **Step 3: GREEN backend**

Run:

```powershell
pytest backend/tests/test_dialogs.py -k "agent_discovery_view" -q
```

Expected: PASS.

### Task 3: Frontend Projection

- [x] **Step 1: Update fallback helper**

In `agentDiscoveryDetailItems()`, read `agent_profile_definition` and append role/tier/delegation details.

- [x] **Step 2: GREEN frontend**

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
python -m compileall backend/app/services/actions
git diff --check
```

- [x] **Step 2: Report and commit**

Update notes and commit:

```text
feat: show agent profile definition in dialog views
```
