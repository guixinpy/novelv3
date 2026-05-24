# Phase206 Agent Tool Policy Projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 基于 Phase205 的 `agent_tool_surface`，在 `build_agent_tool_plan()` / `describe_agent_tools` 中增加 Agent 可消费的工具策略投影，帮助 planner 和后续 Agent loop 直接看到哪些工具可并行读取、哪些工具需要确认、哪些工具仍未分类。

**Architecture:** 不改变工具执行路径、不新增权限拦截器；只新增只读 projection。完整审计仍由 `inspect_agent_tool_contracts` 承担，Phase206 只提供 planner/Agent loop 的轻量决策摘要。

**Tech Stack:** Python, existing Writing Agent registry, pytest.

---

## Reference Project Inputs

- OpenHuman：把 scope / permission level 作为 agent planning 的一等输入。
- Hermes Agent：tool registry 与 toolset exposure 分离，Agent loop 读取工具集摘要后再选择工具。
- OpenClaw：allow/deny/approval policy 应建立在稳定 capability surface 上，而不是散落的字符串判断。

## Files

- Create: `backend/app/services/writing_agent/agent_tool_surface_policy.py`
  - 从 visible/hidden tools 汇总 policy projection。
- Modify: `backend/app/services/writing_agent/tool_registry.py`
  - 在 `build_agent_tool_plan()` 输出中增加 `tool_policy_projection`。
- Modify: `backend/app/services/writing_agent/planner.py`
  - 将 `tool_policy_projection` 放入 planner trace，便于后续 run trace 和恢复判断引用。
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
  - 覆盖 policy projection 的 summary、confirmation、parallel read、unclassified。
- Modify: `backend/tests/test_writing_agent_planner.py`
  - 覆盖 planner trace 携带 tool policy projection。
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-24-phase206-agent-tool-policy-projection.md`
  - 记录 RED/GREEN/T2、参考项目转译、下一阶段。

## Tasks

### Task 1: RED Tests

- [x] **Step 1: Add registry policy projection tests**

Assert:

- `tool_policy_projection.version == "phase206.agent_tool_surface_policy.v1"`
- summary includes visible/hidden/read/write/guarded/unclassified counts.
- `parallel_read_tools` includes `describe_agent_tools`.
- `confirmation_required_tools` includes at least one guarded write tool.
- `policy_rules` includes read parallelism, guarded confirmation, and unclassified visibility rules.

- [x] **Step 2: Add planner trace test**

Assert `build_writing_agent_run_plan(...).trace.tool_policy_projection` exists and carries the same version.

- [x] **Step 3: Run RED**

Expected: FAIL because projection does not exist yet.

### Task 2: Implement Projection

- [x] **Step 1: Add projection helper**

Create `build_agent_tool_surface_policy_projection(visible_tools, hidden_tools)`.

- [x] **Step 2: Wire registry and planner**

Attach projection to:

- `build_agent_tool_plan()` output
- planner `trace`

- [x] **Step 3: Run GREEN**

Run focused tests until green.

### Task 3: Validation

- [x] **Step 1: Targeted backend validation**

Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py -k "tool_policy_projection or agent_tool_plan_exposes" -q
pytest backend/tests/test_writing_agent_planner.py -q
pytest backend/tests/test_writing_agent_tool_executor.py -k "tool_executor_handles_describe_agent_tools" -q
```

- [x] **Step 2: T2 checks**

Run:

```powershell
python -m compileall backend/app/services/writing_agent
git diff --check
```

### Task 4: Review, Report, Commit

- [x] **Step 1: Review**

Ask reviewer to verify:

- no execution behavior changed;
- projection only reads `agent_tool_surface`;
- no sensitive data included;
- planner trace size remains bounded.

- [ ] **Step 2: Update report and commit**

Commit:

```text
feat: project agent tool policy surface
```
