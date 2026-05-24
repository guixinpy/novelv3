# Phase216 Profile Policy Audit Visibility Report

## Scope

把 Phase215 的 `agent_profile_policy_audit` 从 `describe_agent_tools` 的内部 tool plan 投影到运行详情和 compact UI：

- 后端 run detail API 暴露完整 `agent_profile_policy_audit`。
- 后端 `action_result_view.detail_items` 显示 compact `策略审计`。
- 前端 fallback projection 显示同样 compact 文案。
- `AgentRunDrawer` 运行摘要显示 compact `策略审计`。

本阶段不启用 runtime delegation，不改变 planner、executor、profile tool filtering、任务队列或自动恢复逻辑。

## Plan

见 `docs/superpowers/plans/long-memory-agent/2026-05-24-phase216-profile-policy-audit-visibility.md`。

## Reference Project Translation

子代理只读复核结论：Phase216 方向符合三个参考项目的工程取法，前提是保持“可观察性投影”边界。

- OpenClaw：tool policy pipeline 与 status helper 强调 compact、机器可读状态；本阶段只投影 status 和 issue count。
- Hermes Agent：delegation/toolset 运行态只把 summary/result 回传；本阶段不展开子代理内部细节。
- OpenHuman：AgentDefinition、full registry、model-visible tools 分离；本阶段 run detail 保留完整 audit，dialog/drawer 只显示 compact 摘要。

子代理建议补充的边界已进入测试：

- compact view 不渲染 `issue.code`。
- compact view 不渲染 delegate edge 目标如 `ghost_worker`。
- 完整 audit 保留在 run detail payload，供调试和后续工具读取。

## RED

- `pytest backend/tests/test_writing_agent_runs.py -k "profile_projection" -q`
  - 初始失败：`payload["agent_profile_policy_audit"]` 缺失。
- `pytest backend/tests/test_dialogs.py -k "profile_policy_audit" -q`
  - 初始失败：`detail_items` 缺少 `策略审计`。
- `npm run test:unit -- agentRunProjection`
  - 初始失败 1 项：fallback view 缺少 `策略审计`。
- `npm run test:unit -- AgentRunDrawer`
  - 初始失败 1 项：drawer 缺少 `策略审计`。

## Implementation

- `backend/app/services/writing_agent/run_service.py`
  - `detail_payload()` 增加 `agent_profile_policy_audit`。
  - 新增 `_agent_profile_policy_audit_from_steps()`，读取最新 `describe_agent_tools` step output 的 `agent_profile_tool_projection.consistency_audit`。
- `backend/app/schemas/writing_agent.py`
  - `WritingAgentRunDetail` 增加 `agent_profile_policy_audit`。
- `backend/app/services/actions/action_result_view.py`
  - 新增 `_profile_policy_audit_label()`。
  - `status == "passed"` 显示 `通过`。
  - `status == "needs_attention"` 显示 `需关注：N 个问题`。
- `frontend/src/api/types.ts`
  - `WritingAgentRunDetail` 增加 `agent_profile_policy_audit`。
- `frontend/src/components/chat/agentRunProjection.ts`
  - `agentDiscoveryDetailItems()` 显示 compact audit 状态。
- `frontend/src/components/writingAgent/AgentRunDrawer.vue`
  - 增加 audit computed 和 summary fact。
- Tests
  - 后端 run detail 保留完整 audit。
  - 后端 dialog / 前端 projection / drawer 只显示 compact 文案，不泄露 issue code 或 edge target。

## Validation

- `pytest backend/tests/test_writing_agent_runs.py -k "profile_projection" -q`
  - 1 passed, 175 deselected.
- `pytest backend/tests/test_dialogs.py -k "profile_policy_audit or agent_discovery_view" -q`
  - 2 passed, 94 deselected.
- `npm run test:unit -- agentRunProjection`
  - 36 passed.
- `npm run test:unit -- AgentRunDrawer`
  - 11 passed.
- `python -m compileall backend/app/services/writing_agent backend/app/services/actions`
  - passed.
- `npm run build`
  - `vue-tsc --noEmit && vite build` passed.
- `git diff --check`
  - passed; PowerShell emitted a CRLF normalization warning for `backend/tests/test_writing_agent_runs.py`, no whitespace errors.
- DeepSeek key prefix scan
  - no matches in `backend frontend docs`.

## Review

- Run detail API 保留完整 audit，便于后续 Trace/诊断工具读取。
- UI compact surfaces 只显示状态和问题数，不把 issue 细节写进对话正文或模型上下文。
- 当前 audit 仍是 observability，不阻断运行、不重算工具策略、不切换 profile。

## Novel Progress

本阶段不推进正文生成。原因：目标仍是把 novelv3 的模块升级为 Agent 可编排、可审计能力；该阶段为后续长篇创作压测中的 profile/tool policy 问题提供运行态可见性。

## Next

- 将 `agent_profile_policy_audit` 接入 Trace 审计或健康检查工具，使 Agent 能主动发现 profile policy 风险。
- 后续可把 profile definition 扩展为 data-driven declared tools/subagents，再审计 declared intent 与 effective tool surface 的差异。
