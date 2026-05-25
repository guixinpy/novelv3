# Phase28: 命令可用性分发拦截

## 背景

Phase27 已经让后端命令目录和前端候选列表受 Agent tool/capability 可用性约束。但如果用户手动输入 `/continue`，后端 `chat` 入口仍会直接解析命令并继续进入执行路径，绕过目录的 `available=false`。

这会让 Agent 控制面出现分裂：候选菜单说不可用，但执行入口仍然尝试执行。

## 假设

- 后端是最终可信边界，前端候选过滤不能作为唯一保护。
- 不可用命令仍应保存用户输入，方便审计和对话历史解释。
- `/clear`、`/compact` 不依赖 Agent tool，继续按 session command 处理。
- 本阶段只拦截 `available=false` 的已知命令，不改变未知 slash 文本的兼容行为。

## 成功标准

1. `chat` 入口在解析命令后查询 Agent command catalog availability。
2. 当命令不可用时：
   - 不创建 pending action。
   - 不进入 legacy intent 或 action route。
   - 返回结构化 `message_type="command"`。
   - `meta` 包含 `command_name`、`command_available=false`、`unavailable_reasons`。
   - 对话历史保存一条 command feedback。
3. 可用命令保持现有行为不变。

## TDD 计划

1. 后端 RED：mock `dialogs_api.build_agent_chat_command_catalog()` 返回 `/continue available=false`，发送 `/continue`，断言不创建 pending action 且返回不可用原因。
2. 后端实现：在 `dialogs.py` 中抽出命令不可用响应 helper，并在命令解析后、执行分支前拦截。
3. T0/T1 验证：跑新增 dialog 测试、命令目录测试和 dialog chat_command 窄范围。

## 分层验证

- T0: `pytest backend/tests/test_dialogs.py -k "unavailable_agent_command or chat_command" -q`
- T0: `pytest backend/tests/test_agent_command_catalog.py -q`
- T0: `git diff --check`

## 非目标

- 不修改前端 UI 展示。
- 不新增命令。
- 不改变未知 slash 文本处理。
- 不改变 command catalog endpoint 字段结构。
