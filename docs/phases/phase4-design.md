# Phase 4 设计文档：反馈学习 + 增强一致性 + 后台分析器

> **版本**: v3.0 Phase 4  
> **日期**: 2026-04-15  
> **目标**: 构建自优化能力，引入增强版一致性引擎和统一后台分析器

---

## 1. 核心设计：轻量后台分析器

Phase 4 不引入多个独立 Agent 微服务，而是用一个统一的 **BackgroundAnalyzer** 处理所有后台分析任务，避免过度设计和 API 成本爆炸。

### 1.1 架构调整

| 组件 | 职责 | 输出物 |
|-------|------|--------|
| **主对话模块** | 对话交互、流程导演、向用户提案操作 | 自然语言回复 + Action Proposal |
| **BackgroundAnalyzer** | 统一处理一致性检查、拓扑更新、Prompt 优化建议 | ConsistencyIssue[] / Topology 增量 / Prompt 规则建议 |

### 1.2 协作模式

```
主对话模块生成章节内容
    ↓
写入 chapter_contents
    ↓
Event Bus 触发事件
    └──▶ BackgroundAnalyzer（异步，单队列）
            按需执行：
            - L2 事实提取（可选/按需触发）
            - L1/L2 交叉验证
            - 拓扑图增量更新
            - 用户偏好规则更新（基于显式配置）
            输出写入 consistency_checks / topologies / prompt_rules

分析结果通过 Event Bus 回传
    ↓
主对话模块在后续对话中引用结果
    "第 5 章检测到一处地点矛盾：主角同时在 A 城和 B 城出现，已标记。"
```

### 1.3 后台分析器接口

```python
class BackgroundAnalyzer:
    async def process(self, event: DomainEvent) -> AnalyzerResult:
        if event.type == "CHAPTER_GENERATED":
            await self.run_consistency_check(event.payload)
            await self.update_topology(event.payload)
        elif event.type == "PREFERENCE_CHANGED":
            await self.update_prompt_rules(event.payload)
        ...
```

> **TaskQueue 复用说明**：Phase 4 直接复用 Phase 2 定义的 `TaskQueue`（基于 `asyncio` + `background_tasks` 表），不再引入新的队列实现。

---

## 2. 显式偏好配置

由于本地个人使用场景下反馈数据稀疏，**不引入自动偏好学习器**。改为在项目设置页提供显式偏好配置，用户直接调整，系统即时生效。

### 2.1 配置项

| 配置项 | 类型 | 说明 |
|--------|------|------|
| 描写密度 | 滑块 1-5 | 1=极简，5=极繁 |
| 对话比例 | 滑块 1-5 | 1=叙述为主，5=对话为主 |
| 节奏快慢 | 滑块 1-5 | 1=慢热铺垫，5=快节奏推进 |
| 基调偏好 | 多选 | 枚举值：`dark` / `realistic` / `light` / `suspense`（中文界面做 i18n 映射展示） |

### 2.2 快捷反馈入口

在章节生成结果页面增加一键反馈按钮（如"对话太多"、"节奏太慢"、"描写太少"），点击后执行以下两步：
1. 自动调用 `PUT /api/v1/projects/{project_id}/preferences` 将对应滑块调整一档
2. 自动调用 `POST /api/v1/projects/{project_id}/writing/chapters/{chapter_index}/retry` 重新生成当前章

```python
QUICK_FEEDBACK_MAP = {
    "对话太多": {"dialogue_ratio": -1},
    "节奏太慢": {"pacing_speed": +1},
    "描写太少": {"description_density": +1},
    "描写太繁": {"description_density": -1},
}
```

### 2.3 配置存储

```python
class PreferenceConfig:
    async def save(self, project_id: str, config: dict) -> None:
        record = await self.storage.save(project_id, config)
        await self.event_bus.emit("PREFERENCE_CHANGED", {"project_id": project_id, "config": config})
```

### 2.4 偏好画像结构

存储、API 和 Prompt 注入均使用同一套扁平键：

```json
{
  "description_density": 3,
  "dialogue_ratio": 2,
  "pacing_speed": 4,
  "tone_preferences": ["dark", "realistic"]
}
```

---

## 3. Prompt 优化器

### 3.1 动态 Prompt 注入

用户显式配置的偏好由 `PreferenceConfig` 保存，BackgroundAnalyzer 将其转换为 prompt 规则写入 `prompt_rules` 表，PromptManager 在生成前读取并注入。

```python
class PromptOptimizer:
    def optimize(self, base_prompt: str, config: dict) -> str:
        rules = self.build_rules(config)
        if rules:
            base_prompt += "\n\n【用户偏好规则】\n" + "\n".join(rules)
        return base_prompt
```

### 3.2 规则映射示例

| 配置值 | 生成的规则 |
|--------|-----------|
| `description_density >= 4` | 增加环境描写和感官细节 |
| `dialogue_ratio <= 2` | 减少对话比例，增加叙述和心理描写 |
| `pacing_speed >= 4` | 加快节奏，减少铺垫 |
| `tone_preferences` 含 `dark` | 保持压抑、沉重的叙事基调 |

### 3.3 Few-shot 示例库

初期按类型硬编码少量精选示例，不引入向量检索：

```python
class FewShotExampleLibrary:
    HARDCODED_EXAMPLES = {
        "xianxia": { "setup": [...], "outline": [...], "chapter": [...] },
        "apocalypse": { "setup": [...], "outline": [...], "chapter": [...] },
        "romance": { "setup": [...], "outline": [...], "chapter": [...] },
    }

    async def select_examples(
        self,
        task_type: str,
        genre: str,
        limit: int = 2
    ) -> list[Example]:
        # Phase 4: 优先从 HARDCODED_EXAMPLES 返回
        # Phase 5: 优先从 DB 查询用户自定义示例，DB 无结果时 fallback 到硬编码
        db_examples = await self._fetch_from_db(genre, task_type, limit)
        if db_examples:
            return db_examples
        return self.HARDCODED_EXAMPLES.get(genre, {}).get(task_type, [])[:limit]
```

示例在 Prompt 中注入：
```
【参考示例】
示例 1:
输入: ...
输出: ...
```

---

## 4. L2 LLM 提取器 + L1/L2 交叉验证

### 4.1 L2 LLM 提取器

用 LLM 从章节内容中深度提取事实，输出结构化 JSON：

```python
class L2LLMExtractor:
    async def extract(self, chapter_content: str) -> list[ExtractedFact]:
        prompt = self.build_extraction_prompt(chapter_content)
        response = await self.ai_service.complete(prompt, max_tokens=4000)
        return self.parse_facts(response)
```

Prompt 要求 LLM 输出：
```json
[
  {
    "type": "character_state_change",
    "subject": "李明",
    "attribute": "身体状况",
    "new_value": "左腿骨折",
    "evidence": "李明一瘸一拐地走出废墟，左腿传来的剧痛让他冷汗直冒。",
    "confidence": 0.95
  }
]
```

### 4.2 L1/L2 交叉验证器

```python
class CrossValidator:
    def validate(
        self,
        l1_facts: list[ExtractedFact],
        l2_facts: list[ExtractedFact]
    ) -> CrossValidationResult:
        confirmed = []
        conflicts = []
        pending = []

        for l2 in l2_facts:
            matched_l1 = self.find_match(l2, l1_facts)
            if matched_l1 and self.is_consistent(l2, matched_l1):
                l2.validation = {
                    "l1_extracted": True,
                    "l2_extracted": True,
                    "cross_confidence": max(l2.confidence, matched_l1.confidence)
                }
                confirmed.append(l2)
            elif matched_l1 and not self.is_consistent(l2, matched_l1):
                conflicts.append(FactConflict(fact_a=matched_l1, fact_b=l2, ...))
            else:
                l2.validation = {"cross_confidence": l2.confidence * 0.7}
                pending.append(l2)

        return CrossValidationResult(confirmed, conflicts, pending)
```

### 4.3 异步执行策略

- 章节生成**立即返回**，不阻塞用户
- L2 提取改为**可选/按需**：用户可手动触发"深度检查"，或只对最新生成的章节执行
- BackgroundAnalyzer 在后台异步执行交叉验证（耗时 5-30 秒）
- 结果写入 `consistency_checks` 和 `extracted_facts`
- 主对话模块在下一轮对话或工作区刷新时读取并展示结果

---

## 5. 3 类核心检查器

BackgroundAnalyzer 优先实现 3 类核心检查器，`RelationshipChecker` 作为第 4 优先候补，其余 3 类明确推迟：

| 检查器 | 职责 | 依赖 | 优先级 |
|--------|------|------|--------|
| `CharacterStateChecker` | 角色状态冲突（生死、伤势、能力变化） | L1 + L2 事实 | P0 |
| `LocationChecker` | 地点逻辑异常（同时出现在两地、未交代移动） | L1 + L2 事实 | P0 |
| `TimelineChecker` | 时间线矛盾（时间倒流、年龄异常） | L1 + L2 事实 | P0 |
| `RelationshipChecker` | 人物关系突变（未交代铺垫的关系转变） | L1 + L2 事实 | P1 |

**推迟的检查器**：`ForeshadowingChecker`、`ItemPossessionChecker`、`ToneConsistencyChecker`。

> `CharacterStateChecker` 先覆盖"人物关系变更"子类作为过渡；若资源允许，P1 阶段将 `RelationshipChecker` 独立实现。

### 5.1 检查结果分级

| 级别 | 说明 | 处理方式 |
|------|------|----------|
| `fatal` | 严重矛盾，影响阅读 | AI 主动提示用户，建议修正 |
| `warn` | 可疑之处，需关注 | 在工作区标记，用户可选处理 |
| `info` | 提醒或建议 | 折叠显示，不打扰用户 |

---

## 6. 数据模型扩展

### 6.1 `projects` 表扩展

在 `projects` 表中直接增加 `style_config` JSON 字段，存储用户显式偏好（个人本地场景数据量可控，单表查询更简单）：

| 字段 | 类型 | 说明 |
|------|------|------|
| style_config | JSON | 用户显式偏好配置（扁平键结构） |
| updated_at | DateTime | 更新时间 |

### 6.2 few_shot_examples（新增）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(PK) | UUID |
| task_type | String | `setup` / `outline` / `chapter` |
| genre | String | 适用类型 |
| tags | JSON | 风格标签 |
| input | Text | 示例输入 |
| output | Text | 示例输出 |
| rating | Float | 质量评分 |

### 6.3 prompt_rules（新增）

PromptOptimizer 生成的动态规则表。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(PK) | UUID |
| project_id | String(FK) | 关联项目 |
| rule_type | String | `style` / `plot` / `tone` / `format` |
| condition | String | 触发条件 |
| action | String | 规则内容 |
| priority | Integer | 优先级 |
| hit_count | Integer | 命中次数 |
| created_at | DateTime | 创建时间 |

---

## 7. API 扩展

### 7.1 偏好配置 API

```
GET  /api/v1/projects/{project_id}/preferences
PUT  /api/v1/projects/{project_id}/preferences
POST /api/v1/projects/{project_id}/preferences/reset
```

**PUT 语义**：全量覆盖。前端需先 GET 当前配置，在本地修改完整对象后再 PUT。

**PUT 请求体示例**：
```json
{
  "description_density": 4,
  "dialogue_ratio": 2,
  "pacing_speed": 3,
  "tone_preferences": ["dark", "suspense"]
}
```

**GET 响应示例**：
```json
{
  "config": {
    "description_density": 4,
    "dialogue_ratio": 2,
    "pacing_speed": 3,
    "tone_preferences": ["dark", "suspense"]
  },
  "updated_at": "2026-04-16T10:00:00Z"
}
```

### 7.2 后台任务状态 API（调试/监控用）

```
GET /api/v1/projects/{project_id}/background-tasks
GET /api/v1/background-tasks/{task_id}
```

返回 BackgroundAnalyzer 任务的执行状态和结果摘要。

### 7.3 深度一致性检查 API

复用 Phase 2 的一致性检查接口，增加 `depth` 参数以支持 L2 深度分析：

```
POST /api/v1/projects/{project_id}/chapters/{chapter_index}/consistency-check
{
  "depth": "l1" | "l2"
}
```

- `depth=l1`（默认）：仅运行 L1 规则提取器和基础检查器
- `depth=l2`：额外触发 LLM 深度事实提取和 L1/L2 交叉验证，异步执行，结果通过 `background_tasks` 和 `consistency_checks` 回写

用户在工作区点击"深度检查"时，前端自动发送 `depth=l2` 请求。

---

## 8. 性能监控与可观测性

Phase 4 仅扩展 BackgroundAnalyzer 的任务监控和日志追踪，不引入复杂的性能监控体系。

```python
class BackgroundTaskTracker:
    def __init__(self):
        self.tasks: dict[str, dict] = {}

    def start_task(self, task_id: str, task_type: str, payload: dict) -> None:
        self.tasks[task_id] = {
            "type": task_type,
            "status": "running",
            "started_at": time.time(),
            "payload": payload,
        }
        logger.info("Background task started", task_type=task_type, task_id=task_id)

    def finish_task(self, task_id: str, result: any) -> None:
        task = self.tasks.get(task_id)
        if task:
            task["status"] = "completed"
            task["duration_ms"] = (time.time() - task["started_at"]) * 1000
            logger.info("Background task completed", task_id=task_id, duration_ms=task["duration_ms"])

    def fail_task(self, task_id: str, error: str) -> None:
        task = self.tasks.get(task_id)
        if task:
            task["status"] = "failed"
            task["error"] = error
            logger.error("Background task failed", task_id=task_id, error=error)
```

> **状态源统一规则**：`background_tasks` 表是后台任务状态的唯一权威源。`BackgroundTaskTracker` 仅作为进程内内存缓存，用于快速日志标注和前端小面板展示；服务重启后通过读取数据库表恢复状态，HTTP API 查询也始终优先读表。

监控指标通过结构化日志输出，同时保留 7.2 节的轻量 HTTP API 供前端小面板展示后台任务状态（进行中/已完成/失败），方便用户查看按需触发的 L2 检查是否跑完。

---

## 9. 事件总线扩展

Phase 4 新增核心事件：

```python
| { type: 'PREFERENCE_CHANGED'; payload: { project_id: string; config: dict } }
| { type: 'BACKGROUND_TASK_STARTED'; payload: { task_id: string; task_type: string } }
| { type: 'BACKGROUND_TASK_COMPLETED'; payload: { task_id: string; task_type: string; result: any } }
| { type: 'CONSISTENCY_DEEP_CHECK_COMPLETED'; payload: { chapter_index: int; issues: ConsistencyIssue[] } }
```

---

## 10. 里程碑 M4 验收标准

- [ ] 用户显式偏好配置可影响后续生成
- [ ] Prompt 根据显式偏好动态注入规则
- [ ] L2 提取器和 L1/L2 交叉验证按需异步运行
- [ ] 3 类核心检查器可用，结果分级展示
- [ ] Few-shot 示例库按类型返回硬编码精选示例
- [ ] BackgroundAnalyzer 运行稳定，任务不堆积
- [ ] 3 类核心检查器对**已触发检查的章节**准确率显著提升，fatal 级别冲突召回率 > 80%
- [ ] 用户可手动触发任意章节的深度一致性检查

---

## 11. 风险与应对

| 风险 | 应对 |
|------|------|
| L2 异步分析耗时长/API 成本高 | 改为按需触发，不自动每章都跑，限制并发数 |
| 多 Agent 架构过度设计 | 合并为单一 BackgroundAnalyzer，用单队列消费 |
| 交叉验证误报率高 | 低置信度结果标记为 `info`，只把高置信度冲突标为 `fatal` |
| Few-shot 示例库维护成本高 | 初期用硬编码精选示例，每类型 2-3 个即可 |

### 11.1 API 成本估算

以 100 章、每章 3000 字的小说为例：
- L2 深度检查按需触发 30% 章节 ≈ 30 次 × 4K tokens = 120K tokens
- 3 类检查器跑完全书 ≈ 100 次 × 1.5K tokens = 150K tokens
- **总计约 270K tokens / 本**，按 DeepSeek-V3 价格估算约 **0.5-1 元 / 本**

该成本对个人本地使用可接受。
