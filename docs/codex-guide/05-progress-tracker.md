# 05 · 进度追踪

> **最后更新**: 2026-06-01
> **版本**: v1.0
> **重要性**: ★★★★★（**每个 session 必读**）
> **维护规则**: 每次开发 session 结束后必须更新本文档

---

## 使用说明

本文档是 novelv3 Agent 化项目的**唯一真实进度来源**。当 codex 上下文被压缩、丢失之前的讨论时，本文档能告诉你：

1. 我们已经做到了哪里
2. 当前正在做什么
3. 下一步应该做什么
4. 有哪些阻塞项

注意：本文档记录的是当前认知和推进状态，不是不可变路线图。若代码现状、真实生成验证或参考项目适配分析表明原有方向不优，应以实际判断推进，并在本文件中同步修正状态、优先级和理由。

### 轨道说明

项目按以下 7 条轨道并行推进：

| 轨道 | 名称 | 含义 |
|------|------|------|
| T1 | Agent 运行循环 | 工具编排、循环检测、StopHooks、错误恢复 |
| T2 | 长期记忆 | Memory Tree、检索增强、世界模型持久化 |
| T3 | 对话编排 | 意图路由、计划生成、审批流、Followup |
| T4 | Worker/子代理 | Worker 定义、分发、追踪、孤兒恢复 |
| T5 | 审稿与质量 | 多维度审稿、一致性检查、修订闭环 |
| T6 | 上下文与审计 | Trace、压缩、上下文透明化 |
| T7 | 前端 Agent UX | Agent 状态可视化、计划展示、面板整合 |

---

## T1 · Agent 运行循环

### 当前状态

- [x] 基础迭代循环：`_agent_loop_contract()` 含 iteration budget 和相邻去重
- [x] 工具注册/发现/调用：tool_registry + tool_descriptor + tool_adapter + tool_executor
- [x] 工具生命周期钩子：tool_lifecycle_hooks
- [x] StopHooks 策略层：critical loop、BudgetCap、MaxTurns、ContextGuard、approval、memory provenance
- [x] Agent loop refund 预算投影：read 工具成功调用计入 refunded_iterations，不消耗 charged iteration
- [x] 工具权限分级基础枚举契约：ToolMutability + ToolPermissionLevel，公开 surface/contract 保持字符串兼容
- [x] 恢复计划器：recovery_planner + recovery_policy
- [x] 命令契约：agent_command_contracts + agent_step_binding

### 下一步任务

| 优先级 | 任务 | 完成标准 | 状态 |
|--------|------|---------|------|
| P0 | openclaw 五级循环检测（L2-L5） | ping-pong、poll_no_progress、global_circuit_breaker 全部可用 | ✅ 已完成 |
| P1 | 丰富 StopHooks 策略 | 至少包含 BudgetCap、MaxTurns、ContextGuard 三种策略 | ✅ 已完成 |
| P2 | refund 机制（借鉴 hermes-agent） | 程序化工具调用可退还迭代预算 | ✅ 已完成（基础版） |

### 阻塞项

- 无

### 最近完成

- 2026-06-01: 核对代码发现五级循环检测已实现；补充 StopHooks 的显式 BudgetCap / MaxTurns 策略和测试，ContextGuard 既有策略保留。
- 2026-06-01: 新增 Agent loop budget refund 投影，成功 read 工具调用会进入 refunded_iterations，remaining_iterations 按 charged_iterations 计算。
- 2026-06-01: 新增工具权限/可变性基础枚举契约，descriptor 内部返回 ToolMutability，permission 映射返回 ToolPermissionLevel；agent_tool_surface 与 tool_contracts 继续输出普通字符串以兼容既有前端和审批链路。

---

## T2 · 长期记忆

### 当前状态

- [x] Athena 世界模型：结构化实体 + 事件账本 + 提案审批 + layered checker (L0-L4)
- [x] Retrieval 检索：本地 hash embedding + 可切换远程 + lexical/vector score
- [x] Memory Tree 框架：memory_tree.py + 工具适配器
- [x] 记忆激活：memory_activation.py
- [x] 知识库候选：knowledge_base_candidates + 执行
- [x] 世界模型分析执行：world_model_analysis_execution

### 下一步任务

| 优先级 | 任务 | 完成标准 | 状态 |
|--------|------|---------|------|
| P0 | Memory Tree 分层摘要（卷→章两级） | 能生成并持久化卷级和章级摘要节点 | 🔴 待开始 |
| P1 | Memory Tree 语义浏览 | Agent 能通过工具浏览 Tree：展开/收起/搜索 | 🔴 待开始 |
| P2 | 世界模型 L5 语义检查 | 至少实现一个 LLM 驱动的语义一致性检查 | 🔴 待开始 |
| P3 | 检索策略智能化 | Agent 根据上下文自主选择检索策略 | 🔴 待开始 |

### 阻塞项

- Memory Tree 的分层摘要需要真实的长篇小说数据来验证效果

---

## T3 · 对话编排

### 当前状态

- [x] 意图路由：IntentRouter 支持基础写作意图（设定/大纲/正文/审稿/恢复）
- [x] 对话意图计划器：DialogIntentPlanner → WritingAgentPlan
- [x] 审批流：approval_contract + approval_verification_event
- [x] Followup 机制：recommended_followup_planner + 前端 action cards
- [x] 斜杠命令路由：slash_command_route
- [x] 参考模式投影：reference_pattern_projection

### 下一步任务

| 优先级 | 任务 | 完成标准 | 状态 |
|--------|------|---------|------|
| P1 | 意图路由覆盖扩展 | 覆盖所有已实现的 Agent 工具对应的用户意图 | 🟡 进行中 |
| P2 | 模糊意图 LLM 解析 | 用户自然语言模糊描述 → LLM 解析为具体意图 | 🔴 待开始 |
| P3 | pending_action 与 Agent tool approval 统一 | 两套审批机制合并为一个 | 🔴 待开始 |

### 阻塞项

- 无

### 最近完成

- 2026-05-27: dialog-driven-agent-orchestration plan executed — 审稿和恢复意图路由 + planner 分支
- 2026-05-27: 基础 followup 机制（含 memory tree route / story asset / chapter generation followups）

---

## T4 · Worker/子代理

### 当前状态

- [x] Worker 分发：agent_worker_dispatch.py
- [x] Worker 路由注册投影：worker_route_registry_projection.py
- [x] Agent 定义系统：agent_definitions.py + agent_definitions/ 目录，支持 YAML/TOML AgentDefinition loader 与 source_format 审计
- [x] 批量执行框架：batch_enqueue + batch_execution + batch_preflight
- [x] 队列检查器：batch_queue_inspector
- [x] Worker 链追踪：worker_route_registry_projection 含 chain alignment 记录
- [x] 孤兒 Worker 恢复基础审计：agent_worker_recovery 检测 active worker run 的 missing/terminal parent，并输出清理与重分派 preview

### 下一步任务

| 优先级 | 任务 | 完成标准 | 状态 |
|--------|------|---------|------|
| P1 | Worker 定义配置化 | AgentDefinition 文件格式标准化，支持 TOML/YAML | ✅ 已完成（基础版） |
| P2 | 孤兒 Worker 恢复 | Worker 失效后自动检测、清理、重新分配 | 🟡 进行中（检测 + preview） |
| P3 | Worker 并行度控制 | 基于系统资源的 worker 并发限制 | 🔴 待开始 |

### 阻塞项

- 无

### 最近完成

- 2026-06-01: 标准化 AgentDefinition loader，保留现有 YAML 定义并新增 TOML 读取能力；定义注册表审计输出 source_format，用于后续吸收 openhuman agent.toml 形态而不迁移当前文件。
- 2026-06-01: 新增 orphan worker 恢复基础审计，`inspect_agent_worker_dispatch` 会附带 orphan_recovery，自动检测 parent/source run 缺失或失败取消的 active worker run，并给出 mark-blocked 与 redispatch preview。

---

## T5 · 审稿与质量

### 当前状态

- [x] 基础一致性检查：L1 同步 + L2 后台深度检查
- [x] 章节修订：ChapterRevision 含 base/result version
- [x] 审稿修订工具：review_revision_tool_adapters/descriptors
- [x] 修订执行：revision_draft_execution + revision_patch_execution
- [x] 生成后审稿：batch_post_generation_review
- [x] 写作质量诊断：dogfood_evidence_projection

### 下一步任务

| 优先级 | 任务 | 完成标准 | 状态 |
|--------|------|---------|------|
| P1 | 多维度语义审稿（L5 实现） | 至少实现一致性/节奏/爽点密度 3 个维度 | 🔴 待开始 |
| P2 | 审稿结果→修订建议智能转换 | LLM 驱动的修订建议（不只是改错字） | 🔴 待开始 |
| P3 | 跨章节矛盾自动发现 | 死亡角色复生、物品丢失、时间线矛盾等 | 🔴 待开始 |

### 阻塞项

- L5 checker 目前是预留层，需要设计 LLM 调用接口

---

## T6 · 上下文与审计

### 当前状态

- [x] Model Call Trace：AIModelCallTrace 含 context blocks + sources
- [x] 前端 Trace 抽屉：ModelTraceDrawer + modelTraces store
- [x] Trace 脱敏：API key、Bearer token、password 等自动脱敏
- [x] 基础上下文压缩：对话历史长度限制
- [x] 长篇上下文摘要：longform_context_summary
- [x] ContextCompressor 基础计划投影：context pressure 下输出头尾保护预修剪、target_max_chars 和 summarize_longform_context 工具计划

### 下一步任务

| 优先级 | 任务 | 完成标准 | 状态 |
|--------|------|---------|------|
| P1 | 智能上下文压缩（借鉴 hermes-agent） | 预修剪 + LLM 摘要 + 头尾保护 | 🟡 进行中（基础计划） |
| P2 | 端到端 Trace 链路 | 从用户意图→计划→工具调用→模型调用→结果的一条链 | 🔴 待开始 |
| P3 | 上下文预算管理 | 可视化 Token 使用量 + 接近上限时的警告 | 🔴 待开始 |

### 阻塞项

- 无

### 最近完成

- 2026-06-01: `inspect_agent_context_compression_projection` 新增 compression_plan，在窗口压力下给出 head/tail protected pretrim、目标 max_chars 和 summarize_longform_context 工具计划；当前仍是只读计划，尚未写入 LLM 摘要或接入运行时压缩。

---

## T7 · 前端 Agent UX

### 当前状态

- [x] 对话界面含 action cards + followup + trace 入口
- [x] Athena 世界模型面板（实体 + 提案审阅）
- [x] Model Trace 抽屉
- [x] 前端请求隔离（request lane + project scope version）
- [x] Agent 诊断信息展示（dogfood evidence 等）

### 下一步任务

| 优先级 | 任务 | 完成标准 | 状态 |
|--------|------|---------|------|
| P1 | Agent 执行计划可视化 | 对话中展示当前执行计划、工具调用进度 | 🔴 待开始 |
| P2 | Memory Tree 可视化 | 前端展示分层摘要树、支持浏览和搜索 | 🔴 待开始 |
| P3 | 面板整合 | Athena 面板、Memory 面板、Trace 面板的统一导航 | 🔴 待开始 |

### 阻塞项

- 依赖 T2 的 Memory Tree 后端完善

---

## 历史阶段总结

### 阶段 1: 基础稳定性（已完成）

时间：2026-04 至 2026-05 初

主要产出：
- Hermes 流程控制、Athena 世界模型、Retrieval 检索
- Model Call Trace 全链路审计
- 前端请求隔离
- longform scale smoke 测试

详见 `docs/stability-mechanisms.md`

### 阶段 2: Agent 化基础（已完成）

时间：2026-05 中旬

主要产出：
- Writing Agent 核心编排层（tool_registry + executor + planner）
- 对话意图路由 + 计划生成
- Agent 工具系统（descriptor + adapter + execution 三层）
- Batch 执行框架
- Worker 分发基础

### 阶段 3: Narrative Memory Activation（当前）

时间：2026-05 下旬 至今

主要产出：
- Memory Tree 框架 + 工具适配器
- 记忆激活机制
- Followup 机制完善
- 写作质量诊断
- 参考模式投影

当前工作分支: `codex/agent-loop-risk`

### 下一阶段预览: Agent 循环增强后续

计划内容（待确认）：
- 智能上下文压缩
- 多维度语义审稿
- Memory Tree 分层摘要与语义浏览
- 孤兒 Worker 写入式清理与安全重分派执行
