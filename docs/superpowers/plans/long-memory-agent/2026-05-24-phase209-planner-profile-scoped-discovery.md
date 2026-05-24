# Phase209 Planner Profile Scoped Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `build_writing_agent_run_plan()` 生成的第一步 `describe_agent_tools` 自动携带当前 intent 对应的 `agent_profile`，使自动计划从 profile-scoped 工具发现开始。

**Architecture:** 沿用 Phase208 的 `describe_agent_tools(agent_profile=...)` 行为；planner 只改变第一步工具发现参数，不改变后续步骤选择、审批契约和 executor 行为。该阶段是从“可请求 scoped tool discovery”推进到“自动计划默认使用 scoped discovery”的小步。

**Tech Stack:** Python, existing Writing Agent planner, pytest.

---

## Reference Project Inputs

- Hermes Agent：agent loop 传给模型的是当前 toolset，而不是全量 registry。
- OpenHuman：session builder 根据 agent definition 构建当前可见工具。
- OpenClaw：effective inventory 保留全量审计，实际调用上下文按 policy/profile 收窄。

## Files

- Modify: `backend/app/services/writing_agent/planner.py`
  - 第一条 `describe_agent_tools` step params 增加 `agent_profile`。
- Modify: `backend/tests/test_writing_agent_planner.py`
  - 覆盖 continue/review/recovery/setup/inspect intent 的首步 profile 参数。
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-24-phase209-planner-profile-scoped-discovery.md`
  - 记录 RED/GREEN/T2、审查、参考项目转译。

## Tasks

### Task 1: RED Tests

- [x] **Step 1: Add first-step profile assertions**

Update `backend/tests/test_writing_agent_planner.py`:

- continue next chapter first step params includes `agent_profile: drafting_worker`;
- review chapter first step params includes `agent_profile: reviewer_worker`;
- recovery first step params includes `agent_profile: recovery_worker`;
- setup project first step params includes `agent_profile: drafting_worker`;
- inspect tools first step params includes `agent_profile: orchestrator`.

- [x] **Step 2: Run RED**

Run:

```powershell
pytest backend/tests/test_writing_agent_planner.py -q
```

Expected: FAIL because `describe_agent_tools` params do not include `agent_profile`.

### Task 2: Implement Planner Wiring

- [x] **Step 1: Add profile to first step**

In `build_writing_agent_run_plan()`, change first `describe_agent_tools` params from:

```python
{"chapter_index": resolved_chapter_index}
```

to:

```python
{"chapter_index": resolved_chapter_index, "agent_profile": agent_profile}
```

- [x] **Step 2: Run GREEN**

Run:

```powershell
pytest backend/tests/test_writing_agent_planner.py -q
```

Expected: PASS.

### Task 3: Validation

- [x] **Step 1: Targeted backend validation**

Run:

```powershell
pytest backend/tests/test_writing_agent_planner.py -q
pytest backend/tests/test_writing_agent_tool_executor.py -k "describe_agent_tools" -q
pytest backend/tests/test_writing_agent_runs.py -k "auto_plan or recovery" -q
```

- [x] **Step 2: T2 checks**

Run:

```powershell
python -m compileall backend/app/services/writing_agent
git diff --check
```

### Task 4: Review, Report, Commit

- [x] **Step 1: Focused review**

Ask reviewer to verify:

- only first discovery step params changed;
- approval/write behavior unchanged;
- generated plan still keeps trace `agent_profile` and selected steps stable;
- profile-scoped discovery can be executed by existing `describe_agent_tools`.

- [ ] **Step 2: Update report and commit**

Commit:

```text
feat: plan profile scoped tool discovery
```
