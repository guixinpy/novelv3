# Phase22: Pending Action 继续路由显示

## 背景

Phase20 已把章节生成回落路径的 `dialog_route_decision` 写入 pending action params，Phase21 已让 action_result 类消息显示继续路由。但章节生成回落会进入确认卡片，当前卡片不会展示该决策。

## 目标

1. `ActionCard` 从 `action.params.dialog_route_decision` 读取低细节继续路由。
2. 在确认卡片中展示：
   - `继续路由`
   - `路由原因`
3. 只展示人类可读标签，不展示 raw priority、hash 或内部参数。

## 参考项目取舍

参考 Agent 项目的 trace 往往会显示在运行详情中。novelv3 这里优先放在用户即将确认的操作卡片里，因为这是用户最需要理解 Agent 自动选择原因的位置。

## 验证

1. RED：`ActionCard.test.ts` 增加章节生成回落路由展示测试。
2. GREEN：实现卡片中的 route decision detail。
3. T1/T2：运行 ActionCard/ChatMessage 相关单测与前端类型检查。

## 非目标

- 不改变 pending action 创建逻辑。
- 不新增后端 schema 字段。
- 不展示所有 route priority。
