# Phase208 Profile Scoped Describe Tools Report

## Scope

让 `describe_agent_tools` 支持可选 `agent_profile` 参数，按 Phase207 profile projection 返回收窄后的模型可见工具面。

## Plan

见 `docs/superpowers/plans/long-memory-agent/2026-05-24-phase208-profile-scoped-describe-tools.md`。

## Reference Project Translation

- Hermes Agent：把模型可见工具面收窄到当前 toolset，而不是把全局 registry 全量交给模型。
- OpenHuman：session builder 按 agent definition 过滤工具，本阶段对应 `agent_profile` 参数。
- OpenClaw：保留 effective inventory 作为审计基础，但 agent-facing tool list 由 policy/profile scope 收窄。

## RED

- `pytest backend/tests/test_writing_agent_tool_executor.py -k "describe_agent_tools" -q`
  - 初始失败：默认输出缺少 `agent_profile_scope`。
  - 初始失败：`reviewer_worker` profile 未收窄 `visible_tools`。

## Implementation

- `describe_agent_tools` input schema 增加专用可选 `agent_profile`，不污染 `preflight_writing` 的 `_CHAPTER_PARAMS`。
- `_describe_agent_tools` 在生成完整 tool plan 后调用 `apply_agent_profile_tool_scope()`。
- `apply_agent_profile_tool_scope()` 行为：
  - 不传 profile：兼容完整输出，并标记 `agent_profile_scope.status = "not_requested"`。
  - 传未知 profile：fail-closed，返回空 `visible_tools` / `hidden_tools`，并给出 `available_profiles`。
  - 传已知 profile：只返回 profile allowed visible/hidden tools。
  - profile-filtered visible tools 不再带完整 schema 出现在 hidden tools；只在 `agent_profile_scope.profile_filtered_visible_tools` 记录工具名。
  - scoped 输出重新生成 `tool_policy_projection` / `agent_profile_tool_projection`，避免继续暴露未授权工具全集。

## Validation

- `pytest backend/tests/test_writing_agent_tool_executor.py -k "describe_agent_tools" -q`
  - 3 passed, 149 deselected.
- `pytest backend/tests/test_writing_agent_tool_executor.py -k "describe_agent_tools or inspect_agent_tool_contracts" -q`
  - 5 passed, 147 deselected.
- `pytest backend/tests/test_writing_agent_tool_registry.py -k "agent_profile_tool_projection or tool_policy_projection" -q`
  - 2 passed, 61 deselected.
- `pytest backend/tests/test_writing_agent_planner.py -q`
  - 8 passed.
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
  - Important 1: scoped 输出保留全量 projection 会暴露未授权工具名。已改为按 scoped visible/hidden 重新生成 projection。
  - Important 2: profile-filtered 工具放入 hidden 会泄露完整 schema。已改为只在 `profile_filtered_visible_tools` 记录名称，不返回工具契约。
  - Important 3: 未知 profile fail-open。已改为 fail-closed 空工具面。
  - Minor: `_CHAPTER_PARAMS` 共享 schema 会让 `preflight_writing` 误展示 `agent_profile`。已拆出 `describe_agent_tools` 专用输入 schema。

## Novel Progress

本阶段不推进正文生成。原因：当前阶段开始让 Agent 实际消费 profile-scoped 工具集，为后续自主编排创作链路打基础。

## Next

- Phase209 建议让 `plan_writing_agent_run` / dialog intent planner 在第一步 `describe_agent_tools` 中显式传入 `agent_profile`，使自动计划真正从 profile-scoped 工具发现开始。
