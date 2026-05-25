# Phase45: Server Command Contract Result View Report

## 目标

让服务端历史消息重建的 `action_result_view.detail_items` 与前端即时 feedback 保持一致，能展示命令契约健康摘要。

## 变更

- `action_result_view.py` 的 `_agent_discovery_detail_items(...)` 新增命令契约摘要：
  - `命令契约: 已投影`
  - `控制命令: N 个`
  - `契约缺口: N 个`
- 新增 `_agent_command_contract_detail_items(...)`，只读取 `agent_command_contracts.summary`。
- 不输出 `source`、`commands` 或内部 trace path。
- `test_dialogs.py` 新增历史消息重建测试，确认敏感/冗长字段不泄露到 detail items。

## RED 证据

- `pytest backend/tests/test_dialogs.py -k "agent_command_contract_detail_items" -q`
  - 失败原因：`detail_items` 仅包含 `Agent 身份`，缺少 `命令契约`、`控制命令`、`契约缺口`。

## GREEN 证据

- `pytest backend/tests/test_dialogs.py -k "agent_command_contract_detail_items" -q`
  - `1 passed, 103 deselected`
- `pytest backend/tests/test_dialogs.py -k "agent_command_contract_detail_items or agent_profile_policy_audit_detail_item or action_result_view_for_recovery_preview or action_result_view_for_recommended_followup_result_view" -q`
  - `4 passed, 100 deselected`
- `git diff --check`
  - 通过；仅保留既有提示：`backend/tests/test_writing_agent_runs.py` CRLF 将被 Git 转为 LF。

## 下一阶段建议

命令契约可见链路已覆盖 `/status`、planner trace、Agent run detail、运行抽屉、聊天即时 feedback 和服务端历史消息重建。下一阶段可以回到 Agent 工具编排本身，优先审计 `agent_command_contracts` 与 `inspect_agent_tool_contracts` 的交叉诊断，形成一个更高层的 Agent control-plane readiness 摘要。
