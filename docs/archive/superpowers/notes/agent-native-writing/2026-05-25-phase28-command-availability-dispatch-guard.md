# Phase28 Report: 命令可用性分发拦截

## 完成内容

- 在 `chat` 后端入口中加入命令可用性检查。
- 当已知命令在 Agent command catalog 中 `available=false` 时：
  - 保存用户输入命令。
  - 保存一条 system command feedback。
  - 返回 `message_type="command"`。
  - 返回 `meta.command_available=false` 和 `unavailable_reasons`。
  - 不创建 pending action。
  - 不进入 legacy intent、action route 或低细节继续生成路径。
- 在 `agent_command_catalog.py` 中补充命令不可用查询、提示文本和响应 meta helper。

## RED 证据

- `pytest backend/tests/test_dialogs.py -k "unavailable_agent_command" -q` 初始失败：
  - 期望 `message_type == "command"`，实际为 `None`。
  - 说明 `/continue available=false` 仍绕过目录并继续进入旧 chat 路径。

## 修复说明

- `dialogs.py` 在命令解析和用户命令保存后，调用 `find_unavailable_agent_chat_command(parsed_command.name, build_agent_chat_command_catalog())`。
- 使用当前 API 模块导入的 `build_agent_chat_command_catalog()`，便于测试和未来依赖注入，不直接在 helper 内隐式读取全局目录。
- 不可用响应只处理已知命令；未知 slash 保持原有兼容行为。

## 验证证据

- `pytest backend/tests/test_dialogs.py -k "unavailable_agent_command" -q`
  - `1 passed, 102 deselected`
- `pytest backend/tests/test_dialogs.py -k "unavailable_agent_command or chat_command or continue_command_routes_through_low_detail_agent_continue or status_command_routes_through_agent_diagnosis" -q`
  - `5 passed, 98 deselected`
- `pytest backend/tests/test_agent_command_catalog.py -q`
  - `3 passed`
- `git diff --check`
  - passed with existing warning: `backend/tests/test_writing_agent_runs.py` CRLF will be replaced by LF.

## 下一阶段建议

Phase29 可以把不可用命令反馈同步到前端交互：

1. `ChatInput` 候选项可显示不可用命令的灰态说明，但默认不允许选择。
2. Hermes 对 `message_type="command"` 的不可用反馈增加更明确的 Agent 控制面视觉标识。
3. 后续再考虑把 `/status` 扩展为可解释的 Agent health card，而不是纯文本诊断。
