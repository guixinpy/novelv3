# Phase29: 命令反馈展示

## 背景

Phase28 后端已经会在命令不可用时返回 `message_type="command"` 和结构化 `meta`。当前前端 `ChatMessage.vue` 对 `message_type="command"` 没有专门展示，用户只能看到普通气泡文本，无法快速识别这是 Agent 控制面反馈。

## 假设

- 本阶段只做展示层，不改变 store、API 或命令执行逻辑。
- 不可用命令需要比普通 assistant 文本更醒目，但仍要符合现有聊天面板的克制风格。
- 先展示最关键的三类信息：命令、状态、原因。

## 成功标准

1. `ChatMessage.vue` 对 `message_type="command"` 且 `meta.command_available === false` 的消息渲染专门的命令反馈块。
2. 展示：
   - 命令名，例如 `/continue`
   - 状态：暂不可用
   - 不可用原因列表
3. 原消息正文仍保留，避免丢失后端提示。
4. 普通消息、summary、action result 渲染不受影响。

## TDD 计划

1. 前端 RED：在 `ChatMessage.test.ts` 中新增不可用命令反馈测试。
2. 实现 computed 与模板块。
3. 补最小 CSS，沿用现有 token，不引入新视觉体系。
4. 运行 `ChatMessage.test.ts` 和 `vue-tsc`。

## 验证

- T0: `.\node_modules\.bin\vitest.cmd run src/components/chat/ChatMessage.test.ts`
- T1: `.\node_modules\.bin\vue-tsc.cmd --noEmit`
- T0: `git diff --check`

## 非目标

- 不改变命令菜单。
- 不增加可点击修复动作。
- 不做 Agent health card。
