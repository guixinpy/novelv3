# Phase128 Report: Contract Verification Events

## 阶段目标

把“用户确认执行”和“系统实际校验审批契约通过/阻断”区分开。用户确认只说明允许进入执行阶段，系统仍必须校验当前计划、契约快照、项目和工具契约没有漂移。

## 实际完成

- `backend/app/services/writing_agent/chapter_generation_execution.py`
  - 新增 `_approval_verification_event(...)`。
  - `execute_generate_chapter_with_approval(...)` 成功路径会写入 `approval_verification_event`。
  - 校验阻断路径也会写入 `approval_verification_event`，事件类型为 `contract_blocked`。
  - 事件只包含清洗后的状态、原因、契约版本、写入步骤数量和工具契约漂移数量，不包含原始 approval hash。
- `backend/app/services/writing_agent/agent_trace_audit.py`
  - `event_chain` 现在会在 `tool_step` 后追加 `contract_verified` 或 `contract_blocked`。
- `backend/tests/test_writing_agent_tool_executor.py`
  - 新增直接服务测试，验证执行成功时输出清洗后的 `approval_verification_event`。
- `backend/tests/test_writing_agent_trace_audit.py`
  - 事件链顺序扩展为：
    - `approval_decision`
    - `run_dispatched`
    - `tool_step`
    - `contract_verified`
    - `trace_attached`
    - `result_message`

## 小说进度

本阶段没有生成新章节。原因：本阶段补的是写入前安全校验的审计证据，属于 Agent 长篇自动化写作前的基础防护。

## 已修复的问题

- 事件链过去只能看到用户已确认和工具步骤，无法判断系统是否真的重新校验过审批契约。
- 现在 `contract_verified/contract_blocked` 能明确表示执行前的契约校验结果。

## 未修复但记录的问题

- 批量章节执行的 approval contract 校验尚未输出同样的 `approval_verification_event`。
- `contract_blocked` 路径已有实现但还缺专门测试覆盖具体 mismatch 场景。
- UI 还没有展示 `event_chain`，目前只作为 Agent 工具审计输出。

## 验证证据

- RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_trace_audit.py::test_inspect_agent_trace_audit_includes_dialog_approval_events_without_raw_hash -q`
  - 失败原因：事件链缺少 `contract_verified`。
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_tool_executor.py::test_execute_generate_chapter_with_approval_records_verification_event -q`
  - 失败原因：`KeyError: 'approval_verification_event'`。
- GREEN:
  - 两个 targeted 测试均通过。
  - trace audit targeted: `1 passed in 0.12s`
  - tool executor targeted: `1 passed in 0.14s`
- Regression:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_trace_audit.py backend\tests\test_writing_agent_tool_executor.py -q`
  - `85 passed in 2.99s`
- Hygiene:
  - `git diff --check`
  - 退出码 0。
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`
  - 无匹配。

## 下一阶段建议

Phase129 建议补 `contract_blocked` 的 mismatch 测试，并把批量章节执行路径也接入相同的 `approval_verification_event` 模式，避免单章与批量写入在审批审计语义上分裂。
