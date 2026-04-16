# Phase 2 设计文档：故事线 + 大纲 + 连续写作 + Action Proposal 机制

> **版本**: v3.0 Phase 2  
> **日期**: 2026-04-15  
> **目标**: 补全大纲生成能力，引入拓扑图、基础一致性检查和连续写作调度

---

## 1. 核心交互机制：Action Proposal 循环

Phase 2 的交互模式区别于传统的"命令-执行"或"死板审批流"。AI 作为流程导演，在自由对话中识别时机，以自然语言向用户提出建议操作，经用户确认后由系统执行，执行结果重新注入上下文供 AI 反馈。

### 1.1 对话示例（验证设计）

```
我: hello!
AI: 你好啊，我是墨舟，你的长篇写作助手。今天想写什么故事？

我: 我想写一本末世小说，你能给我点灵感吗？
AI: 可以。末世题材有很多方向，比如病毒爆发、气候灾变、异兽入侵……
        你更倾向于生存冒险，还是人类重建文明的主题？

我: 那你按照我跟你聊的这个主角性格创建一下主角的设定吧！
AI: 好的！基于我们的讨论，我为主角草拟了以下设定：
        [设定卡片展示]
        如果你确认没问题，我就把这个设定正式保存到项目里。
        [用户看到确认卡片：同意 / 取消]

用户点击"同意"
系统执行保存 -> 结果回传上下文
AI: 已完成主角设定创建。接下来我建议补充世界观和势力分布，
        这样故事线会更有支撑。你觉得呢？

用户点击"取消"
系统记录取消 -> 原因/说明回传上下文
AI: 操作已中断。是觉得性格设定需要调整，还是想先聊聊背景故事？

我: 还有什么要设定的吗？
AI: 经过分析，目前项目还缺少世界观和势力设定。
        建议先把这两块补齐，再进入故事线规划。

我: 那就开始写第二章大纲吧！
AI: 很抱歉，经过分析，主枝干结构尚未生成，最好不要跳过步骤进行大纲创作。
        我们可以先创建故事线，再基于它生成完整大纲。要我先生成几条供你选择吗？

我: 那就先创建主枝干结构吧！
AI: 很好。根据目前的设定，我设计了以下主枝干方案：
        A. 病毒源于实验室泄露，主角是知情者后裔...
        B. 太阳风暴导致全球停电，主角是前电网工程师...
        你选哪个，或者有什么想修改的？

我: 就选 A 吧，但是要把主角改成普通人。
AI: 明白，主角改为普通人。我现在生成调整后的故事线：
        [故事线预览]
        [确认卡片：同意 / 取消]
```

### 1.2 Action Proposal 协议

由于系统使用纯 API Key 调用（无原生 tool use），采用**混合模式**确保对话能可靠触发操作：

#### 第一层：固定话术提案（主路径）

在 system prompt 中要求 LLM 只在明确需要用户确认时才说固定话术。LLM 的自然语言回复中不应包含 JSON、XML 或代码块。

```markdown
可用的固定话术：
- "我现在可以为你生成主角设定，是否继续？" → generate_setup
- "我现在可以为你生成故事线，是否继续？" → generate_storyline
- "我现在可以为你生成章节大纲，是否继续？" → generate_outline
```

后端检测到固定话术后，直接拼接对应 `pending_action`。

#### 第二层：XML 标记双保险（补漏路径）

如果固定话术无法清晰表达，允许 LLM 在回复末尾附加一个注释标记作为补充：

```markdown
我已经理解了你的需求，接下来为你生成主角设定。

<!--ACTION:{"type":"generate_setup","scope":"character"}-->
```

后端在第一层未命中时，通过正则 `<!--ACTION:(.*?)-->` 提取并解析标记，同样拼接 `pending_action`。

#### 第三层：上下文继承确认

如果上一轮 AI 已提出 proposal，用户本轮回复确认/取消意向时，系统不依赖 LLM 再次输出固定话术，直接触发对应 action：

- **确认**："好的"、"可以"、"同意"、"那就这样吧"、"行"、"OK"、"没问题"、"搞吧"
- **取消**："算了"、"先不要"、"等等"、"不对"、"改一下"、"先别"、"我还没想好"、"换一个"

#### 第四层：快捷命令 / 按钮兜底（极端情况）

前端在对话气泡下方始终提供快捷操作按钮（如"生成设定""生成故事线"），用户点击后直接触发对应 action，完全绕过 LLM。同时支持手动输入斜杠命令：

```
/generate setup
/generate storyline
/generate outline
```

```json
{
  "message": "AI 的自然语言回复...",
  "pending_action": {
    "id": "act_xxx",
    "type": "generate_setup",
    "description": "AI 解释为什么要做这个操作",
    "params": {
      "project_id": "xxx",
      "scope": "character"
    },
    "requires_confirmation": true
  },
  "project_state": {
    "missing_items": ["world_building", "plotlines"],
    "completed_items": ["setup_characters"],
    "suggested_next_step": "generate_storyline"
  }
}
```

#### 安全机制

无论通过哪一层触发 action，后端都必须执行以下保护：

1. **参数白名单**：后端只接受预定义的 `type`（如 `generate_setup`、`generate_storyline`、`generate_outline`），非法 type 直接拒绝
2. **确认卡片**：任何 action 在真正执行前，必须通过前端确认卡片由用户点击"同意"后方可执行
3. **沙箱执行**：action 处理函数只读写项目数据库，禁止直接操作文件系统或发起外部网络请求

### 1.3 前端确认卡片

用户在对话气泡下方看到可交互卡片：
- **操作说明**：AI 的自然语言解释
- **预览内容**（如有）：设定卡片/故事线摘要/大纲摘要
- **操作按钮**：`同意执行` / `取消` / `修改后再执行`

用户选择后，前端发送：
```json
POST /api/v1/dialog/resolve-action
{
  "action_id": "act_xxx",
  "decision": "confirm" | "cancel" | "revise",
  "comment": "用户补充说明"
}
```

### 1.4 意图识别规则表

| 意图 | 关键词/正则示例 | 上下文继承规则 |
|------|----------------|----------------|
| `generate_setup` | `创建(主角\|人物\|设定\|世界观)`、`给我人物设定`、`写一下世界观` | 上轮 AI 提议生成设定，本轮回复"好的/可以/同意/行/OK/那就这样吧" |
| `generate_storyline` | `创建(主枝干\|故事线)`、`生成故事线`、`剧情怎么走` | 上轮 AI 提议生成故事线，本轮口语化确认 |
| `generate_outline` | `写第.*章大纲`、`生成章节大纲`、`大纲怎么写` | 上轮 AI 提议生成大纲，本轮口语化确认 |
| `query_state` | `还有什么要设定的吗`、`接下来做什么`、`然后呢`、`接下来呢` | 无 |
| `confirm_proposal` | `同意`、`可以`、`好的`、`行`、`OK`、`没问题`、`就这样`、`搞吧`、`那就这样吧` | **仅在上轮存在 pending_action 时生效** |
| `cancel_proposal` | `算了`、`先不要`、`等等`、`不对`、`改一下`、`先别`、`我还没想好`、`换一个` | **仅在上轮存在 pending_action 时生效** |

**兜底策略**：任何意图匹配失败时，系统不拼接 `pending_action`，直接让 LLM 自由回复。

---

### 1.5 结果回传机制

无论确认还是取消，系统都会生成一条 `system` 角色的上下文消息：

```json
{
  "role": "system",
  "content": "[ACTION_RESULT] type=generate_setup, decision=confirm, result=success, setup_id=xxx"
}
```

或：

```json
{
  "role": "system",
  "content": "[ACTION_RESULT] type=generate_setup, decision=cancel, reason=用户想先修改主角背景"
}
```

AI 在下一轮生成时必须基于这些 system 消息给出反馈。

---

## 2. 功能边界

### 2.1 新增功能

| 功能 | 说明 | 优先级 |
|------|------|--------|
| 故事线生成 | 基于设定生成结构化故事线（主线+支线+伏笔+里程碑） | P0 |
| 完整单章大纲 | 基于故事线生成每章标题、摘要、场景、角色、目的 | P0 |
| Action Proposal 协议 | AI 提案 → 用户确认 → 执行 → 结果回传 | P0 |
| 项目状态诊断 | AI 可查询当前项目缺失项，主动引导用户补全 | P0 |
| 拓扑图基础版 | 从大纲自动解析节点/边，支持角色关系、情节时间线查询 | P1 |
| L1 规则提取器 | 正则/关键词提取事实（角色状态、地点、时间） | P0 |
| 基础一致性检查 | CharacterStateChecker、LocationChecker | P0 |
| 连续写作调度器 | 按大纲逐章生成，自动注入前文上下文 | P1 |
| 全局错误处理 | AI 调用重试、超时、降级 | P1 |

### 2.2 不包含功能（推迟）

- 版本管理与回滚
- 复杂审批面板
- L2 LLM 提取器
- 交叉验证
- 反馈学习与偏好画像
- 多 Agent 架构

---

## 3. 数据模型扩展

Phase 2 在 Phase 1 基础上新增/扩展以下表。

### 3.1 outlines（新增）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(PK) | UUID |
| project_id | String(FK) | 关联项目 |
| total_chapters | Integer | 总章节数 |
| chapters | JSON | ChapterOutline[] |
| plotlines | JSON | Plotline[] |
| foreshadowing | JSON | Foreshadowing[] |
| status | String | `pending` / `generating` / `generated` / `approved` / `rejected` |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### 3.2 storylines（新增）

专门存储故事线/主枝干结构，与 outline 解耦。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(PK) | UUID |
| project_id | String(FK) | 关联项目 |
| plotlines | JSON | Plotline[] |
| foreshadowing | JSON | Foreshadowing[] |
| status | String | `pending` / `generating` / `generated` / `approved` / `rejected` |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### 3.3 topologies（新增）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(PK) | UUID |
| project_id | String(FK) | 关联项目 |
| version | Integer | 拓扑图版本 |
| nodes | JSON | TopologyNode[] |
| edges | JSON | TopologyEdge[] |
| indexes | JSON | 索引缓存 |
| updated_at | DateTime | 更新时间 |

### 3.4 consistency_checks（新增）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(PK) | UUID |
| project_id | String(FK) | 关联项目 |
| chapter_index | Integer | 章节序号 |
| checker_name | String | 检查器名称 |
| severity | String | `fatal` / `warn` / `info` |
| subject | String | 检查对象 |
| description | String | 问题描述 |
| evidence | Text | 证据文本 |
| suggested_fix | Text | 修复建议 |
| status | String | `pending` / `acknowledged` / `resolved` |
| created_at | DateTime | 创建时间 |

### 3.5 extracted_facts（新增）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(PK) | UUID |
| project_id | String(FK) | 关联项目 |
| chapter_index | Integer | 来源章节 |
| type | String | FactType |
| source | String | `l1_rule` |
| confidence | Float | 置信度 |
| data | JSON | {subject, attribute, old_value, new_value} |
| evidence | JSON | {text, position, summary} |
| created_at | DateTime | 创建时间 |

---

## 4. 核心 API 扩展

### 4.1 故事线 API

```
POST /api/v1/projects/{project_id}/storyline/generate
GET  /api/v1/projects/{project_id}/storyline
```

### 4.2 大纲 API（Phase 1 预留，Phase 2 实现）

```
POST /api/v1/projects/{project_id}/outline/generate
GET  /api/v1/projects/{project_id}/outline
PATCH /api/v1/projects/{project_id}/outline/chapters/{chapter_index}
```

### 4.3 拓扑图 API

```
GET /api/v1/projects/{project_id}/topology
GET /api/v1/projects/{project_id}/topology/character-graph
GET /api/v1/projects/{project_id}/topology/timeline
```

### 4.4 一致性检查 API

```
POST /api/v1/projects/{project_id}/chapters/{chapter_index}/consistency-check
GET  /api/v1/projects/{project_id}/consistency-issues
```

### 4.5 对话/Action API

```
POST /api/v1/dialog/chat
POST /api/v1/dialog/resolve-action
GET  /api/v1/projects/{project_id}/state-diagnosis
```

`state-diagnosis` 返回项目当前缺失项和已完成项，供 AI 引导用户使用。

---

## 5. 基础设施继承

Phase 2 沿用并扩展 Phase 1 已建立的基础设施：

- **Event Bus**：用于触发一致性检查、拓扑更新等异步事件
- **CacheManager**：缓存拓扑图和频繁访问的章节内容
- **ErrorHandler / with_retry**：统一处理 AI 服务超时和异常
- **TokenBudgetManager / ContextCompressor**：扩展新增 `storyline`、`outline` 预算项

Phase 2 新增**轻量级后台任务队列**（基于 `asyncio` + SQLite），用于异步执行一致性检查和拓扑构建，避免阻塞主线程。

```python
class BackgroundTaskQueue:
    async def enqueue(self, task_type: str, payload: dict) -> str:
        # 写入 SQLite 任务表
        ...

    async def worker_loop(self):
        # 单 worker 循环消费任务
        ...
```

---

## 6. AI 引擎扩展

### 5.1 Prompt 模板新增

- `generate_storyline`：基于设定生成故事线
- `generate_outline`：基于故事线生成完整单章大纲
- `diagnose_project_state`：分析项目当前状态，给出下一步建议
- `build_chapter_context_v2`：Phase 2 版章节上下文，注入前文摘要、拓扑图相关节点、一致性检查结果

### 5.2 TokenBudgetManager 调整

Phase 2 新增 `storyline` 和 `outline` 预算项：

```python
class TokenBudgetManager:
    DEFAULT_BUDGET = {
        # ... Phase 1 项
        "storyline": 1500,
        "outline_chapter": 400,  # 每章大纲
        "topology_nodes": 800,
        "consistency_notes": 600,
    }
```

### 5.3 上下文压缩器增强

- `compress_storyline`：将故事线压缩为适合 prompt 的摘要
- `compress_outline`：按相关度压缩大纲（当前章及前后 2 章优先）
- `compress_topology`：提取与当前章节相关的拓扑子图

---

## 7. 拓扑图基础版

### 6.1 自动构建

大纲生成后，系统自动解析并构建拓扑图：

```python
class TopologyBuilder:
    def build_from_outline(self, project_id: str, outline: Outline) -> Topology:
        nodes = []
        edges = []

        # 角色节点（来自 setup）
        for char in setup.characters:
            nodes.append(TopologyNode(type="CHARACTER", label=char.name, ...))

        # 地点节点（来自 outline 场景）
        for location in extract_locations(outline):
            nodes.append(TopologyNode(type="LOCATION", label=location, ...))

        # 事件节点（来自章节摘要）
        for chapter in outline.chapters:
            nodes.append(TopologyNode(type="EVENT", label=chapter.title, ...))

        # 关系边（角色关系 + 出场关系 + 因果关系）
        edges.extend(self.build_character_edges(setup))
        edges.extend(self.build_appearance_edges(outline))

        return Topology(nodes=nodes, edges=edges, ...)
```

### 6.2 增量更新

章节生成后，增量更新拓扑图：
- 新增地点/物品/事件节点
- 更新角色出场次数和最近出现章节
- 新增/更新关系边

---

## 8. L1 规则提取器与基础一致性检查

### 7.1 L1 提取器

基于最简单的正则和关键词模式，从章节内容中提取高频事实（角色名出现、关键地点、时间词）：

```python
class L1RuleExtractor:
    def extract(self, chapter: ChapterContent) -> list[ExtractedFact]:
        facts = []
        facts.extend(self.extract_character_mentions(chapter.content))
        facts.extend(self.extract_locations(chapter.content))
        return facts

    def extract_character_mentions(self, content: str) -> list[ExtractedFact]:
        # 只记录角色名出现，不做复杂状态推断
        ...
```

### 7.2 基础检查器

| 检查器 | 检查内容 | 状态来源 |
|--------|----------|----------|
| `CharacterStateChecker` | 角色状态冲突（如已死角色再次出现） | storyline / setup 中的 `character_status` 作为"官方状态"，与 L1 提取到的"角色在本章出现"做比对 |
| `LocationChecker` | 地点逻辑异常（同一角色同时出现在两地） | L1 提取的事实 |
| `TimelineChecker` | 时间线明显矛盾（时间倒流） | L1 提取的时间词 |

检查器输出 `ConsistencyIssue`，写入 `consistency_checks` 表。

> **character_status 说明**：在 setup 的 `characters` 或 storyline 中维护角色的官方状态字段（`alive` / `dead` / `missing` 等），`CharacterStateChecker` 通过比对官方状态与章节实际出现情况来检测冲突。

---

## 9. 连续写作调度器

### 8.1 职责

- 按大纲顺序逐章生成
- 每章生成前构建上下文（前文摘要 + 拓扑图 + 一致性提示）
- 支持暂停、继续、单章重试
- 每章生成后自动执行一致性检查

### 8.2 一致性检查失败策略

默认策略为 `warn_and_continue`：发现一致性问题时**不中断**连续写作，只将 issue 写入 `consistency_checks` 表并注入下一章上下文，避免频繁打断用户。

```python
class WritingScheduler:
    def __init__(self):
        self.state = {
            "project_id": "xxx",
            "current_chapter": 1,
            "status": "running" | "paused" | "completed",
            "last_error": None,
            "on_consistency_fail": "warn_and_continue",  # "pause" | "warn_and_continue" | "retry"
        }
```

### 8.3 API

```
POST /api/v1/projects/{project_id}/writing/start
POST /api/v1/projects/{project_id}/writing/pause
POST /api/v1/projects/{project_id}/writing/resume
POST /api/v1/projects/{project_id}/writing/chapters/{chapter_index}/retry
```

---

## 10. 里程碑 M2 验收标准

- [ ] 可生成结构化故事线并保存
- [ ] 可基于故事线生成完整单章大纲
- [ ] Action Proposal 机制跑通（提案 → 确认 → 执行 → 反馈）
- [ ] AI 能基于项目状态诊断主动引导用户
- [ ] 可连续生成多章内容
- [ ] 拓扑图能自动构建并支持基础查询
- [ ] 基础一致性错误可被检测并提示

---

## 11. 风险与应对

| 风险 | 应对 |
|------|------|
| Action Proposal 机制导致对话延迟 | 异步执行 + 前端骨架屏，复杂操作显示进度条 |
| 大纲过长超出模型上下文 | 上下文压缩器优先，必要时拆分大纲生成 |
| 拓扑图解析不准确 | L1 规则为主，允许用户手动修正节点（Phase 3） |
| 连续写作中途失败 | 断点续写，从失败章节重试，已生成章节保留 |
