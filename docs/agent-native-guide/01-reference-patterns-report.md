# 参考项目模式提取报告

> 产出方式：三个研究 agent 并行深读 openclaw、hermes-agent、openhuman 的架构文档和核心源码，按统一问题框架提取模式，由 Claude 汇总合成。
> 
> 本文档是指导性参考，不是施工图纸。Codex 在实现时应有自己的工程判断。

---

## 零、Codex 审查修正：本文档的使用方式

本文档用于指导后续 goal，但不能直接等同于施工路线。后续执行必须遵守以下修正：

1. **核心目标保持 agent-first**：novelv3 的主目标是升级为面向网文写作的 domain-specific long-memory Agent；真实小说生成是 pressure-test / problem-discovery spine，不是脱离 Agent 化工作的单独交付物。
2. **参考项目只提供模式，不提供优先级**：openclaw、hermes-agent、openhuman 的模式必须先映射到 novelv3 当前缺口，再决定是否实现。不得因为参考项目存在某模式，就默认在 novelv3 中重建同等复杂度。
3. **优先处理真实运行链路的硬失败**：下一阶段优先加固 Agent 运行控制环，包括工具循环风险、恢复建议、审稿/质量趋势投影和轻量 provenance；Memory Tree、配置驱动子 Agent、StopHooks 等较大架构变化必须由真实生成过程暴露的失败来触发。
4. **所有阶段都要可验证**：每个改动必须绑定一个失败用例或可复现诊断输出。不能以“架构更完整”“未来更灵活”作为完成标准。
5. **避免重复上一轮低效模式**：不做空泛优化，不一次性铺开全套架构；采用“真实生成小说 → 审查质量/体验 → 记录问题 → 修复 → 针对性验证 → 继续生成”的闭环。

---

## 一、三个项目的定位对比

| 维度 | openclaw | hermes-agent | openhuman |
|------|----------|-------------|-----------|
| 语言 | TypeScript (pnpm monorepo) | Python (setuptools) | Rust 核心 + React/TypeScript 前端 (Tauri) |
| 定位 | 多通道 AI 网关 + 可扩展消息平台 | 自改进 CLI Agent，Nous Research 出品 | 桌面 AI 助手，带完整 UI |
| Agent 架构 | 嵌入式 Pi Agent + 插件式上下文引擎 | 对话循环 Agent + 插件/技能双轨扩展 | 类型化 Agent trait + 层次化子 Agent |
| 记忆系统 | 根记忆文件 + SQLite(向量+FTS) + QMD | SessionDB(SQLite FTS5) + MemoryProvider 插件 | UnifiedMemory(SQLite) + Memory Tree 分层摘要 |
| 子 Agent | 完备（spawn/registry/announce/orphan recovery） | delegate_task（leaf/orchestrator 分层）+ Kanban | AgentDefinition(TOML) + Chat/Reasoning/Worker 三级 |
| 上下文管理 | 插件式 ContextEngine + compaction | ContextCompressor(预修剪+LLM摘要+头尾保护) | ContextPipeline(TokenJuice+微压缩+自动压缩+断路器) |
| 运行循环 | 双层（外层重试 + 内层模型调用） | 单层 while(iteration_budget) | 单层 while(tool_iterations) + StopHooks |
| 权限模型 | 网关角色+作用域 + ownerOnly 工具策略 | ToolGuardrails(pre_approve/deny/require_confirm) | PermissionLevel(None/ReadOnly/Write/Execute/Dangerous) |
| 恢复机制 | session 挂起+自动恢复 + 子agent 孤儿恢复 | checkpoint resume + jittered backoff + model fallback | turn_state 快照 + transcript 恢复 + 断路器 |
| **网文创作适配度** | **高**（抽象层次清晰，可借鉴模块边界设计） | **最高**（Python 技术栈相同，压缩和批量执行直接相关） | **中高**（架构严谨性可借鉴，但 Rust→Python 翻译成本大） |

---

## 二、按关注点的横向对比与推荐模式

### 2.1 Agent 记忆系统

| 项目 | 分层方式 | 检索机制 | 注入策略 |
|------|---------|---------|---------|
| openclaw | 根记忆文件 → 插件记忆(SQLite+向量+FTS) → QMD 外部 | `MemorySearchManager` + 语义搜索 | `buildMemoryPromptSection()` 注入 system prompt |
| hermes-agent | SessionDB(SQLite FTS5) → MemoryProvider 插件 | FTS5 全文搜索 + 外部 provider 预取 | `<memory-context>` fence 标签注入 + StreamingContextScrubber 防泄露 |
| openhuman | Key-Value → FTS5+向量搜索 → **Memory Tree 分层摘要** | 语义 recall + Tree 导航（顶层概览→深层挖掘） | `memory_context.rs` 在用户消息前注入 |

**对网文创作 Agent 的推荐方向：**

网文创作需要管理四类记忆，可以借鉴上述分层：

- **世界观/设定记忆** → 借鉴 openhuman 的 Memory Tree：将世界观实体（地域、势力、规则）组织为分层摘要，按需展开
- **角色档案记忆** → 借鉴 openclaw 的根记忆 + 向量搜索：角色外貌/性格/动机弧线作为结构化条目，语义检索获取
- **章节/情节记忆** → 借鉴 hermes-agent 的 FTS5 全文搜索：按关键词检索历史章节内容
- **写作风格记忆** → 借鉴 openclaw 的根记忆文件：风格锚定样本作为持久化的"写作圣经"条目

**特别值得关注：** openhuman 的 Memory Tree 模式——文档被分块、打分，汇总到分层树节点中，Agent 可以浏览顶层或深入特定话题。这天然适配"百万字小说"场景：卷→章→节→段落 的层级结构本身就是一棵树，不需要重新发明。

**Memory Tree 与 FTS5 全文搜索的关系：** 两者是互补而非替代。Memory Tree 解决"我不知道要找什么，让我浏览"的场景——Agent 从顶层摘要开始，按需 drill-down 到具体章节。FTS5 全文搜索解决"我知道要找什么，帮我定位"的场景——按关键词精确检索某段对话或某个设定。一个完整的记忆系统需要两者并存：Tree 做分层摘要浏览，FTS5 做精确检索。

**Memory Tree 召回与上下文压缩的冲突（来自审查反馈）：** openhuman 的实际实现中，Memory Tree 的语义召回需要将检索到的记忆注入上下文，但上下文压缩会破坏 KV-cache 前缀。openhuman 通过限制注入量（默认最多 5 条、2000 字符）并在 AgentDefinition 中提供 `omit_memory_context = true` 跳过标记来缓解。这个 tradeoff 在实现 novelv3 的记忆系统时需要显式处理。

---

### 2.2 工具编排

| 项目 | 注册方式 | 发现/过滤 | 调用生命周期 | 循环检测 |
|------|---------|----------|-------------|---------|
| openclaw | `defineToolDescriptor()` | `buildToolPlan()` 按 availability 表达式过滤 | before-tool-call 钩子 + owner-only 门控 | **5 级检测**：generic_repeat / ping-pong / unknown_tool_repeat / known_poll_no_progress / global_circuit_breaker |
| hermes-agent | `registry.register()` 自注册 + AST 扫描发现 | `get_tool_definitions(enabled/disabled_toolsets)` | handle_function_call 调度 | `_invalid_tool_retries` 等计数器（各上限 3 次） |
| openhuman | `Box<dyn Tool>` trait 对象 + 工厂函数 | AgentDefinition 中的工具 scope 筛选 | 权限检查 → timeout 执行 → TokenJuice 压缩 → 结果追加 | `max_tool_iterations` 硬限制 |

**对网文创作 Agent 的推荐方向：**

- **工具注册**：novelv3 当前的双重登记（descriptor + adapter）可以借鉴 hermes-agent 的自注册模式简化——但不需要 AST 扫描，Python 的装饰器或 `__init_subclass__` 更自然
- **循环检测**：openclaw 的五级分类比 novelv3 当前的单一"相邻去重"更细粒度。网文场景特别需要检测 "ping-pong"（反复修改同一段）、"poll_no_progress"（反复检查但不产出）和 "global_circuit_breaker"（全局熔断，30 次调用硬终止）
- **工具权限**：openhuman 的 PermissionLevel 枚举（None→ReadOnly→Write→Execute→Dangerous）比 novelv3 当前的字符串标签更严谨。建议借鉴但简化为 Read/Write/GuardedWrite 三级

---

### 2.3 运行循环

| 项目 | 循环结构 | 迭代控制 | 终止条件 | 特别机制 |
|------|---------|---------|---------|---------|
| openclaw | 双层：外层重试 + 内层模型调用 | bootstrap-budget + context-window-guard | 压缩耗尽 / 空闲超时 / 循环检测触发 | post-compaction-loop-guard 防无限重试 |
| hermes-agent | 单层：`while api_call_count < max_iterations` | IterationBudget 消费/退款 | 无 tool_calls / budget 耗尽 / 用户中断 | refund() 机制（execute_code 调用退还 budget） |
| openhuman | 单层：`while tool_iterations` + StopHooks | max_tool_iterations(默认10) + StopHooks | 无 tool_calls / 迭代耗尽 / ContextGuard 断路器 | **StopHooks 策略层**：预算上限、最大轮次在每次迭代前检查 |

**对网文创作 Agent 的推荐方向：**

novelv3 当前的 `_agent_loop_contract()` 已经做了迭代预算和相邻去重检测，但可以从三个项目中吸收以下增强：

- **从 openclaw 吸收**：ping-pong 和 poll_no_progress 检测（当前只有 adjacent_repeat）
- **从 hermes-agent 吸收**：refund 机制——某些"程序化"工具调用（如批量填充角色信息）不应计入创作迭代预算
- **从 openhuman 吸收**：StopHooks 模式——把终止条件从循环体内抽出来成为独立的策略层，方便以后加新的终止条件而不改循环代码

**关键架构认知（来自 hermes-agent 报告）：** `run_conversation()` 是"单次用户输入→多轮工具调用→返回"。百万字创作需要一个**上层的故事编排循环**，在每个"章节生成"迭代中调用 `run_conversation()`，而不是把整个百万字生成塞进一次调用。novelv3 当前的 planner→run_service 架构已经体现了这种分层，应该保持并强化。

---

### 2.4 子 Agent / Worker

| 项目 | 层级模型 | 调度方式 | 上下文传递 | 限制机制 |
|------|---------|---------|----------|---------|
| openclaw | 无显式层级（平等 spawn） | sessions_spawn + subagent-registry | isolated(独立) 或 fork(复制父上下文) | max_spawn_depth + max_children_per_agent |
| hermes-agent | leaf(不能再委托) / orchestrator(可递归) | delegate_task 工具 + Kanban 看板 | 独立上下文 + 受限工具集 | max_concurrent_children(默认3) |
| openhuman | **Chat → Reasoning → Worker 三级** | spawn_subagent + spawn_parallel_agents | fork_context 共享父上下文 | **max 3 跳深度** + Worker 不能再派遣 |

**对网文创作 Agent 的推荐方向：**

网文创作天然适合子 Agent 模式，但场景与通用 Agent 不同：

- **适合子 Agent 的场景**：角色对话生成、设定一致性检查、风格审稿、伏笔追踪——这些是"可独立完成然后向主编汇报"的任务
- **不适合子 Agent 的场景**：主线情节推进——这是单一叙事流，需要主编的连贯判断

推荐借鉴 openhuman 的 **AgentDefinition(TOML)** 模式：把子 Agent 定义为配置文件而非硬编码，这样新增一个"角色对话审查 Agent"或"设定一致性 Agent"不需要改代码。

openclaw 的子 Agent 孤儿恢复机制（网关重启后扫描中断 session 并发合成恢复消息）对长时间运行的批量章节生成有价值。

---

### 2.5 上下文管理

这是对网文创作 **最关键** 的维度。

| 项目 | 压缩策略 | 触发条件 | 保护机制 |
|------|---------|---------|---------|
| openclaw | LLM 摘要合并（`MERGE_SUMMARIES_INSTRUCTIONS`） | 上下文接近 token 预算限制 | 保留活跃任务状态、最后用户请求、决策理由 |
| hermes-agent | **三层**：工具输出预修剪 → 去重 → LLM 摘要（头尾保护） | context_length 的 50% 阈值 | protect_first_n(默认3) + protect_last_n(默认4) + 反抖动(10%阈值) |
| openhuman | **四层**：TokenJuice 压缩 → 微压缩(替换旧工具结果) → 自动压缩(LLM 摘要) → ContextGuard 断路器 | ContextGuard 逐次检查 | 保留最近 N 个结果 + 断路器(3 次连续失败后跳闸) |

**对网文创作 Agent 的推荐方向（最重要）：**

这个维度直接决定"百万字小说能否不崩"。三个项目各有关键贡献：

- **从 hermes-agent 吸收**：分层压缩策略。预修剪（去重、摘要旧工具结果）不消耗 LLM 调用，这对减少成本和提高速度很关键。保护头尾的机制天然适配"保留当前章节上下文 + 保留全局设定"的需求
- **从 openhuman 吸收**：微压缩（清理旧工具结果信封但保持 API 协议完整）和 ContextGuard 断路器（3 次失败后硬终止，避免无限压缩循环）
- **从 openclaw 吸收**：压缩摘要中明确要求保留"活跃任务状态"和"决策理由"——对网文场景，这对应"未收伏笔"和"当前情节线的走向决策"

**网文场景特有的上下文管理需求：**
- "当前章节"窗口（~30K tokens）必须保持完整
- 早期章节应被压缩为"情节摘要 + 关键对话摘录 + 新引入设定清单"
- 角色出场频率变化时，相关角色档案的注入优先级应动态调整
- 伏笔的"埋→提醒→收"状态应显式追踪，不在压缩中丢失

---

### 2.6 恢复机制

| 项目 | 故障检测 | 恢复策略 | 特别设计 |
|------|---------|---------|---------|
| openclaw | 配额耗尽 / 手动冻结 / 断路器打开 | session 挂起+自动恢复(TTL 30min) + 认证 profile 轮换 | 子 agent 孤儿恢复（扫描 abortedLastRun 并发送合成恢复消息） |
| hermes-agent | API error 分类（可重试/不可重试） | jittered backoff + model fallback + checkpoint resume(batch) | SessionDB 的 BEGIN IMMEDIATE + jitter retry(15次,20-150ms) |
| openhuman | ContextGuard 断路器(3 次连续失败) | turn_state 快照 + transcript 恢复(从磁盘加载) | `MaxIterationsExceeded` 被特殊处理（抑制 Sentry，视为预期状态） |

**对网文创作 Agent 的推荐方向：**

novelv3 当前的 `recovery_policy.py` + `recovery_planner.py` 已经是一套专门的恢复子系统。可以从三个项目中吸收：

- **从 openclaw 吸收**：子 agent 孤儿恢复——如果批量生成中某个章节的子任务被中断，恢复后可以从中断处继续
- **从 hermes-agent 吸收**：checkpoint resume（批量生成场景，跳过已完成的章节）
- **从 openhuman 吸收**：把某些故障（如迭代耗尽）视为"预期状态"而非系统缺陷——这对控制告警噪音有意义

---

### 2.7 权限与审计

| 项目 | 权限模型 | 审计机制 |
|------|---------|---------|
| openclaw | 网关角色(operator/node) + 作用域(admin/read/write/approvals/pairing/talk.secrets) + ownerOnly 工具策略 | payload JSONL 日志 + control-plane-audit + trace-base |
| hermes-agent | ToolGuardrails(pre_approve/deny/require_confirm) + Terminal approval_callback | SQLite 持久化所有消息 + session_search 全文检索 |
| openhuman | PermissionLevel(None/ReadOnly/Write/Execute/Dangerous) + ApprovalManager | 事件总线发布 ToolExecutionStarted/Completed + tracing/log |

**对网文创作 Agent 的推荐方向：**

novelv3 已经有 `approval_contract.py`（审批合同）和 `agent_trace_audit.py`（跟踪审计）。可以从 openhuman 吸收 PermissionLevel 的枚举化思路，从 openclaw 吸收 ownerOnly 策略——某些"修改核心设定"的工具只允许主 Agent 调用，不允许子 Agent 调用。

但**不需要** openclaw 的网关角色/作用域模型——那是多用户网关场景的，单用户网文创作 Agent 不需要 operator/node 划分。

---

### 2.8 溯源（Provenance）模式 —— 三个项目都有，novelv3 不应自己发明

novelv3 当前在 `agent_memory_route.py`、`agent_knowledge_base_route.py`、`longform_context_summary.py` 中各自实现了一份 `_memory_provenance()`。三个参考项目其实都有自己的溯源机制：

| 项目 | 溯源机制 | 实现方式 |
|------|---------|---------|
| openclaw | `SessionLineageMeta`（session 血缘元数据）+ `subagent-registry-memory.ts`（子 Agent 血缘追踪） | `src/acp/session-lineage-meta.ts` — 记录 session 的父子关系链 |
| hermes-agent | `skill_provenance.py` — `set_current_write_origin()` | 追踪写操作的来源（哪个技能/工具写入的） |
| openhuman | `Metadata` 和 `SourceRef`（"back-pointer" 注释标注） | Memory Tree 的每个节点带有来源引用，支持回溯到原始文档 |

**对 novelv3 的指导：** Provenance 是一个通用需求，不是 novelv3 的发明。novelv3 当前的三个 `_memory_provenance()` 实现结构相似但不完全相同——说明抽象时机已到。但参考项目也没有统一的"Provenance trait"——它们各自在需要的地方做轻量级溯源。建议 novelv3 先提取一个轻量的字段约定（version、status、sources、recovery），而不是设计重量级的 provenance 框架。

---

## 三、参考项目的盲区与 novelv3 当前差距

三个参考项目都是通用 Agent 基础设施，而非写作工具。以下能力是它们天然不具备、需要 novelv3 自己创造的。这些不是对参考项目的批评，而是对 novelv3 目标架构的补充输入。

但这里需要补充一个 Codex 审查结论：novelv3 并不是从零开始。当前仓库已经有 `review_chapter_quality`、`review_chapter_continuity`、审批契约、Trace 审计、批量章节进度恢复、tool contract 和 memory provenance 的雏形。下一阶段的缺口不是“创建这些概念”，而是把它们串进一个可诊断、可恢复、可持续生成的 Agent 控制环。

| 差距 | 参考项目为什么没有 | novelv3 当前状态 | 下一阶段处理方式 |
|------|------------------|------------------|------------------|
| **质量趋势与衰减监控** | 通用 Agent 不关心"越写越差" | 已有章节质量/连续性审稿工具，但尚未形成跨章节趋势投影 | 接入 `agent_health_projection`，让连续质量下降成为可诊断信号 |
| **风格锚定与漂移检测** | 通用 Agent 没有"文风一致性"的概念 | 已有 style_config 和部分 drift finding，但缺少稳定风格锚点与漂移趋势 | 先作为质量趋势的一类 finding，不单独重建风格系统 |
| **伏笔追踪（埋→提醒→收）** | 通用 Agent 不追踪叙事因果链 | Athena/Storyline 已有 foreshadowing 数据和 overdue 检查雏形 | 暂不新建大模型；先把逾期/未闭合信号暴露给控制环 |
| **节奏控制（爽点密度、张弛度）** | 通用 Agent 没有"读者体验节奏"概念 | 仍高度依赖人类叙事判断 | 本阶段不自动化，只设计人工介入点 |
| **人类叙事判断的介入点设计** | 通用 Agent 假设人类只需"确认操作" | 已有审批契约，但偏操作确认 | 把“需要叙事判断”的质量/伏笔/风格风险投影出来，避免 Agent 继续盲写 |

**这些盲区的处理策略：**

- **节奏控制**：当前 AI 的最弱项，建议初期不追求自动化，保留为人类作者的核心决策权
- **伏笔追踪**：不要在没有失败用例前新建完整状态机；先把已有 foreshadowing 数据中的 overdue / unresolved 信号接入 Agent 诊断
- **风格漂移检测**：可以借鉴 hermes-agent 的 `StreamingContextScrubber` 思路——用 fence 标签标记"风格锚定样本"，生成时注入作为风格参照，生成后对比检测偏差
- **质量评审**：参考 openhuman 的子 Agent 模式——用一个独立的"审稿 Agent"（不同模型或不同 prompt）来评审初稿，但要认识到它只能发现"不一致"和"明显问题"，不能判断"是否精彩"
- **质量衰减监控**：优先在 `agent_health_projection` 的框架下增加"创作质量趋势"指标，让连续 N 章的风险上升或评审失败可见、可阻断

---

## 四、对 novelv3 目标架构的核心建议

基于以上分析，以下是应该向 Codex 传达的方向性指导：

### 4.1 下一阶段应优先吸收的模式（直接服务控制环）

1. **五级工具循环检测**（openclaw）——比当前的单一 adjacent_repeat 更完备；下一阶段优先实现 `generic_repeat`、`ping_pong`、`known_poll_no_progress`、`unknown_tool_repeat`、`global_circuit_breaker` 的诊断输出与阻断建议
2. **质量趋势投影**（novelv3 原创 + openhuman 子 Agent 思路）——复用已有审稿工具，把连续章节质量风险、风格/设定 drift、伏笔逾期暴露到 `agent_health_projection`
3. **轻量 Provenance 字段约定**（三个项目共同模式）——统一 memory/context/knowledge route 的 `version`、`status`、`sources`、`windows`、`recovery`、`trace` 字段，不设计重量级 provenance 框架
4. **恢复与继续生成建议**（hermes-agent checkpoint + openhuman 预期状态思路）——让批量生成、章节审稿失败、循环风险触发后都有明确 next tool / next action，不让 Agent 继续盲跑
5. **上下文分层压缩的前置诊断**（hermes-agent 主体 + openhuman 断路器）——本阶段先暴露上下文窗口、截断、检索覆盖和压缩风险；只有当真实生成显示现有摘要不足时，再进入 Memory Tree 或压缩架构重建

### 4.2 应注意但暂缓的模式（有价值但非当前瓶颈）

6. **Memory Tree 分层记忆**（openhuman）——方向正确，但不是下一阶段起手式；先用现有 longform memory / retrieval / Athena 数据找出具体缺口
7. **AgentDefinition 配置文件驱动子 Agent**（openhuman）——适合后续扩展审稿、伏笔、风格 worker；但当前应先稳定主 Agent 控制环
8. **StopHooks 策略层**（openhuman）——概念值得借鉴，但不应为了抽象而拆 `run_service.py`；先用 loop diagnostics 和 health projection 证明终止条件确实需要独立策略层
9. **插件钩子系统**（hermes-agent）——pre_tool_call/post_tool_call 钩子适合写作校验，但在基础架构稳定前不是优先级
10. **事件总线**（openhuman）——松耦合是好的，但在模块边界还不清晰时过早引入事件总线会增加调试难度
11. **自注册工具系统**（hermes-agent）——当前的双重登记虽然冗余但是可以工作，优先解决更紧迫的运行缺口

### 4.3 不应照搬的模式（场景不适配）

12. 网关角色/作用域权限（openclaw）——多用户网关场景，单用户创作不需要；只吸收 owner-only / child-agent-write-gate 的约束思想
13. 多平台 Gateway（hermes-agent）——Telegram/Discord/Slack 集成对网文创作无用
14. Rust 的类型系统严谨性（openhuman）——借鉴思路但不要强行翻译到 Python
15. Cron 定时任务系统（openclaw + hermes-agent）——网文创作是交互式/按需的，不是定时触发的

---

## 五、下一阶段 goal：Agent-native 写作控制环加固

**Goal 名称：** Agent-native writing control loop hardening

**Goal 目标：** 在不重建整套记忆/子 Agent 架构的前提下，把 novelv3 的写作 Agent 控制环加固到可以支撑持续真实生成：能发现工具循环风险，能投影质量/记忆/审批/恢复状态，能在风险出现时给出明确 next action，而不是继续盲写。

**范围内：**

1. 扩展 `agent_loop` 诊断，从单一 adjacent_repeat 升级到五类可解释风险：`generic_repeat`、`ping_pong`、`known_poll_no_progress`、`unknown_tool_repeat`、`global_circuit_breaker`
2. 将已有章节审稿、连续性审稿、伏笔逾期、风格/设定 drift 信号汇总进 Agent 健康投影，形成跨章节质量趋势入口
3. 统一 memory/context/knowledge route 的轻量 provenance 字段约定，减少重复实现带来的投影漂移
4. 打通风险后的恢复建议：每类 loop / quality / provenance 风险都必须给出 next tool、是否需要用户判断、是否允许继续生成
5. 用真实生成链路或针对性 fixture 证明：Agent 可以从风险中停止、解释、推荐恢复，而不是继续执行同类工具

**范围外：**

1. 不在本 goal 内实现完整 Memory Tree
2. 不在本 goal 内引入配置驱动子 Agent 框架
3. 不在本 goal 内重构 `run_service.py` 为 StopHooks 架构
4. 不在本 goal 内引入事件总线或插件钩子系统
5. 不把“生成更多章节”作为主交付；生成只用于压测和发现问题

### 5.1 明确完成条件

这个 goal 只有在同时满足以下条件时才算完成：

1. **Loop risk 可诊断**：至少有单元测试覆盖 `generic_repeat`、`ping_pong`、`known_poll_no_progress`、`unknown_tool_repeat`、`global_circuit_breaker` 五类风险；`inspect_agent_health_projection` 或等价投影能展示风险类型、证据片段、阈值和 recommended next action
2. **风险可阻断或可恢复**：当风险达到 critical 阈值时，Agent 不继续盲目执行同类工具；输出必须包含 `status`、`reason`、`next_tool` / `recommended_tools`、`requires_user_input`
3. **质量趋势进入控制面**：已有 `review_chapter_quality` / `review_chapter_continuity` 结果能被汇总为跨章节趋势或最近窗口风险；至少覆盖质量风险上升、无风险、数据不足三种状态
4. **Provenance 字段一致**：memory route、knowledge base route、longform context summary 至少共享一套字段约定和测试断言：`version`、`status`、`sources`、`windows`、`recovery`、`trace`
5. **真实链路压测通过**：用现有本地服务或后端测试夹具跑一次“生成/审稿/诊断/恢复建议”的闭环，输出可回溯到具体 run、chapter 或 fixture
6. **验证分层完成**：小改动有针对性 pytest；涉及 health projection / run_service 的阶段跑相关后端测试；goal 收尾前跑项目既有质量验证脚本或说明无法运行的具体原因
7. **文档回填**：在本文件或后续 phase note 中记录实际发现的失败类型、修复方式、验证命令和下一轮才应考虑的架构项

### 5.2 本轮实现回填

本轮按 5.1 收敛到控制环加固，没有展开完整 Memory Tree、配置驱动子 Agent 或 StopHooks 重构。

**已修复/加固：**

1. 新增 `agent_loop_risk` 诊断模块，覆盖五类风险：`generic_repeat`、`ping_pong`、`known_poll_no_progress`、`unknown_tool_repeat`、`global_circuit_breaker`
2. `run_service` 与 `inspect_agent_health_projection` 复用同一 loop risk 结果；warning/critical 输出包含 detector、evidence、thresholds 和 `recommended_next_action`
3. `inspect_agent_health_projection` 新增 `creative_quality` 投影，汇总 `review_chapter_quality` / `review_chapter_continuity` 为 `insufficient_data`、`clear`、`risk_rising` 等趋势
4. 新增轻量 `memory_provenance_contract`，统一 memory route、knowledge base route、longform context summary 的 `version`、`status`、`sources`、`windows`、`recovery`、`trace` 字段约定
5. 新增后端 fixture 覆盖“生成/审稿/诊断/恢复建议”闭环：同一 health projection 能同时投影工具循环风险、质量风险上升和恢复建议工具链

**已验证命令：**

1. `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_loop_risk.py backend\tests\test_writing_agent_health_projection.py -q` → `15 passed`
2. `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_memory_route.py backend\tests\test_writing_agent_knowledge_base_route.py backend\tests\test_writing_agent_runs.py -k "agent_loop or longform_context_provenance or can_summarize_longform_context" -q` → `7 passed, 187 deselected`
3. `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\verify_local_quality.ps1` → backend `1324 passed`，frontend unit `567 passed`，frontend build passed；perf smoke 和 E2E 按脚本默认跳过，需额外环境变量或 `-RunE2E`

**仍留到后续 goal 的架构项：**

1. 若真实长篇压测继续出现跨 run 状态散落，再讨论 `run_service.py` 的 StopHooks/阶段管线拆分
2. 若 provenance 字段继续扩张，再把当前 helper 升级为更正式的 provenance schema/trait
3. 若质量趋势需要长期决策，再把当前最近窗口投影扩展为跨卷/跨章节的长期质量记忆

---

## 六、与 Codex 后续待讨论的开放问题

以下问题需要在汇总文档后与 Codex 讨论，结合它的工程判断来定方向：

1. **上下文压缩的粒度**：是按"卷"压缩还是按"固定 token 数"压缩？hermes-agent 按轮次数保护头尾，网文场景可能需要按"章节"保护
2. **Memory Tree 的节点定义**：卷/章/节/段落 四层够吗？还是需要更细的粒度（场景/角色出场/伏笔节点）？
3. **子 Agent 的层级深度**：openhuman 限制 3 跳，网文场景需要几层？
4. **`run_service.py` 的拆分策略**：loop contract、validation、projection 是否应该拆成独立模块？拆分的边界在哪里？
5. **Provenance 模式的抽象**：当前三个模块的 `_memory_provenance()` 重复，是否需要统一的 provenance trait/协议？

这些问题不阻塞下一阶段 goal。它们只有在控制环加固后的真实生成压测中继续暴露同类失败时，才进入后续架构设计。

---

> **迭代方式**：本文档是 Codex 的第一份指导性参考。Codex 基于本文档的方向执行后，根据实际执行结果进行下一轮分析，产出针对性的后续指导。不走"一次性全套文档"路线——文档随工程进展迭代演进。
