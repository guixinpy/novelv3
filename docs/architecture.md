# 墨著 AI Writer — 项目架构文档

## 概览

墨著是一个 AI 辅助小说创作平台，采用 FastAPI + Vue 3 双包单仓架构。系统通过对话驱动的工作流，引导用户完成从设定构建、大纲生成到章节写作的全流程，并提供世界模型、一致性校验、版本管理等高级功能。

```
novelv3/
├── backend/          FastAPI 后端，SQLite 数据库，Alembic 迁移
├── frontend/         Vue 3 + TypeScript + Vite 前端
└── data/             SQLite 数据库文件（不入库）
```

---

## 模块总览

| 模块 | 职责 | 后端入口 | 前端入口 |
|------|------|----------|----------|
| 项目管理 | 项目 CRUD、状态流转 | `api/projects.py` | `stores/project.ts` |
| 对话系统 | 聊天交互、意图路由、动作确认 | `api/dialogs.py` | `stores/chat.ts` |
| 设定生成 | 角色/世界观/核心概念的 AI 生成 | `api/setups.py` | `tabs/SetupTab.vue` |
| 故事线 | 叙事弧线生成与展示 | `api/storylines.py` | `tabs/StorylineTab.vue` |
| 大纲 | 章节大纲生成与展示 | `api/outlines.py` | `tabs/OutlineTab.vue` |
| 章节写作 | AI 章节生成、写作调度 | `api/chapters.py`, `api/writing.py` | `tabs/ContentTab.vue` |
| 世界模型 | 事实管理、提案审批、投影视图 | `api/world_model.py` | `stores/worldModel.ts` |
| 拓扑关系 | 角色/实体关系图谱 | `api/topologies.py` | `tabs/TopologyTab.vue` |
| 一致性校验 | 跨章节事实/时间线冲突检测 | `api/consistency.py` | Inspector 面板 |
| 版本管理 | 项目快照、回滚 | `api/versions.py` | `tabs/VersionsTab.vue` |
| 偏好设置 | 项目级用户偏好 | `api/preferences.py` | `tabs/PreferencesTab.vue` |
| 导出 | Markdown/TXT 导出 | `api/export.py` | 工作区操作 |
| 后台任务 | 异步任务状态轮询 | `api/background_tasks_api.py` | `stores/chat.ts` |
| 全局配置 | API Key 管理 | `api/config.py` | `views/SettingsView.vue` |

---

## 1. 项目管理

管理项目的生命周期：创建、查询、删除、状态流转。

**后端**
- `api/projects.py` — CRUD 端点（`POST/GET/DELETE /projects`）
- `models/project.py` — `Project` 模型：name, genre, word_count, status, phase, ai_model, language, style, complexity

**前端**
- `stores/project.ts` — 项目列表和当前项目状态，`loadProjects()`, `createProject()`, `deleteProject()`
- `views/ProjectList.vue` — 项目列表页
- `views/ProjectDetail.vue` — 项目工作区入口

**数据流**：用户创建项目 → 进入工作区 → 通过对话或面板触发各模块功能 → 项目 phase 随内容生成推进。

---

## 2. 对话系统

核心交互入口。用户通过聊天与 AI 协作，系统路由意图并驱动工作流。

**后端**
- `api/dialogs.py` — `POST /dialog/chat`（发送消息）、`POST /dialog/resolve-action`（确认/取消动作）、`GET /dialog/messages`（历史）
- `core/intent_router.py` — 意图识别，将用户输入路由到：确认、生成、命令等
- `core/chat_commands.py` — 命令注册表（`/clear`, `/compact`, `/setup`, `/storyline`, `/outline`, `/content`, `/world`, `/topology`）
- `core/chat_compaction.py` — 压缩聊天历史以节省 token
- `core/ui_hints.py` — 生成 UI 提示，引导前端面板切换
- `models/dialog.py` — `Dialog`, `DialogMessage`, `PendingAction`

**前端**
- `stores/chat.ts` — 消息列表、待确认动作、轮询机制
- `components/workspace/ChatWorkspace.vue` — 聊天界面
- `components/workspace/ChatCommandMenu.vue` — 斜杠命令菜单

**数据流**：
1. 用户输入文本 → `sendChat()` → 后端 `IntentRouter` 判断意图
2. 响应包含：message, pending_action, ui_hint, refresh_targets
3. 若有 pending_action → 用户确认/取消 → `resolveAction()` 执行
4. 后台任务通过 `pollForCompletion()` 每 3s 轮询直到完成

---

## 3. 设定生成

AI 生成小说的基础设定：角色、世界观、核心概念。

**后端**
- `api/setups.py` — `POST /setup/generate`（生成）、`GET /setup`（查询）
- `core/prompt_manager.py` — 加载 `generate_setup` 模板，填充项目元数据
- `core/ai_service.py` — 调用 DeepSeek API（temperature=0.7）
- `models/setup.py` — `Setup` 模型：characters(JSON), world_building(JSON), core_concept(JSON)

**前端**
- `components/tabs/SetupTab.vue` — 设定总览，含摘要卡片和世界模型视图
- `components/tabs/SetupDetailModal.vue` — 设定详情弹窗
- `components/tabs/SetupSummaryCard.vue` — 角色/世界观/概念摘要卡片
- `components/world/SetupWorldPanel.vue` — 世界观面板

---

## 4. 故事线 & 大纲

故事线定义叙事弧线，大纲将其拆解为章节级计划。

**后端**
- `api/storylines.py` — `POST /storyline/generate`, `GET /storyline`
- `api/outlines.py` — `POST /outline/generate`, `GET /outline`
- `models/storyline.py` — `Storyline` 模型
- `models/outline.py` — `Outline` 模型

**前端**
- `components/tabs/StorylineTab.vue` — 故事线展示
- `components/tabs/OutlineTab.vue` — 大纲展示

---

## 5. 章节写作

AI 逐章生成小说内容，支持写作调度（开始/暂停/恢复）。

**后端**
- `api/chapters.py` — `POST /chapters/{idx}/generate`, `GET /chapters/{idx}`, `GET /chapters`
- `api/writing.py` — `POST /writing/start`, `/pause`, `/resume`, `/retry`
- `core/writing_scheduler.py` — 写作调度器，管理章节生成工作流
- `models/chapter_content.py` — `ChapterContent` 模型

**前端**
- `components/tabs/ContentTab.vue` — 章节内容展示与编辑

**数据流**：用户触发写作 → `writing_scheduler` 按大纲逐章调用 AI → 生成内容存入 `ChapterContent` → 前端轮询刷新。

---

## 6. 世界模型

管理小说世界的结构化知识：实体、事实、事件、时间线。通过提案审批工作流维护数据一致性。

**后端**
- `api/world_model.py` — 7 个端点：
  - `GET /world-model` — 当前真相投影
  - `GET /world-model/subject-knowledge` — 主体认知视图
  - `GET /world-model/snapshot` — 章节快照视图
  - `GET /world-model/proposal-bundles` — 提案列表（分页/筛选）
  - `GET /world-model/proposal-bundles/{id}` — 提案详情（含冲突检测）
  - `POST /world-model/proposal-items/{id}/review` — 审批提案条目
  - `POST /world-model/proposal-bundles/{id}/split` — 拆分提案
  - `POST /world-model/reviews/{id}/rollback` — 回滚审批
- `core/world_projection.py` — 投影引擎：`project_world_truth()`, `project_subject_knowledge()`, `project_snapshot()`
- `core/world_proposal_service.py` — 提案生命周期：审批、拆分、回滚
- `core/world_replay.py` — 事件回放重建世界状态
- `core/world_time_normalizer.py` — 故事时间点归一化
- `core/world_checker_registry.py` — 世界一致性检查器注册表
- `core/world_contracts.py` — 权威类型、约束定义

**数据模型**
- `WorldCharacter`, `WorldLocation`, `WorldFaction`, `WorldResource`, `WorldArtifact` — 世界实体
- `WorldEvent` — 故事事件（含章节索引、时间锚点）
- `WorldFactClaim` — 事实声明（subject_ref, predicate, object_ref_or_value, claim_layer, claim_status）
- `WorldTimelineAnchor` — 时间线锚点
- `WorldRelation`, `WorldEvidence`, `WorldRule` — 关系、证据、规则
- `WorldProposalBundle` → `WorldProposalItem` → `WorldProposalReview` — 提案工作流
- `WorldProposalImpactScopeSnapshot` — 影响范围快照
- `ProjectProfileVersion` — 世界档案版本

**前端**
- `stores/worldModel.ts` — 投影、提案、分页、筛选、审阅者身份
- `components/world/WorldProjectionViewer.vue` — 3-tab 视图（当前真相/主体认知/章节快照）
- `components/world/WorldSubjectKnowledge.vue` — 主体认知内容
- `components/world/WorldChapterSnapshot.vue` — 章节快照内容
- `components/world/WorldProposalBundleList.vue` — 提案列表（分页+筛选）
- `components/world/WorldProposalItemCard.vue` — 提案条目卡片（冲突标记）
- `components/world/WorldProposalActionPanel.vue` — 审批操作面板
- `components/world/ProposalClaimDiffEditor.vue` — 字段级 diff 编辑器
- `components/world/WorldProposalImpactList.vue` — 影响范围展示
- `components/world/WorldProfileBanner.vue` — 档案版本横幅

**提案工作流**：
1. 后端从生成内容中提取事实 → 打包为 `ProposalBundle`
2. 用户在前端逐条审批（通过/编辑后通过/驳回/标记不确定）
3. 通过的事实写入 `WorldFactClaim`（claim_status=confirmed）
4. 世界投影重新计算

---

## 7. 拓扑关系

构建并展示角色/实体之间的关系图谱。

**后端**
- `api/topologies.py` — `GET /topology`
- `core/topology_builder.py` — 从世界数据构建关系图

**前端**
- `components/tabs/TopologyTab.vue` — 关系图谱可视化（使用 ECharts）

---

## 8. 一致性校验

检测跨章节的事实矛盾、时间线冲突、角色知识缺口。

**后端**
- `api/consistency.py` — `POST /consistency/chapters/{idx}/check?depth=l2`
- `core/consistency_checker.py` — 一致性检查引擎
- `core/l1_extractor.py` — L1 事实提取（直接事实）
- `core/l2_extractor.py` — L2 事实提取（关系、推断）
- `core/cross_validator.py` — 交叉验证
- `models/consistency_check.py` — `ConsistencyCheck` 模型

**前端**
- Inspector 面板中展示校验结果

---

## 9. 版本管理

项目快照与回滚，支持按节点类型（setup/storyline/outline/content）筛选。

**后端**
- `api/versions.py` — `GET/POST/DELETE /versions`, `POST /versions/{id}/rollback`
- `models/version.py` — `Version` 模型：node_type, label, snapshot(JSON)

**前端**
- `components/tabs/VersionsTab.vue` — 版本列表
- `components/tabs/VersionDiff.vue` — 版本差异对比

---

## 10. 工作区 & 面板系统

管理前端工作区的面板切换逻辑，支持 AI 驱动的自动导航。

**前端**
- `stores/workspace.ts` — 面板状态机：mode(auto/locked), panel, source(ai/user/system)
- `components/workspace/ProjectWorkspaceShell.vue` — 工作区容器
- `components/workspace/InspectorPanel.vue` — 右侧检查面板

**面板类型**：overview, setup, storyline, outline, content, topology, versions, preferences

**导航逻辑**：AI 通过 `ui_hint` 建议面板切换 → `applyUiHint()` 在 auto 模式下自动跳转，locked 模式下忽略。

---

## 基础设施

### AI 服务层
- `core/ai_service.py` — AIService 封装，统一调用入口
- `core/deepseek_adapter.py` — DeepSeek API 适配器，含重试逻辑
- `core/prompt_manager.py` — 提示词模板加载与变量替换
- `core/prompt_optimizer.py` — 提示词 token 优化
- `core/token_budget.py` — Token 预算追踪
- `core/few_shot_library.py` — Few-shot 示例库
- `core/context_compressor.py` — 上下文压缩

### 数据库
- SQLite（`data/mozhou.db`），外键启用
- SQLAlchemy ORM + Alembic 迁移
- `app/db.py` — `get_db()` 依赖注入

### 后台任务
- `api/background_tasks_api.py` — `GET /background-tasks/{taskId}`
- `core/background_analyzer.py` — 后台分析任务
- `models/background_task.py` — `BackgroundTask` 模型
- 前端通过 `pollForCompletion()` 轮询

### 前端构建
- Vite 构建输出到 `backend/static/`
- FastAPI 提供 SPA fallback
- 开发模式 Vite 代理 `/api` → `localhost:8000`
