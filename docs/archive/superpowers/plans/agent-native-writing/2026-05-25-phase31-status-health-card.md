# Phase31: `/status` Agent Health Card

## 背景

Phase30 已经让 `/status` 返回 `meta.agent_health_projection`，但前端仍只展示文本摘要。Agent 化后的状态入口应能直接展示健康状态、诊断项和建议工具，便于用户理解 Agent 当前能力边界。

## 假设

- 本阶段只在 `ChatMessage.vue` 中展示已有 meta，不新增 API。
- health card 不替代正文，正文继续保留。
- 样式沿用现有聊天气泡，保持密度和可读性。

## 成功标准

1. `message_type="command"` 且存在 `meta.agent_health_projection` 时展示 `agent-health-card`。
2. 展示状态中文标签：
   - `ready` -> 就绪
   - `degraded` -> 部分降级
   - `needs_attention` -> 需要处理
3. 展示诊断项列表，最多 3 条。
4. 展示推荐工具列表，最多 5 个。
5. 不影响不可用命令反馈与普通消息渲染。

## TDD 计划

1. 前端 RED：新增 `ChatMessage.test.ts` 用例，断言 health card 内容。
2. 实现 computed 与模板。
3. 添加最小 CSS。
4. 运行 `ChatMessage.test.ts`、`vue-tsc`、`git diff --check`。

## 非目标

- 不做可点击工具调用。
- 不新增专门 HealthCard 组件。
- 不改变 `/status` 后端响应。
