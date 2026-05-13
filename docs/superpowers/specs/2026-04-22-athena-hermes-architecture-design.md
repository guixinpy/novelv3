---
title: Athena + Hermes 双对话架构设计
date: 2026-04-22
status: approved
scope: 子项目 1 — Athena 三层数据模型 + Facade API
---

# Athena + Hermes 双对话架构设计

## 概述

将世界模型从"一个模块"提升为整个后台的认知基座（代号 Athena），吞并设定、拓扑、一致性校验、大纲等模块。建立两个独立对话上下文（Athena / Hermes），共享同一个世界模型作为 ground truth。

## 命名

- **Athena（雅典娜）** — 世界模型总称，代表智慧与全知。用户进入 Athena 界面即进入世界的上帝视角。
- **Hermes（赫尔墨斯）** — 主对话入口，信使之神。聚焦正文创作与章节生成。

## 迁移策略

渐进式三阶段迁移：

| 阶段 | 内容 | 旧 API |
|------|------|--------|
| 阶段 1（本 spec） | Athena Facade API，内部代理到现有模块 | 完全不动 |
| 阶段 2（子项目 4） | 逐步将旧模块逻辑迁入 Athena core | 标记 deprecated |
| 阶段 3（未来） | 移除旧 API | 删除 |

## Athena 三层数据模型

### 第 1 层：世界本体 (Ontology)

世界"是什么"——静态定义，很少变化。

| 数据 | 现有模型 | 吞并来源 |
|------|---------|---------|
| 实体定义 | WorldCharacter, WorldLocation, WorldFaction, WorldArtifact, WorldResource | 设定生成（角色/世界观） |
| 关系网络 | WorldRelation | 拓扑关系模块 |
| 规则与约束 | WorldRule, WorldContracts, GenreProfile | 设定生成（核心概念） |

### 第 2 层：世界状态 (State)

世界"现在怎样"——随章节推进动态变化。

| 数据 | 现有模型 | 吞并来源 |
|------|---------|---------|
| 事实声明 | WorldFactClaim（当前真相、主体认知） | — |
| 时间线 | WorldEvent, WorldTimelineAnchor, 章节快照 | — |
| 证据链 | WorldEvidence, ExtractedFact | 一致性校验的 L1/L2 提取产出 |

### 第 3 层：世界演化 (Evolution)

世界"将去向何方"——计划与变更管理。

| 数据 | 现有模型 | 吞并来源 |
|------|---------|---------|
| 剧情计划 | Outline, Storyline | 大纲模块、故事线模块 |
| 变更管理 | ProposalBundle, ProposalItem, ProposalReview | — |
| 校验守护 | ConsistencyCheck, 冲突检测 | 一致性校验的校验逻辑 |

### 不纳入 Athena 的模块

- **章节写作** — 消费世界模型，不属于世界模型本身。归 Hermes。
- **版本管理** — 基础设施，服务于所有模块。保持独立。
- **项目管理** — 项目 CRUD，与世界模型正交。保持独立。

## Athena Facade API

统一前缀：`/api/v1/projects/{project_id}/athena`

### 第 1 层端点：本体 (Ontology)

```
GET  /athena/ontology              → 聚合视图：实体 + 关系 + 规则 + 设定摘要
GET  /athena/ontology/entities     → 代理：现有 world model entities
GET  /athena/ontology/relations    → 代理：现有 topology API
GET  /athena/ontology/rules        → 代理：现有 world rules
POST /athena/ontology/generate     → 代理：现有 setup/generate
```

### 第 2 层端点：状态 (State)

```
GET  /athena/state                              → 代理：现有 world-model overview
GET  /athena/state/subject-knowledge?subject_ref=X → 代理：现有 subject-knowledge
GET  /athena/state/snapshot?chapter_index=N      → 代理：现有 snapshot
GET  /athena/state/timeline                      → 新增：时间线锚点 + 事件序列
```

### 第 3 层端点：演化 (Evolution)

```
GET  /athena/evolution/plan                      → 代理：现有 outline + storyline
POST /athena/evolution/plan/generate             → 代理：现有 outline/generate + storyline/generate
GET  /athena/evolution/proposals                 → 代理：现有 proposal-bundles（分页/筛选）
GET  /athena/evolution/proposals/{bundle_id}     → 代理：现有 proposal bundle detail
POST /athena/evolution/proposals/{item_id}/review → 代理：现有 proposal review
POST /athena/evolution/proposals/{bundle_id}/split → 代理：现有 proposal split
POST /athena/evolution/reviews/{review_id}/rollback → 代理：现有 review rollback
GET  /athena/evolution/consistency               → 代理：现有 consistency check
```

### Athena 对话端点

```
POST /athena/dialog/chat           → 新增：Athena 专属对话（世界构建上下文）
POST /athena/dialog/resolve-action → 新增：Athena 动作确认
GET  /athena/dialog/messages       → 新增：Athena 对话历史
```

### Hermes 对话端点（重命名现有）

```
POST /hermes/dialog/chat           → 现有 /dialog/chat（正文创作上下文）
POST /hermes/dialog/resolve-action → 现有 /dialog/resolve-action
GET  /hermes/dialog/messages       → 现有 /dialog/messages
```

## 双对话架构

### 独立上下文，共享世界模型

```
                    ┌─────────────────────┐
                    │   Athena 世界模型     │
                    │   (结构化数据库)       │
                    │   唯一事实源           │
                    └────────┬────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
              ┌─────┴─────┐    ┌─────┴─────┐
              │  Athena    │    │  Hermes    │
              │  Dialog    │    │  Dialog    │
              │  世界构建   │    │  正文创作   │
              └───────────┘    └───────────┘
```

### 数据模型变更

现有 `Dialog` 模型新增 `dialog_type` 字段：

```python
dialog_type: str  # "athena" | "hermes"
```

每个项目有两个 Dialog session，各自独立的消息历史和 pending action。

### Context Injection 策略

**Athena Dialog system prompt：**
- 注入完整世界本体（实体、关系、规则）
- 注入当前世界状态摘要（事实、时间线）
- 注入演化计划摘要（大纲、待审提案）
- 专用命令集：`/entity`, `/fact`, `/rule`, `/check`, `/propose`

**Hermes Dialog system prompt：**
- 注入世界状态摘要（精简版，只含当前章节相关的实体和事实）
- 注入当前章节上下文（前文、大纲）
- 注入写作偏好（风格、复杂度）
- 专用命令集：`/write`, `/continue`, `/revise`, `/chapter`

**关键原则：** 一致性由结构化数据保证，不依赖对话记忆。Athena 修改世界状态后，Hermes 下次生成时自动拿到最新摘要。

## 前端架构

### 导航结构

顶部导航新增两个入口：

```
项目列表 | ☿ Hermes — 正文创作 | ⏣ Athena — 世界智慧 | 设置
```

路由：
- `/projects/:id` → Hermes 工作区（现有 ProjectDetail，移除世界模型 UI）
- `/projects/:id/athena` → Athena 仪表盘（新增）

### Athena 界面布局

```
┌──────────────────────────────────────────────────┐
│ ⏣ Athena   [本体] [状态] [演化]    Profile v3    │
├────────────────────────────────┬─────────────────┤
│                                │ ⏣ Athena 对话   │
│   主内容区                      │                 │
│   根据 tab 切换：               │  用户: 给张三加  │
│   · 本体：实体/关系/规则         │  暗伤设定...    │
│   · 状态：真相/认知/快照/时间线   │                 │
│   · 演化：大纲/提案/校验         │  AI: 已创建提案  │
│                                │  ...            │
│                                │                 │
│                                │  [输入框] [发送]  │
└────────────────────────────────┴─────────────────┘
```

### 前端 Store

新增 `stores/athena.ts`：
- 聚合三层数据的加载和缓存
- 管理 Athena Dialog 状态
- 提供 context injection 数据给 Hermes store

### 组件结构

```
components/athena/
├── AthenaShell.vue              — Athena 工作区容器
├── AthenaNav.vue                — 三层 tab 导航
├── AthenaMiniDialog.vue         — 右侧微缩对话
├── ontology/
│   ├── OntologyOverview.vue     — 本体聚合视图
│   ├── EntityList.vue           — 实体列表
│   ├── RelationGraph.vue        — 关系图谱（复用 ECharts）
│   └── RuleList.vue             — 规则列表
├── state/
│   ├── StateOverview.vue        — 状态聚合视图
│   ├── TruthProjection.vue      — 当前真相（复用 WorldProjectionViewer 逻辑）
│   ├── SubjectKnowledge.vue     — 主体认知（复用）
│   ├── ChapterSnapshot.vue      — 章节快照（复用）
│   └── Timeline.vue             — 时间线视图（新增）
└── evolution/
    ├── EvolutionOverview.vue     — 演化聚合视图
    ├── PlanView.vue              — 大纲 + 故事线
    ├── ProposalList.vue          — 提案列表（复用）
    └── ConsistencyView.vue       — 一致性校验结果
```

## 子项目分解

本 spec 覆盖整体架构设计。实现分 4 个子项目：

### 子项目 1：Athena Facade API + 数据模型
- 后端新增 `api/athena.py` 路由，facade 代理到现有模块
- Dialog 模型新增 `dialog_type` 字段 + migration
- Athena Dialog 端点（独立上下文）
- 新增 `GET /athena/state/timeline` 端点
- 不动现有 API，不动前端

### 子项目 2：Hermes 对话分离
- 现有 Dialog 迁移为 `dialog_type="hermes"`
- Hermes Dialog system prompt 注入 Athena 世界摘要
- Athena Dialog system prompt 注入完整世界知识
- 新增 context injection service
- 前端 chat store 支持双对话切换

### 子项目 3：Athena 前端界面
- 新增 `/projects/:id/athena` 路由
- AthenaShell + 三层 tab + 微缩对话
- 复用现有世界模型组件
- 从 SetupTab 迁出世界相关 UI

### 子项目 4：模块吞并与旧 API 退役
- 设定生成逻辑迁入 Athena ontology
- 拓扑逻辑迁入 Athena ontology
- 一致性校验迁入 Athena evolution
- 大纲/故事线迁入 Athena evolution
- 旧 API 标记 deprecated → 最终移除

### 实现顺序

子项目 1 → 子项目 2 → 子项目 3 → 子项目 4

每个子项目独立可交付、可测试。
