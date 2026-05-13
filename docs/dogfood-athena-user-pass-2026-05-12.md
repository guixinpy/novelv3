# Athena 用户视角深度使用记录（2026-05-12）

项目：霜灯档案：20章Dogfood  
项目 ID：`b9d50481-6f5c-4f54-9b60-984c43e40808`  
测试入口：`http://127.0.0.1:5173/projects/b9d50481-6f5c-4f54-9b60-984c43e40808/athena/overview`  
测试分支：`codex/athena-dogfood-2026-05-12`

## 测试目标

- 站在真实用户视角深度使用 Athena。
- 覆盖总览、设定库、叙事脉络、真相认知、待审变更、检索、对话等主要路径。
- 重点复查叙事图谱模式合并到 `main` 后的真实可用性。
- 可安全当场修复的问题直接修复并记录验证；较大优化项保留在本文档。

## 环境

- 前端：`http://127.0.0.1:5173`
- 后端：`http://127.0.0.1:8000`
- 日期：2026-05-12
- 当前状态：`main` 已合并叙事图谱模式，本轮在 `codex/athena-dogfood-2026-05-12` 上做 dogfood 和修复。

## Running Notes

- 2026-05-12：建立本轮记录，启动前端 5173，开始用户视角遍历 Athena。
- 2026-05-12：发现原 8000 进程返回 `/api/v1/...` 404，重启为当前仓库 FastAPI 服务后恢复。后续验证中后端进程出现一次无明显异常日志退出，已作为本地环境前置问题处理，不计入 Athena 产品缺陷。
- 2026-05-12：稳定等待后复查总览、设定库、叙事脉络、真相认知、待审变更，未再复现 `Unknown error` 或 Truth 误空态。
- 2026-05-12：检索页使用 `灯塔` 搜索，命中 119 条，未复现早前后端未启动时的错误。

## Issues And Improvements

_本节按发现顺序记录。_

### ADF-2026-05-12-001 叙事视图加载中短暂显示业务空态

状态：已当场修复  
严重度：P2  
位置：Athena > 叙事脉络 > 时间线 / 图谱 / 故事线 / 章节 / 伏笔

现象：
- 快速进入或切换叙事视图时，接口数据尚未返回前，页面会短暂显示：
  - `尚未生成叙事规划`
  - `暂无时间线数据`
- 实际 API `GET /athena/evolution/plan` 返回完整 20 章规划、4 条故事线、10 条伏笔。
- 用户会误以为规划丢失，尤其是在刚合并图谱模式后更容易误判。

影响：
- 这是此前总览/设定库/检索已修过的“加载态与业务空态混淆”问题在叙事模块里的复现。
- 图谱模式首屏如果先显示空态，再突然切为图谱，会降低用户对数据稳定性的信任。

修复记录：
- `AthenaView` 增加 route data loading 状态，路由数据加载期间不再让子视图直接渲染业务空态。
- `TimelineView` 加入 `loading`，显示 `正在读取叙事时间线...`。
- `NarrativeAtlasView` / `NarrativeWorkbench` 加入 `loading`，显示 `正在读取叙事规划...`。
- 补充组件测试覆盖加载态优先于业务空态。

验证：
- `npm run test:unit -- TimelineView.test.ts NarrativeWorkbench.test.ts NarrativeAtlasView.test.ts AthenaView.test.ts`
- 浏览器复查 `narrative?view=graph`，确认最终渲染 20 章、4 条故事线、10 条伏笔，未再出现叙事规划空态。

### ADF-2026-05-12-002 时间线在已有 20 章规划时仍显示空页

状态：已当场修复  
严重度：P2  
位置：Athena > 叙事脉络 > 时间线

现象：
- 项目已有 20 章规划、4 条故事线、10 条伏笔。
- 但 `/athena/narrative?view=timeline` 由于后端 timeline events 为空，只显示 `暂无时间线数据`，用户必须自己切换到章节或图谱理解整体进度。

影响：
- “时间线”作为叙事入口不应在已有章节规划时成为空页。
- 对 20 章项目来说，这会让用户误判时间线功能没有工作。

修复记录：
- `AthenaView` 在正式 timeline events 为空时，从 evolution plan 的章节规划衍生 timeline events。
- `TimelineView` 支持直接显示 `chapter_index`，并把衍生事件标记为 `章节规划`。
- 补充 `TimelineView` 与 `AthenaView` 测试覆盖章节规划 fallback。

验证：
- `npm run test:unit -- NarrativeAtlasCanvas.test.ts TimelineView.test.ts AthenaView.test.ts`
- 浏览器复查时间线页，确认不再显示 `暂无时间线数据`，页面直接列出第 1-20 章章节规划。

### ADF-2026-05-12-003 图谱中故事线/伏笔连线难以选中

状态：已当场修复  
严重度：P2  
位置：Athena > 叙事脉络 > 图谱

现象：
- 章节节点可以正常点击并打开详情。
- 故事线和伏笔连接线视觉上可见，但点击区域太窄，并且部分连线中段会被上层节点矩形拦截。
- 自动化按用户点击方式选择 `主线：集体失忆之谜`、`灯塔影像中的钟楼指针停在11:55` 连接时超时。

影响：
- 图谱模式的核心价值是从主干进入枝干、伏笔埋收链路；连线不可稳定点击会降低可探索性。

修复记录：
- `NarrativeAtlasCanvas` 为连线增加透明宽命中路径。
- 增加轻量连接选择手柄，放在连线中段且位于节点层之上，避免节点遮挡。
- 视觉线条保持原有宽度和样式。
- 补充组件测试覆盖连接选择目标。

验证：
- `npm run test:unit -- NarrativeAtlasCanvas.test.ts TimelineView.test.ts AthenaView.test.ts`
- 使用 Chrome + Playwright 复查：
  - 第10章节点可选中并显示章节详情。
  - `主线：集体失忆之谜` 连接可选中并显示故事线详情。
  - `灯塔影像中的钟楼指针停在11:55` 伏笔连接可选中并显示伏笔详情。

### ADF-2026-05-12-004 Athena 对话历史可能与当前项目状态不一致

状态：已当场修复  
严重度：P3  
位置：Athena > 对话面板

现象：
- 打开 Athena 对话历史时，旧回答仍声称“当前世界模型中仅记录了第1章”“无法看到第2-20章正文”。
- 当前项目实际已有 20 章正文，叙事规划、检索索引和章节列表也都能看到 20 章。

判断：
- 后端当前 `dialog.athena` 上下文构造代码已经包含正文进度、章节清单、最近章节摘录、叙事规划摘要和上下文边界。
- 浏览器里看到的问题更像旧历史回答未标注上下文时间/证据范围，而不是当前后端上下文仍缺章。

建议优化：
- 对 Athena 历史回答显示 trace/context 时间或“回答基于当时上下文”的提示。
- 当项目章节数、world-model profile、检索索引发生明显变化时，在对话面板顶部提示可 `/clear` 或重新提问。
- 对回答中“我无法看到正文/仅看到第1章”这类结论，前端可提供 trace 入口或上下文快照摘要，避免用户把旧回答当成当前状态。

修复记录：
- `AthenaChatPanel` 顶部增加当前上下文快照，展示章节数、当前字数、Profile 版本、检索索引文档数。
- 对话面板提示历史回答基于当时上下文，项目状态变化后应重新提问或清空上下文。
- `ChatMessage` 对助手/系统消息显示创建时间，帮助用户区分旧回答与当前状态。
- `AthenaChatPanel` 向通用聊天消息组件传递 `created_at`。
- 检索诊断尚未加载时，索引文档显示为 `未读取`，避免把未知状态误报为 0。

验证：
- 采用 TDD：先写失败测试，再实现。
- `npm run test:unit -- AthenaChatPanel.test.ts ChatMessage.test.ts`：11 passed。
- 浏览器复查 Athena 对话面板，确认顶部显示 `当前上下文 / 章节 20 / Profile v1 / 索引文档 未读取`，历史助手消息显示创建时间。
- `npm run test:unit`：59 files / 337 tests passed。
- `npx vue-tsc --noEmit`：passed。
- `npm run build`：passed。

## Verification

- `pytest`：使用系统 Python 3.14 运行时失败，原因是该解释器下 `python -m alembic` 不可执行；改用项目后端虚拟环境验证。
- `backend/.venv/Scripts/python.exe -m pytest`：420 passed。
- `npm run test:unit`：59 files / 334 tests passed。
- `npx vue-tsc --noEmit`：passed。
- `npm run build`：passed，前端 bundle 成功构建到 `backend/static/`。
- 浏览器复查：
  - Athena 主要页面无 `Unknown error`。
  - 时间线页显示 20 章章节规划 fallback。
  - 图谱中章节节点、故事线连接、伏笔连接均可选中并显示详情。
  - 检索页搜索 `灯塔` 命中 119 条。
