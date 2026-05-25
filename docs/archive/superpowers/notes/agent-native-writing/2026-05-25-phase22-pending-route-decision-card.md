# Phase22 报告：Pending Action 继续路由显示

## 完成内容

1. `ActionCard` 现在从 `action.params.dialog_route_decision` 读取继续路由决策。
2. 确认卡片展示：
   - `继续路由`
   - `路由原因`
3. 卡片只展示人类可读标签，不展示 `priority`、raw route key、hash 或内部工具参数。

## 参考项目取舍记录

参考项目中的 Agent trace 往往集中在运行详情，但章节生成回落会先进入用户确认卡片。本阶段选择把决策原因放在用户确认前的位置，提升“对话驱动 Agent”的可解释性；底层仍复用 Phase20 的结构化元数据。

## 验证

RED：

```powershell
.\node_modules\.bin\vitest.cmd run ActionCard.test.ts -t "dialog continue route"
```

结果：测试失败，确认卡片未展示 `继续路由`。

GREEN：

```powershell
.\node_modules\.bin\vitest.cmd run ActionCard.test.ts -t "dialog continue route"
```

结果：`1 passed, 2 skipped`。

T1：

```powershell
.\node_modules\.bin\vitest.cmd run ActionCard.test.ts ChatMessage.test.ts ChatMessageList.test.ts
.\node_modules\.bin\vue-tsc.cmd --noEmit
```

结果：

- `3 passed`, `29 passed`
- `vue-tsc` 通过

T2：

```powershell
.\node_modules\.bin\vite.cmd build
```

结果：沙箱外授权运行通过，245 modules transformed。

## 下一阶段建议

1. 将低细节继续 route decision 写入 Agent Trace，使对话消息、pending action、Agent run 三者可串联审计。
2. 梳理三个参考项目的 memory/trace event 设计，选择适合 novelv3 的轻量 trace event contract。
