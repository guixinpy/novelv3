# Phase207 Agent Profile Tool Policy Report

## Scope

在 tool plan 中增加最小 Agent profile 工具过滤投影，并让 planner trace 记录当前 intent 对应的 profile。

## Plan

见 `docs/superpowers/plans/long-memory-agent/2026-05-24-phase207-agent-profile-tool-policy.md`。

## Reference Project Translation

- Hermes Agent：迁移 toolset exposure 思路，profile 只是决定模型可见工具面，不改变 executor。
- OpenHuman：迁移 agent tier / worker 边界，Planner/Orchestrator 偏只读，worker 才获得有限写能力。
- OpenClaw：迁移 effective inventory + allow/deny pipeline 的前置形态，本阶段先生成 profile 级工具投影。

## RED

- `pytest backend/tests/test_writing_agent_tool_registry.py -k "agent_profile_tool_projection" -q`
  - 初始失败：`KeyError: 'agent_profile_tool_projection'`。
- `pytest backend/tests/test_writing_agent_planner.py -k "ready_next_chapter_tool_chain or recovery_intent or review_only" -q`
  - 初始失败：`KeyError: 'agent_profile'`。

## Implementation

- `agent_tool_surface_policy.py` 增加 `AGENT_PROFILE_TOOL_POLICY_VERSION` 和最小 profile 规则：
  - `orchestrator`
  - `drafting_worker`
  - `reviewer_worker`
  - `world_model_worker`
  - `recovery_worker`
- `build_agent_tool_plan()` 输出 `agent_profile_tool_projection`。
- planner 将 intent 映射到当前 profile，并只把当前 profile projection 放入 trace。
- 按审查反馈修正：
  - 不用 `preflight` 非 read 一刀切规则，改为显式 denied tool。
  - `drafting_worker` 不直接获得整类 `athena_world_model` 写权限，只通过 override 允许 `analyze_chapter_world_model`。
  - 增加测试证明 profile projection 不改变 `visible_tools` / `hidden_tools`。

## Validation

- `pytest backend/tests/test_writing_agent_tool_registry.py -k "agent_profile_tool_projection or visibility" -q`
  - 2 passed, 61 deselected.
- `pytest backend/tests/test_writing_agent_planner.py -q`
  - 8 passed.
- `pytest backend/tests/test_writing_agent_tool_executor.py -k "tool_executor_handles_describe_agent_tools" -q`
  - 1 passed, 149 deselected.
- `pytest backend/tests/test_writing_agent_runs.py -k "auto_plan or recovery" -q`
  - 20 passed, 155 deselected.
- `python -m compileall backend/app/services/writing_agent`
  - passed.
- `git diff --check`
  - passed.
- Sensitive DeepSeek key-prefix scan
  - no matches.

## Review

- 子代理审查结论：
  - Critical: 无。
  - Important 1: `preflight` 非 read 一刀切会挡住合法 apply 链路。已改为显式 denied tool。
  - Important 2: `drafting_worker` 允许整类 `athena_world_model` 过宽。已改为只 override `analyze_chapter_world_model`。
  - Important 3: 缺少只读不改变行为测试。已补 `visible_tools` / `hidden_tools` 不变断言。
  - Minor: trace 只携带当前 profile projection，输出不含 schema、diagnostics、项目文本或敏感数据。

## Novel Progress

本阶段不推进正文生成。原因：当前阶段继续把原模块工具化并建立 Agent profile 边界。

## Next

- Phase208 建议把 `describe_agent_tools` 支持可选 `agent_profile` 参数，返回 profile-scoped visible tools，开始让模型实际消费被收窄的工具面。
