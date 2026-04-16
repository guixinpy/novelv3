# Phase 3 设计文档：交互优化 + 版本管理 + 项目工作区

> **版本**: v3.0 Phase 3  
> **日期**: 2026-04-15  
> **目标**: 完善用户体验，引入版本管理、项目工作区和更丰富的响应生成

---

## 1. 设计原则

Phase 3 延续 Phase 2 的 **Action Proposal + 对话确认** 机制，不引入独立审批面板。核心改进：

- **项目工作区**：在详情页可完整查看/编辑设定、故事线、大纲、章节
- **版本管理**：每个节点（设定/故事线/大纲/章节）支持保存历史版本、对比、回滚
- **富响应生成**：AI 回复可携带结构化卡片（角色卡、大纲节点、进度条）
- **对话状态机**：明确对话所处的状态，控制输入和可用操作

---

## 2. 功能边界

### 2.1 新增功能

| 功能 | 说明 | 优先级 |
|------|------|--------|
| 项目工作区（Workspace） | 详情页升级为 Tab 式工作区，支持查看和轻量编辑 | P0 |
| 版本管理 | 设定/故事线/大纲/章节的历史快照、对比、一键回滚 | P0 |
| 对话状态机 | 明确 `IDLE` / `CHATTING` / `PENDING_ACTION` / `GENERATING` / `REVISION` / `PAUSED` / `ERROR` 七态 | P0 |
| 富响应生成器 | AI 回复可内嵌卡片、进度条、操作按钮 | P0 |
| 拓扑图可视化 | 角色关系图、情节时间线的简单图形展示 | P1 |
| 导出模块 | 支持导出 Markdown / TXT（Phase 1-2 预留） | P1 |

### 2.2 不包含功能（推迟到 Phase 4）

- 反馈收集与偏好学习
- L2 LLM 提取器与交叉验证
- 多 Agent 架构
- 复杂插件系统

---

## 3. 项目工作区（Workspace）

### 3.1 页面结构

工作区取代 Phase 1 的简易详情页，成为项目的核心视图。

```
/project/:id/workspace
├── 概览          # 项目信息、进度、最近动态
├── 设定          # 世界观、角色、核心概念（可编辑 JSON/表单）
├── 故事线        # 主线/支线/伏笔（可视化时间线）
├── 大纲          # 章节目录 + 每章摘要/场景（可编辑）
├── 正文          # 章节列表，支持阅读模式
├── 拓扑图        # 角色关系图、情节时间线（简单图形）
└── 版本历史      # 全局版本记录
```

### 3.2 轻量编辑

工作区中的编辑是**本地草稿式**的：
- 用户修改内容后点击"保存草稿"
- 只有点击"提交为正式版"时才会触发 Action Proposal，由 AI 确认后覆盖当前版本
- 或者直接触发 `revise_xxx` 的 Action，让 AI 基于修改重生成

### 3.3 与对话的联动

工作区中任何内容都可以被用户引用到对话中：
- "把第三章的这段改一下：[引用正文片段]"
- 前端自动将引用内容作为上下文附加到用户输入

---

## 4. 版本管理

### 4.1 版本存储策略

**全量快照**，每张表独立管理版本。理由：
- 节点之间（设定/故事线/大纲）不频繁联动回滚
- 实现简单，对个人用户数据量可控

```python
class VersionManager:
    async def create_version(
        self,
        project_id: str,
        node_type: "SETUP" | "STORYLINE" | "OUTLINE" | "CHAPTER",
        node_id: str,
        content: str,  # JSON 序列化后的全量内容
        description: str,
        author: "ai_system" | "user",
    ) -> Version:
        ...
```

### 4.2 数据表：versions

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(PK) | UUID |
| project_id | String(FK) | 关联项目 |
| node_type | String | `setup` / `storyline` / `outline` / `chapter` |
| node_id | String | 对应节点 ID |
| version_number | Integer | 自增版本号 |
| content | Text | 全量快照（JSON） |
| description | String | 版本说明 |
| author | String | `ai_system` / `user` |
| created_at | DateTime | 创建时间 |

### 4.3 版本对比

前端做轻量级文本对比：
- 设定/故事线/大纲：用 `diff` 对比 JSON 的文本化表示
- 章节：用行级 diff 对比 Markdown 正文

引入轻量级 diff 库（如 `diff-match-patch`）处理文本差异，**不自研分句 diff 算法**。

**具体策略**：
- **章节正文**：先用 `diff-match-patch` 的 **行级模式**（`diff_linesToChars_`）预处理 Markdown 文本，再做 diff，避免字符级碎片导致可读性变差。
- **设定/故事线/大纲**：不要直接 diff 原始 JSON 字符串，而是先格式化为 `key: value\n` 的平铺文本（或按字段拆成数组），再逐字段 diff。这样用户看到的是"世界观描述：修改了 XX"而不是 JSON 括号乱飞。

### 4.4 回滚机制

回滚只恢复指定节点的 `content`，不影响其他节点。

```
POST /api/v1/projects/{project_id}/versions/{version_id}/rollback
```

回滚成功后，在工作区显示提示，并生成新版本（`description: "Rollback to vX"`）。

---

## 5. 对话状态机

### 5.1 状态定义

```typescript
type DialogState =
  | 'IDLE'           // 初始状态，等待用户输入
  | 'CHATTING'       // 正常对话中
  | 'PENDING_ACTION' // 等待用户确认某个 Action Proposal
  | 'GENERATING'     // AI 正在生成内容（设定/大纲/章节）
  | 'REVISION'       // 用户或 AI 正在对某个节点进行修订
  | 'PAUSED'         // 连续写作被暂停
  | 'ERROR';         // 发生错误，等待用户处理
```

### 5.2 状态转换规则

```
IDLE --(用户输入)--> CHATTING
CHATTING --(AI 返回 pending_action)--> PENDING_ACTION
CHATTING --(API 错误/超时)--> ERROR
CHATTING --(用户主动结束对话/切换项目)--> IDLE
PENDING_ACTION --(用户确认)--> GENERATING
PENDING_ACTION --(用户取消)--> CHATTING
GENERATING --(完成)--> CHATTING
GENERATING --(失败)--> ERROR
GENERATING --(用户点击暂停)--> PAUSED
ERROR --(用户重试)--> GENERATING
ERROR --(用户关闭/忽略)--> IDLE
CHATTING --(用户发起修订)--> REVISION
REVISION --(完成)--> CHATTING
PAUSED --(用户点击继续)--> GENERATING
PAUSED --(用户取消)--> CHATTING
```

### 5.3 状态对 UI 的影响

| 状态 | UI 表现 |
|------|---------|
| `IDLE` | 输入框可用，显示快速开始按钮 |
| `CHATTING` | 输入框可用 |
| `PENDING_ACTION` | 输入框禁用或缩小，突出显示确认卡片 |
| `GENERATING` | 输入框禁用，显示进度条/骨架屏 |
| `REVISION` | 工作区进入编辑模式，对话侧显示修订上下文 |
| `PAUSED` | 输入框可用，显示"继续生成"和"取消"按钮 |
| `ERROR` | 输入框可用，消息气泡内显示重试按钮 |

---

## 6. 富响应生成器

### 6.1 响应消息协议扩展

由于无原生 tool use，**不依赖 LLM 返回 `attachments` 结构**。前端根据 `ui_state`（对话/视图状态）和 `project_diagnosis`（项目缺失项诊断）自动渲染辅助卡片：

```typescript
interface AIResponse {
  message: string;
  pending_action?: PendingAction;
  ui_state?: UIState;
  project_diagnosis?: ProjectDiagnosis;
}

interface UIState {
  dialog_state: 'IDLE' | 'CHATTING' | 'PENDING_ACTION' | 'GENERATING' | 'REVISION' | 'PAUSED' | 'ERROR';
  current_view: 'overview' | 'setup' | 'storyline' | 'outline' | 'content' | 'topology' | 'versions';
  generating_progress?: { node_type: string; current: number; total: number };
}

interface ProjectDiagnosis {
  missing_items: string[];
  completed_items: string[];
  suggested_next_step: string | null;
}
```

### 6.2 前端状态驱动渲染

**状态更新路径**：用户在工作区切换 Tab 时，前端主动调用 `POST /api/v1/projects/{id}/state` 上报当前视图（`ui_state`），后端透存并返回最新的 `ui_state` 和 `project_diagnosis`。不依赖 LLM 推断用户当前在看什么。

**渲染优先级规则**（高优先级覆盖低优先级）：
1. 当 `dialogState === 'GENERATING'` 时，**始终显示进度条/骨架屏**，无论当前在哪个 Tab
2. 当 `dialogState === 'PENDING_ACTION'` 时，优先显示确认卡片
3. 当 `current_view === 'setup'` 时，对话气泡旁显示角色卡片
4. 当 `current_view === 'outline'` 时，显示大纲节点折叠卡片
5. 当 `current_view === 'topology'` 时，工作区主体显示拓扑图
6. 版本相关 API 返回 `{"version_saved": true, "version_id": "..."}` 时，前端据此弹 Toast

> 核心原则：辅助卡片的显示由**前端已知状态**决定，不解析 LLM 回复中的任何附件指令。

---

## 7. 拓扑图可视化（简化版）

### 7.1 角色关系图

使用力导向图简单展示：
- 节点：角色（大小按出场次数）
- 边：关系类型（友谊/敌对/恋人等），颜色区分

技术选型：**D3.js 力导向图** 或 **ECharts Graph**。推荐 ECharts，封装更成熟。

### 7.2 情节时间线

横向时间轴展示：
- X 轴：章节序号
- 节点：事件（圆点大小按事件影响度）
- 连线：主情节线的走向

### 7.3 与编辑联动

可视化是**只读**的。Phase 3 不支持直接在图上拖拽编辑节点，编辑需回到工作区的表单/文本模式。

---

## 8. 导出模块

### 8.1 支持格式

| 格式 | Phase 3 支持 |
|------|-------------|
| Markdown | ✅ |
| TXT | ✅ |
| DOCX | ❌（Phase 4 或后续） |
| EPUB | ❌（Phase 4 或后续） |

### 8.2 导出内容选项

```json
{
  "include_setup": true,
  "include_outline": true,
  "chapter_range": [1, 10]
}
```

### 8.3 异步导出

导出任务放入后台执行（对于长篇小说可能需要几秒）：

```
POST /api/v1/projects/{project_id}/export
GET  /api/v1/export/{task_id}/status
GET  /api/v1/export/{task_id}/download
```

Phase 3 数据量小，也可以直接同步返回文件流，简化实现。

---

## 9. API 扩展

### 9.1 版本管理 API

```
GET    /api/v1/projects/{project_id}/versions
GET    /api/v1/projects/{project_id}/versions?node_type=setup&node_id=xxx
POST   /api/v1/projects/{project_id}/versions/{version_id}/rollback
DELETE /api/v1/projects/{project_id}/versions/{version_id}
```

### 9.2 导出 API

```
POST /api/v1/projects/{project_id}/export
GET  /api/v1/export/{task_id}/status
GET  /api/v1/export/{task_id}/download
```

### 9.3 工作区数据 API

复用现有 API，工作区是前端组合页面：
- `GET /api/v1/projects/{project_id}/setup`
- `GET /api/v1/projects/{project_id}/storyline`
- `GET /api/v1/projects/{project_id}/outline`
- `GET /api/v1/projects/{project_id}/chapters`（章节列表，返回 `{ chapters: ChapterSummary[] }`）
- `GET /api/v1/projects/{project_id}/topology`

### 9.4 UI 状态 API

```
POST /api/v1/projects/{project_id}/state
```

**请求体**：
```json
{
  "current_view": "outline"
}
```

**响应**：
```json
{
  "ui_state": {
    "dialog_state": "CHATTING",
    "current_view": "outline"
  },
  "project_diagnosis": {
    "missing_items": ["storyline"],
    "completed_items": ["setup"],
    "suggested_next_step": "preview_storyline"
  }
}
```

后端将 `current_view` 直接写入 `dialogs.current_view` 字段，供后续 `Intent Router` 和前端渲染使用。

### 9.5 ChapterSummary 结构

`GET /api/v1/projects/{project_id}/chapters` 返回的章节摘要：

```json
{
  "chapters": [
    {
      "chapter_index": 1,
      "title": "第一章 初入末世",
      "word_count": 3200,
      "status": "generated"
    }
  ]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| chapter_index | Integer | 章节序号 |
| title | String | 章节标题 |
| word_count | Integer | 字数 |
| status | String | `pending` / `generating` / `generated` / `approved` / `rejected` |

---

## 10. 轻量监控

仅保留结构化日志记录关键耗时，规范为 3 个固定事件，不引入专门的 `PerformanceMonitor` 类：

```python
logger.info("generation_completed", latency_ms=latency_ms, project_id=pid, node_type=node_type)
logger.info("version_created", latency_ms=latency_ms, project_id=pid, node_type=node_type)
logger.info("export_completed", latency_ms=latency_ms, project_id=pid, format=fmt)
```

后续可通过 `jq` 或简单脚本对这些日志做分析。`cache_access` 等其它事件按需补充。

---

## 11. 里程碑 M3 验收标准

- [ ] 项目工作区可完整查看设定/故事线/大纲/章节
- [ ] 设定/故事线/大纲/章节均有版本历史，可对比和回滚
- [ ] 对话状态机完整，UI 随状态正确变化
- [ ] 前端可根据对话状态自动渲染角色卡、大纲节点、进度条等辅助内容
- [ ] 角色关系图和情节时间线可在工作区查看
- [ ] 支持导出 Markdown / TXT

---

## 12. 风险与应对

| 风险 | 应对 |
|------|------|
| 版本历史过多导致数据库膨胀 | 只保留最近 50 个版本，更旧的自动归档为文件 |
| 工作区编辑与对话修订逻辑冲突 | 统一走 `revise_xxx` Action，工作区编辑只是触发 Action 的另一种入口 |
| 拓扑图可视化性能差 | 节点数超过 200 时启用聚合/简化渲染 |
| 富响应格式增加前后端耦合 | 改为前端状态驱动渲染，不依赖后端返回附件结构 |
