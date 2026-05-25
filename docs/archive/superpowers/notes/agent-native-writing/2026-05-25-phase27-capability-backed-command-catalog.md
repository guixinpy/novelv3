# Phase27 Report: 能力约束的 Agent 命令目录

## 完成内容

- 新增 `backend/app/services/writing_agent/agent_command_catalog.py`，由 writing-agent service 层组合命令注册表、Agent tool descriptor 和静态 adapter 可用性。
- 将命令目录版本升级为 `phase27.agent_chat_command_catalog.v1`。
- 为命令条目补充 Agent 原生元数据：
  - `category`
  - `capability_id`
  - `required_agent_tools`
  - `available`
  - `unavailable_reasons`
- `/continue` 现在要求以下 Agent 工具同时具备 descriptor 与 adapter：
  - `inspect_agent_health_projection`
  - `plan_recovery_tools`
  - `plan_recommended_followups`
  - `prepare_generate_chapter_execution`
- `/status` 现在要求 `inspect_agent_health_projection`。
- `/clear`、`/compact` 归类为 session command，不依赖 Agent tool。
- 前端命令规范化保留能力字段，候选菜单只展示 `public && available` 的命令。
- 旧兼容命令继续隐藏但可被 parser 识别。

## 设计取舍

- 没有把工具可用性判断放进 `app.core.chat_commands`，避免 core 层反向依赖 writing-agent service。
- 没有改变 `/continue`、`/status` 的执行语义，本阶段只让目录与 UI 候选符合 Agent 能力状态。
- 没有新增公开命令，避免在 Agent 控制面还未完全稳定前扩大行为面。

## RED 证据

- `pytest backend/tests/test_agent_command_catalog.py -q` 初始失败：`ModuleNotFoundError: No module named 'app.services.writing_agent.agent_command_catalog'`。
- `.\node_modules\.bin\vitest.cmd run src/components/workspace/chatCommands.test.ts` 初始失败：前端 normalize 未保留 `category`、`capabilityId`、`requiredAgentTools`、`available`、`unavailableReasons`。

## 验证证据

- `pytest backend/tests/test_agent_command_catalog.py -q`
  - `3 passed in 0.02s`
- `.\node_modules\.bin\vitest.cmd run src/components/workspace/chatCommands.test.ts`
  - `9 passed`
- `pytest backend/tests/test_dialogs.py -k "chat_command" -q`
  - `2 passed, 100 deselected`
- `.\node_modules\.bin\vitest.cmd run src/views/HermesView.test.ts src/stores/chat.workspace.test.ts`
  - `40 passed`
- `.\node_modules\.bin\vue-tsc.cmd --noEmit`
  - passed
- `pytest backend/tests/test_agent_command_catalog.py backend/tests/test_dialogs.py -k "agent_command_catalog or chat_command" -q`
  - `5 passed, 100 deselected`
- `git diff --check`
  - passed with existing warning: `backend/tests/test_writing_agent_runs.py` CRLF will be replaced by LF.

## 工作区说明

- 当前工作区存在大量前序阶段与文档归档变更，本阶段未回退或整理这些既有改动。
- 本阶段新增/修改的核心文件：
  - `backend/app/services/writing_agent/agent_command_catalog.py`
  - `backend/app/core/chat_commands.py`
  - `backend/app/api/dialogs.py`
  - `backend/tests/test_agent_command_catalog.py`
  - `backend/tests/test_dialogs.py`
  - `frontend/src/api/types.ts`
  - `frontend/src/components/workspace/chatCommands.ts`
  - `frontend/src/components/workspace/chatCommands.test.ts`

## 下一阶段建议

Phase28 可以把对话入口的命令解析也接入能力目录，避免用户手输一个已不可用的公开命令时绕过前端候选过滤。建议保持窄范围：

1. 后端 parse/dispatch 前查询 command catalog availability。
2. 不可用命令返回结构化提示，而不是静默当普通文本或继续进入旧路径。
3. 在 Hermes UI 中展示不可用原因，形成 Agent 控制面的自解释能力。
