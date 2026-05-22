# Phase127 Report: Agent Trace Event Chain

## 阶段目标

在 `inspect_agent_trace_audit` 中增加统一、只读的 `event_chain`，把审批决策、run 调度、工具步骤、模型 trace 和结果消息串成一个顺序化审计链。

## 实际完成

- `backend/app/services/writing_agent/agent_trace_audit.py`
  - 新增 `_event_chain(...)`。
  - 输出顶层 `event_chain`。
  - 在 `audit` 中增加 `event_chain_count`。
  - 当前事件类型：
    - `approval_decision`
    - `run_dispatched`
    - `tool_step`
    - `trace_attached`
    - `result_message`
- `backend/tests/test_writing_agent_trace_audit.py`
  - 在审批审计测试中加入 step 和 trace fixture。
  - 验证事件顺序、关键 id、工具名、trace id、结果消息 id。
  - 验证事件链不泄露原始 `approval:` hash。

## 小说进度

本阶段没有生成新章节。原因：这是 Agent 审计/可观察性基础设施阶段，目的是支撑后续真实长篇生成过程中的安全追溯。

## 已修复的问题

- 过去 `inspect_agent_trace_audit` 输出分散在 `dialog_events/approval_events/steps/traces` 中，Agent 需要自行拼接。
- 现在同一审计结果包含一个顺序化事件链，便于 Agent 或 UI 直接展示“用户批准了什么、系统调度了什么、执行了哪个工具、挂了哪个 trace、结果消息是哪条”。

## 未修复但记录的问题

- `event_chain` 仍是只读投影，不是持久化 event store。
- 工具 start/complete 事件目前由 `WritingAgentStep` 摘要代表，没有独立 start/complete id。
- `contract_verified/tool_blocked` 等更细事件还没有进入链路。
- 还没有把 Athena/世界模型写入审批接入同一事件链。

## 验证证据

- RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_trace_audit.py::test_inspect_agent_trace_audit_includes_dialog_approval_events_without_raw_hash -q`
  - 失败原因：`KeyError: 'event_chain'`。
- GREEN:
  - 同一 targeted 命令。
  - `1 passed in 0.11s`
- Regression:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_trace_audit.py -q`
  - `3 passed in 0.20s`
- Hygiene:
  - `git diff --check`
  - 退出码 0。
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`
  - 无匹配。

## 下一阶段建议

Phase128 建议把 `contract_verified` 审计信息纳入工具步骤输出，先覆盖 `execute_generate_chapter_with_approval` 的成功和阻塞路径。这样事件链能区分“用户确认了”和“系统实际校验通过了”。
