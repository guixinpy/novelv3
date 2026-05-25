# Phase35: Command Menu Agent Contracts

## 背景

Phase34 已经让命令目录暴露 `control_projection_type`。但 Hermes 输入框的 `/` 候选仍只展示命令名、描述和示例，用户无法在输入前判断该命令属于 Agent 控制、会返回什么结构化结果、是否依赖多个 Agent 工具。

本阶段把命令目录契约转成紧凑的候选标签，保持现有 CommandMenu 组件边界。

## 成功标准

1. `CommandMenu.vue` 对每个候选展示分类标签：
   - `agent_control` -> `Agent 控制`
   - `session` -> `会话`
   - `legacy_alias` -> `兼容`
2. 当 `controlProjectionType` 存在时展示结果标签：
   - `continue_agent_control` -> `继续控制`
   - `agent_health_projection` -> `状态诊断`
3. 当 `requiredAgentTools` 非空时展示能力数量，例如 `4 项能力`。
4. 不展示 raw projection id，不改选择、键盘导航和命令过滤行为。

## TDD 计划

1. 前端 RED：新增 `CommandMenu.test.ts`，断言候选渲染 `Agent 控制`、`继续控制`、`4 项能力`，且不泄漏 `continue_agent_control`。
2. 实现组件 helper：
   - `categoryLabel(category)`
   - `projectionLabel(type)`
   - `requiredToolCount(command)`
3. 添加模板 meta row 和 CSS。
4. 验证：
   - `.\node_modules\.bin\vitest.cmd run src/components/chat/CommandMenu.test.ts src/components/workspace/chatCommands.test.ts`
   - `.\node_modules\.bin\vue-tsc.cmd --noEmit`
   - `git diff --check`

## 非目标

- 不改变命令目录接口。
- 不改变 ChatInput 的候选计算和 pending action 限制。
- 不把 legacy alias 重新开放到候选列表。
