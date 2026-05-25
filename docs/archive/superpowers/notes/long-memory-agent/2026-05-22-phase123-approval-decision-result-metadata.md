# Phase123 Report: Approval Decision Result Metadata

## 阶段目标

把用户对 `PendingAction` 的确认/取消/修改意见决策记录到 `action_result.data.approval_decision`，使 Agent 工具执行链路具备可审计的“用户决策边界”。

本阶段继续服务长期目标中的 Agent 化方向：原有模块工具化后，工具调用不仅要有参数和结果，也要有明确的审批证据。

## 实际完成

- 在 `backend/app/api/dialogs.py` 增加 `_approval_decision_metadata(...)`。
- `/api/v1/dialog/resolve-action` 现在会在 `action_result.data.approval_decision` 中返回：
  - `pending_action_id`
  - `action_type`
  - `pending_action_type`
  - `decision`
  - `decision_comment`
  - `resolved_at`
  - `approval_mode`
  - `approval_contract_hash`
  - `approval_contract_version`
- 终端 system message 现在持久化完整 `action_result`，不再只存 `{type, status}`，便于历史消息、Trace 和后续审计视图复用。
- 新增后端测试覆盖章节审批 follow-up 的确认路径，验证响应和持久化 system message 使用同一份审批决策元数据。

## 小说进度

本阶段没有生成新章节。原因：本阶段是审批/Trace 基础设施改造，目标是让后续真实长篇生成中的写入动作可以被审计。

## 发现的问题

- 现有自然语言到章节生成的意图路由仍不够稳，Phase122 浏览器 dogfood 已记录：低细节自然语言不一定触发章节 pending action，`/chapter` 命令稳定触发。该问题应在后续 intent-router/dialog-planner 阶段处理。

## 已修复的问题

- 解决了 `resolve-action` 的结果缺少用户审批决策元数据的问题。
- 解决了终端 system message 只保存最小 action_result，导致历史审计信息不足的问题。

## 未修复但记录的问题

- `approval_decision` 尚未接入独立 Trace/Event 视图。
- 世界模型写入审批路径尚未统一复用本阶段的审批决策元数据模式。
- 当前审批模式仍是单 pending action 决策，尚未建模批量审批、分步审批或 approve-always 策略。

## 验证证据

- RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_chapter_approval_followup_resolve_action_records_decision_metadata -q`
  - 失败原因：`KeyError: 'approval_decision'`。
- GREEN:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_chapter_approval_followup_resolve_action_records_decision_metadata -q`
  - `1 passed in 0.17s`
- Dialog 后端回归：
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py -q`
  - `65 passed in 23.63s`
- Hygiene:
  - `git diff --check`
  - 退出码 0。
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`
  - 无匹配。

## 下一阶段建议

Phase124 建议二选一：

1. 把 `approval_decision` 投影到 Trace/Event 或对话历史可见的审计视图，让用户能在 UI 中追溯“哪个审批导致了哪个工具写入”。
2. 将同一审批决策元数据模式扩展到 Athena/世界模型写入审批路径，继续推进模块工具化后的统一审批语义。
