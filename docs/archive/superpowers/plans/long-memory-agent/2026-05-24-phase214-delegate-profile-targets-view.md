# Phase214 Delegate Profile Targets View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development. Keep this phase narrow: expose declared delegate targets as observability metadata only.

**Goal:** 把 `agent_profile_definition.delegate_to_profiles` 作为“可委派目标声明”展示到对话结果视图和运行抽屉，帮助用户理解当前 Agent profile 的编排边界。

**Non-Goal:** 不实现运行时委派、不新增按钮、不创建子任务、不声明 enforcement 已启用。

**Architecture:** 复用 Phase212/213 的 `agent_profile_definition` 投影。只有当 `delegation_allowed === true` 且 `delegate_to_profiles` 是非空数组时，展示 `可委派目标: N 个声明`。该字段表达 profile declaration，不表达当前 run 已实际生成子代理。

**Tech Stack:** Python, pytest, TypeScript, Vitest, Vue.

---

## Reference Project Inputs

- Hermes Agent：`delegate_task` 区分 `leaf/orchestrator`，并明确 depth、concurrency、orchestrator enablement 等运行时限制；本阶段只转译“目标声明可见”，不转译执行限制。
- OpenHuman：agent definition 把 tools/subagents 作为能力面声明；本阶段把 `delegate_to_profiles` 看作 profile 能力声明，而不是即时工具调用。
- OpenClaw：subagent/tool inventory 以 compact observable metadata 暴露；本阶段继续只展示摘要计数，不展开完整 profile schema。

## Files

- Modify: `backend/tests/test_dialogs.py`
- Modify: `backend/app/services/actions/action_result_view.py`
- Modify: `frontend/src/components/chat/agentRunProjection.test.ts`
- Modify: `frontend/src/components/chat/agentRunProjection.ts`
- Modify: `frontend/src/components/writingAgent/AgentRunDrawer.test.ts`
- Modify: `frontend/src/components/writingAgent/AgentRunDrawer.vue`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-24-phase214-delegate-profile-targets-view.md`

## Tasks

### Task 1: RED Tests

- [x] **Backend RED**

Add a dialog projection test with an orchestrator profile definition:

```python
{"label": "可委派目标", "value": "4 个声明"}
```

Run:

```powershell
pytest backend/tests/test_dialogs.py -k "delegate_profile_targets" -q
```

Expected: FAIL because backend projection currently ignores `delegate_to_profiles`.

- [x] **Frontend Projection RED**

Add a fallback projection test for `agentRunProjection.ts` with an orchestrator profile definition and assert:

```ts
{ label: '可委派目标', value: '4 个声明' }
```

Run:

```powershell
npm run test:unit -- agentRunProjection
```

Expected: FAIL because frontend fallback currently ignores `delegate_to_profiles`.

- [x] **Run Drawer RED**

Add an `AgentRunDrawer` test for orchestrator profile definition and assert it renders `可委派目标` and `4 个声明`.

Run:

```powershell
npm run test:unit -- AgentRunDrawer
```

Expected: FAIL because drawer currently only renders delegation allowed/denied.

### Task 2: Backend Projection

- [x] Add a helper/count check in `_agent_discovery_detail_items()`.
- [x] Append `可委派目标: N 个声明` only for enabled, non-empty delegate target arrays.
- [x] Re-run backend targeted test.

### Task 3: Frontend Projection

- [x] Add the same detail item to `agentDiscoveryDetailItems()`.
- [x] Add computed target count to `AgentRunDrawer.vue`.
- [x] Render `可委派目标` in the run summary only when count is positive.
- [x] Re-run frontend targeted tests.

### Task 4: Validation, Report, Commit

- [x] Run:

```powershell
pytest backend/tests/test_dialogs.py -k "delegate_profile_targets or agent_discovery_view or action_result_view" -q
npm run test:unit -- agentRunProjection
npm run test:unit -- AgentRunDrawer
python -m compileall backend/app/services/actions
npm run build
git diff --check
```

- [x] Run a DeepSeek key prefix scan without embedding the full key in files.
- [x] Write phase report and commit:

```text
feat: show delegate profile targets in agent views
```
