# Phase220 Report: Continuation Profile Policy Health

## Scope

本阶段把 profile/tool policy 的 compact health 接入 `output.continuation_state`。现在运行结果和 run detail 消费者可以直接看到当前 run 的 profile policy 是否通过、缺失或需要关注。

本阶段不改变执行、planner selection、profile filtering、recovery 或 followup 行为。

## Plan

见 `docs/superpowers/plans/long-memory-agent/2026-05-24-phase220-continuation-profile-policy-health.md`。

## RED

扩展 `test_agent_run_detail_exposes_agent_profile_projection_for_auto_plan()`：

- 断言 `output.continuation_state.profile_policy_health` 存在。
- 断言 `passed` 状态下无推荐工具。
- 断言 compact health 不包含 raw `delegate_edges`。

初始失败符合预期：

```text
KeyError: 'profile_policy_health'
```

## Implementation

- `backend/app/services/writing_agent/run_service.py`
  - 新增 `_profile_policy_health(steps)`。
  - `_continuation_state(...)` 增加 `profile_policy_health`。
  - 复用 `_agent_profile_policy_audit_from_steps(steps)`。
  - full audit 仍只保留在 run detail top-level `agent_profile_policy_audit`，continuation state 只输出 compact health。
- `backend/tests/test_writing_agent_runs.py`
  - 覆盖 auto-plan result 的 compact health。

## Validation

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py -k "agent_profile_projection_for_auto_plan or continuation_state_exposes_recommended_followups" -q`
  - 2 passed, 174 deselected.
- `backend\.venv\Scripts\python.exe -m compileall backend\app\services\writing_agent`
  - passed.
- `git diff --check`
  - passed; PowerShell/Git emitted a CRLF normalization warning for `backend/tests/test_writing_agent_runs.py`, no whitespace errors.
- DeepSeek key prefix scan:
  - `$pat='sk-'+'f6aa'; rg -n $pat backend frontend docs --glob '!frontend/node_modules/**'`
  - no matches.

## Review

Phase217 让 Trace 能看到 profile policy audit，Phase218 让 Agent 能聚合健康投影，Phase219 让 planner trace 带上 health evidence。本阶段则把运行态 continuation state 补齐，让用户/Agent 在看一个 run 的后续状态时也能看到 profile policy health。

这是从“可查”走向“运行态可解释”的一小步，仍然不自动修改路由或执行写入。

## Novel Progress

本阶段不推进正文生成。原因：当前仍在补 Agent 自主编排前的可解释运行状态，后续真实长篇 dogfood 会用这些状态判断系统是否能在低细节用户输入下稳定推进。

## Next

- 把 `profile_policy_health` 和 `agent_health_projection` 做 compact UI 展示。
- 后续可让 planner 在 `profile_policy_health.needs_attention` 时优先推荐 `inspect_agent_health_projection`。
- 开始一次短 dogfood：用低细节“继续写下一章”请求，观察 health trace、continuation state 和 followup 是否能串起来。
