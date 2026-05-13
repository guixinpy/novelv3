---
title: Workspace 性能架构治理设计
date: 2026-04-29
status: approved
scope: Hermes / Athena / Calliope 高频切换、冷启动、重数据渲染、请求竞态与性能回归防护
---

# Workspace 性能架构治理设计

## 目标

把项目工作区从“路由进入即重建、各模块各拉各的”改成“项目级数据会话 + 工作区按需激活 + 可度量性能门禁”。

本设计不只修 Athena 与 Hermes 切换卡顿，也覆盖冷启动、请求风暴、重复数据加载、长对话历史、正文编辑重渲染、过期响应覆盖新状态等系统性问题。

## 现状问题

- `/projects/:id/hermes`、`/athena`、`/manuscript` 是独立 route component，切换会卸载当前视图。
- Hermes 初始化会重置项目局部状态，再拉 chat、diagnosis、project、setup、storyline、outline、chapters、versions。
- Hermes 历史 action watcher 会在返回页面后重放最后一个已完成 action，触发二次刷新。
- Athena 进入时无条件 `athena.reset()`，同项目热切换仍重新拉 ontology/messages/chapters。
- Calliope 进入时默认重新加载第一章，不能恢复上次章节。
- API 粒度偏细，冷启动和工作区切换需要多个 GET。
- 缺少稳定性能基线，无法阻止请求数量和切换耗时回退。

本地实测基线：

- `Athena -> Hermes`：10 个 API。
- 快速连续切换 7 次：46 个 API。

## 设计原则

- **同项目热切换不 reset**：只在项目 ID 变化或明确 dirty 时清状态。
- **入口数据最小化**：当前视图只加载可见区域需要的数据，重数据懒加载。
- **请求去重**：同一资源同一时刻只有一个 in-flight 请求。
- **过期响应不可写入**：所有异步写入必须经过 project scope / request ticket 校验。
- **刷新有原因**：所有 refresh 必须来自 route activation、ui hint、dirty target、用户动作或后台任务完成。
- **性能可测试**：请求数量、console error、切换耗时进入浏览器 smoke 脚本。

## 目标架构

```text
Vue Router
  -> Project Workspace Session
       -> project cache
       -> hermes cache
       -> athena cache
       -> manuscript cache
       -> request coordinator
       -> dirty target registry
       -> performance probes

Views
  HermesView      -> ensureHermesWorkspace(projectId)
  AthenaView      -> ensureAthenaWorkspace(projectId, section)
  ManuscriptView  -> ensureManuscriptWorkspace(projectId, chapterIndex)
```

视图负责声明需求，不直接决定全量刷新策略。

## 前端数据层

新增 `frontend/src/stores/projectWorkspace.ts`：

- 保存 `activeProjectId`、各工作区最后激活时间、dirty targets。
- 提供 `enterProject(projectId)`、`markDirty(targets)`、`consumeDirty(target)`。
- 提供 `rememberWorkspaceRoute(workspace, path)`、`lastManuscriptChapterByProject`。
- 提供轻量性能 probe 的共享类型。

新增 `frontend/src/stores/requestCache.ts`：

- `dedupe(key, loader)`：复用同 key 的 in-flight Promise。
- `markFresh(key)` / `isFresh(key, ttlMs)`：短 TTL 热缓存。
- `invalidate(prefix)`：按项目或资源失效。
- 不缓存失败结果。

改造现有 stores：

- `project.ts` 保留 lane request ticket，但加载函数先走 request cache。
- `chat.ts` 初始化拆成 `initProjectIfNeeded()` 与 `refreshHermesIfDirty()`。
- `athena.ts` 增加 project scope，不再同项目热切换 `reset()`。
- `manuscript.ts` 保留选中章节与 active revision，项目变化才 reset。

## 工作区生命周期

### Hermes

进入 Hermes：

1. 如果 projectId 变化：初始化 project scope。
2. 如果同项目且缓存存在：立即展示。
3. 根据 dirty targets 决定是否刷新 `messages / diagnosis / project / content / versions`。
4. 初始化期间禁用历史 action watcher。
5. action watcher 只处理“本次会话新出现”的 fingerprint。

### Athena

进入 Athena：

1. 不再无条件 reset。
2. ontology/messages 只在冷启动、dirty 或 TTL 过期时加载。
3. section 数据懒加载：
   - entity/relation/rule 共享 ontology。
   - projection/knowledge 共享 state。
   - outline/storyline 共享 evolution plan。
   - retrieval/consistency/optimization 可设置短 TTL 或每次主动刷新。

### Calliope

进入 Calliope：

1. 恢复项目上次章节。
2. chapters 列表可复用 project cache。
3. 章节内容和 active revision 走 request cache。
4. 切出页面不丢本地批注/修正 draft。

## 后端优化

阶段性新增 `GET /api/v1/projects/{project_id}/workspace-bootstrap`：

返回冷启动所需最小数据：

```json
{
  "project": {},
  "diagnosis": {},
  "chapters": [],
  "latest_versions": [],
  "dialog_summaries": {
    "hermes": { "message_count": 0, "latest_message_id": null },
    "athena": { "message_count": 0, "latest_message_id": null }
  }
}
```

后续扩展：

- Hermes/Athena messages 支持 `limit`、`before_id`、`after_id`。
- heavy detail 继续独立 API，不塞进 bootstrap。

## 性能验收指标

阶段性指标：

- `Athena -> Hermes`：从 10 个 API 降到 4 个以内。
- 快速切换 7 次：从 46 个 API 降到 18 个以内。
- 同项目热切换：主内容区域 150ms 内可见旧缓存。
- 无 console error。
- `npm run build` 通过。

最终指标：

- 项目冷启动 API 数减少 40% 以上。
- 长 Hermes 历史不全量阻塞首屏。
- Athena section 切换只加载对应 section 数据。
- Calliope 返回保留上次章节。

## 测试策略

- Vitest：request cache、workspace state、Hermes watcher、Athena 同项目不 reset、Manuscript 章节恢复。
- Browser smoke：打开测试项目，执行 Hermes/Athena/Calliope 切换，记录 API 数、耗时、console error。
- Backend pytest：bootstrap API 合同、messages limit/after_id 合同。
- Build gate：每阶段跑 `npm run build`。

## 风险与约束

- 不一次性重写路由结构，先在现有 route component 上收敛数据生命周期。
- 不把所有数据塞进一个巨型 store，避免状态边界失控。
- 不用纯 `KeepAlive` 作为主方案；它只能减少卸载，不能解决请求风暴与 stale response。
- 不改变后端 404 合同；前端继续按 diagnosis/dirty targets 决定是否请求可选资源。
