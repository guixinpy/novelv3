# Phase43: Agent Run Command Contract Visibility

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 Agent run 详情和前端运行抽屉直接展示命令契约健康摘要，避免命令控制面只藏在 planner trace 内部。

**Architecture:** 后端从 auto-plan 的 `planner.trace.agent_health_projection.command_contracts` 抽取轻量摘要，作为 `agent_command_contracts` 投影暴露给 `WritingAgentRunDetail`。前端只展示摘要数字和状态，不展开完整命令清单，避免抽屉噪声过大。

**Tech Stack:** FastAPI/Pydantic、pytest、Vue 3、Vitest。

---

## 参考项目吸收

- hermes-agent：运行详情应暴露控制面诊断，而不是只把诊断埋在内部循环日志里。
- openhuman：投影需要带 provenance，前端展示摘要即可，详情仍保留在原始 trace 中。

## 成功标准

1. `GET /api/v1/projects/{project_id}/agent-runs/{run_id}` 返回 `agent_command_contracts`。
2. 该投影至少包含 `summary.gap_count`、`summary.agent_control_commands`、`summary.available_commands` 与 `source`。
3. `AgentRunDrawer` 展示“命令契约”摘要和缺口数量。
4. 不改变工具执行顺序，不新增 run step，不把完整 command list 展开到抽屉。

## Task 1: Backend Run Detail Projection

**Files:**
- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/app/schemas/writing_agent.py`
- Test: `backend/tests/test_writing_agent_runs.py`

- [ ] **Step 1: Write failing backend test**

Add an assertion to `test_agent_run_detail_exposes_agent_profile_projection_for_auto_plan`:

```python
    command_contracts = payload["agent_command_contracts"]
    assert command_contracts["source"] == "planner_trace.agent_health_projection.command_contracts"
    assert command_contracts["summary"]["agent_control_commands"] == 2
    assert isinstance(command_contracts["summary"]["gap_count"], int)
    assert detail_payload["agent_command_contracts"] == command_contracts
```

- [ ] **Step 2: Verify RED**

Run:

```powershell
pytest backend/tests/test_writing_agent_runs.py -k "agent_run_detail_exposes_agent_profile_projection_for_auto_plan" -q
```

Expected: FAIL because `agent_command_contracts` is missing.

- [ ] **Step 3: Implement projection helper**

Add a helper in `run_service.py`:

```python
def _agent_command_contracts_from_run(run: WritingAgentRun) -> dict[str, Any] | None:
    run_input = run.input if isinstance(run.input, dict) else {}
    planner = run_input.get("planner") if isinstance(run_input.get("planner"), dict) else {}
    trace = planner.get("trace") if isinstance(planner.get("trace"), dict) else {}
    health = trace.get("agent_health_projection") if isinstance(trace.get("agent_health_projection"), dict) else {}
    contracts = health.get("command_contracts") if isinstance(health.get("command_contracts"), dict) else {}
    summary = contracts.get("summary") if isinstance(contracts.get("summary"), dict) else {}
    if not summary:
        return None
    return {
        "source": "planner_trace.agent_health_projection.command_contracts",
        "summary": {
            "total_commands": _optional_int(summary.get("total_commands")) or 0,
            "public_commands": _optional_int(summary.get("public_commands")) or 0,
            "agent_control_commands": _optional_int(summary.get("agent_control_commands")) or 0,
            "available_commands": _optional_int(summary.get("available_commands")) or 0,
            "gap_count": _optional_int(summary.get("gap_count")) or 0,
        },
    }
```

Then include it in `detail_payload(...)` as `"agent_command_contracts": _agent_command_contracts_from_run(run)`.

- [ ] **Step 4: Update response schema**

Add to `WritingAgentRunDetail`:

```python
    agent_command_contracts: dict[str, Any] | None = None
```

- [ ] **Step 5: Verify GREEN**

Run:

```powershell
pytest backend/tests/test_writing_agent_runs.py -k "agent_run_detail_exposes_agent_profile_projection_for_auto_plan" -q
```

Expected: PASS.

## Task 2: Frontend Drawer Summary

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/components/writingAgent/AgentRunDrawer.vue`
- Test: `frontend/src/components/writingAgent/AgentRunDrawer.test.ts`

- [ ] **Step 1: Write failing frontend test**

Add a test that mounts `AgentRunDrawer` with:

```ts
agent_command_contracts: {
  source: 'planner_trace.agent_health_projection.command_contracts',
  summary: {
    total_commands: 8,
    public_commands: 5,
    agent_control_commands: 2,
    available_commands: 5,
    gap_count: 0,
  },
},
```

Assert the drawer contains `命令契约`、`控制命令`、`2`、`契约缺口`、`0`。

- [ ] **Step 2: Verify RED**

Run:

```powershell
cd frontend; .\node_modules\.bin\vitest run src/components/writingAgent/AgentRunDrawer.test.ts -t "renders command contract summary"
```

Expected: FAIL because drawer does not render this projection yet.

- [ ] **Step 3: Implement minimal UI**

Add `agentCommandContracts` and `agentCommandContractSummary` computed values in `AgentRunDrawer.vue`, then render three facts in the summary `<dl>`:

- `命令契约`: `已投影`
- `控制命令`: summary `agent_control_commands`
- `契约缺口`: summary `gap_count`

- [ ] **Step 4: Update TypeScript type**

Add to `WritingAgentRunDetail`:

```ts
  agent_command_contracts?: Record<string, unknown> | null
```

- [ ] **Step 5: Verify GREEN**

Run:

```powershell
cd frontend; .\node_modules\.bin\vitest run src/components/writingAgent/AgentRunDrawer.test.ts -t "renders command contract summary"
```

Expected: PASS.

## Task 3: Phase Verification and Report

**Files:**
- Create: `docs/superpowers/notes/agent-native-writing/2026-05-25-phase43-agent-run-command-contract-visibility.md`

- [ ] **Step 1: Run targeted verification**

Run:

```powershell
pytest backend/tests/test_writing_agent_runs.py -k "agent_run_detail_exposes_agent_profile_projection_for_auto_plan" -q
cd frontend; .\node_modules\.bin\vitest run src/components/writingAgent/AgentRunDrawer.test.ts -t "renders command contract summary"
cd ..; git diff --check
```

- [ ] **Step 2: Write phase report**

Record RED evidence, GREEN evidence, changed files, and next-phase recommendation.
