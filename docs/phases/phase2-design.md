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

由于系统使用纯 API Key 调用（无原生 tool use），采用**服务端 Action Router** 架构确保对话能可靠触发操作。核心原则：**动作来源由系统状态决定，LLM 只负责自然语言解释，不再输出任何动作编码**。

#### 路由一：用户主动触发（主路径）

前端对话气泡下方始终提供快捷操作按钮，用户点击后直接向服务端发送动作请求：

```json
POST /api/v1/dialog/chat
{ "project_id": "xxx", "input_type": "button", "action_type": "preview_setup", "params": { "scope": "character" } }
```

同时支持斜杠命令：

```
/generate setup
/generate storyline
/generate outline
```

#### 路由二：服务端 Intent Router（补路径）

当用户发送自由文本时，服务端基于 `project_diagnosis + 当前对话状态 + 用户输入` 推断意图。若匹配度高，则自动生成 preview 动作并写入 `pending_actions` 表；若匹配度低，则**不拼接 pending_action，直接让 LLM 自由回复或追问**。

```python
class IntentRouter:
    def resolve(
        self,
        user_input: str,
        dialog_state: str,
        pending_action_id: str | None,
        diagnosis: ProjectDiagnosis,
    ) -> ActionCandidate | None:
        # 1. 若已有 pending_action，仅解析 confirm / cancel / revise
        if pending_action_id:
            return self.resolve_confirmation(user_input)
        # 2. 否则根据 diagnosis + 关键词匹配动作候选
        return self.resolve_action_candidate(user_input, diagnosis)
```

**关键约束**：自由文本不猜动作。只有以下情况才生成 `pending_action`：
- 用户输入包含明确动作关键词 + 项目当前状态允许该动作
- 输入与上轮 AI 提议高度相关（如 AI 刚问"要生成故事线吗？"，用户回"好"）

#### 路由三：上下文继承确认

如果上一轮 AI 已提出 proposal（存在未决 `pending_action`），用户本轮回复确认/取消意向时，系统不依赖 LLM，直接触发确认解析：

- **确认**："好的"、"可以"、"同意"、"那就这样吧"、"行"、"OK"、"没问题"、"搞吧"
- **取消**："算了"、"先不要"、"等等"、"不对"、"改一下"、"先别"、"我还没想好"、"换一个"
- **修改**："改一下..."、"先把主角换成..." → 触发 `revise` 决策，携带用户补充说明

#### 响应结构

```json
{
  "message": "AI 的自然语言回复（只解释，不含任何动作编码）...",
  "pending_action": {
    "id": "act_xxx",
    "type": "preview_setup",
    "description": "AI 解释为什么要做这个操作",
    "params": { "project_id": "xxx", "scope": "character" },
    "requires_confirmation": true
  },
  "project_diagnosis": {
    "missing_items": ["storyline"],
    "completed_items": ["setup"],
    "suggested_next_step": "preview_storyline"
  }
}
```

#### 安全机制

1. **参数白名单**：后端只接受预定义的 `type`（如 `preview_setup`、`generate_setup`、`preview_storyline`、`preview_outline`），非法 type 直接拒绝
2. **统一执行入口**：任何 action 的确认、取消、修改都**必须通过** `POST /api/v1/dialog/resolve-action` 提交。不存在后端因解析到用户文本"同意"就直接执行的逻辑
3. **沙箱执行**：action 处理函数只读写项目数据库，禁止直接操作文件系统或发起非 AI 服务的外部网络请求

### 1.3 前端确认卡片

用户在对话气泡下方看到可交互卡片：
- **操作说明**：AI 的自然语言解释
- **预览内容**（如有）：设定卡片/故事线摘要/大纲摘要
- **操作按钮**：`同意执行` / `取消` / `修改后再执行`

**用户点击卡片按钮**或**在自由文本中回复确认意向**时，前端最终都统一发送：
```json
POST /api/v1/dialog/resolve-action
{
  "action_id": "act_xxx",
  "decision": "confirm" | "cancel" | "revise",
  "comment": "用户补充说明"
}
```

> **执行映射规则**：`resolve-action` 接收到的 `pending_action.type` 若为 `preview_*`，则内部映射为对应的 `generate_*` 实际执行。映射表如下：

| pending_action.type | 实际执行 |
|---------------------|----------|
| `preview_setup` | `generate_setup` |
| `preview_storyline` | `generate_storyline` |
| `preview_outline` | `generate_outline` |

`ACTION_RESULT` 中的 `type` 字段统一记录实际执行类型（如 `generate_setup`）。

### 1.4 意图识别规则表

Intent Router 仅处理以下两类输入：

**A. 动作请求（生成 pending_action）**

| 候选动作 | 触发条件 | 状态约束 |
|----------|----------|----------|
| `preview_setup` | 关键词命中 `创建(主角\|人物\|设定\|世界观)` 等，或按钮/斜杠命令触发 | 项目处于 `setup` 阶段 |
| `preview_storyline` | 关键词命中 `创建(主枝干\|故事线)` 等，或按钮/斜杠命令触发 | `setup` 已完成 |
| `preview_outline` | 关键词命中 `写第.*章大纲`、`生成章节大纲` 等，或按钮/斜杠命令触发 | `storyline` 已存在 |
| `query_diagnosis` | `还有什么要设定的吗`、`接下来做什么`、`然后呢` | 无 |

**B. 继承确认（解析已有 pending_action）**

| 决策 | 关键词示例 | 生效条件 |
|------|------------|----------|
| `confirm` | `同意`、`可以`、`好的`、`行`、`OK`、`没问题`、`搞吧`、`那就这样吧` | **必须存在未决 pending_action** |
| `cancel` | `算了`、`先不要`、`等等`、`不对`、`先别`、`我还没想好`、`换一个` | **必须存在未决 pending_action** |
| `revise` | `改一下...`、`先把主角换成...` | **必须存在未决 pending_action** |

**兜底策略**：
- 自由文本若未命中动作请求规则，**不拼接 `pending_action`**，直接交由 LLM 自由回复或追问。
- 若用户意图模糊但状态明确（如缺少设定时问"然后呢"），由 LLM 基于 `project_diagnosis` 引导，而不是强制生成 action。

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
| source | String | `l1_rule` / `l2_llm` |
| confidence | Float | 置信度 |
| data | JSON | {subject, attribute, old_value, new_value} |
| evidence | JSON | {text, position, summary} |
| created_at | DateTime | 创建时间 |

### 3.6 dialogs（新增）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(PK) | UUID |
| project_id | String(FK) | 关联项目 |
| state | String | `idle` / `chatting` / `pending_action` / `generating` / `revision` / `paused` / `error`（DB 层统一小写；API/UI 层使用大写，序列化时互相转换） |
| pending_action_id | String | 当前未决 action ID（可为空） |
| current_view | String | 用户当前工作区视图，如 `setup` / `outline` / `content` |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### 3.7 dialog_messages（新增）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(PK) | UUID |
| dialog_id | String(FK) | 关联对话 |
| role | String | `user` / `ai` / `system` |
| content | Text | 消息内容 |
| action_result | JSON | 若为 system 的 ACTION_RESULT，结构化存储 |
| created_at | DateTime | 创建时间 |

### 3.8 pending_actions（新增）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(PK) | UUID |
| dialog_id | String(FK) | 关联对话 |
| type | String | 动作类型（白名单内） |
| params | JSON | 动作参数 |
| status | String | `pending` / `confirmed` / `cancelled` / `revised` |
| decision_comment | Text | 用户决策时的补充说明 |
| created_at | DateTime | 创建时间 |
| resolved_at | DateTime | 决策时间 |

### 3.9 background_tasks（新增）

统一后台任务表，替代各 Phase 分散的队列实现。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(PK) | UUID |
| project_id | String(FK) | 关联项目 |
| task_type | String | `consistency_check` / `topology_build` / `outline_generate` 等 |
| payload | JSON | 任务参数 |
| status | String | `pending` / `running` / `completed` / `failed` |
| result | JSON | 任务结果（可选） |
| error | Text | 失败信息 |
| created_at | DateTime | 创建时间 |
| started_at | DateTime | 开始执行时间 |
| finished_at | DateTime | 完成时间 |

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

**POST /consistency-check 同步响应**（`depth=l1` 时）：
```json
{
  "issues": [
    {
      "severity": "fatal",
      "subject": "李明",
      "description": "已死亡角色在本章再次出现",
      "suggested_fix": "确认角色状态或修改出场安排"
    }
  ]
}
```

**GET /consistency-issues 响应**：
```json
{
  "issues": [
    {
      "id": "issue_xxx",
      "chapter_index": 5,
      "checker_name": "CharacterStateChecker",
      "severity": "fatal",
      "subject": "李明",
      "description": "已死亡角色在本章再次出现",
      "evidence": "李明冷冷地看着对方。",
      "suggested_fix": "确认角色状态或修改出场安排",
      "status": "pending"
    }
  ]
}
```

### 4.5 对话/Action API

```
POST /api/v1/dialog/chat
POST /api/v1/dialog/resolve-action
GET  /api/v1/projects/{project_id}/state-diagnosis
```

`state-diagnosis` 返回 `ProjectDiagnosis`（缺失项、已完成项、下一步建议），供 AI 引导和 Intent Router 使用。

---

## 5. 基础设施继承

Phase 2 沿用并扩展 Phase 1 已建立的基础设施：

- **Event Bus**：用于触发一致性检查、拓扑更新等异步事件
- **CacheManager**：缓存拓扑图和频繁访问的章节内容
- **ErrorHandler / with_retry**：统一处理 AI 服务超时和异常
- **TokenBudgetManager / ContextCompressor**：扩展新增 `storyline`、`outline` 预算项

Phase 2 新增**统一后台任务队列**（基于 `asyncio` + `background_tasks` 表），用于异步执行一致性检查、拓扑构建等任务，避免阻塞主线程。

```python
class TaskQueue:
    def __init__(self, max_workers: int = 2):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.max_workers = max_workers
        self.workers = [asyncio.create_task(self._worker_loop()) for _ in range(max_workers)]

    async def enqueue(self, task_type: str, payload: dict) -> str:
        # 写入 background_tasks 表，并放入内存队列
        ...

    async def _worker_loop(self):
        while True:
            task = await self.queue.get()
            try:
                await task()
            except Exception as e:
                logger.error("Background task failed", error=str(e))
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

---

## 附录 A：统一数据契约（跨 Phase 使用）

以下结构在 Phase 2-4 中复用，避免各文档定义不一致。

### A.1 PendingAction

```json
{
  "id": "act_xxx",
  "type": "preview_setup",
  "description": "AI 解释为什么要做这个操作",
  "params": { "project_id": "xxx", "scope": "character" },
  "requires_confirmation": true
}
```

`type` 白名单：`preview_setup`、`preview_storyline`、`preview_outline`、`generate_setup`、`generate_storyline`、`generate_outline`、`revise_setup`、`revise_storyline`、`revise_outline`、`revise_chapter`、`query_diagnosis`。

### A.2 ProjectDiagnosis

```json
{
  "missing_items": ["storyline"],
  "completed_items": ["setup"],
  "suggested_next_step": "preview_storyline"
}
```

> **item 命名空间约定**：`missing_items` 与 `completed_items` 使用标准节点类型键：`setup` / `storyline` / `outline` / `chapters`。

### A.3 DomainEvent

```python
class DomainEvent:
    type: str
    payload: dict
```

核心事件类型枚举：
- `CHAPTER_GENERATED`
- `PREFERENCE_CHANGED`
- `BACKGROUND_TASK_STARTED`
- `BACKGROUND_TASK_COMPLETED`
- `CONSISTENCY_DEEP_CHECK_COMPLETED`

### A.4 ActionResult

`resolve-action` 执行成功后注入对话上下文的结构化格式：

```json
{
  "type": "generate_setup",
  "decision": "confirm",
  "result": "success",
  "setup_id": "xxx"
}
```

对话中的 system 消息文本表示为：`[ACTION_RESULT] type=generate_setup, decision=confirm, result=success, setup_id=xxx`。

---

## 附录 B：核心 JSON 领域结构定义

### B.1 ChapterOutline

```json
{
  "chapter_index": 1,
  "title": "第一章 初入末世",
  "summary": "主角在废墟中醒来，发现城市已沦陷...",
  "scenes": ["废墟醒来", "遭遇第一只变异体", "逃入地铁站"],
  "characters": ["李明", "王阿姨"],
  "purpose": "引入世界观，建立主角初始状态"
}
```

### B.2 Plotline

```json
{
  "name": "主线：生存逃亡",
  "type": "main",
  "milestones": [
    { "chapter_index": 1, "event": "主角醒来" },
    { "chapter_index": 5, "event": "找到避难所" }
  ]
}
```

`type` 枚举：`main` / `sub` / `romance`。

### B.3 Foreshadowing

```json
{
  "hint": "实验室泄露的病毒样本编号",
  "planted_chapter": 2,
  "resolved_chapter": 15,
  "status": "planted"
}
```

`status` 枚举：`planted` / `resolved` / `abandoned`。

### B.4 TopologyNode

```json
{
  "id": "node_xxx",
  "type": "CHARACTER",
  "label": "李明",
  "meta": { "appearance_count": 12, "last_chapter": 8 }
}
```

`type` 枚举：`CHARACTER` / `LOCATION` / `EVENT` / `ITEM`。

### B.5 TopologyEdge

```json
{
  "id": "edge_xxx",
  "source": "node_char_001",
  "target": "node_char_002",
  "type": "relationship",
  "meta": { "relation_subtype": "friendship", "strength": 3 }
}
```

`type` 枚举：`relationship` / `appearance` / `causality` / `possession`。

### B.6 ExtractedFact

```json
{
  "type": "character_state_change",
  "subject": "李明",
  "attribute": "身体状况",
  "old_value": null,
  "new_value": "左腿骨折",
  "confidence": 0.95,
  "evidence": "李明一瘸一拐地走出废墟，左腿传来的剧痛让他冷汗直冒。"
}
```

`type` 枚举：`character_state_change` / `location_presence` / `time_reference` / `relationship_change`。

### B.7 ConsistencyIssue

```json
{
  "id": "issue_xxx",
  "chapter_index": 5,
  "checker_name": "CharacterStateChecker",
  "severity": "fatal",
  "subject": "李明",
  "description": "已死亡角色在本章再次出现",
  "evidence": "李明冷冷地看着对方。",
  "suggested_fix": "确认角色状态或修改出场安排",
  "status": "pending"
}
```

`severity` 枚举：`fatal` / `warn` / `info`。
`status` 枚举：`pending` / `acknowledged` / `resolved`。
