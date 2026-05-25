# Phase24: 文本意图与 Slash Command 路由 Trace

## 背景

Phase23 已把低细节“继续”的路由决策写入 Trace。但普通文本意图与旧 `/` 命令创建 pending action 时，虽然已经把 `agent_route` 写进参数，仍没有独立审计事件。这样旧命令系统仍像 Agent 外部的旁路，不利于后续把对话入口统一升级为 Agent 控制面。

## 参考项目取舍

- `openhuman` 的核心价值是 transport/domain 分离与 typed event；本阶段不引入事件总线，只把“用户输入 -> Agent 工具路线”的转换固化为 Trace 事件。
- `hermes-agent` 对工具调用历史有统一统计；本阶段把 route-to-tool 的选择也纳入可统计历史。
- `openclaw` 的使用视图重视用户命令、工具调用、消耗之间的关联；本阶段先保证后端可追踪，前端可视化延后。

## 目标

1. Slash command 触发的 pending action 写入 `dialog_agent_route` Trace。
2. 普通文本意图触发的 pending action 写入 `dialog_agent_route` Trace。
3. Trace 绑定 `dialog_id`、请求消息、响应消息、pending action，并保存脱敏后的 `agent_route`。
4. 低细节“继续”不重复写 generic route Trace，继续使用 Phase23 的 `dialog_route_decision`。

## 验证

1. RED：补命令路径与文本意图路径测试，证明当前不会生成 `dialog_agent_route` Trace。
2. GREEN：实现最小 helper 并在两处 pending action 创建后调用。
3. T1：运行相关 dialog 路由测试。
4. T2：运行 model-call-trace 基础测试，确认新 trace type 仍走通现有列表/详情能力。

## 非目标

- 不调整 intent router 规则。
- 不改变 `/clear`、`/compact` 等非 pending action 命令。
- 不改变 pending action 参数结构。
- 不新增前端展示。
