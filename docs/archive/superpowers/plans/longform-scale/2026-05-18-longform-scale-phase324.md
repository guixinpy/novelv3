# Phase 324 - Hermes 写作诊断建议展示

## 目标

把 Phase 323 后端返回的 `generation_diagnostic_recommendations` 接入前端，让用户在 Hermes 仪表盘里直接看到批量写作后的“建议处理”列表。

## RED

新增/扩展测试：

- `frontend/src/stores/project.workspace.test.ts`
  - 轮询写作范围任务时，store 必须保存 `writingTaskRecommendations`。
- `frontend/src/components/shared/ProjectDashboard.test.ts`
  - Dashboard 必须展示“建议处理”、建议标题、章节索引与建议正文。

初次运行结果：2 个测试按预期失败，原因分别是 store 中字段不存在、Dashboard 未渲染建议区域。

## GREEN

实现内容：

- `frontend/src/api/types.ts`
  - 新增 `GenerationDiagnosticRecommendation` 类型。
  - `BackgroundTaskResult` 支持 `generation_diagnostic_recommendations`。
- `frontend/src/stores/project.ts`
  - 新增 `writingTaskRecommendations`。
  - 写作任务 compact 轮询时同步保存建议。
  - 项目切换、开始写作、继续写作时清空旧建议。
- `frontend/src/components/shared/ProjectDashboard.vue`
  - 新增紧凑“建议处理”区，最多展示 5 条建议。
  - 复用章节索引格式化，保持 Hermes 侧栏可扫读。
- `frontend/src/views/HermesView.vue`
  - 将 store 中的建议传给 Dashboard。

## 阶段验证

已通过：

```powershell
npm run test:unit -- --run src/stores/project.workspace.test.ts src/components/shared/ProjectDashboard.test.ts
```

结果：`2 passed`, `43 passed`

浏览器烟测：

- URL: `http://127.0.0.1:5173/projects/b9d50481-6f5c-4f54-9b60-984c43e40808/hermes`
- 结果：`.dashboard` 存在，页面包含 `AI 任务`，非 favicon 资源错误和页面错误为 0。
