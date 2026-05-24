# Phase212 Agent Profile Definition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `agent_profile` 从散落字符串升级为稳定的 profile definition projection，暴露 `display_name`、`role`、`tier`、`delegation_allowed`、`source` 和可委派 profile，为后续 Agent 编排和子代理边界做基础契约。

**Architecture:** 在 `agent_tool_surface_policy.py` 中新增单一 profile definition 来源；tool plan、run detail 和前端详情抽屉只读取投影，不改变 profile scope 过滤规则、planner 选工具逻辑或 executor 行为。

**Tech Stack:** Python, pytest, Vue, Vitest, TypeScript.

---

## Reference Project Inputs

- OpenHuman：agent definition 声明 `id/display_name/tools/subagents/agent_tier`，本阶段转译为 `agent_profile_definition`。
- Hermes Agent：subagent role 区分 `leaf/orchestrator`，worker 默认不继续委派，本阶段用 `delegation_allowed` 表达边界。
- OpenClaw：profile/policy 和 effective inventory 分离，本阶段 profile definition 只描述身份，不直接改变工具可见性。

## Files

- Modify: `backend/app/services/writing_agent/agent_tool_surface_policy.py`
  - 新增 `AGENT_PROFILE_DEFINITION_VERSION`、静态 profile metadata、definition builder。
- Modify: `backend/app/services/writing_agent/run_service.py`
  - `detail_payload()` 增加 `agent_profile_definition`，并标注 profile 来源。
- Modify: `backend/app/schemas/writing_agent.py`
  - response schema 增加 `agent_profile_definition`。
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
  - 覆盖 tool plan profile definitions。
- Modify: `backend/tests/test_writing_agent_runs.py`
  - 覆盖 run detail profile definition。
- Modify: `frontend/src/api/types.ts`
  - TypeScript 类型同步新增字段。
- Modify: `frontend/src/components/writingAgent/AgentRunDrawer.vue`
  - 摘要优先展示 definition 的 display name、role、tier、委派边界。
- Modify: `frontend/src/components/writingAgent/AgentRunDrawer.test.ts`
  - 覆盖 profile definition 展示。
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-24-phase212-agent-profile-definition.md`
  - 记录 RED/GREEN、验证、参考项目转译。

## Tasks

### Task 1: RED Tests

- [x] **Step 1: Backend tool plan RED**

Add assertions to `test_agent_tool_plan_exposes_agent_profile_tool_projection()`:

```python
definitions = projection["profile_definitions"]
assert definitions["version"] == "phase212.agent_profile_definition.v1"
assert definitions["profiles"]["orchestrator"]["role"] == "orchestrator"
assert definitions["profiles"]["orchestrator"]["delegation_allowed"] is True
assert "drafting_worker" in definitions["profiles"]["orchestrator"]["delegate_to_profiles"]
assert definitions["profiles"]["drafting_worker"]["tier"] == "worker"
assert definitions["profiles"]["drafting_worker"]["delegation_allowed"] is False
```

Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py -k "agent_profile_tool_projection" -q
```

Expected: FAIL because definitions do not exist.

- [x] **Step 2: Backend run detail RED**

Extend `test_agent_run_detail_exposes_agent_profile_projection_for_auto_plan()`:

```python
definition = payload["agent_profile_definition"]
assert definition["version"] == "phase212.agent_profile_definition.v1"
assert definition["profile"] == "orchestrator"
assert definition["display_name"] == "编排主控"
assert definition["role"] == "orchestrator"
assert definition["tier"] == "reasoning"
assert definition["delegation_allowed"] is True
assert definition["source"] == "planner_trace"
```

Run:

```powershell
pytest backend/tests/test_writing_agent_runs.py -k "profile_projection" -q
```

Expected: FAIL because run detail does not expose `agent_profile_definition`.

- [x] **Step 3: Frontend RED**

Extend `AgentRunDrawer.test.ts` to provide `agent_profile_definition` and assert:

```text
编排层级
reasoning
委派
可委派
```

Run:

```powershell
npm run test:unit -- AgentRunDrawer
```

Expected: FAIL because drawer ignores profile definition.

### Task 2: Implement Profile Definitions

- [x] **Step 1: Add definition builder**

In `agent_tool_surface_policy.py`, add:

```python
AGENT_PROFILE_DEFINITION_VERSION = "phase212.agent_profile_definition.v1"
AGENT_PROFILE_DEFINITIONS = {...}
def build_agent_profile_definitions_projection() -> dict[str, Any]: ...
def build_agent_profile_definition(profile: str | None, *, source: str | None = None) -> dict[str, Any] | None: ...
```

- [x] **Step 2: Wire tool plan projection**

Add `profile_definitions` to `build_agent_profile_tool_projection()`.

- [x] **Step 3: Wire run detail projection**

Import `build_agent_profile_definition()` in `run_service.py` and include `agent_profile_definition` in `_agent_profile_projection()`.

- [x] **Step 4: GREEN backend**

Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py -k "agent_profile_tool_projection" -q
pytest backend/tests/test_writing_agent_runs.py -k "profile_projection" -q
```

Expected: PASS.

### Task 3: Frontend Projection

- [x] **Step 1: Type update**

Add:

```ts
agent_profile_definition?: Record<string, unknown> | null
```

- [x] **Step 2: Drawer display**

Prefer `run.agent_profile_definition.display_name` for profile label and show:

- 编排层级: `tier`
- 委派: `delegation_allowed ? "可委派" : "不可委派"`

- [x] **Step 3: GREEN frontend**

Run:

```powershell
npm run test:unit -- AgentRunDrawer
```

Expected: PASS.

### Task 4: Validation, Report, Commit

- [x] **Step 1: Targeted validation**

Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py -k "agent_profile_tool_projection" -q
pytest backend/tests/test_writing_agent_runs.py -k "profile_projection or auto_plan" -q
npm run test:unit -- AgentRunDrawer
npm run build
git diff --check
```

- [x] **Step 2: Report and commit**

Update notes and commit:

```text
feat: define agent profile projection
```
