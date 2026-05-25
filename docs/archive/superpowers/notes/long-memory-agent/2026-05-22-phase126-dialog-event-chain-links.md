# Phase126 Report: Dialog Event Chain Links

## 阶段目标

补齐“审批确认消息 -> WritingAgentRun -> 结果消息”的反链，使 Agent trace audit 不只依赖 `action_result.data.agent_run_id` 过滤，也能通过 `WritingAgentRun.request_message_id/response_message_id` 直接追溯对话事件。

## 实际完成

- `backend/app/api/dialogs.py`
  - `resolve_action(...)` 保存确认/取消/修改意见 system message 后，会在确认路径中把该 message id 回填到对应 `WritingAgentRun.request_message_id`。
  - 新增 `_link_run_request_message(...)`，只在 `agent_run_id` 存在且 run 可查时执行，不改变无 run 的取消/修改意见路径。
- `backend/app/services/writing_agent/agent_trace_audit.py`
  - 新增 `dialog_events`：
    - `approval_message`
    - `result_message`
  - 每个消息摘要只包含 `id/role/action_type/action_status`，不暴露原始 action data。
- `backend/tests/test_dialogs.py`
  - 确认章节 pending action 被确认后，`WritingAgentRun.request_message_id` 指向审批 system message。
- `backend/tests/test_writing_agent_trace_audit.py`
  - 验证 trace audit 能返回审批消息和结果消息摘要。

## 小说进度

本阶段没有生成新章节。原因：本阶段是 Agent 审计链路补强，目标是支撑后续自动化长篇生成时的可追溯性。

## 已修复的问题

- `WritingAgentRun` 过去无法直接指回触发它的审批确认消息。
- `inspect_agent_trace_audit` 过去只返回审批事件本身，没有明确展示审批消息和结果消息的对话边界。

## 未修复但记录的问题

- 还没有统一 `event_chain` 列表把 approval、dispatch、step、trace、result 串成一个排序时间线。
- 还没有把工具内部的 `contract_verified/tool_started/tool_completed/tool_blocked` 作为独立事件输出。
- `result_message` 依赖后台任务完成后已有的 `run.response_message_id`，进行中的 run 仍会显示 `result_message: null`。

## 验证证据

- RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_resolve_chapter_action_confirm_dispatches_prepare_tool backend\tests\test_writing_agent_trace_audit.py::test_inspect_agent_trace_audit_includes_dialog_approval_events_without_raw_hash -q`
  - 失败原因：
    - `run.request_message_id is None`
    - `KeyError: 'dialog_events'`
- GREEN:
  - 同一 targeted 命令。
  - `2 passed in 0.21s`
- Regression:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py backend\tests\test_writing_agent_trace_audit.py -q`
  - `68 passed in 24.66s`
- Hygiene:
  - `git diff --check`
  - 退出码 0。
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`
  - 无匹配。

## 下一阶段建议

Phase127 建议在 `inspect_agent_trace_audit` 中增加统一 `event_chain` 列表，以时间顺序串联：

- approval decision
- run dispatch
- tool step start/finish summary
- attached trace summary
- result message

这一步仍可保持只读投影，不新增表。
