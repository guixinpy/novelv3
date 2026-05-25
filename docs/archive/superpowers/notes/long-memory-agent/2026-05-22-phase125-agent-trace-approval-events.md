# Phase125 Report: Agent Trace Approval Events

## 阶段目标

让 `inspect_agent_trace_audit` 输出对话审批事件，使 Agent 可以在同一个审计结果中看到“用户审批 -> Agent run -> 工具步骤/Trace”的最小链路。

## 实际完成

- `backend/app/services/writing_agent/agent_trace_audit.py`
  - 引入 `DialogMessage` 查询。
  - 新增 `_approval_events_for_run(...)`，从同一 dialog 的 system action_result 中抽取 `approval_decision`。
  - 只绑定 `action_result.data.agent_run_id == run.id` 的审批事件。
  - 输出顶层 `approval_events`。
  - 在 `audit` 中增加 `approval_event_count`。
  - 审计事件不暴露原始 `approval_contract_hash`，只输出 `approval_contract_bound: true/false`。
- `backend/tests/test_writing_agent_trace_audit.py`
  - 新增审批事件测试，覆盖确认决策、契约绑定、版本、message_id 关联和 hash 隐藏。

## 子代理调研结论

### 本仓库 Trace/Event 调研

只读代理确认最小集成点不应是新 Event 表，而是复用现有链路：

- `DialogMessage.action_result`：当前动作事件载体，已有 action_result 局部索引。
- `PendingAction`：审批挂起态，保存决策、备注和解决时间。
- `WritingAgentRun`：已有 `dialog_id/request_message_id/response_message_id/background_task_id`。
- `WritingAgentStep`：已有工具级输入、输出、状态、trace_id 和目标对象。
- `AIModelCallTrace`：已有模型调用 trace，保留 raw context 的访问边界。
- `inspect_agent_trace_audit`：现成只读聚合入口，应优先扩展。

代理建议后续补一条反链：`resolve_action(confirm)` 保存审批 system message 后，把该 message id 回填到 `WritingAgentRun.request_message_id`，使 run 能直接指回触发它的审批消息。

### 参考项目调研

- openclaw 的启发：事件流应轻量、窗口化；审批执行前要有 hash/baseHash 防漂移。
- hermes-agent 的启发：工具事件应有 start/complete 配对和稳定工具调用 id；权限/审批选项要稳定，未知或异常默认 deny。
- openhuman 的启发：先持久化 run trace，再把反馈挂到 trace/run 上；工具可见性和 runtime 工具集要区分。

本阶段采纳的原则：

- 不照搬外部协议。
- 不引入外部依赖。
- 不建立通用 Agent OS。
- 先把 novelv3 现有审批/工具/trace 链路读出来。

## 小说进度

本阶段没有生成新章节。原因：本阶段属于 Agent 审计基础设施，目标是让后续真实长篇生成中的工具调用可追溯。

## 发现的问题

- 当前 `approval_events` 通过 `DialogMessage.action_result.data.agent_run_id` 绑定 run；这是可行的最小方案，但不是最强反链。
- `WritingAgentRun.request_message_id` 当前没有在 `resolve_action(confirm)` 时回填审批消息 id。后续应补齐。
- `approval_events` 目前只覆盖用户决策事件，还没有覆盖 `contract_verified/tool_started/tool_completed/tool_blocked/trace_attached` 等完整事件词表。

## 已修复的问题

- `inspect_agent_trace_audit` 过去只能看到 run、steps、traces、context、failure，无法看到触发 run 的用户审批决策。
- 现在 Agent 可通过同一工具结果看到审批事件数量和审批事件摘要。

## 未修复但记录的问题

- 还没有新增 `event_chain` 统一时间线。
- 还没有在工具步骤中显式输出 `contract_verified` 审计事件。
- 还没有把终态 dialog result message 纳入 `inspect_agent_trace_audit` 的事件链。
- 还没有把 Athena/世界模型写入审批统一接入同一审批事件模型。

## 验证证据

- RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_trace_audit.py::test_inspect_agent_trace_audit_includes_dialog_approval_events_without_raw_hash -q`
  - 失败原因：`KeyError: 'approval_events'`。
- GREEN:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_trace_audit.py::test_inspect_agent_trace_audit_includes_dialog_approval_events_without_raw_hash -q`
  - `1 passed in 0.12s`
- Regression:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_trace_audit.py backend\tests\test_dialogs.py -q`
  - `68 passed in 27.20s`
- Hygiene:
  - `git diff --check`
  - 退出码 0。
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`
  - 无匹配。

## 下一阶段建议

Phase126 建议补 `WritingAgentRun.request_message_id` 的审批消息反链，并让 `inspect_agent_trace_audit` 返回 `dialog_events`：

- approval decision message
- dispatch/run summary
- tool steps
- attached traces
- result message

这会把当前 `approval_events` 从单类事件扩展成更完整的、仍然只读的 Agent 事件链。
