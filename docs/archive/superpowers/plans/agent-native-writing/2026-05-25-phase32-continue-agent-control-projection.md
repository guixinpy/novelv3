# Phase32: `/continue` Agent Control Projection

## 背景

当前 `/continue` 虽然是公开 Agent 控制命令，但执行时仍先转译为文本 `"继续"`，再被 `_is_low_detail_continue_text()` 捕获。结果是它的核心决策藏在低细节文本路由中，而不是一个明确的 Agent control projection。

本阶段不改变 `/continue` 的实际选择逻辑，先把现有 recover/followup/chapter 三路选择封装为结构化控制投影，并写入 pending/meta/trace，为后续将 `/continue` 完全迁成 Agent-native control action 做准备。

## 成功标准

1. `/continue` 响应的 `meta` 包含 `agent_control`：
   - `version`
   - `command_name="continue"`
   - `selected_route`
   - `reason_code`
   - `required_agent_tools`
2. 创建 pending action 时，`pending_action.params.agent_control` 与响应 meta 一致。
3. 原有 `dialog_route_decision` 字段继续保留，避免破坏现有 UI 与 trace。
4. 文本输入“继续吧”仍保持原路径，不附加 command-specific `agent_control`。

## TDD 计划

1. 后端 RED：扩展 `/continue` 测试，断言 response meta 和 pending params 中存在 `agent_control`。
2. 实现最小 service/helper：
   - `backend/app/services/writing_agent/continue_agent_control.py`
   - 负责构造 projection 和向旧 `dialog_route_decision` 映射。
3. 在 `dialogs.py` 中只对 parsed `/continue` 命令注入该 projection。
4. 跑命令相关窄范围测试和 `git diff --check`。

## 验证

- T0: `pytest backend/tests/test_dialogs.py -k "continue_command_routes_through_low_detail_agent_continue" -q`
- T1: `pytest backend/tests/test_dialogs.py -k "continue_command or status_command or unavailable_agent_command or chat_command" -q`
- T0: `git diff --check`

## 非目标

- 不改变 recover/followup/chapter 的优先级。
- 不改 `/continue` 的 pending action 类型。
- 不新增前端 UI。
- 不移除 `dialog_route_decision`。
