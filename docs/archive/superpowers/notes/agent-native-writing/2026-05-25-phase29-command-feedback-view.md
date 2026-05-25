# Phase29 Report: 命令反馈展示

## 完成内容

- `ChatMessage.vue` 增加不可用命令反馈展示。
- 当消息满足 `message_type="command"` 且 `meta.command_available === false` 时，额外展示：
  - 命令名，例如 `/continue`
  - 状态：暂不可用
  - `unavailable_reasons` 原因列表
- 原始后端消息正文继续保留，避免丢失解释文本。
- 样式沿用现有聊天气泡 token，只加轻量提示块。

## RED 证据

- `.\node_modules\.bin\vitest.cmd run src/components/chat/ChatMessage.test.ts` 初始失败：
  - 找不到 `[data-testid="command-feedback"]`。
  - 说明 command feedback 仍按普通气泡渲染。

## 验证证据

- `.\node_modules\.bin\vitest.cmd run src/components/chat/ChatMessage.test.ts`
  - `24 passed`
- `.\node_modules\.bin\vue-tsc.cmd --noEmit`
  - passed
- `git diff --check`
  - passed with existing warning: `backend/tests/test_writing_agent_runs.py` CRLF will be replaced by LF.

## 下一阶段建议

Phase30 可以继续收束斜杠命令与 Agent 控制面：

1. 让 `CommandMenu` 在需要时能显示不可用命令的灰态说明，而不是完全隐藏。
2. 或者先推进 `/status` 的 Agent health card，把 health projection 变成可读 UI，而非普通文本诊断。
3. 两者中优先建议做 `/status` health card，因为它更贴近 Agent 自解释能力。
