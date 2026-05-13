---
title: 前端 E2E 合同测试设计
date: 2026-04-29
status: approved
scope: local frontend E2E, critical workflow regression, Playwright, temporary database isolation
---

# 前端 E2E 合同测试设计

## 目标

补一套更完整但不过度的前端 E2E，用来守住真实用户链路：项目创建、Hermes/Athena/Manuscript 工作区切换、Hermes action 后台任务、刷新目标消费、浏览器错误检查。

这套 E2E 不是 UI 细节测试。按钮颜色、布局微调、文案小改不应该导致它失效。路由、API 合同、关键用户流程、后台任务语义变更时，它应该失败并提示同步更新测试。

## 为什么会过时

E2E 一定会过时，原因是它描述的是产品行为。只要产品行为变化，测试就必须变化。

要控制的不是“永不过时”，而是“只在该过时时过时”。当前 `scripts/verify_full_app_ui.sh` 已经有路径漂移风险：它依赖大量 CSS selector、长文案和旧测试文件路径。继续堆这种脚本会让维护成本上升。

## 设计原则

- 只测稳定业务合同，不测视觉实现。
- 优先使用 `data-testid`，不依赖 CSS class、DOM 层级或图标。
- 每条 E2E 覆盖一个完整用户旅程，而不是覆盖所有按钮。
- 测试数据必须自动创建和清理。
- 默认使用本地临时 SQLite 数据库，不污染 `data/mozhou.db`。
- 不引入远程服务、CI 平台、录屏平台或复杂 fixture 服务。
- agent-browser 继续作为人工 dogfood/smoke 工具，不再作为正式 E2E 框架。

## 测试栈

使用 Playwright。

原因：

- 它是浏览器 E2E 的稳定标准工具。
- 可以拦截 console error、page error、network response。
- 可以直接使用角色、文本、test id 定位。
- 适合项目内脚本化运行，不需要额外服务。

## 本地运行模型

新增 E2E 运行脚本：

```text
scripts/verify_frontend_e2e.sh
```

脚本职责：

1. 创建临时 SQLite DB。
2. 使用临时 DB 跑 Alembic migration。
3. 构建前端静态资源。
4. 启动 FastAPI，服务 API 和静态 SPA。
5. 运行 Playwright E2E。
6. 收集日志。
7. 退出时清理后端进程、临时 DB、临时项目数据。

为支持临时 DB，后端允许读取：

```text
MOZHOU_DATABASE_URL=sqlite:////tmp/novelv3-e2e-xxx/mozhou.db
```

Alembic 也读取同一个环境变量。未设置时仍使用现有 `data/mozhou.db`，不改变本地正常启动行为。

## 关键 E2E 场景

### 场景 1：项目创建与工作区入口

用户从首页创建项目，进入项目默认 Hermes 工作区。

验证：

- 项目创建成功。
- URL 落到 `/projects/:id/hermes` 或项目默认入口。
- Hermes 输入区可用。
- 首屏无 console error、page error。

### 场景 2：工作区热切换合同

用户在 Hermes、Athena、Manuscript 之间快速切换。

验证：

- 切换后 URL 正确。
- 当前工作区主区域存在。
- 请求数不超过预算。
- 相同阶段没有重复请求风暴。
- console error、page error 为空。

请求预算延续现有 smoke 口径：

- Hermes 冷启动最多 1 个 workspace bootstrap 请求。
- Hermes 到 Athena 最多 2 个 Athena 初始化请求。
- Athena 回 Hermes 最多 1 个请求。
- 快速切换最多 8 个 API 请求。

### 场景 3：Hermes Action 到后台任务

用户在 Hermes 触发 setup preview，确认执行。

验证：

- pending action 出现。
- confirm 后返回并轮询 `task_id`。
- 无 API key 时任务进入 `failed`，错误可见，输入区恢复可用。
- 有 refresh targets 时前端能标记并消费。
- 页面不因为失败任务卡死。

### 场景 4：刷新恢复

在 Hermes/Athena 页面刷新。

验证：

- 页面重新加载后不请求不存在的 setup/storyline/outline 资源。
- 已存在的项目上下文能恢复。
- 无 4xx 噪音请求。
- 无 console error、page error。

## 稳定定位合同

新增或补齐稳定 test id：

- `project-create-button`
- `project-create-modal`
- `project-name-input`
- `project-create-submit`
- `workspace-hermes`
- `workspace-athena`
- `workspace-manuscript`
- `chat-input`
- `chat-send`
- `pending-action-card`
- `pending-action-confirm`
- `background-task-status`

已有稳定 test id 可复用，不重复新增。

## 与现有脚本的关系

`scripts/workspace_perf_smoke.mjs` 保留，作为轻量性能 smoke。

`scripts/verify_full_app_ui.sh` 不继续扩展。后续被 Playwright E2E 覆盖后，可以降级为历史脚本或删除。

`scripts/verify_local_quality.sh` 默认保持快速：

```text
pytest + vitest + build
```

只有显式设置：

```text
RUN_E2E=1 scripts/verify_local_quality.sh
```

才追加正式 E2E。

## 过时处理规则

修改或拓展功能时按这个标准处理：

- 只改视觉：不要改 E2E，除非 test id 被删。
- 改用户流程：先改 E2E 预期，再改实现。
- 改 API 合同：同步更新 E2E 和单元测试。
- 新增模块：只补该模块核心 journey，不扩大旧 journey。
- 删除旧功能：删除对应 E2E，不保留假测试。

## 验收标准

- `npm run test:e2e` 可独立运行。
- `scripts/verify_frontend_e2e.sh` 可从干净 shell 启动后端、迁移临时 DB、构建前端、运行 E2E、清理资源。
- Playwright 至少覆盖 4 个关键场景。
- E2E 失败输出包含 console error、page error 或网络失败信息。
- `scripts/verify_local_quality.sh` 仍保持默认快速运行。
- 所有新增行为有先失败后通过的测试证据。

## 风险控制

- 不一次性覆盖所有功能，先守住最高价值链路。
- 不依赖真实大模型成功返回，缺 API key 的失败状态也作为有效合同。
- 不用随机长等待，优先等待明确 UI 状态或 API 状态。
- 每阶段提交一次，并跑对应链路测试。
