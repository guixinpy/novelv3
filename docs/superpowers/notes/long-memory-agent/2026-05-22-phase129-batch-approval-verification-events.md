# Phase129 Report: Batch Approval Verification Events

## 阶段目标

让单章直接生成和长篇批量章节执行使用同一套清洗后的审批契约校验事件，避免 Agent 审计链在单章/批量路径上语义分裂。

## 实际完成

- 新增 `backend/app/services/writing_agent/approval_verification_event.py`
  - 提供 `build_approval_verification_event(...)`。
  - 输出字段保持与 Phase128 一致：
    - `event_type`
    - `status`
    - `reason`
    - `approval_contract_bound`
    - `approval_contract_version`
    - `write_step_count`
    - `tool_contract_drift_count`
  - 不输出原始 approval hash。
- `backend/app/services/writing_agent/chapter_generation_execution.py`
  - 改为使用共享 helper。
  - 移除私有重复 helper。
- `backend/app/services/writing_agent/batch_execution.py`
  - 批量执行成功路径写入 `approval_verification_event`。
  - 批量执行 agent plan approval 阻断路径也写入 `approval_verification_event`。
- `backend/tests/test_writing_agent_chapter_generation_execution.py`
  - stale contract 阻断路径现在断言 `contract_blocked`。
- `backend/tests/test_writing_agent_runs.py`
  - 批量章节执行成功路径现在断言 `contract_verified`。

## 小说进度

本阶段没有生成新章节。原因：本阶段继续补 Agent 写入安全审计链路，为后续批量长篇生成提供可追溯审批证据。

## 已修复的问题

- 单章路径有审批契约校验事件，批量路径没有。
- 单章路径的事件 helper 原本是私有实现，无法被批量路径复用。
- stale contract 阻断路径缺少明确的测试断言。

## 未修复但记录的问题

- 批量路径中早期 `_validate_execution_request(...)` 的 hash/manifest mismatch 仍属于 phase61 execution contract 阻断，尚未统一成 `approval_verification_event`。
- `contract_blocked` 目前覆盖 agent plan approval verification 阻断；更早的 task/manifest 校验可以后续作为 `execution_contract_blocked` 单独建模。
- `event_chain` 尚未接入批量执行的完整真实 run 示例。

## 验证证据

- RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_chapter_generation_execution.py::test_execute_generate_chapter_with_approval_blocks_stale_contract backend\tests\test_writing_agent_runs.py::test_agent_run_can_execute_approved_longform_chapter_batch_once -q`
  - 结果：单章 stale contract 测试已通过；批量执行测试失败于 `KeyError: 'approval_verification_event'`。
- GREEN:
  - 同一 targeted 命令。
  - `2 passed in 0.33s`
- Regression:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_chapter_generation_execution.py backend\tests\test_writing_agent_runs.py::test_agent_run_can_execute_approved_longform_chapter_batch_once backend\tests\test_writing_agent_tool_executor.py::test_execute_generate_chapter_with_approval_records_verification_event -q`
  - `6 passed in 0.53s`
- Hygiene:
  - `git diff --check`
  - 退出码 0；Git 额外提示 `backend/tests/test_writing_agent_runs.py` 下次会从 CRLF 规范为 LF。
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`
  - 无匹配。

## 下一阶段建议

Phase130 建议从审计链转向 Agent 自主能力：选一个低细节用户输入场景，验证 dialog intent planner 是否能自主选择 `/chapter` 等工具链，而不是要求用户明确输入命令。之前 dogfood 已发现自然语言触发章节生成不够稳。
