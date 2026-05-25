# Phase32 Report: `/continue` Agent Control Projection

## 完成内容

- 新增 `backend/app/services/writing_agent/continue_agent_control.py`。
- `/continue` 现在会生成结构化 `agent_control` 投影：
  - `version="phase32.continue_agent_control.v1"`
  - `command_name="continue"`
  - `source="slash_command"`
  - `selected_route`
  - `reason_code`
  - `source_run_id`
  - `required_agent_tools`
- 对 slash `/continue` 的 chapter-generation 路径，`agent_control` 会写入：
  - response `meta.agent_control`
  - `pending_action.params.agent_control`
  - dialog route decision trace metadata
- recover/followup 两条低细节继续路径也支持传入 `agent_control`，但文本“继续吧”不会附加 slash-command 专属投影。
- 原有 `dialog_route_decision` 保留，现有 UI/trace 兼容不变。

## RED 证据

- `pytest backend/tests/test_dialogs.py -k "continue_command_routes_through_low_detail_agent_continue" -q` 初始失败：
  - `KeyError: 'agent_control'`
  - 说明 `/continue` 响应只有 `dialog_route_decision`，没有显式 Agent control projection。

## 修复说明

- `continue_agent_control.py` 负责构造 projection，并映射回旧 `dialog_route_decision` 结构。
- `dialogs.py` 在 parsed command 为 `continue` 时构造 projection。
- 普通文本低细节继续没有 `routed_command_name="continue"`，因此不会注入 command-specific `agent_control`。

## 验证证据

- `pytest backend/tests/test_dialogs.py -k "continue_command_routes_through_low_detail_agent_continue" -q`
  - `1 passed, 102 deselected`
- `pytest backend/tests/test_dialogs.py -k "continue_command or low_detail_continue" -q`
  - `6 passed, 97 deselected`
- `pytest backend/tests/test_dialogs.py -k "continue_command or low_detail_continue or status_command or unavailable_agent_command or chat_command" -q`
  - `10 passed, 93 deselected`
- `pytest backend/tests/test_agent_command_catalog.py -q`
  - `3 passed`
- `git diff --check`
  - passed with existing warning: `backend/tests/test_writing_agent_runs.py` CRLF will be replaced by LF.

## 下一阶段建议

Phase33 可以把 `agent_control` 从后端元数据推进到前端可视化：

1. Hermes chat message 展示 `/continue` 的 selected route 和 reason。
2. AgentRun/Trace 面板显示 continue control projection。
3. 或者先抽象通用 command control projection，为后续 `/plan`、`/review`、`/memory` 等 Agent-native 命令预留统一形状。
