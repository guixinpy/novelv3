# Phase210 Agent Profile Run Projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Writing Agent run detail projection 中暴露当前 `agent_profile`、原始 `agent_profile_scope` 和归一化 `agent_tool_discovery` 状态，让前端与 Trace 能直接看到当前 Agent 使用的能力边界。

**Architecture:** 只新增只读投影，不改变 planner、executor、tool policy 或审批行为。投影从 `run.input.planner.trace.agent_profile`、首个 `describe_agent_tools` step input/output 中派生，并以稳定字段暴露给 API 和前端详情抽屉。

**Tech Stack:** Python, FastAPI response schema, pytest, Vue, Vitest, TypeScript.

---

## Reference Project Inputs

- Hermes Agent：agent loop 应把当前 agent 能见到的 toolset 作为运行上下文的一部分，而不是隐藏在内部步骤里。
- OpenHuman：session builder / agent definition 的身份信息应进入 session 可观测数据，便于确认当前 agent 能力边界。
- OpenClaw：effective inventory 和实际 scoped inventory 需要同时保留审计信号；本阶段先在 run projection 暴露 profile 与 scoped discovery summary，而不是迁移完整策略引擎。

## Files

- Modify: `backend/app/services/writing_agent/run_service.py`
  - 新增 run 级 `agent_profile`、`agent_profile_scope`、`agent_tool_discovery` 投影。
- Modify: `backend/app/schemas/writing_agent.py`
  - API response schema 增加投影字段。
- Modify: `backend/tests/test_writing_agent_runs.py`
  - RED 覆盖 profile-scoped discovery run detail/list projection。
- Modify: `frontend/src/api/types.ts`
  - TypeScript 类型同步新增字段。
- Modify: `frontend/src/components/writingAgent/AgentRunDrawer.vue`
  - 运行摘要中显示 Agent 身份、工具面状态、可见/过滤工具计数。
- Modify: `frontend/src/components/writingAgent/AgentRunDrawer.test.ts`
  - RED 覆盖详情抽屉展示中文 profile/status。
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-24-phase210-agent-profile-run-projection.md`
  - 记录 RED/GREEN、参考项目转译、验证证据和下一步。

## Tasks

### Task 1: RED Tests

- [x] **Step 1: Backend RED**

Add a test in `backend/tests/test_writing_agent_runs.py` that posts an auto-plan chapter generation run and asserts:

```python
assert payload["agent_profile"] == "drafting_worker"
assert payload["agent_profile_scope"]["status"] == "applied"
assert payload["agent_profile_scope"]["agent_profile"] == "drafting_worker"
assert payload["agent_profile_scope"]["allowed_visible_tool_count"] > 0
assert payload["agent_profile_scope"]["profile_filtered_visible_tool_count"] > 0
assert payload["agent_tool_discovery"]["scope_applied"] is True
assert payload["agent_tool_discovery"]["filter_stages"] == ["profile"]
```

Also fetch the same run detail with `GET /agent-runs/{run_id}` and assert the same projection is present.

Run:

```powershell
pytest backend/tests/test_writing_agent_runs.py -k "profile_projection" -q
```

Expected: FAIL because the response does not expose these fields.

- [x] **Step 2: Frontend RED**

Add a test in `frontend/src/components/writingAgent/AgentRunDrawer.test.ts` that mounts a run with:

```ts
agent_profile: 'drafting_worker',
  agent_tool_discovery: {
  version: 'phase210.agent_tool_discovery_projection.v1',
  scope_applied: true,
  scope_source: 'agent_profile',
  requested_profile: 'drafting_worker',
  effective_profile: 'drafting_worker',
  visible_tool_count: 12,
  filtered_by_profile_count: 7,
  filter_stages: ['profile'],
  }
```

Assert the drawer contains:

```text
Agent 身份
创作执行者
工具面
已按身份收窄
12
7
```

Run:

```powershell
npm run test:unit -- AgentRunDrawer
```

Expected: FAIL because UI does not render the projection.

### Task 2: Backend Projection

- [x] **Step 1: Implement helper**

Add helper functions in `run_service.py`:

```python
def _agent_profile_projection(run: WritingAgentRun, steps: list[WritingAgentStep]) -> dict[str, Any]:
    profile = _agent_profile_from_run_input(run) or _agent_profile_from_describe_step_input(steps)
    scope = _agent_profile_scope_from_steps(steps)
    if isinstance(scope, dict) and scope.get("agent_profile"):
        profile = str(scope.get("agent_profile") or profile or "").strip() or None
return {"agent_profile": profile, "agent_profile_scope": scope, "agent_tool_discovery": discovery}
```

Keep the helper read-only and tolerant of historical runs without profile metadata.

- [x] **Step 2: Wire detail payload and schema**

Include the projection in `detail_payload()` and list items if cheap:

```python
projection = _agent_profile_projection(run, steps)
return {**_model_dict(run), **projection, "steps": steps}
```

For `list_runs()`, avoid extra step queries in this phase; leave list items unchanged unless there is already enough data. This keeps the change surgical.

Update `WritingAgentRunDetail` schema so the response keeps the new fields.

- [x] **Step 3: GREEN backend**

Run:

```powershell
pytest backend/tests/test_writing_agent_runs.py -k "profile_projection" -q
```

Expected: PASS.

### Task 3: Frontend Display

- [x] **Step 1: Update TypeScript type**

Add optional fields to `WritingAgentRunDetail`:

```ts
agent_profile?: string | null
agent_profile_scope?: Record<string, unknown> | null
agent_tool_discovery?: Record<string, unknown> | null
```

- [x] **Step 2: Render projection**

In `AgentRunDrawer.vue`, add computed labels:

```ts
function agentProfileLabel(profile: unknown) {
  if (profile === 'orchestrator') return '编排主控'
  if (profile === 'drafting_worker') return '创作执行者'
  if (profile === 'reviewer_worker') return '审稿执行者'
  if (profile === 'world_model_worker') return '世界模型执行者'
  if (profile === 'recovery_worker') return '恢复维护者'
  return stringValue(profile) || '未标注'
}
```

Render summary facts when `run.agent_profile`, `run.agent_tool_discovery`, or `run.agent_profile_scope` is present. Prefer normalized `agent_tool_discovery` counts and fall back to raw scope for historical payloads.

- [x] **Step 3: GREEN frontend**

Run:

```powershell
npm run test:unit -- AgentRunDrawer
```

Expected: PASS.

### Task 4: Validation, Review, Report, Commit

- [x] **Step 1: Targeted validation**

Run:

```powershell
pytest backend/tests/test_writing_agent_runs.py -k "profile_projection or auto_plan" -q
npm run test:unit -- AgentRunDrawer
npm run build
git diff --check
```

- [x] **Step 2: Reference review**

Use subagent review to check:

- projection is derived, not changing execution behavior;
- historical runs without profile metadata still serialize;
- frontend labels are Chinese and do not leak raw internal status where a Chinese label exists;
- reference project learnings were translated, not copied.

- [x] **Step 3: Report and commit**

Update notes with RED/GREEN/validation and commit:

```text
feat: expose agent profile run projection
```
