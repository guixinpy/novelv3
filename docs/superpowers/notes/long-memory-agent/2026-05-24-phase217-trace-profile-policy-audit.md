# Phase217 Report: Trace Profile Policy Audit

## Scope

本阶段把 Phase215/216 已产生的 profile/tool policy 一致性审计，接入 Writing Agent 的 Trace 审计工具 `inspect_agent_trace_audit`。

这仍然是只读可观察性改进：不改变 planner、executor、profile filtering、delegation runtime 或 recovery gate。

## Plan

见 `docs/superpowers/plans/long-memory-agent/2026-05-24-phase217-trace-profile-policy-audit.md`。

## Reference Project Translation

- OpenClaw：policy/health findings 应该以机器可读 status 和 issue snapshot 暴露，而不是只留在内部日志。
- Hermes Agent：delegation/toolset 报告应返回 compact 摘要，避免把子代理或 delegate edge 细节泄露到高层 Trace。
- OpenHuman：visible tool specs、registry 和运行 trace 应可检查，但完整策略内部结构应和面向 Agent 的 compact view 分层。

本阶段采用这些原则：Trace 工具可看到 `status`、`issue_count` 和 compact issues，但不输出完整 `delegate_edges`。

## RED

新增 `test_inspect_agent_trace_audit_includes_profile_policy_audit()`。

初始失败符合预期：

```text
KeyError: 'profile_policy_status'
```

说明 `inspect_agent_trace_audit` 尚未暴露 profile policy audit。

## Implementation

- `backend/app/services/writing_agent/agent_trace_audit.py`
  - 新增 `_profile_policy_audit_from_steps()`：从最新 `describe_agent_tools` step 的 `agent_profile_tool_projection.consistency_audit` 读取审计。
  - 新增 `_profile_policy_audit_summary()`：输出 compact/sanitized 结构。
  - `inspect_agent_trace_audit()` 增加：
    - `audit.profile_policy_status`
    - `audit.profile_policy_issue_count`
    - top-level `profile_policy_audit`
- `backend/tests/test_writing_agent_trace_audit.py`
  - 覆盖 Trace audit 能读取 profile policy audit。
  - 覆盖 top-level compact audit 不包含 `delegate_edges`。

## Validation

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_trace_audit.py -k "profile_policy_audit or successful_run" -q`
  - 2 passed, 3 deselected.
- `backend\.venv\Scripts\python.exe -m compileall backend\app\services\writing_agent`
  - passed.
- `git diff --check`
  - passed.
- DeepSeek key prefix scan:
  - `$pat='sk-'+'f6aa'; rg -n $pat backend frontend docs --glob '!frontend/node_modules/**'`
  - no matches.

## Review

这一步让 Agent 自己通过 Trace 工具发现 profile/tool policy 风险，而不是只能依赖 run detail UI 或人工观察。它继续推进“模块工具化 + 可审计”的主线：profile policy audit 成为 Agent 可读取的运行证据。

## Novel Progress

本阶段不推进正文生成。原因：当前更高优先级是把 Agent 的工具可见性、策略审计和 Trace 诊断打通，减少后续长篇自动创作时工具编排黑箱。

## Next

- 继续把 profile policy audit 接入更高层的 Agent health/route diagnosis，让 planner 能在选择 profile 前主动检查工具面风险。
- 后续可以把 profile definitions 从静态规则推进到 data-driven 配置，并审计 declared capabilities 与 effective visible tools 的差异。
