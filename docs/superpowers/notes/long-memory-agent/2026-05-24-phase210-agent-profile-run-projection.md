# Phase210 Agent Profile Run Projection Report

## Scope

在 Writing Agent run detail projection 中暴露当前 `agent_profile`、原始 `agent_profile_scope` 与归一化 `agent_tool_discovery` 状态，并在运行详情抽屉中展示中文化摘要。

## Plan

见 `docs/superpowers/plans/long-memory-agent/2026-05-24-phase210-agent-profile-run-projection.md`。

## Reference Project Translation

- Hermes Agent：运行上下文需要明确当前 agent 可见工具面；本阶段把 scoped discovery 从步骤 output 提升到 run projection。
- OpenHuman：agent/session identity 需要可观测；本阶段让 run detail 显示当前 profile。
- OpenClaw：保留审计信号而非只给最终工具列表；本阶段暴露 `allowed_visible_tool_count` 与 `profile_filtered_visible_tool_count`，帮助后续 Trace/UI 判断工具面是否过宽或过窄。
- 子代理调研补充：
  - OpenClaw 的 effective inventory 启发本阶段新增 `agent_tool_discovery` 归一化摘要，而不是让前端直接解析完整工具 schema。
  - Hermes Agent 的 profile 早期定型启发本阶段从 `run.input.planner.trace.agent_profile` 和首个 `describe_agent_tools` step 中派生 profile。
  - OpenHuman 的 agent identity / visible tools 分离启发本阶段同时保留 profile 身份与 scoped tool discovery 计数。
  - 明确不照搬 OpenClaw 多层 policy pipeline、Hermes 文件系统级 profile 隔离或 OpenHuman Rust agent registry。

## RED

- `pytest backend/tests/test_writing_agent_runs.py -k "profile_projection" -q`
  - 初始失败：`KeyError: 'agent_profile'`。
  - 第二轮 RED 失败：`KeyError: 'agent_tool_discovery'`。
- `npm run test:unit -- AgentRunDrawer`
  - 初始失败：详情抽屉不显示 `Agent 身份`。
  - 第二轮 RED 失败：仅提供归一化 `agent_tool_discovery` 时不显示 `工具面`。

## Implementation

- `detail_payload()` 新增 `_agent_profile_projection(run, steps)` 派生字段。
- `agent_profile` 来源优先级：
  1. `run.input.planner.agent_profile`
  2. `run.input.planner.trace.agent_profile`
  3. `run.input.tools[].params.agent_profile`
  4. 首个 `describe_agent_tools` step input params
  5. 首个 `describe_agent_tools` step output scope profile
- `agent_profile_scope` 保留 `describe_agent_tools` output 原始 scope。
- `agent_tool_discovery` 新增归一化摘要：
  - `version`
  - `status`
  - `scope_applied`
  - `scope_source`
  - `requested_profile`
  - `effective_profile`
  - `visible_tool_count`
  - `filtered_by_profile_count`
  - `hidden_tool_count`
  - `candidate_visible_tool_count`
  - `filter_stages`
  - `warnings`
- 前端 `AgentRunDrawer` 摘要区显示：
  - `Agent 身份`
  - `工具面`
  - `可见工具`
  - `已过滤`
- 前端优先读取 `agent_tool_discovery`，并对历史 payload 回退到 `agent_profile_scope`。

## Validation

- `pytest backend/tests/test_writing_agent_runs.py -k "profile_projection" -q`
  - 1 passed, 175 deselected.
- `npm run test:unit -- AgentRunDrawer`
  - 9 passed.
- `pytest backend/tests/test_writing_agent_runs.py -k "profile_projection or auto_plan" -q`
  - 14 passed, 162 deselected.
- `python -m compileall backend/app/services/writing_agent`
  - passed.
- `npm run build`
  - `vue-tsc --noEmit && vite build` passed.
- `git diff --check`
  - passed；仅提示 `backend/tests/test_writing_agent_runs.py` 将从 CRLF 转 LF。
- DeepSeek key prefix scan
  - no matches in `backend frontend docs`.

## Review

- 本地审查：
  - 投影只读取 `run.input` 和 steps，不改变 planner、executor、tool policy 或审批行为。
  - 历史 run 缺少 profile/scope 时返回 `None`，schema 允许空值。
  - 前端中文标签覆盖已知 profile 和 status，未知值保留原始值便于排障。
- 子代理调研结论：
  - 当前阶段不应迁移完整外部 Agent 框架，只需要轻量结构化投影。
  - 后续可进一步补 `role/source/tier`、filter stages、warning/notices，但应作为独立阶段推进。

## Novel Progress

本阶段不推进正文生成。原因：当前阶段继续把 Agent 工具化链路变成可观察、可调试的运行面；这是后续自主生成和问题定位的基础。

## Next

- Phase211 建议把 `agent_tool_discovery` 接入 dialog `action_result_view` 或 Trace audit 摘要，使用户从对话消息中也能看到本次 Agent 使用的 profile 和工具面。
- 后续可参考 OpenHuman loader 的 tier 约束，正式定义 orchestrator/worker 的委派边界。
