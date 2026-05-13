---
title: 本地架构渐进式重构设计
date: 2026-04-29
status: approved
scope: backend service boundaries, local task system, action pipeline, workspace state, local diagnostics
---

# 本地架构渐进式重构设计

## 目标

在不引入外部基础设施的前提下，解决当前项目的结构性痛点：API 文件过大、任务状态散落、后台执行不可恢复、Hermes/Athena/Manuscript 工作区状态耦合、性能回归缺少门禁。

本项目现阶段只运行在本地单用户环境。允许大规模重构，但重构必须渐进、可测试、可回滚。外部 API 路径和前端主要交互保持兼容，内部实现逐阶段替换。

## 明确不做

- 不引入 PostgreSQL。
- 不引入 Redis、Celery、MQ 或分布式任务队列。
- 不做微服务拆分。
- 不做复杂 CI/CD。
- 不上远程观测平台。
- 不一次性重写全部路由和页面。

## 当前问题

### 后端边界混乱

`backend/app/api/dialogs.py`、`backend/app/api/athena.py`、`backend/app/api/world_model.py` 承担了路由、状态判断、任务执行、消息写入、UI hint、数据库读写等多种职责。文件变大后，任何局部改动都容易触发跨链路回归。

### 后台任务没有统一生命周期

项目已有 `background_tasks` 表，也已有查询 API，但任务创建和执行逻辑分散在不同 API 中。`consistency.py` 直接 `asyncio.ensure_future`，`writing_scheduler.py` 使用内存 dict，Hermes action 又有自己的后台执行逻辑。结果是：任务失败难追踪、后端重启后状态不可靠、前端无法稳定轮询。

### Action 管线不清晰

Hermes 的建议动作、用户确认、后台执行、系统消息、UI 刷新目标混在一起。当前已经能工作，但动作类型继续增加后会迅速变脆。

### 前端工作区状态仍有耦合风险

上一阶段已经降低了切换请求风暴，但长期看，Hermes、Athena、Manuscript 仍需要更清晰的工作区会话边界：哪个 store 拥有项目级状态，哪个 store 只拥有模块状态，什么时候刷新，什么时候复用缓存，都要固定下来。

### 本地调试证据不足

发生卡死、重复加载、任务失败时，目前主要靠浏览器 network、console 和人工判断。需要增加本地可读的 request/action/task 耗时和状态日志。

## 目标架构

```text
FastAPI routers
  -> services/*
       -> domain-specific orchestration
       -> task lifecycle
       -> action execution
       -> workspace read models
  -> models / schemas

Vue views
  -> projectWorkspace session
  -> module stores
  -> requestCache
  -> backend ui_hint / refresh_targets
```

路由层只负责 HTTP 参数、权限/存在性校验、响应模型。业务流程进入 service 层。后台执行统一进入本地任务系统。前端把项目级会话、模块数据、请求缓存分开。

## 后端服务边界

新增 `backend/app/services/`，按业务边界拆分：

- `services/tasks/`：本地任务生命周期。
- `services/actions/`：Hermes action proposal、resolve、execute、result。
- `services/workspace/`：workspace bootstrap 和聚合读模型。
- `services/dialog/`：Hermes/Athena 对话消息与分页。
- `services/athena/`：Athena 对话、检索、优化入口编排。
- `services/writing/`：写作状态、章节生成 retry、调度状态。

API 文件不再继续膨胀。每个阶段只迁移一个边界，迁移后原路由路径保持不变。

## 本地任务系统

统一使用现有 SQLite `background_tasks` 表作为任务事实源。

任务状态：

- `pending`
- `running`
- `completed`
- `failed`
- `cancelled`

新增 `BackgroundTaskService`：

- 创建任务。
- 标记开始。
- 标记完成。
- 标记失败。
- 标记取消。
- 查询项目最近任务。
- 查询单个任务详情。
- 恢复卡住任务。

新增 `LocalTaskRunner`：

- 使用当前 FastAPI 进程内 `asyncio.create_task` 执行。
- 每个任务拥有独立 DB session。
- 捕获异常并写入 `background_tasks.error`。
- 本地单用户场景只保证进程内执行，不承诺跨进程续跑。

后端重启时，遗留 `running` 任务不能假装继续执行。默认策略是标记为 `failed`，错误为 `Task interrupted by local process restart`。

## Action 管线

Hermes action 统一为：

```text
propose action
  -> persist PendingAction
  -> user resolve
  -> create BackgroundTask
  -> LocalTaskRunner executes action
  -> ActionResultService writes system message
  -> frontend refresh_targets refresh panel
```

阶段性保持同步兼容：旧前端若只看系统消息和 `action_result`，仍能工作。新前端可以优先使用 `task_id` 轮询。

## 前端工作区边界

`projectWorkspace` 是项目级会话源：

- active project。
- 最近访问的 workspace。
- dirty targets。
- 每个项目的 Manuscript 章节记忆。
- 对后台任务完成后的 refresh targets 做消费。

模块 store 只负责模块自身数据：

- `chat.ts`：Hermes 消息、pending action、对话状态。
- `athena.ts`：Athena ontology/state/messages/optimization。
- `manuscript.ts`：章节内容、revision draft、批注。

`requestCache` 只负责请求去重、短 TTL 和失效，不承载业务状态。

## 本地可调试性

增加轻量结构化日志，不引入平台：

```text
event=request_done request_id=... method=GET path=/api/v1/... status=200 duration_ms=12
event=task_done task_id=... task_type=generate_chapter project_id=... status=completed duration_ms=8342
event=action_failed action_type=generate_outline project_id=... task_id=... error="..."
```

日志输出到本地服务进程 stdout。测试只校验关键字段存在，不追求复杂日志系统。

## 渐进式实施

### 阶段 0：重构护栏

建立本地一键验证脚本，确认当前性能 smoke、后端测试、前端测试、前端构建全部可跑。没有护栏不进入拆分。

### 阶段 1：服务层骨架与 Workspace 读模型

先迁移低风险读路径：workspace bootstrap、dialog message 分页读、Athena dialog 读。外部 API 不变。

### 阶段 2：本地任务系统

实现 `BackgroundTaskService` 与 `LocalTaskRunner`，先迁移 consistency deep check。该链路已有 `background_tasks` 基础，适合做第一条样板。

### 阶段 3：写作调度持久化

替换内存态 `WritingScheduler`。写作 start/pause/resume/state 从进程内 dict 迁移到 SQLite 事实源。

### 阶段 4：Action Router 正式化

把 Hermes action resolve 和后台执行迁入 `services/actions/`，让 generate setup/storyline/outline/chapter 走统一任务管线。

### 阶段 5：前端工作区状态收敛

基于现有上一阶段性能优化结果，继续收敛 projectWorkspace/requestCache/module stores 的职责边界。重点防止重构后请求数回退。

### 阶段 6：API 文件瘦身

在服务层稳定后，再清理 `dialogs.py`、`athena.py`、`world_model.py` 的剩余职责。路由文件只保留 router、Depends、HTTP 错误和响应拼装。

### 阶段 7：本地诊断完善

补 request/action/task 日志和最近任务查看能力，让后续卡顿、卡死、失败有证据可查。

## 验收标准

每阶段必须满足：

- 后端相关 pytest 通过。
- 前端相关 vitest 通过。
- `npm run build` 通过。
- 关键链路浏览器 smoke 无 console error。
- workspace perf smoke 不比上一阶段退化。
- 每阶段单独提交。

最终满足：

- `dialogs.py`、`athena.py`、`world_model.py` 不再承载核心业务编排。
- 后台任务统一可查，失败可见。
- 写作状态不因后端 service 实例重建丢失。
- Hermes action 有统一执行链路。
- Hermes/Athena/Manuscript 热切换性能不退化。
- 本地日志能串起 request、task、action。

## 风险控制

- 先读路径，后写路径。
- 先 service 封装，后路由瘦身。
- 先单条任务链路，后迁移全部 action。
- 每阶段保持旧 API 兼容。
- 任何阶段测试失败，不进入下一阶段。
