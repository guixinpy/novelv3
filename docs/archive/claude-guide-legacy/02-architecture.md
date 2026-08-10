# 02 · 目标架构

## 总览

```
┌─────────────────────────────────────────────────────────┐
│ frontend/ (Vue3+TS, 保留并瘦身)                          │
│   对话面板 + Agent 运行轨迹可视化 + 少量直接编辑界面       │
└──────────────┬──────────────────────────────────────────┘
               │ REST + SSE（流式）
┌──────────────┴──────────────────────────────────────────┐
│ backend/app/                                             │
│                                                          │
│  api/          薄 API 层：会话/运行/审批 + 少量 CRUD      │
│                                                          │
│  agent/        ★ 新内核（全新编写，小而精）                │
│   ├ loop.py        无状态回合引擎：组装→调用→执行→观察     │
│   ├ harness.py     有状态外壳：会话、队列、钩子、持久化     │
│   ├ providers/     Provider 抽象（原生 tool-call + 流式）  │
│   ├ context.py     上下文组装：三层提示词 + 多通道注入      │
│   ├ compaction.py  上下文压缩（头尾保护 + 摘要）           │
│   ├ budget.py      迭代/令牌预算（含 refund 机制）         │
│   ├ guards.py      循环风险检测（移植五级检测器）           │
│   └ approval.py    审批门（beforeToolCall 钩子实现）       │
│                                                          │
│  tools/        ★ 工具目录（自注册，每文件一组工具）         │
│   ├ registry.py    注册表 + JSON Schema 校验              │
│   ├ chapters.py    章节读/写/修订                          │
│   ├ world.py       世界观查询/提案（提案-审批门保留）        │
│   ├ memory.py      记忆树读写/检索                         │
│   ├ retrieval.py   语义检索                                │
│   ├ consistency.py 一致性检查                              │
│   └ project.py     设定/大纲/项目状态                      │
│                                                          │
│  domain/       保留的领域服务（工具背后的实现）              │
│   ├ world/         世界观模型 + checker registry（保留）    │
│   ├ memory/        记忆树存储 + 激活 + 摘要（整合为一个服务） │
│   ├ retrieval/     athena_retrieval（保留）                │
│   └ manuscript/    章节/版本/导出                           │
│                                                          │
│  models/       ORM（基本原样保留，35 表）                   │
│  db.py / config.py                                        │
└──────────────────────────────────────────────────────────┘
```

## 核心设计决策

### 1. 控制反转：模型驱动循环

新内核的回合流程（参考 hermes-agent `conversation_loop` + openclaw `agentLoop`）：

```
组装消息（系统提示三层 + 历史 + 记忆注入）
  → LLM 流式调用（原生 tools 参数）
  → 若有 tool_calls：校验 → 审批门 → 执行（可并行）→ 结果回填为 observation
  → 循环，直到模型自然结束 / 预算耗尽 / 风险熔断 / 用户打断
  → 回合落盘（JSONL 会话日志 + DB 运行记录）
```

- **loop 与 harness 分离**（openclaw 模式）：`loop.py` 是无状态纯函数，事件经 sink 发出，可独立测试；`harness.py` 持有会话状态、steering/follow-up 队列、生命周期钩子。
- **钩子而非配置表**：`before_tool_call`（审批/拦截）、`after_tool_call`（结果修补）、`prepare_next_turn`（模型/上下文调整）。旧的 lifecycle_hooks 概念以此形式重生。

### 2. Provider 抽象

参考 hermes-agent `ProviderTransport`：子类只做格式转换（messages/tools/response 归一化），重试与流式逻辑只写一遍。首发支持 DeepSeek（OpenAI 兼容格式，原生 function calling + 流式），预留 Anthropic。**不做 11 个 provider 的适配迷宫。**

### 3. 三层系统提示（hermes-agent 模式）

- **稳定层**：Agent 身份、写作纪律、工具使用指引——字节级稳定，吃 prefix cache。
- **上下文层**：项目设定摘要、文风约束、当前卷/章定位。
- **易变层**：记忆快照、质量趋势、时间戳——每回合重建。

### 4. 工具系统：一层取代三层

旧版 descriptor/adapter/execution 三层 + 注册表 ≈ 每工具 200+ 行模板代码。新版（hermes-agent 自注册模式 + 显式审计折中）：

```python
# tools/chapters.py
@tool(
    name="read_chapter",
    description="读取指定章节正文与元数据",
    schema=READ_CHAPTER_SCHEMA,
    permission="read",          # read | propose | write
)
async def read_chapter(ctx: ToolContext, chapter_index: int) -> ToolResult: ...
```

- 权限三级：`read` 直接执行；`propose` 产生提案待审批；`write` 经审批门（继承旧 ADR-002 提案-审批模式）。
- 工具结果必须是结构化、模型可理解的：错误信息写给模型看（它要据此调整），不是写给人看。
- 旧版 27 个只读诊断工具中,有真实价值的并入对应工具文件，其余删除。

### 5. 记忆系统：整合五条码路为一个服务

旧版 5 个半独立记忆模块（longform_memory / memory_tree / summary_execution / activation / capture）整合为 `domain/memory/` 单一服务，对外只暴露：

- `append(chapter)` —— 章节完成后归档：确定性 chunk ID（openhuman 模式，幂等重入）→ 入树
- `cascade()` —— 层级摘要级联：章 → 卷 → 全书梗概（openhuman bucket_seal 模式），桶满即封
- `recall(query, lanes)` —— 多通道召回（openhuman 四通道适配）：
  - 语义检索（现有 athena_retrieval）
  - 实体通道（出场人物/地点的当前状态）
  - 情节线通道（活跃伏笔、未闭环线索）
  - 工作记忆（最近 N 章摘要）
- 实体索引：每个 chunk 标注提及的实体，同 chunk 共现即图边，支持「林思和灯塔同时出现的所有场景」类查询。

### 6. 会话与运行持久化

- 会话 = JSONL 追加日志（openclaw 模式）：消息、压缩记录、自定义条目（章节完成、字数、质量评分），支持断点恢复。
- 复用现有 `WritingAgentRun` / `WritingAgentStep` / `AIModelCallTrace` 表作 DB 侧运行记录——前端轨迹可视化建立在其上，不可丢。

### 7. 护栏：在新循环内重建旧资产

| 旧资产 | 新位置 | 说明 |
| --- | --- | --- |
| 五级循环风险检测（ping_pong 等） | `agent/guards.py` | 直接移植算法，挂在 after_tool_call |
| 迭代预算 + refund | `agent/budget.py` | hermes 模式：程序性工具调用退还预算 |
| 提案-审批门 | `agent/approval.py` + `propose` 权限 | 世界观写入必须过提案 |
| 上下文预算预检 + 压缩 | `agent/compaction.py` | 头尾保护 + 中段摘要，75% 触发 |
| 溯源契约 | 工具结果统一字段 | version/sources/trace 收敛为一处定义 |

## 保留 / 重建 / 删除清单

### ✅ 原样保留（只动 import）
- `models/`（35 表 ORM）+ Alembic 迁移
- `core/world_checker_registry.py`（产品级校验管线）
- `core/athena_retrieval.py`（检索/嵌入管线）
- `core/world_proposal_service.py`（提案生命周期）
- 前端三工作区骨架、AgentRunDrawer 轨迹可视化、Pinia stores

### 🔄 重建（逻辑保留、形态重写）
- 记忆五模块 → `domain/memory/` 单服务
- 循环风险/预算/审批/压缩 → 新内核护栏模块
- 6 条生成管线 → 删除管线本身，能力变成「模型 + 章节/大纲/设定工具」
- 对话 API（dialogs.py 1912 行）→ 薄会话 API + SSE 流

### ❌ 删除（不迁移）
- `core/intent_router.py`（2400 行规则意图路由——模型的工作）
- `services/writing_agent/planner.py` + 脚本化 plan/step 编排
- `run_service.py`（2015 行上帝模块——被 loop+harness 取代）
- 全部 descriptor/adapter 三层模板（~15 文件）
- slash command 路由、dialog_intent_planner、route_opt_in 机制
- 仅为以上机器兜底的测试（预计删除测试代码的 50%+）

## API 演进

- 新增 `/api/v2/sessions`（创建会话、发消息、SSE 流、审批决议、打断/steering）。
- 保留 v1 中作者直接编辑所需的 CRUD（章节、设定、导出、偏好）。
- v1 中被 Agent 取代的编排类端点（~60 个）随旧编排层删除；前端同步迁移到 v2 会话流。
