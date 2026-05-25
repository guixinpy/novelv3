# Phase21 报告：继续路由决策详情展示

## 完成内容

1. 后端 `action_result_view` 已将 `route_decision` 转成人可读详情：
   - `继续路由`
   - `路由原因`
2. 前端 `buildAgentRunActionResultView` fallback 同步支持相同详情项。
3. 当前覆盖 `plan_recovery_tools` 和 `plan_recommended_followups` 两类预览消息；低细节继续回落到章节生成的 pending action 已在 Phase20 保留结构化元数据，后续可扩展 pending action 详情展示。

## 参考项目取舍记录

参考项目的 decision trace 通常进入事件流或运行时间线。本阶段先复用 novelv3 已有 `detail_items` 投影，使用户立即能看到 Agent 自动选择的原因；这比新增独立 timeline 更小、更可验证，也不会打断现有聊天体验。

## 验证

RED：

```powershell
pytest backend/tests/test_dialogs.py -k "get_messages_includes_action_result_view_for_recovery_preview or get_messages_includes_action_result_view_for_recommended_followup_result_view" -q
```

结果：2 个测试失败，详情中缺少 `继续路由` 和 `路由原因`。

前端 RED 首次用 `npm run test:unit -- agentRunProjection.test.ts -t "fallback views for"` 执行时失败，原因是当前全局 npm shim 指向缺失的 `C:\Users\31106\AppData\Roaming\npm\node_modules\npm\bin\npm-cli.js`。改用项目内 `.bin` 后继续验证。

GREEN：

```powershell
pytest backend/tests/test_dialogs.py -k "get_messages_includes_action_result_view_for_recovery_preview or get_messages_includes_action_result_view_for_recommended_followup_result_view" -q
.\node_modules\.bin\vitest.cmd run agentRunProjection.test.ts -t "fallback views for"
```

结果：

- `2 passed, 96 deselected`
- `1 passed`, `20 passed, 17 skipped`

T1：

```powershell
pytest backend/tests/test_dialogs.py -k "low_detail_continue or recommended_followup_result_view or recovery_preview" -q
.\node_modules\.bin\vitest.cmd run agentRunProjection.test.ts
```

结果：

- `7 passed, 91 deselected`
- `37 passed`

T2：

```powershell
.\node_modules\.bin\vue-tsc.cmd --noEmit
.\node_modules\.bin\vite.cmd build
```

结果：

- `vue-tsc` 通过。
- 沙箱内 `vite build` 因 Node 创建 `backend/static/assets` 报 `EPERM`；同一命令经授权在沙箱外运行通过，245 modules transformed。

## 下一阶段建议

1. 将 pending action 的 `dialog_route_decision` 也展示到确认卡片中，让章节生成回落路径同样可见。
2. 将低细节继续 route decision 写入 Agent Trace，形成跨消息、run、step 的审计链。
