# Phase209 Planner Profile Scoped Discovery Report

## Scope

让 planner 生成的第一步 `describe_agent_tools` 自动携带当前 intent 对应的 `agent_profile`。

## Plan

见 `docs/superpowers/plans/long-memory-agent/2026-05-24-phase209-planner-profile-scoped-discovery.md`。

## Reference Project Translation

- Hermes Agent：把当前 toolset 作为 agent loop 的工具发现入口，本阶段让 planner 的第一步工具发现带上 profile。
- OpenHuman：session builder 按 agent definition 构建可见工具，本阶段对应 planner 自动传入当前 `agent_profile`。
- OpenClaw：全量 effective inventory 保留在 trace/projection 中，但实际 discovery request 按 policy/profile 收窄。

## RED

- `pytest backend/tests/test_writing_agent_planner.py -q`
  - 初始失败 6 项：continue / approved_prepare / recovery / review / setup / inspect 的第一步 `describe_agent_tools` params 缺少 `agent_profile`。

## Implementation

- `build_writing_agent_run_plan()` 的第一步 `describe_agent_tools` params 从 `{"chapter_index": resolved_chapter_index}` 改为 `{"chapter_index": resolved_chapter_index, "agent_profile": agent_profile}`。
- 未改变 `_build_*_plan()` 后续 step 选择逻辑。
- 未改变 approval contract、executor 或 tool adapter 行为。

## Validation

- `pytest backend/tests/test_writing_agent_planner.py -q`
  - 8 passed.
- `pytest backend/tests/test_writing_agent_tool_executor.py -k "describe_agent_tools" -q`
  - 3 passed, 149 deselected.
- `pytest backend/tests/test_writing_agent_runs.py -k "auto_plan or recovery" -q`
  - 20 passed, 155 deselected.
- `pytest backend/tests/test_dialogs.py -k "agent_run or recovery_preview or low_detail_continue" -q`
  - 7 passed, 86 deselected.
- `python -m compileall backend/app/services/writing_agent`
  - passed.
- `git diff --check`
  - passed.
- Sensitive DeepSeek key-prefix scan
  - no matches.

## Review

- 子代理审查结论：
  - Critical: 无。
  - Important: 无。
  - Minor: 首步 `params` 变化会改变首步 `step_id`，属预期内变化；approval contract 只纳入写步骤，不受影响。
  - 覆盖情况：continue、approved_prepare、recovery、review、setup、默认 inspect 都有首步 profile 断言。

## Novel Progress

本阶段不推进正文生成。原因：当前阶段继续把 Agent 工具发现链路接入 profile-scoped 工具面。

## Next

- Phase210 建议让 dialog intent planner / run projection 在展示层明确标注 `agent_profile` 和 profile-scoped discovery 状态，方便前端与调试面板确认 Agent 当前使用的是哪类工具面。
