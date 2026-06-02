# 05 · 进度追踪

> **最后更新**: 2026-06-02
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
- [x] 工具契约快照：inspect_agent_tool_contracts 聚合工具契约覆盖率、迁移差距和 reference alignment
- [x] 恢复计划器：recovery_planner + recovery_policy
- [x] 命令契约：agent_command_contracts + agent_step_binding
- [x] 命令契约快照：inspect_agent_command_contracts 聚合 slash command 投影、依赖工具和缺口
- [x] 控制面就绪度：inspect_agent_control_plane_readiness 聚合工具契约与命令契约
- [x] 写入门禁覆盖审计：inspect_agent_write_gate_coverage 聚合写入工具的 Agent 计划审批门禁覆盖
- [x] 写入变更指纹审计：inspect_agent_mutation_fingerprints 计算计划写入工具的稳定 mutation fingerprint，用于恢复、审批和冲突诊断

### 下一步任务

| 优先级 | 任务 | 完成标准 | 状态 |
|--------|------|---------|------|
| P0 | openclaw 五级循环检测（L2-L5） | ping-pong、poll_no_progress、global_circuit_breaker 全部可用 | ✅ 已完成 |
| P1 | 丰富 StopHooks 策略 | 至少包含 BudgetCap、MaxTurns、ContextGuard 三种策略 | ✅ 已完成 |
| P2 | refund 机制（借鉴 hermes-agent） | 程序化工具调用可退还迭代预算 | ✅ 已完成（基础版） |

### 阻塞项

- 无

### 最近完成

- 2026-06-02: `inspect_agent_mutation_fingerprints` 接入对话只读意图链路：自然语言“检查 generate_chapter 第4章写入变更指纹”会经 `mutation_fingerprints_intent` 生成无需审批的 read tool 计划，并把显式工具名与章节号整理为 `tools[{tool_name, params}]`。
- 2026-06-02: `inspect_agent_command_contracts` 接入对话只读意图链路：自然语言“检查命令契约缺口/slash command 投影”会经 `command_contracts_intent` 直接生成无需审批的 read tool 计划；含“控制面/control plane”的短语仍保留给 `inspect_agent_control_plane_readiness` 综合就绪度入口。
- 2026-06-02: `inspect_agent_tool_contracts` 接入对话只读意图链路：自然语言“检查工具契约覆盖率/迁移差距”会经 `tool_contracts_intent` 直接生成无需审批的 read tool 计划；含“控制面/control plane”的短语仍保留给 `inspect_agent_control_plane_readiness` 综合就绪度入口。
- 2026-06-02: `inspect_agent_write_gate_coverage` 接入对话只读意图链路：自然语言“检查写入工具的审批门禁覆盖/写入门禁缺口”会经 `write_gate_coverage_intent` 生成无需审批的 read tool 计划，供 Agent 在执行写入前快速审计 gate coverage。
- 2026-06-01: 核对代码发现五级循环检测已实现；补充 StopHooks 的显式 BudgetCap / MaxTurns 策略和测试，ContextGuard 既有策略保留。
- 2026-06-01: 新增 Agent loop budget refund 投影，成功 read 工具调用会进入 refunded_iterations，remaining_iterations 按 charged_iterations 计算。
- 2026-06-01: 新增工具权限/可变性基础枚举契约，descriptor 内部返回 ToolMutability，permission 映射返回 ToolPermissionLevel；agent_tool_surface 与 tool_contracts 继续输出普通字符串以兼容既有前端和审批链路。

---

## T2 · 长期记忆

### 当前状态

- [x] Athena 世界模型：结构化实体 + 事件账本 + 提案审批 + layered checker (L0-L4)
- [x] Retrieval 检索：本地 hash embedding + 可切换远程 + lexical/vector score
- [x] Memory Tree 框架：memory_tree.py + 工具适配器
- [x] Memory Tree 卷/章摘要持久化基础版：record_agent_memory_tree_summaries 写入 LongformMemory 摘要节点
- [x] Memory Tree 基础浏览：inspect_agent_memory_tree 支持 expand_node_id、max_depth、include_ancestors，用于展开/收起/搜索上下文
- [x] Memory Tree 语义召回基础：query 精确匹配失败时返回 relevance score、matched_terms / matched_fields 和 recommended_drilldowns
- [x] Memory Tree 层级语义回流：过滤到 volume/chapter 等上层节点时，可用 scene/beat 后代强匹配回流召回父节点，并抑制低分单字噪声
- [x] Memory Tree 写前激活：build_memory_activation_plan 可将高 relevance Memory Tree 节点纳入 activation.memory_tree，并保留未来章节防泄漏
- [x] Memory Route 对话入口：自然语言“检查第 N 章长篇记忆路由/检索维护状态”可投影为 inspect_agent_memory_route 只读工具计划
- [x] Memory Activation Plan 对话入口：自然语言“检查第 N 章记忆激活计划：<query>”可投影为 inspect_agent_memory_activation_plan 只读工具计划
- [x] Knowledge Base Route 对话入口：自然语言“检查第 N 章知识库路由 query=<query> limit <n>”可投影为 inspect_agent_knowledge_base_route 只读工具计划
- [x] Post Chapter Memory Capture 对话入口：自然语言“规划第 N 章写后记忆沉淀”可投影为 plan_post_chapter_memory_capture 只读工具计划，Memory Tree 工作区 chapter 节点也可直接创建对应只读 run
- [x] Retrieval Context 对话入口：自然语言“检索第 N 章前的上下文证据 query=<query> limit <n>”可投影为 search_agent_retrieval_context 只读工具计划
- [x] Longform Context Summary 对话入口：自然语言“汇总第 N 章长篇上下文 query=<query> max_chars <n>”可投影为 summarize_longform_context 只读工具计划
- [x] 记忆激活：memory_activation.py
- [x] 知识库候选：knowledge_base_candidates + 执行；AgentRunDrawer 可从写后记忆捕获候选发起 prepare_record_agent_knowledge_base_candidate 只读审批准备 continuation，并在待审批写入区展示候选标题、触发 execute_record_agent_knowledge_base_candidate_with_approval payload；执行成功后展示候选标题、类型、数量和推荐下一步工具
- [x] 世界模型分析执行：world_model_analysis_execution
- [x] 世界模型路由诊断：自然语言“检查第 N 章 subject_ref 世界模型路由”可投影为 inspect_agent_world_model_route 只读工具计划

### 下一步任务

| 优先级 | 任务 | 完成标准 | 状态 |
|--------|------|---------|------|
| P0 | Memory Tree 分层摘要（卷→章两级） | 能生成并持久化卷级和章级摘要节点 | ✅ 已完成（基础版） |
| P1 | Memory Tree 语义浏览 | Agent 能通过工具浏览 Tree：展开/收起/搜索 | ✅ 已完成（基础浏览） |
| P2 | 世界模型 L5 语义检查 | 至少实现一个 LLM 驱动的语义一致性检查 | 🔴 待开始 |
| P3 | 检索策略智能化 | Agent 根据上下文自主选择检索策略 | 🔴 待开始 |
| P4 | Memory Tree 语义召回/摘要质量增强 | 接入向量/LLM 摘要或真实长篇验证，不只依赖确定性摘要和文本匹配 | 🟡 进行中（层级 relevance + 写前激活基础） |

### 阻塞项

- Memory Tree 摘要质量仍需真实长篇小说数据验证；当前基础版是确定性摘要写入，不等同于 LLM 语义归纳。

### 最近完成

- 2026-06-02: `plan_post_chapter_memory_capture` 接入对话只读意图链路：Agent 可从自然语言直接规划章节后长期记忆/知识库候选沉淀，保留 chapter_index，并在有审稿证据时继续推荐 `prepare_record_agent_knowledge_base_candidate`。
- 2026-06-02: `inspect_agent_knowledge_base_route` 接入对话只读意图链路：Agent 可从自然语言直接读取作者偏好、项目策略、学习规则、知识库候选和写法参考路由，支持 chapter_index、query、limit 的确定性抽取。
- 2026-06-02: `search_agent_retrieval_context` 与 `summarize_longform_context` 接入对话只读意图链路：Agent 可从自然语言直接检索上下文证据或汇总指定章节长篇上下文，支持 query、limit、max_chapter_index、max_chars 和 include_prompt_context 等确定性参数抽取。
- 2026-06-02: `inspect_agent_world_model_route` 接入对话只读意图链路：Agent 可从自然语言直接诊断世界模型 profile、确认事实、待审提案压力和推荐后续动作，并支持 chapter_index、subject_ref、limit 的确定性抽取。
- 2026-06-02: `inspect_agent_memory_route` 与 `inspect_agent_memory_activation_plan` 接入对话只读意图链路：Agent 可从自然语言直接诊断长篇记忆/检索维护路由、上下文摘要开关和指定章节写前激活计划，不再只能依赖其他工具的 recommended_next_tools 间接触达。
- 2026-06-02: `inspect_agent_memory_tree` 语义召回新增层级回流：当调用方限定 `level` / `node_id` / `chapter_index` 后，候选上层节点会检查 scene/beat 后代的强匹配，将 `descendant_semantic_match`、`matched_descendant_ids` 和 `descendant.*` matched_fields 写入 relevance，并把 recommended_drilldowns 标为 `descendant_relevance`；同时引入最低 semantic relevance 阈值，避免单个汉字造成弱召回噪声。
- 2026-06-01: 新增 record_agent_memory_tree_summaries，按卷/章 materialize Memory Tree 摘要到 LongformMemory，并接入 memory_worker 路由与工具契约测试。
- 2026-06-01: 增强 inspect_agent_memory_tree 浏览能力，支持按节点展开、max_depth 收起、搜索命中时返回祖先上下文，供 Agent 渐进浏览 Memory Tree。
- 2026-06-02: 增强 `inspect_agent_memory_tree` 查询召回：精确 title/summary 匹配无结果时，使用确定性 token overlap relevance 召回跨字段节点，返回 score、matched_terms、matched_fields、match_reasons，并在 navigation 中给出最高相关节点的 recommended_drilldowns；这仍是向量/LLM 召回前的可审计基础层。
- 2026-06-02: `build_memory_activation_plan` 新增 `activation.memory_tree` 桶，query 命中高 relevance Memory Tree 节点时写入 prompt block、activated_counts 和 memory_provenance；过滤 `chapter_index >= target_chapter` 的节点，避免未来章节泄漏。

---

## T3 · 对话编排

### 当前状态

- [x] 意图路由：IntentRouter 支持基础写作意图（设定/大纲/正文/审稿/恢复）
- [x] 对话意图计划器：DialogIntentPlanner → WritingAgentPlan
- [x] Memory Tree 只读浏览意图：自然语言“浏览/搜索记忆树”可投影为 inspect_agent_memory_tree 只读工具计划
- [x] Memory Route 只读诊断意图：自然语言“检查第3章长篇记忆路由，包含上下文摘要”可投影为 inspect_agent_memory_route 只读工具计划
- [x] Memory Activation Plan 只读诊断意图：自然语言“检查第3章记忆激活计划：灯塔旧回声”可投影为 inspect_agent_memory_activation_plan 只读工具计划
- [x] Knowledge Base Route 只读诊断意图：自然语言“检查第4章知识库路由 query=写法偏好 limit 9”可投影为 inspect_agent_knowledge_base_route 只读工具计划
- [x] Post Chapter Memory Capture 只读规划意图：自然语言“规划第4章写后记忆沉淀”可投影为 plan_post_chapter_memory_capture 只读工具计划
- [x] World Model Route 只读诊断意图：自然语言“检查第2章 char.hero 世界模型路由 limit 7”可投影为 inspect_agent_world_model_route 只读工具计划
- [x] World Model Proposal Review 只读队列意图：自然语言“检查世界模型提案队列 limit 20”可投影为 review_world_model_proposals 只读工具计划
- [x] World Model Proposal Resolution Plan 只读规划意图：自然语言“规划世界模型提案解决方案 offset 2 limit 7”可投影为 plan_world_model_proposal_resolution 只读工具计划
- [x] Retrieval Context 只读检索意图：自然语言“检索第3章前的上下文证据 query=灯塔旧回声 limit 5”可投影为 search_agent_retrieval_context 只读工具计划
- [x] Longform Context Summary 只读摘要意图：自然语言“汇总第3章长篇上下文 query=灯塔旧回声 max_chars 2000”可投影为 summarize_longform_context 只读工具计划
- [x] ContextCompressor 只读自检意图：自然语言“检查上下文压缩/预算/窗口压力”可投影为 inspect_agent_context_compression_projection 只读工具计划
- [x] ContextCompressor dry-run payload 只读意图：自然语言“构建第3章上下文压缩 dry-run payload max_chars 2000 context_guard_failure_count 2”可投影为 build_agent_context_compression_payload 只读工具计划
- [x] Worker Dispatch 只读审计意图：自然语言“检查 worker 分发/孤儿恢复”可投影为 inspect_agent_worker_dispatch 只读工具计划
- [x] Agent Event Projection 只读审计意图：自然语言“检查 task-abc123 的 Agent 事件投影 limit 12”可投影为 inspect_agent_event_projection 只读工具计划
- [x] Agent Job Projection 只读诊断意图：自然语言“检查第3章 generate_chapter failed 任务队列 limit 8”可投影为 inspect_agent_job_projection 只读工具计划
- [x] Chapter Conflict Recovery 只读恢复计划意图：自然语言“规划第3章章节冲突恢复”可投影为 plan_chapter_conflict_recovery 只读工具计划
- [x] Trace Audit 只读审计意图：自然语言“检查 run trace/执行链路/失败原因”可投影为 inspect_agent_trace_audit 只读工具计划
- [x] Write Gate Coverage 只读审计意图：自然语言“检查写入工具的审批门禁覆盖”可投影为 inspect_agent_write_gate_coverage 只读工具计划
- [x] Legacy Hermes Migration 只读审计意图：自然语言“检查 legacy Hermes action 迁移路线”可投影为 inspect_legacy_hermes_action_migration 只读工具计划
- [x] Route Approval Opt-in 只读规划意图：自然语言“规划 pending-action-123 的 Agent 审批链 opt-in”可投影为 plan_agent_route_approval_opt_in 只读工具计划
- [x] Pending Action Route Opt-in Apply Preview/Contract 只读意图：自然语言“预览/生成 pending-action-123 的 Agent 审批链 opt-in 应用/契约”可投影为 preview_pending_action_route_approval_opt_in_apply / preview_pending_action_route_approval_opt_in_apply_contract 只读工具计划
- [x] Pending Action Route Opt-in Apply Prepare 只读意图：自然语言“准备 pending-action-123 的 Agent 审批链 opt-in 执行审批”可投影为 prepare_apply_pending_action_route_approval_opt_in 只读工具计划，contract preview 的 recommended followup 也可进入该 prepare 工具，prepare 输出携带仍需确认的 execute-with-approval 调用骨架，并在 followup planner、dialog action result 和前端 fallback projection 中保留为 pending confirmation
- [x] Mutation Fingerprints 只读审计意图：自然语言“检查 generate_chapter 第4章写入变更指纹”可投影为 inspect_agent_mutation_fingerprints 只读工具计划
- [x] Tool Contracts 只读自检意图：自然语言“检查工具契约覆盖率/迁移差距”可投影为 inspect_agent_tool_contracts 只读工具计划
- [x] Command Contracts 只读自检意图：自然语言“检查命令契约缺口/slash command 投影”可投影为 inspect_agent_command_contracts 只读工具计划
- [x] Slash Command Route 只读审计意图：自然语言“检查 /continue 斜杠命令路由”可投影为 inspect_agent_slash_command_route 只读工具计划
- [x] Dialog Route Projection 只读审计意图：自然语言“检查 button action 统一对话路由投影”可投影为 inspect_agent_dialog_route_projection 只读工具计划
- [x] Intent Projection 只读审计意图：自然语言“检查意图投影：<待分析文本>”可投影为 inspect_agent_intent_projection 只读工具计划
- [x] Dialog Control Plane 只读审计意图：自然语言“检查 generate_chapter 对话控制面投影”可投影为 inspect_agent_dialog_control_plane_projection 只读工具计划
- [x] Reference Alignment 只读审计意图：自然语言“检查参考项目模式对齐/开源项目适配”可投影为 inspect_agent_reference_alignment 只读工具计划
- [x] Dogfood Evidence 只读审计意图：自然语言“检查 dogfood pressure-test 证据覆盖”可投影为 inspect_agent_dogfood_evidence 只读工具计划
- [x] Route Preference 只读审计意图：自然语言“检查 text_intent 路由偏好/Agent 审批链迁移建议”可投影为 inspect_agent_route_preference_projection 只读工具计划
- [x] Agent Health 只读自检意图：自然语言“检查 Agent 健康/工具诊断”可投影为 inspect_agent_health_projection 只读工具计划
- [x] Control Plane 只读自检意图：自然语言“检查控制面就绪度/工具契约/命令契约”可投影为 inspect_agent_control_plane_readiness 只读工具计划
- [x] 审批流：approval_contract + approval_verification_event
- [x] Followup 机制：recommended_followup_planner + 前端 action cards
- [x] 斜杠命令路由：slash_command_route，可由自然语言“检查 /continue 斜杠命令路由”直接规划到 inspect_agent_slash_command_route，并可检查统一 dialog route projection
- [x] 参考模式投影：reference_pattern_projection

### 下一步任务

| 优先级 | 任务 | 完成标准 | 状态 |
|--------|------|---------|------|
| P1 | 意图路由覆盖扩展 | 覆盖所有已实现的 Agent 工具对应的用户意图 | 🟡 进行中（read tool intents） |
| P2 | 模糊意图 LLM 解析 | 用户自然语言模糊描述 → LLM 解析为具体意图 | 🔴 待开始 |
| P3 | pending_action 与 Agent tool approval 统一 | 两套审批机制合并为一个 | 🟡 进行中（read plan/preview/contract/prepare/execute handoff + dialog followup visibility） |

### 阻塞项

- 无

### 最近完成

- 2026-06-02: `dialog` recommended followup preview 透传 `pending_confirmation_tool_calls`，`action_result_view` 新增“待确认后继/待确认工具”摘要；execute handoff 在对话层可见但仍不进入自动执行工具列表。
- 2026-06-02: `normalize_tool_recommendations` 新增 `recommended_next_tool_calls` 保留逻辑，`plan_recommended_followups` 会把 `requires_confirmation=true` 的 execute-with-approval 调用暴露为 `pending_confirmation_tool_calls` 和 execution policy 计数；该调用不会进入 `tools` 自动执行列表，仍由写入门禁与确认流程控制。
- 2026-06-02: `prepare_apply_pending_action_route_approval_opt_in` 输出新增 `recommended_next_tool_calls`，将 `execute_apply_pending_action_route_approval_opt_in_with_approval` 的 `pending_action_id`、route apply contract/hash 与 Agent plan approval contract/hash 组织成 `requires_confirmation=true` 的调用骨架；descriptor schema 同步公开该字段，便于 Agent 在不自动写入的前提下审计 execute handoff。
- 2026-06-02: `IntentRouter` 新增 `route_approval_opt_in_apply_prepare_intent`，可将“准备 pending-action-123 的 Agent 审批链 opt-in 执行审批”自然语言直达 `prepare_apply_pending_action_route_approval_opt_in` read tool；`plan_recommended_followups` 现在会接受 contract preview 推荐的 `prepare_apply_pending_action_route_approval_opt_in`，但 direct `apply_pending_action_route_approval_opt_in` 和审批后的 execute 工具仍保持写入门禁。
- 2026-06-02: `IntentRouter` 新增 `route_approval_opt_in_plan_intent` / `route_approval_opt_in_apply_preview_intent` / `route_approval_opt_in_apply_contract_intent`，可将 pending-action 的 Agent 审批链 opt-in 规划、应用预览和契约生成自然语言直达 read tool；`apply_pending_action_route_approval_opt_in` 仍保持 guarded write。
- 2026-06-02: `IntentRouter` 新增 `legacy_hermes_migration_intent`，可将“检查 legacy Hermes action 迁移路线”等自然语言投影为 `inspect_legacy_hermes_migration` action；`plan_dialog_intent_agent_run` 对该只读 action 生成无需审批的 `inspect_legacy_hermes_action_migration` 工具计划，用于审计 legacy setup/storyline/outline 生成动作迁移到 Agent-native preview/approval/execute 工具链的覆盖状态。
- 2026-06-02: `IntentRouter` 新增 `context_compression_payload_intent`，可将“构建第3章上下文压缩 dry-run payload max_chars 2000 context_guard_failure_count 2”等自然语言投影为 `build_context_compression_payload` action；`plan_dialog_intent_agent_run` 对该只读 action 生成无需审批的 `build_agent_context_compression_payload` 工具计划，并保留 chapter_index、max_chars 与 context_guard_failure_count，补齐 ContextCompressor 从自检投影到 payload builder 的对话直达入口。
- 2026-06-02: `IntentRouter` 新增 `world_model_proposal_review_intent` 与 `world_model_proposal_resolution_plan_intent`，可将“检查世界模型提案队列 limit 20”和“规划世界模型提案解决方案 offset 2 limit 7”等自然语言分别投影为 `review_world_model_proposals` / `plan_world_model_proposal_resolution` action；`plan_dialog_intent_agent_run` 对两者生成无需审批的 read tool 计划，并保留 offset/limit，便于 Agent 在应用世界模型提案决议前先完成队列审阅和处理规划。
- 2026-06-02: `IntentRouter` 新增 `agent_event_projection_intent`，可将“检查 task-abc123 的 Agent 事件投影 limit 12”等自然语言投影为 `inspect_agent_event_projection` action；`plan_dialog_intent_agent_run` 对该只读 action 生成无需审批的工具计划，并保留 task_id/run_id/limit，补强后台任务与 Agent run/step 的事件流审计入口。
- 2026-06-02: `IntentRouter` 新增 `post_chapter_memory_capture_intent`，可将“规划第4章写后记忆沉淀”等自然语言投影为 `plan_post_chapter_memory_capture` action；`plan_dialog_intent_agent_run` 对该只读 action 生成无需审批的工具计划，并保留 chapter_index，打通写后知识沉淀规划的对话入口。
- 2026-06-02: `IntentRouter` 新增 `agent_job_projection_intent` 与 `chapter_conflict_recovery_intent`，可将“检查第3章 generate_chapter failed 任务队列 limit 8”和“规划第3章章节冲突恢复”等自然语言分别投影为 `inspect_agent_job_projection` / `plan_chapter_conflict_recovery` action；`plan_dialog_intent_agent_run` 对两者生成无需审批的 read tool 计划，并保留 chapter_index、task_type、status、limit。
- 2026-06-02: `IntentRouter` 新增 `knowledge_base_route_intent`，可将“检查第4章知识库路由 query=写法偏好 limit 9”等自然语言投影为 `inspect_knowledge_base_route` action；`plan_dialog_intent_agent_run` 对该只读 action 生成无需审批的 `inspect_agent_knowledge_base_route` 工具计划，并保留 chapter_index、query、limit，避免被宽泛“检查”审稿意图抢占。
- 2026-06-02: `IntentRouter` 新增 `retrieval_context_intent` 与 `longform_context_summary_intent`，可将“检索第3章前的上下文证据 query=灯塔旧回声 limit 5”和“汇总第3章长篇上下文 query=灯塔旧回声 max_chars 2000 include_prompt_context”等自然语言分别投影为 `search_retrieval_context` / `summarize_longform_context` action；`plan_dialog_intent_agent_run` 对两者生成无需审批的 read tool 计划。
- 2026-06-02: `IntentRouter` 新增 `world_model_route_intent`，可将“检查第2章 char.hero 世界模型路由 limit 7”等自然语言投影为 `inspect_world_model_route` action；`plan_dialog_intent_agent_run` 对该只读 action 生成无需审批的 `inspect_agent_world_model_route` 工具计划，并保留 chapter_index、subject_ref、limit。
- 2026-06-02: `IntentRouter` 新增 `memory_route_intent` 与 `memory_activation_plan_intent`，可将“检查第3章长篇记忆路由，包含上下文摘要”和“检查第3章记忆激活计划：灯塔旧回声”等自然语言分别投影为 `inspect_memory_route` / `inspect_memory_activation_plan` action；`plan_dialog_intent_agent_run` 对两者生成无需审批的 read tool 计划，并保留 chapter_index、include_context_summary 与冒号后的 query。
- 2026-06-02: `IntentRouter` 新增 `mutation_fingerprints_intent`，可将“检查 generate_chapter 第4章写入变更指纹”等自然语言投影为 `inspect_mutation_fingerprints` action，并确定性抽取显式 snake_case 工具名与章节号；`plan_dialog_intent_agent_run` 对该只读 action 直接生成 `inspect_agent_mutation_fingerprints` 工具计划，approval_contract 为 not_required，并放在宽泛 review 规则之前避免被“检查”类审稿意图抢占。
- 2026-06-02: `IntentRouter` 新增 `route_preference_intent`，可将“检查 text_intent 路由偏好/Agent 审批链迁移建议”等自然语言投影为 `inspect_route_preference` action，并确定性抽取 `source`；`plan_dialog_intent_agent_run` 对该只读 action 直接生成 `inspect_agent_route_preference_projection` 工具计划，approval_contract 为 not_required。
- 2026-06-02: `IntentRouter` 新增 `dialog_route_projection_intent`，可将“检查 button action 统一对话路由投影”等自然语言投影为 `inspect_dialog_route` action，并确定性抽取 `source`；`plan_dialog_intent_agent_run` 对该只读 action 直接生成 `inspect_agent_dialog_route_projection` 工具计划，approval_contract 为 not_required，且与 route preference/审批链迁移建议入口保持语义边界。
- 2026-06-02: `IntentRouter` 新增 `intent_projection_intent`，可将“检查意图投影：<待分析文本>”投影为 `inspect_intent_projection` action，并把冒号后的待分析文本传给 `inspect_agent_intent_projection`；`plan_dialog_intent_agent_run` 对该只读 action 生成无需审批的工具计划，便于持续审计自然语言规则匹配。
- 2026-06-02: `IntentRouter` 新增 `dialog_control_plane_projection_intent`，可将“检查 generate_chapter 对话控制面投影”等自然语言投影为 `inspect_dialog_control_plane` action，并确定性抽取 `action_type`；`plan_dialog_intent_agent_run` 对该只读 action 直接生成 `inspect_agent_dialog_control_plane_projection` 工具计划，approval_contract 为 not_required，用于审计 pending action 当前运行工具与推荐审批工具链。
- 2026-06-02: `IntentRouter` 新增 `dogfood_evidence_intent`，可将“检查 dogfood pressure-test 证据覆盖/真实长篇自吃证据”等自然语言投影为 `inspect_dogfood_evidence` action；`plan_dialog_intent_agent_run` 对该只读 action 直接生成 `inspect_agent_dogfood_evidence` 工具计划，approval_contract 为 not_required，并放在宽泛 review 规则之前避免被“检查”类审稿意图抢占。
- 2026-06-02: `IntentRouter` 新增 `slash_command_route_intent`，可将“检查 /continue 斜杠命令路由”等自然语言投影为 `inspect_slash_command_route` action，并确定性抽取 `command_name`；`plan_dialog_intent_agent_run` 对该只读 action 直接生成 `inspect_agent_slash_command_route` 工具计划，approval_contract 为 not_required，并通过 command contracts guard 避免被更泛的 slash command 契约查询抢占。
- 2026-06-02: `IntentRouter` 新增 `reference_alignment_intent`，可将“检查参考项目模式对齐/开源项目适配”等自然语言投影为 `inspect_reference_alignment` action；`plan_dialog_intent_agent_run` 对该只读 action 直接生成 `inspect_agent_reference_alignment` 工具计划，approval_contract 为 not_required，并放在宽泛 review 规则之前避免被“检查”类审稿意图抢占。
- 2026-06-02: `IntentRouter` 新增 `command_contracts_intent`，可将“检查命令契约缺口/slash command 投影”等自然语言投影为 `inspect_command_contracts` action；`plan_dialog_intent_agent_run` 对该只读 action 直接生成 `inspect_agent_command_contracts` 工具计划，approval_contract 为 not_required，并通过规则 guard 避免抢占含“控制面”的 readiness 查询。
- 2026-06-02: `IntentRouter` 新增 `tool_contracts_intent`，可将“检查工具契约覆盖率/迁移差距”等自然语言投影为 `inspect_tool_contracts` action；`plan_dialog_intent_agent_run` 对该只读 action 直接生成 `inspect_agent_tool_contracts` 工具计划，approval_contract 为 not_required，并通过规则 guard 避免抢占含“控制面”的 readiness 查询。
- 2026-06-02: `IntentRouter` 新增 `write_gate_coverage_intent`，可将“检查写入工具的审批门禁覆盖/写入门禁缺口”等自然语言投影为 `inspect_write_gate_coverage` action；`plan_dialog_intent_agent_run` 对该只读 action 直接生成 `inspect_agent_write_gate_coverage` 工具计划，approval_contract 为 not_required。
- 2026-06-02: `IntentRouter` 新增 `trace_audit_intent`，可将“检查 run trace/执行链路/失败原因”等自然语言投影为 `inspect_trace_audit` action，并抽取 run_id / chapter_index；`plan_dialog_intent_agent_run` 对该只读 action 直接生成 `inspect_agent_trace_audit` 工具计划，approval_contract 为 not_required。
- 2026-06-02: `IntentRouter` 新增 `control_plane_readiness_intent`，可将“检查 Agent 控制面就绪度/工具契约/命令契约”等自然语言投影为 `inspect_control_plane_readiness` action；`plan_dialog_intent_agent_run` 对该只读 action 直接生成 `inspect_agent_control_plane_readiness` 工具计划，approval_contract 为 not_required。
- 2026-06-02: `IntentRouter` 新增 `agent_health_intent`，可将“检查 Agent 健康/工具诊断”等自然语言投影为 `inspect_agent_health` action，并抽取 chapter_index；`plan_dialog_intent_agent_run` 对该只读 action 直接生成 `inspect_agent_health_projection` 工具计划，approval_contract 为 not_required。
- 2026-06-02: `IntentRouter` 新增 `worker_dispatch_intent`，可将“检查 worker 分发/孤儿恢复/子代理调度”等自然语言投影为 `inspect_worker_dispatch` action，并抽取显式 worker_name；`plan_dialog_intent_agent_run` 对该只读 action 直接生成 `inspect_agent_worker_dispatch` 工具计划，approval_contract 为 not_required。
- 2026-06-02: `IntentRouter` 新增 `context_compression_intent`，可将“检查第 N 章上下文压缩/预算/窗口压力”等自然语言投影为 `inspect_context_compression` action，并抽取 chapter_index / max_chars；`plan_dialog_intent_agent_run` 对该只读 action 直接生成 `inspect_agent_context_compression_projection` 工具计划，approval_contract 为 not_required。
- 2026-06-02: `IntentRouter` 新增 `memory_tree_intent`，可将“浏览/查看/搜索/检索记忆树/长期记忆”等自然语言投影为 `inspect_memory_tree` action，抽取 query、level、chapter_index 并默认 include_ancestors；`plan_dialog_intent_agent_run` 对该只读 action 直接生成 `inspect_agent_memory_tree` 工具计划，approval_contract 为 not_required。
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
- [x] 孤兒 Worker 恢复写入闭环基础版：apply_agent_worker_orphan_recovery 确认后标记 orphan worker blocked，并可创建 pending redispatch run
- [x] Worker 分发/孤兒恢复只读入口：自然语言“检查 worker 分发/孤儿恢复”可直接规划到 inspect_agent_worker_dispatch
- [x] Agent Event Projection 只读入口：自然语言可直接规划到 inspect_agent_event_projection，审计后台任务、Agent run 和 step 推导出的事件流
- [x] Agent Job Projection/章节冲突恢复只读入口：自然语言可直接规划到 inspect_agent_job_projection 和 plan_chapter_conflict_recovery，检查后台任务队列、章节占用与恢复工具计划

### 下一步任务

| 优先级 | 任务 | 完成标准 | 状态 |
|--------|------|---------|------|
| P1 | Worker 定义配置化 | AgentDefinition 文件格式标准化，支持 TOML/YAML | ✅ 已完成（基础版） |
| P2 | 孤兒 Worker 恢复 | Worker 失效后自动检测、清理、重新分配 | ✅ 已完成（基础闭环） |
| P3 | Worker 并行度控制 | 基于系统资源的 worker 并发限制 | 🔴 待开始 |

### 阻塞项

- 无

### 最近完成

- 2026-06-02: `inspect_agent_event_projection` 接入对话只读意图链路：Agent 可从自然语言直接按 task_id/run_id/limit 查看后台任务、Agent run 和 step 记录推导出的事件流，并继续推荐 `inspect_agent_job_projection`。
- 2026-06-02: `inspect_agent_job_projection` 与 `plan_chapter_conflict_recovery` 接入对话只读意图链路：Agent 可从自然语言直接检查后台任务队列、筛选章节/任务类型/状态，并为章节占用冲突生成只读恢复计划。
- 2026-06-02: `inspect_agent_worker_dispatch` 接入对话只读意图链路：自然语言“检查 worker 分发/孤儿恢复”会经 `worker_dispatch_intent` 生成无需审批的 read tool 计划，保留显式 worker_name 并默认提供空 tasks 以执行纯审计预览。
- 2026-06-01: 标准化 AgentDefinition loader，保留现有 YAML 定义并新增 TOML 读取能力；定义注册表审计输出 source_format，用于后续吸收 openhuman agent.toml 形态而不迁移当前文件。
- 2026-06-01: 新增 orphan worker 恢复基础审计，`inspect_agent_worker_dispatch` 会附带 orphan_recovery，自动检测 parent/source run 缺失或失败取消的 active worker run，并给出 mark-blocked 与 redispatch preview。
- 2026-06-01: 新增 `apply_agent_worker_orphan_recovery` guarded write 工具，确认后将 orphan worker run 标记为 blocked；若父 run 已失败且原始工具链可恢复，可创建新的 pending redispatch run。

---

## T5 · 审稿与质量

### 当前状态

- [x] 基础一致性检查：L1 同步 + L2 后台深度检查
- [x] 章节修订：ChapterRevision 含 base/result version
- [x] 审稿修订工具：review_revision_tool_adapters/descriptors
- [x] 修订执行：revision_draft_execution + revision_patch_execution
- [x] 生成后审稿：batch_post_generation_review
- [x] 写作质量诊断：dogfood_evidence_projection，可由自然语言“检查 dogfood pressure-test 证据覆盖”直接规划到 inspect_agent_dogfood_evidence

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
- [x] Trace Audit 自然语言只读入口：自然语言“检查 run trace/执行链路/失败原因”可直接规划到 inspect_agent_trace_audit
- [x] 基础上下文压缩：对话历史长度限制
- [x] 长篇上下文摘要：longform_context_summary
- [x] ContextCompressor 基础计划投影：context pressure 下输出头尾保护预修剪、target_max_chars 和 summarize_longform_context 工具计划
- [x] ContextCompressor dry-run payload：build_agent_context_compression_payload 输出头尾保护、summary 注入、pretrim evidence 和无副作用 trace，并成为 context pressure 的推荐恢复入口
- [x] ContextCompressor preflight runtime gate：preflight_writing 输出 context_compression 检查、warning issue、recommended_next_tools 和裁剪后的 payload preview；ContextGuard opened 时作为 blocker 处理
- [x] ContextCompressor 章节 prompt block 压缩：章节生成上下文构建在 longform 压力下用 dry-run compressed_context 替换原始 longform block，并在 trace metadata 记录压缩来源
- [x] ContextCompressor 持久摘要写入工具：record_agent_context_compression_summary 将 ready payload 的 compressed_context 幂等写入 LongformMemory，作为后续恢复、审计和复用工件
- [x] ContextCompressor 持久摘要自动复用：章节生成在 longform 压力下优先复用同章节同预算的 context_compression_summary，未命中再回退 dry-run payload builder
- [x] ContextCompressor preflight 持久摘要推荐链：preflight_writing 在窗口压力且 payload ready 时推荐 record_agent_context_compression_summary，并在 preview 中暴露该后续工具
- [x] ContextCompressor preflight 持久摘要复用：preflight_writing 在窗口压力下先查同章节同预算 context_compression_summary，命中时暴露脱敏 preview 并推荐 prepare_generate_chapter_execution

### 下一步任务

| 优先级 | 任务 | 完成标准 | 状态 |
|--------|------|---------|------|
| P1 | 智能上下文压缩（借鉴 hermes-agent） | 预修剪 + LLM 摘要 + 头尾保护 | 🟡 进行中（preflight persistent reuse） |
| P2 | 端到端 Trace 链路 | 从用户意图→计划→工具调用→模型调用→结果的一条链 | 🔴 待开始 |
| P3 | 上下文预算管理 | 可视化 Token 使用量 + 接近上限时的警告 | 🔴 待开始 |

### 阻塞项

- 无

### 最近完成

- 2026-06-02: `inspect_agent_trace_audit` 接入对话只读意图链路：自然语言“检查 run trace/执行链路/失败原因”会经 `trace_audit_intent` 生成无需审批的 read tool 计划，支持 run_id 和 chapter_index 的确定性抽取；这补强了端到端 Trace 链路的入口，但完整“用户意图→计划→工具调用→模型调用→结果”聚合仍未完成。
- 2026-06-02: `build_agent_context_compression_payload` 接入对话只读意图链路：自然语言可直接构建指定章节/预算/ContextGuard 失败次数下的 dry-run payload，跳过泛化压缩自检入口但保留投影快照、pretrim evidence 和无副作用 trace。
- 2026-06-02: `preflight_writing` 的 context window pressure 分支接入 `load_agent_context_compression_summary`：若同章节同预算的 `context_compression_summary` 已存在且含可用 compressed_context，则不再调用 `build_agent_context_compression_payload`，改为输出脱敏 `context_compression_payload_preview`（移除 compression_payload.compressed_context 与 record.summary），并将下一步推荐为 `prepare_generate_chapter_execution`。
- 2026-06-02: `preflight_writing` 在 context window pressure 且 `build_agent_context_compression_payload` 返回 ready `compressed_context` 时，将 `record_agent_context_compression_summary` 追加到顶层 `recommended_next_tools` 和 `context_compression_payload_preview.recommended_next_tools`，并在 warning issue 中带上 followup_tool/followup_params，避免 Agent 停在只读 payload 预览而不产出可复用持久工件。
- 2026-06-02: 章节生成 longform block 压缩路径新增持久工件复用：压力触发后先通过 `load_agent_context_compression_summary` 查找 `context_compression:chapter:{n}:max_chars:{budget}`，命中则直接用 `LongformMemory.summary` 注入 prompt，并在 trace metadata 标记 `context_compression_summary_record`；未命中仍回退 `build_agent_context_compression_payload`。
- 2026-06-02: 新增 `record_agent_context_compression_summary`，基于 `build_agent_context_compression_payload` 的 ready payload 将 `compressed_context` 以 `context_compression_summary` 类型写入 `LongformMemory`，scope 为 `context_compression:chapter:{n}:max_chars:{budget}`，同章节同预算幂等更新；同步 memory_worker 工具定义、adapter、worker route 和 registry 契约。
- 2026-06-02: 章节生成 prompt 构建路径接入 ContextCompressor：`build_chapter_prompt_context_blocks` 支持 `max_context_chars`，在 longform 原始长度达到窗口压力阈值时调用 `build_agent_context_compression_payload`，用 dry-run `compressed_context` 替换 `longform_memory_context`，并在 trace block metadata 记录 applied 状态、target_max_chars、compression_ratio、pretrimmed section keys 和 side_effects；仍未写入持久 LLM 摘要。
- 2026-06-02: `preflight_writing` 接入 ContextCompressor 运行时检查：支持 `max_context_chars` / `context_guard_failure_count` 参数，输出 `checks.context_compression`、warning issue、`recommended_next_tools` 和裁剪后的 `context_compression_payload_preview`；该 preview 保持只读 dry-run，不包含完整 `compressed_context`，尚未替换最终生成 prompt。
- 2026-06-01: `build_agent_context_compression_payload` 接入 memory_worker，基于 projection 生成只读 dry-run payload，包含 protected_head、summarize_longform_context summary、protected_tail、pretrimmed_sections、side_effects 和 runtime_behavior_changed=false trace；尚未写入 LLM 摘要或替换运行时上下文构建路径。
- 2026-06-01: `inspect_agent_context_compression_projection` 在 context pressure 下开始推荐 `build_agent_context_compression_payload`，并通过 compression_plan.payload_tool / recovery.tools / health projection recommended_tools 传播，避免 Agent 只停在 summarize 计划层。
- 2026-06-01: `inspect_agent_context_compression_projection` 新增 compression_plan，在窗口压力下给出 head/tail protected pretrim、目标 max_chars 和 summarize_longform_context 工具计划；当前仍是只读计划，尚未写入 LLM 摘要或接入运行时压缩。

---

## T7 · 前端 Agent UX

### 当前状态

- [x] 对话界面含 action cards + followup + trace 入口
- [x] Recommended followup fallback view 可展示 pending confirmation handoff，且 pending-only 计划不会显示“执行后继”自动执行按钮
- [x] AgentRunDrawer 执行计划进度摘要：展示计划工具数、已执行、已完成、进行中、下一步工具和逐项计划工具状态
- [x] AgentRunDrawer Memory Tree 投影：展示 inspect_agent_memory_tree 的状态、查询条件、导航模式、推荐展开数、节点列表和项目级会话浏览历史，并可通过自由查询、推荐 drilldown 或返回节点展开发起只读浏览 run；Hermes 已注册 Memory 主工作区，子导航常驻 Memory Tree 面板可切入工作区、直接提交只读搜索 run、按 parent/children 展示当前返回节点层级树、从结果节点发起只读展开并显示当前展开节点，也可从历史入口重新打开对应 run；工作区中带 chapter_index 的节点可跳转并加载正文章节，也可从安全节点标签发起 Retrieval 证据只读 run、Longform Context Summary 只读 run、Memory Activation Plan 只读 run、Knowledge Base Route 只读 run、Post Chapter Memory Capture 写后记忆沉淀规划 run、Trace Audit 章节审计 run 或 Athena 世界模型路由 run；写后记忆捕获候选可在 Drawer 中继续准备知识库候选写入审批，并在待审批写入区显示候选标题、触发已审批执行 payload，执行成功后展示写入结果和推荐下一步工具
- [x] Athena 世界模型面板（实体 + 提案审阅）
- [x] Model Trace 抽屉
- [x] 前端请求隔离（request lane + project scope version）
- [x] Agent 诊断信息展示（dogfood evidence 等）

### 下一步任务

| 优先级 | 任务 | 完成标准 | 状态 |
|--------|------|---------|------|
| P1 | Agent 执行计划可视化 | 对话中展示当前执行计划、工具调用进度 | 🟡 进行中（Drawer per-tool progress + followup pending confirmation fallback） |
| P2 | Memory Tree 可视化 | 前端展示分层摘要树、支持浏览和搜索 | 🟡 进行中（Drawer read-only projection + free search + recommended/node drilldown + project-scoped history + Hermes Memory workspace + subnav search/history/hierarchical results/expand state + chapter/retrieval/context-summary/memory-activation/knowledge-base/post-capture/trace/athena deep-link；更完整树工作区能力待补） |
| P3 | 面板整合 | Athena 面板、Memory 面板、Trace 面板的统一导航 | 🟡 进行中（Memory workspace → content/retrieval/longform context summary/memory activation/knowledge base/post chapter memory capture/knowledge candidate prepare approval/execute approval payload/execution result projection/trace audit/athena world model route；更完整导航体验待补） |

### 最近完成

- 2026-06-02: `recoveryAgentRunProjection` 的 recommended followup fallback view 新增“待确认后继/待确认工具”摘要，只展示工具名、不泄露 pending action id 或 approval contract hash；`ChatMessage` 仅在存在自动后继 `tools` 时显示“执行后继”按钮，pending-only handoff 保持人工确认路径。
- 2026-06-02: `AgentRunDrawer` 新增执行计划进度摘要，从 `run.input.tools` 或 planner 输出推导计划工具数，并按 steps 展示已执行、已完成、进行中和下一步工具；这是 T7 Agent 执行计划可视化的静态详情层进展，后续仍需补流式工具调用进度。
- 2026-06-02: `AgentRunDrawer` 执行计划卡片新增逐项计划工具状态列表，将计划工具与当前 step 顺序映射为“已完成/进行中/待执行/失败/已阻止”，让运行详情不再只能靠原始 step 列表推断工具调用进度。
- 2026-06-02: `AgentRunDrawer` 新增 Memory Tree 只读投影区，消费 `inspect_agent_memory_tree` 工具输出并展示状态、层级、返回节点、查询条件、导航模式、推荐 drilldown 和节点摘要，同时避免泄露 source_refs/source_id。
- 2026-06-02: `AgentRunDrawer` 的 Memory Tree 投影新增“展开推荐节点”只读 continuation，基于 `navigation.recommended_drilldowns` 创建 `inspect_agent_memory_tree` read plan（expand_node_id + include_ancestors + max_depth），让搜索结果可继续按需展开而无需写入审批。
- 2026-06-02: `AgentRunDrawer` 的 Memory Tree 投影新增自由搜索输入，提交后创建 `inspect_agent_memory_tree` 只读 continuation（query + include_ancestors），让用户不离开运行详情即可继续搜索分层记忆树。
- 2026-06-02: `AgentRunDrawer` 的 Memory Tree 投影新增“展开节点”只读 continuation，对返回结果中带 children 的节点创建 `inspect_agent_memory_tree` read plan（expand_node_id + include_ancestors + max_depth），让用户不依赖推荐 drilldown 也能继续浏览任意已返回分支，按钮标签仍避免泄露内部 node id。
- 2026-06-02: `projectWorkspace` 新增按项目隔离的 Memory Tree 浏览历史状态，`HermesView` 在 `inspect_agent_memory_tree` planner continuation 成功后写入清洗后的“搜索/推荐展开/节点展开”行为标签并传回 `AgentRunDrawer`；历史不显示 node id、source id 或 approval hash，关闭 Drawer 后重新打开同项目 run 仍可恢复，跨项目隔离且只保留最近 8 条。
- 2026-06-02: `HermesView` 子导航新增 Memory Tree 历史入口，读取项目级浏览历史并以安全标签展示；点击历史项会用隐藏的 runId 重新打开对应 Agent run，不在面板中显示 run id 或 node id，这是独立 Memory Tree 面板前的可导航入口层。
- 2026-06-02: `HermesView` 子导航 Memory Tree 面板改为常驻，并新增只读搜索表单；提交后创建 `inspect_agent_memory_tree` Agent run（query + include_ancestors + max_depth），打开 Drawer 展示结果，同时写入同项目安全历史标签，不显示 approval、source id 或 node id。
- 2026-06-02: `HermesView` 子导航 Memory Tree 面板新增最近结果摘要，读取当前活动 run 的最新 `inspect_agent_memory_tree` 输出，展示返回节点数、卷/章/场景/节拍概况和最多 3 条安全节点摘要；面板继续过滤 source id、node id、approval 等内部字段。
- 2026-06-02: `HermesView` 子导航 Memory Tree 最近结果中，带 `children` 的安全节点摘要可直接发起 `ui_memory_tree_panel_expand` 只读 run（expand_node_id + include_ancestors + max_depth），成功后打开新 run、写入“节点展开：...”安全历史标签，并在面板内显示“当前展开：...”状态，不暴露 node id 或 source id。
- 2026-06-02: `HermesView` 子导航 Memory Tree 最近结果改为按 `parent_id` / `children` 投影当前 run 返回节点，展示卷→章→场景→节拍层级缩进并保留全部返回节点；树行继续只显示安全标题、章节、摘要和相关度，不渲染 node id、source_refs 或 source id。
- 2026-06-02: `WorkspacePanel` 新增 `memory`，`HermesView` 子导航 Memory Tree 区可切入主区 Memory Tree 工作区；主工作区支持只读搜索、层级树结果、节点展开、当前展开状态和安全浏览历史，形成从对话/子导航到 Memory Tree 工作区的基础跨面板导航。
- 2026-06-02: `HermesView` Memory Tree 工作区中带 `chapter_index` 的结果节点新增“查看章节”深链，点击后通过 `project.loadChapter` 加载对应章节并切回正文面板；测试覆盖按钮存在、章节加载参数和离开 Memory Tree 工作区。
- 2026-06-02: `HermesView` Memory Tree 工作区结果节点新增“检索证据”深链，基于安全标题或摘要创建 `search_agent_retrieval_context` 只读 Agent run（含 `limit=8` 和可用的 `max_chapter_index`），打开 Drawer 展示 Retrieval 投影，并写入安全浏览历史；测试覆盖请求参数、Drawer 切换和不泄露 node id/source id。
- 2026-06-02: `HermesView` Memory Tree 工作区中带 `chapter_index` 的结果节点新增“汇总上下文”深链，创建 `summarize_longform_context` 只读 Agent run（chapter_index + query + max_chars + include_prompt_context），打开 Drawer 展示长篇上下文摘要结果，并写入安全浏览历史；测试覆盖请求参数、Drawer 切换和不泄露 node id/source id。
- 2026-06-02: `HermesView` Memory Tree 工作区中带 `chapter_index` 的结果节点新增“检查激活”深链，创建 `inspect_agent_memory_activation_plan` 只读 Agent run（chapter_index + query），打开 Drawer 展示写前记忆激活计划，并写入安全浏览历史；测试覆盖请求参数、Drawer 切换和不泄露 node id/source id。
- 2026-06-02: `HermesView` Memory Tree 工作区中带 `chapter_index` 的结果节点新增“检查知识库”深链，创建 `inspect_agent_knowledge_base_route` 只读 Agent run（chapter_index + query + limit），打开 Drawer 展示作者偏好/项目策略/学习规则/写法参考路由，并写入安全浏览历史；测试覆盖请求参数、Drawer 切换和不泄露 node id/source id。
- 2026-06-02: `HermesView` Memory Tree 工作区中带 `chapter_index` 的结果节点新增“规划沉淀”深链，创建 `plan_post_chapter_memory_capture` 只读 Agent run（chapter_index），打开 Drawer 展示写后记忆沉淀候选规划，并写入安全浏览历史；测试覆盖请求参数、Drawer 切换和不泄露 node id/source id。
- 2026-06-02: `AgentRunDrawer` 写后记忆沉淀候选新增“准备候选” continuation，读取候选 `next_tool_call` 创建 `prepare_record_agent_knowledge_base_candidate` 只读审批准备计划，按钮只显示清洗后的候选标题，不渲染 source_refs/source id；测试覆盖 payload、隐藏内部来源和不直接写入知识库。
- 2026-06-02: `AgentRunDrawer` 待审批写入区新增知识库候选标题投影：`prepare_record_agent_knowledge_base_candidate` run 可显示清洗后的候选标题，并通过确认按钮生成 `execute_record_agent_knowledge_base_candidate_with_approval` payload；测试覆盖候选标题、隐藏 source_refs/approval hash 和执行参数。
- 2026-06-02: `AgentRunDrawer` 新增知识库候选写入成功投影，消费 `execute_record_agent_knowledge_base_candidate_with_approval` 输出并展示候选标题、memory_type 标签、候选数量和推荐下一步工具，同时隐藏 candidate id、source_refs、approval hash 与审批验证内部字段。
- 2026-06-02: `HermesView` Memory Tree 工作区中带 `chapter_index` 的结果节点新增“审计 Trace”深链，创建 `inspect_agent_trace_audit` 只读 Agent run（chapter_index + limit），打开 Drawer 展示 Trace Audit run，并写入安全浏览历史；测试覆盖请求参数、Drawer 切换和不泄露 node id/source id。
- 2026-06-02: `HermesView` Memory Tree 工作区结果节点新增“检查世界模型”深链，基于安全标题或摘要创建 `inspect_agent_world_model_route` 只读 Agent run（subject_ref + limit，并在可用时带 chapter_index），打开 Drawer 展示 Athena 世界模型路由结果，并写入安全浏览历史；测试覆盖请求参数、Drawer 切换和不泄露 node id/source id。

### 阻塞项

- 独立 Memory Tree 面板仍需要前端交互契约：当前已有 Drawer 只读投影、自由搜索、推荐展开、节点展开、项目级会话浏览历史、Hermes Memory 主工作区、子导航搜索/历史/当前返回节点层级树/结果节点展开与当前展开状态、章节正文深链基础、Retrieval 证据只读 run 深链、Longform Context Summary 只读 run 深链、Memory Activation Plan 只读 run 深链、Knowledge Base Route 只读 run 深链、Post Chapter Memory Capture 只读 run 深链、写后记忆候选 prepare approval continuation、execute approval payload 与执行成功投影、Trace Audit 只读 run 深链，以及 Athena 世界模型路由深链；仍需补更完整树工作区能力和真实长篇数据下的可视化验证。

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
- Memory Tree 卷/章摘要持久化基础版
- 记忆激活机制
- Followup 机制完善
- 写作质量诊断
- 参考模式投影
- Reference Alignment 自然语言只读入口

当前工作分支: `codex/agent-loop-risk`

### 下一阶段预览: Agent 循环增强后续

计划内容（待确认）：
- 智能上下文压缩
- 多维度语义审稿
- Memory Tree 语义召回与 LLM 摘要质量增强
- 孤兒 Worker 写入式清理与安全重分派执行
