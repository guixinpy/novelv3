# Phase207 Agent Profile Tool Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Phase206 的 effective tool inventory 基础上，增加最小 Agent profile 工具过滤投影，让 Writing Agent 后续能按 Orchestrator / Drafting / Reviewer / World Model / Recovery 等角色看到不同工具面。

**Architecture:** 只做只读投影，不做执行拦截。`build_agent_tool_plan()` 输出所有 profile 的 allowed/blocked 工具清单；planner trace 只携带当前 intent 对应的 profile 投影，避免 trace 膨胀。

**Tech Stack:** Python, existing Writing Agent registry, pytest.

---

## Reference Project Inputs

- Hermes Agent：toolsets 先限制模型暴露面，executor 再执行。
- OpenHuman：agent definition / agent tier / tool scope 分离，Planner 默认只读，Worker 才有写能力。
- OpenClaw：effective inventory + inherited allow/deny，为后续多层 policy pipeline 留接口。

## Files

- Modify: `backend/app/services/writing_agent/agent_tool_surface_policy.py`
  - 增加 profile 规则和 profile projection helper。
- Modify: `backend/app/services/writing_agent/tool_registry.py`
  - `build_agent_tool_plan()` 输出 `agent_profile_tool_projection`。
- Modify: `backend/app/services/writing_agent/planner.py`
  - intent -> agent profile 映射，并把当前 profile projection 放入 trace。
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
  - 覆盖 profile projection。
- Modify: `backend/tests/test_writing_agent_planner.py`
  - 覆盖 continue/review/recovery 的 profile 映射。
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-24-phase207-agent-profile-tool-policy.md`
  - 记录 RED/GREEN/T2、审查、参考项目转译。

## Tasks

### Task 1: RED Tests

- [x] **Step 1: Add registry profile tests**

Assert:

- `agent_profile_tool_projection.version == "phase207.agent_profile_tool_policy.v1"`
- `orchestrator.allowed_visible_tools` includes `describe_agent_tools` and excludes `generate_chapter`
- `drafting_worker.allowed_visible_tools` includes `generate_chapter`
- `reviewer_worker.allowed_visible_tools` includes `review_chapter_quality` and excludes `generate_chapter`
- profile summaries count allowed/blocked tools.

- [x] **Step 2: Add planner profile tests**

Assert:

- continue chapter -> `drafting_worker`
- review chapter -> `reviewer_worker`
- recovery -> `recovery_worker`

- [x] **Step 3: Run RED**

Expected: FAIL because profile projection does not exist.

### Task 2: Implement Profile Projection

- [x] **Step 1: Add profile rules**

Rules should be explicit and small:

- `orchestrator`: preflight / trace / read-only routing tools.
- `drafting_worker`: generation / knowledge / memory / review / world-model read-analysis.
- `reviewer_worker`: review / revision / knowledge / memory.
- `world_model_worker`: athena world model / knowledge / trace.
- `recovery_worker`: preflight / task queue / maintenance / trace / longform memory.

- [x] **Step 2: Wire registry and planner**

Attach:

- `agent_profile_tool_projection` to tool plan.
- selected `agent_profile` + `agent_profile_tool_projection` to planner trace.

### Task 3: Validation

- [x] **Step 1: Targeted backend validation**

Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py -k "agent_profile_tool_projection or tool_policy_projection" -q
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

- [x] **Step 1: Focused review**

Ask reviewer to verify:

- no execution behavior changed;
- profile rules are explicit and bounded;
- planner trace carries only selected profile projection;
- no project content or sensitive data appears in profile projection.

- [ ] **Step 2: Update report and commit**

Commit:

```text
feat: add agent profile tool policy projection
```
