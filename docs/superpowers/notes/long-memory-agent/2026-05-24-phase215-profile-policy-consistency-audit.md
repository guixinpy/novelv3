# Phase215 Profile Policy Consistency Audit Report

## Scope

为 Agent profile tool projection 增加 `consistency_audit`，用于静态检查：

- profile definition 是否都有对应工具策略；
- 工具策略 profile 是否都有对应 definition；
- `delegate_to_profiles` 目标是否存在 definition；
- `delegate_to_profiles` 目标是否存在工具策略；
- 不允许委派的 profile 是否错误声明了委派目标；
- 被委派目标是否仍是 leaf profile。

本阶段只做审计投影，不启用 runtime delegation，不改变 planner、executor、任务队列或 profile 工具可见性。

## Plan

见 `docs/superpowers/plans/long-memory-agent/2026-05-24-phase215-profile-policy-consistency-audit.md`。

## Reference Project Translation

子代理只读复核了三个参考项目，未修改文件。结论：

- OpenClaw：`tool-policy-pipeline`、tool catalog、subagent capabilities 体现了 inventory 与 effective visibility 分离；本阶段转译为 `consistency_audit`。
- Hermes Agent：registry/toolsets 与 `delegate_task` 分离；本阶段只学习 registered inventory vs exposed toolset，不引入 child agent runtime。
- OpenHuman：`AgentDefinition` / `agent.toml` 将 tools、disallowed_tools、subagents 数据化；本阶段把 novelv3 的 profile definition 和 profile policy 做静态一致性检查。

明确不照搬：

- OpenClaw 的 session spawn、handoff、runtime inherited allowlist。
- Hermes 的 `delegate_task` 执行器、子 Agent 线程、depth/concurrency runtime control。
- OpenHuman 的 mini LLM subagent runner、worker thread、prompt fork。
- 任何 `*` 或过宽默认授权。
- 静默跳过 unknown tool/subagent 的做法。

## RED

- `pytest backend/tests/test_writing_agent_tool_registry.py -k "agent_profile_tool_projection" -q`
  - 初始失败：导入 `build_agent_profile_policy_audit` 失败，且 projection 缺少 `consistency_audit`。
- `pytest backend/tests/test_writing_agent_tool_registry.py -k "profile_policy_audit" -q`
  - 初始失败：导入 `build_agent_profile_policy_audit` 失败。

## Implementation

- `agent_tool_surface_policy.py`
  - 新增 `AGENT_PROFILE_POLICY_AUDIT_VERSION = "phase215.agent_profile_policy_audit.v1"`。
  - 新增 `build_agent_profile_policy_audit()`。
  - 在 `build_agent_profile_tool_projection()` 中复用 `profile_definitions` 并追加 `consistency_audit`。
  - 审计输出包含 `status`、`summary`、`delegate_edges`、`issues`、`rules`。
- `test_writing_agent_tool_registry.py`
  - 扩展 ready-project profile projection 测试，要求 audit passed、0 issues、4 条 delegate edges。
  - 新增 helper 测试，验证 unknown delegate target 会产生 missing definition 和 missing tool rule 两个 issue。

## Validation

- `pytest backend/tests/test_writing_agent_tool_registry.py -k "agent_profile_tool_projection or profile_policy_audit" -q`
  - 2 passed, 62 deselected.
- `pytest backend/tests/test_writing_agent_tool_registry.py -q`
  - 64 passed.
- `python -m compileall backend/app/services/writing_agent`
  - passed.
- `git diff --check`
  - passed.
- DeepSeek key prefix scan
  - no matches in `backend frontend docs`.

## Review

- 审计为只读 projection，不参与执行器判断，因此不会扩大能力面。
- 输出使用机器可读 code，后续可接入 Trace、对话 detail 或 UI 检查面板。
- 当前只审计 profile/subagent 声明一致性；尚未审计 profile 声明的“期望工具”与实际工具集合差异，因为 profile definition 还没有显式 declared tools 字段。

## Novel Progress

本阶段不推进正文生成。原因：目标仍在将系统升级为可编排 Agent；本阶段为后续启用真正子代理/worker runtime 前补契约审计基础。

## Next

- 将 audit 投影接入 run detail 或对话消息的 compact warning，便于用户在当前 run 中看到 profile policy 不一致。
- 后续可引入 data-driven profile definition 字段，例如 `expected_tool_categories` / `declared_tools`，再审计 declared intent 与 effective tool surface 的差异。
