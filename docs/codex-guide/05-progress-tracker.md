# 05 · 进度追踪

> **最后更新**: 2026-06-06
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
- [x] 写入门禁覆盖审计：inspect_agent_write_gate_coverage 聚合写入工具的 Agent 计划审批门禁覆盖，并可在 AgentRunDrawer 展示安全摘要
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

- 2026-06-06: `inspect_agent_write_gate_coverage` 接入 `AgentRunDrawer` 安全投影，展示写入工具数、Agent 审批覆盖、确认守卫、门禁缺口、高风险直写、风险目标和推荐动作，同时不暴露 adapter/handler、gate version/type、raw write policy、confirmation_fields、indirect_coverage、trace coverage_basis 与 mutability 等内部字段。
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
- [x] Memory Tree 卷/章摘要持久化基础版：record_agent_memory_tree_summaries 写入 LongformMemory 摘要节点，直接写入口已改为 Agent 计划审批链 redirect
- [x] Memory Tree 基础浏览：inspect_agent_memory_tree 支持 expand_node_id、max_depth、include_ancestors，用于展开/收起/搜索上下文
- [x] Memory Tree 语义召回基础：query 精确匹配失败时返回 relevance score、lexical_score / local hash vector_score、embedding 元数据、matched_terms / matched_fields 和 recommended_drilldowns
- [x] Memory Tree 层级语义回流：过滤到 volume/chapter 等上层节点时，可用 scene/beat 后代强匹配回流召回父节点，并抑制低分单字噪声
- [x] Memory Tree 质量审计与复核：inspect_agent_memory_tree_quality 可只读报告节点覆盖、摘要支撑、semantic probe、诊断和推荐后续；真实 dogfood 已暴露 summary backing 与 semantic probe 缺口，隔离副本通过审批式摘要物化后复核为 ready
- [x] Memory Tree LLM 摘要计划：build_agent_memory_tree_llm_summary_plan 可只读生成章级 evidence window、Trace-required prompt contract、quality precheck/postcheck 和候选生成/检查后续；真实 dogfood 可把 `灯塔旧回声` 缺口转成 3 个来源/848 字证据窗口，不执行模型调用或写入
- [x] Memory Tree LLM 摘要候选 Trace：summarize_agent_memory_tree_llm_candidate 可复用摘要计划证据窗口，执行 `memory_tree_summary_generation` Trace，把候选摘要/关键词/开放问题/来源覆盖写入 Trace metadata 并返回候选；inspect_agent_memory_tree_llm_candidates 可按章节读回候选；临时 dogfood 副本 + fake model 已证明 trace success、候选读回、0 个章级摘要记忆写入
- [x] Memory Tree LLM 候选审批式物化：record_agent_memory_tree_llm_candidate_summary 直接写入口只返回 approval redirect；inspect_agent_memory_tree_llm_candidates 会为检查窗口内每个 ready 且未物化候选输出 prepare recommended_next_tool_calls，多个待物化 ready 候选时推荐 prepare_record_agent_memory_tree_llm_candidate_summaries_batch，并在执行后回流 pending/materialized 计数以抑制同 trace 重复 prepare；自然语言“准备第 N 章记忆树 LLM 摘要候选批量审批 limit <n>”可直达 batch prepare 只读 run；AgentRunDrawer 可安全展示多个候选摘要、物化状态并逐项触发 prepare continuation；prepare_record_agent_memory_tree_llm_candidate_summary 会把候选 trace id 与候选摘要 hash 绑定进 Agent plan approval contract，并输出 requires_confirmation=true 的 execute recommended_next_tool_calls；prepare_record_agent_memory_tree_llm_candidate_summaries_batch 可为多个候选批量生成逐条 trace-bound approval contract 与 execute 调用骨架但不写入，AgentRunDrawer 可安全展示 batch prepare 结果并逐条触发 execute-with-approval payload；execute_record_agent_memory_tree_llm_candidate_summary_with_approval 经审批、mutation fingerprint 和 resource binding 验证后只写选中的章级 LongformMemory，并返回 Memory Tree quality postcheck；execute_record_agent_memory_tree_llm_candidate_summaries_batch_with_approval 可消费 batch prepare 产出的多个单候选 execute payload，逐条复用单候选审批校验后批量物化，AgentRunDrawer 可展示安全批量写入摘要
- [x] Memory Tree 写前激活：build_memory_activation_plan 可将高 relevance Memory Tree 节点纳入 activation.memory_tree，并保留未来章节防泄漏
- [x] Memory Route 对话入口：自然语言“检查第 N 章长篇记忆路由/检索维护状态”可投影为 inspect_agent_memory_route 只读工具计划；AgentRunDrawer 独立 Panel 可展示长篇记忆/检索/维护安全摘要和诊断信息
- [x] Memory Activation Plan 对话入口：自然语言“检查第 N 章记忆激活计划：<query>”可投影为 inspect_agent_memory_activation_plan 只读工具计划；AgentRunDrawer 独立 Panel 可展示写前激活桶、覆盖债务、风险和推荐工具的安全摘要
- [x] Knowledge Base Route 对话入口：自然语言“检查第 N 章知识库路由 query=<query> limit <n>”可投影为 inspect_agent_knowledge_base_route 只读工具计划；AgentRunDrawer 独立 Panel 可展示状态、章节/query、作者偏好、学习规则、知识库候选、写法参考、推荐工具和诊断摘要
- [x] Post Chapter Memory Capture 对话入口：自然语言“规划第 N 章写后记忆沉淀”可投影为 plan_post_chapter_memory_capture 只读工具计划，Memory Tree 工作区 chapter 节点也可直接创建对应只读 run；AgentRunDrawer 独立 Panel 可展示章节可用性、审稿证据、候选标题/类型/摘要/置信度、来源覆盖和推荐工具安全摘要，Drawer 记忆闭环区保留候选 prepare action
- [x] Retrieval Context 对话入口：自然语言“检索第 N 章前的上下文证据 query=<query> limit <n>”可投影为 search_agent_retrieval_context 只读工具计划；AgentRunDrawer 可展示查询/过滤条件、返回窗口、证据条目、来源覆盖和推荐后续的安全摘要
- [x] Retrieval Strategy 只读策略规划、质量复核与主动预取计划：inspect_agent_retrieval_strategy 可按 chapter_index、query、limit、candidate_limit 与长篇维护状态选择 query-aware retrieval、章节上下文摘要或维护诊断；inspect_agent_retrieval_strategy_quality 可在同一输入上汇总策略输出、检索/维护诊断和 dogfood evidence 开放 finding，输出 ready / needs_dogfood_review / blocked 状态和后续工具建议；inspect_agent_retrieval_prefetch_plan 会把策略推荐过滤成章节生成前可执行的只读工具调用，章节生成 planner 已先调用预取计划再进入长篇上下文摘要；retrieval_worker、自然语言入口、AgentRunDrawer 检索策略/质量复核/预取计划安全投影与聊天 action descriptor 已覆盖
- [x] Longform Context Summary 对话入口：自然语言“汇总第 N 章长篇上下文 query=<query> max_chars <n>”可投影为 summarize_longform_context 只读工具计划；AgentRunDrawer 可展示章节目标、生成进度、来源覆盖、预算截断、分区条目和诊断安全摘要
- [x] 记忆激活：memory_activation.py
- [x] 知识库候选：knowledge_base_candidates + 执行；AgentRunDrawer 可从写后记忆捕获候选发起 prepare_record_agent_knowledge_base_candidate 只读审批准备 continuation，并在待审批写入区展示候选标题、触发 execute_record_agent_knowledge_base_candidate_with_approval payload；执行成功后展示候选标题、类型、数量和推荐下一步工具，并可继续发起只读 Knowledge Base Route 检查
- [x] 世界模型分析执行：world_model_analysis_execution
- [x] 世界模型路由诊断：自然语言“检查第 N 章 subject_ref 世界模型路由”可投影为 inspect_agent_world_model_route 只读工具计划
- [x] 世界模型 L5 语义一致性检查基础版：inspect_agent_world_model_semantic_check 可对已生成章节和确认世界事实窗口执行 Trace-bound LLM JSON 审查，只返回 L5 issue，不写世界事实或提案；自然语言“语义检查第 N 章世界模型 subject=<ref> max_facts <n>”可投影到该只读工具，world_model_worker、followup safe list、loop risk known poll 和 AgentRunDrawer 独立 Panel 安全投影已覆盖

### 下一步任务

| 优先级 | 任务 | 完成标准 | 状态 |
|--------|------|---------|------|
| P0 | Memory Tree 分层摘要（卷→章两级） | 能生成并持久化卷级和章级摘要节点 | ✅ 已完成（基础版） |
| P1 | Memory Tree 语义浏览 | Agent 能通过工具浏览 Tree：展开/收起/搜索 | ✅ 已完成（基础浏览） |
| P2 | 世界模型 L5 语义检查 | 至少实现一个 LLM 驱动的语义一致性检查 | ✅ 已完成（基础版：inspect_agent_world_model_semantic_check 只读 L5 Trace-bound LLM 检查 + 自然语言入口 + world_model_worker + 独立 Panel 安全投影；后续补真实 dogfood 和跨章事实链） |
| P3 | 检索策略智能化 | Agent 根据上下文自主选择检索策略 | 🟡 进行中（inspect_agent_retrieval_strategy 只读策略规划 + inspect_agent_retrieval_strategy_quality 只读 dogfood finding 质量复核 + inspect_agent_retrieval_prefetch_plan 只读主动预取计划 + 章节生成 planner 预取步骤 + 自然语言入口 + retrieval_worker 路由 + Drawer/聊天 action 安全投影；后续补 LLM/真实 strategy dogfood、更细粒度质量评估和真实预取缓存） |
| P4 | Memory Tree 语义召回/摘要质量增强 | 接入向量/LLM 摘要或真实长篇验证，不只依赖确定性摘要和文本匹配 | 🟡 进行中（层级 relevance + 本地 hash vector_score 输出 + 写前激活基础 + quality baseline + 审批式 materialize/recheck + LLM-ready summary plan + traced fake-model candidate + Trace 候选读回 + 候选 trace 绑定审批物化 + 多候选 recommended_next_tool_calls handoff + batch prepare approval handoff + batch execute 逐候选审批物化 + Drawer batch execute handoff/结果安全投影 + 执行后物化状态回流/重复 prepare 抑制 + 跨章批量候选质量回归证据；后续补真实模型质量验证/远程向量召回/真实 dogfood 批量质量复核） |

### 阻塞项

- Memory Tree 摘要质量已有真实长篇闭环证据：原始 `data/agent_native_dogfood_20260526.db` 仍报告 `memory_tree_summary_gap` 与 `memory_tree_semantic_probe_miss`，但临时副本通过 `prepare_record_agent_memory_tree_summaries` → `execute_record_agent_memory_tree_summaries_with_approval` 物化 1 个卷摘要和 3 个章摘要后，`inspect_agent_memory_tree_quality` 复核为 ready；`inspect_agent_memory_tree` 现在会在 semantic relevance 中暴露本地 hash embedding 的 `vector_score` 与 provider/model/dimensions，作为远程向量召回前的可审计信号；`build_agent_memory_tree_llm_summary_plan` 已能在原始 DB 上只读生成 Trace-required LLM 摘要计划，`summarize_agent_memory_tree_llm_candidate` 已在临时副本上用 fake model 跑通 trace/candidate 路径并保持 0 记忆写入，`inspect_agent_memory_tree_llm_candidates` 已能从 Trace metadata 读回多个候选并为每个未物化 ready trace 输出 prepare 调用对象，执行后也能回流 materialized 状态并停止重复推荐同 trace prepare；`prepare_record_agent_memory_tree_llm_candidate_summaries_batch` 已能为多个候选批量生成逐条 trace-bound approval contract 和 execute-with-approval 调用骨架，也可由自然语言直接规划成只读 batch prepare run，`execute_record_agent_memory_tree_llm_candidate_summaries_batch_with_approval` 可消费这些逐条审批 payload 并逐候选复用单条 execute 校验后批量物化；AgentRunDrawer 已能安全展示 batch prepare、逐条 execute handoff 与 batch execute 写入摘要；候选专用 prepare/execute 审批链已可将第 2 章候选写入章级 LongformMemory，prepare 输出携带 approval contract/hash 的 execute 调用对象，使 `灯塔旧回声` semantic probe 命中；本地 fake-model 批量回归已证明两个章节候选经 batch execute 后 summary-backed chapter 达到 2/2、quality diagnostics 清零，并由 `inspect_agent_dogfood_evidence` 的 `memory_tree_llm_candidate_batch_materialization_20260605` 记录。下一步应接入真实模型质量验证、远程向量召回或真实 dogfood 批量质量复核，而不是扩大直接写入口。

### 最近完成

- 2026-06-04: 新增 `inspect_agent_memory_tree_quality` 只读质量审计投影，报告 volume/chapter/scene/beat 节点覆盖、Memory Tree 摘要支撑比例、semantic probe 命中、诊断和推荐后续；`IntentRouter` / `plan_dialog_intent_agent_run` / `memory_worker` 已支持自然语言“检查第 N 章记忆树质量 query=<query>”。
- 2026-06-05: 新增 `inspect_agent_world_model_semantic_check` 只读 L5 语义一致性检查，基于已生成章节和确认世界事实窗口执行 Trace-bound LLM JSON 审查，返回 `semantic_consistency_llm` issue、Trace id、prompt contract 和推荐后续审批工具；自然语言入口、world_model_worker、followup safe list 与 loop risk known poll 已同步覆盖。
- 2026-06-05: `AgentRunDrawer` 新增 World Model Semantic Check 安全投影，消费 `inspect_agent_world_model_semantic_check` 输出并展示检查状态、章节/主体、确认事实窗口、issue 数量、摘要、证据摘录和推荐后续工具，同时隐藏 project/profile/claim/trace/prompt/evidence_refs 等内部字段；2026-06-06 已按 ADR-010 迁出为独立 Panel。
- 2026-06-05: 新增 `inspect_agent_retrieval_strategy` 只读工具和自然语言入口“规划第 N 章检索策略 query=<query> limit <n> candidate_limit <n>”；工具会根据章节/query/维护状态推荐 `search_agent_retrieval_context`、`summarize_longform_context` 或维护诊断，作为后续预取计划和质量复核的策略基线，retrieval_worker 与 AgentRunDrawer 安全投影同步覆盖。
- 2026-06-05: 新增 `inspect_agent_retrieval_strategy_quality` 只读质量复核工具和自然语言入口“复核第 N 章检索策略质量 query=<query> limit <n> candidate_limit <n>”；工具复用检索策略基线、检索/维护诊断与 `inspect_agent_dogfood_evidence` 摘要，遇到开放 finding 时返回 `needs_dogfood_review` 并合并策略与 dogfood 后续工具建议；retrieval_worker、followup safe list 与 loop risk known poll 已同步覆盖。
- 2026-06-05: 新增 `inspect_agent_retrieval_prefetch_plan` 只读主动预取计划和自然语言入口“预取第 N 章检索上下文 query=<query> limit <n> candidate_limit <n>”；工具复用检索策略基线，只保留 `search_agent_retrieval_context` / `summarize_longform_context` / `inspect_agent_memory_route` 等只读调用，章节生成 planner 已升级为先规划预取再进入长篇上下文摘要；retrieval_worker、followup safe list 与 loop risk known poll 已同步覆盖。
- 2026-06-05: `AgentRunDrawer` 与聊天 action descriptor 新增 Retrieval Strategy Quality 安全投影，消费 `inspect_agent_retrieval_strategy_quality` 输出并展示复核状态、策略、query、章节窗口、检索文档数、dogfood 覆盖、开放问题和推荐后续工具，同时隐藏 project id、trace/version、dogfood source、source_ref 与 raw recommended_next_tool_calls。
- 2026-06-05: `inspect_agent_memory_tree` 的 semantic relevance 新增本地 hash embedding 相似度信号：当 query 进入语义召回时，节点 relevance 会保留既有 score/matched_terms/matched_fields，同时输出 `lexical_score`、`vector_score` 和 `embedding{provider,model,dimensions}`，为后续远程向量召回/质量复核提供可审计基线。
- 2026-06-04: `inspect_agent_dogfood_evidence` 新增 `memory_tree_quality_projection_20260604` 证据，记录 `data/agent_native_dogfood_20260526.db` 中 3 个章节节点但 0 个 memory_tree summary-backed chapter，semantic probe `灯塔旧回声` miss，并把 `memory_tree_summary_gap` / `memory_tree_semantic_probe_miss` 作为下一步真实 dogfood finding。
- 2026-06-04: `record_agent_memory_tree_summaries` 直接写入口改为 approval redirect，新增 `prepare_record_agent_memory_tree_summaries` 与 `execute_record_agent_memory_tree_summaries_with_approval`；execute 会在审批契约、mutation fingerprint 与 resource binding 验证后物化摘要，并立即返回 `post_materialization_quality` 复核结果。
- 2026-06-04: `inspect_agent_dogfood_evidence` 新增 `memory_tree_summary_approval_recheck_20260604` 证据：在真实 dogfood DB 临时副本中，审批式物化创建 4 个摘要节点，summary-backed chapter 从 0/3 提升到 3/3，`灯塔旧回声` semantic probe 从 missing_match 变为 matched，quality diagnostics 清零。
- 2026-06-04: 新增 `build_agent_memory_tree_llm_summary_plan` 只读工具和自然语言入口“构建第 N 章记忆树 LLM 摘要计划 query=<query> max_chars <n>”，输出 evidence window、`memory_tree_summary_generation` Trace 契约、quality precheck/postcheck 和候选生成/检查后续；`inspect_agent_dogfood_evidence` 新增 `memory_tree_llm_summary_plan_20260604`，记录真实 dogfood 第 2 章可生成 3 个来源/848 字证据窗口且 side effects 为 0。
- 2026-06-04: 新增 `summarize_agent_memory_tree_llm_candidate` 只读业务工具和自然语言入口“生成第 N 章记忆树 LLM 摘要候选 query=<query> max_chars <n>”，复用 LLM 摘要计划证据窗口执行 `memory_tree_summary_generation` Trace，候选会写入 Trace metadata 并返回；新增 `inspect_agent_memory_tree_llm_candidates` 只读工具和“查看第 N 章记忆树 LLM 摘要候选 limit <n>”入口，可按章节从 Trace metadata 读回候选；`inspect_agent_dogfood_evidence` 的 `memory_tree_llm_summary_candidate_20260604` 记录真实 dogfood 临时副本 + fake model 跑出 3 个 context block、trace success、候选 ready、trace id 读回匹配且 memory_tree_chapter_summary 写入数保持 0。
- 2026-06-04: 新增 Memory Tree LLM 候选审批式物化链：`record_agent_memory_tree_llm_candidate_summary` 直接写入口保持 guarded redirect，`prepare_record_agent_memory_tree_llm_candidate_summary` 将 candidate_trace_id 与 candidate_summary_hash 绑定进 approval contract，`execute_record_agent_memory_tree_llm_candidate_summary_with_approval` 验证审批、mutation fingerprint 和 resource binding 后写入选中章级摘要并返回 quality postcheck；dogfood 临时副本证明第 2 章候选写入 1 个 LongformMemory 后 `灯塔旧回声` semantic probe matched，但整体仍因其他章节未摘要而 degraded。
- 2026-06-04: Memory Tree LLM 候选链路补齐 handoff payload：`inspect_agent_memory_tree_llm_candidates` 会为 ready 候选输出 `prepare_record_agent_memory_tree_llm_candidate_summary` recommended_next_tool_calls，`prepare_record_agent_memory_tree_llm_candidate_summary` 会输出带 approval contract/hash 且 `requires_confirmation=true` 的 `execute_record_agent_memory_tree_llm_candidate_summary_with_approval` 调用对象；descriptor schema 与单测已覆盖。
- 2026-06-05: `AgentRunDrawer` 新增 Memory Tree LLM 候选摘要安全投影，消费 `inspect_agent_memory_tree_llm_candidates` 输出并展示状态、候选/可准备计数、章节、候选摘要、salient terms、来源字数和质量预检；可从 `recommended_next_tool_calls` 触发 `prepare_record_agent_memory_tree_llm_candidate_summary` read-only continuation，同时隐藏 candidate_trace_id、scope_key 和 approval contract。
- 2026-06-05: `inspect_agent_memory_tree_llm_candidates` 的 prepare handoff 从单个最近候选扩展为检查窗口内所有 ready 候选，保持只读候选检查和逐项审批准备边界；`AgentRunDrawer` 多按钮回归覆盖第二个候选 trace 的 prepare payload，向批量候选审批物化推进一小步。
- 2026-06-05: 新增 `prepare_record_agent_memory_tree_llm_candidate_summaries_batch` 只读工具，可根据显式 candidate_trace_ids 或候选检查窗口为多个 ready 候选批量生成逐条 trace-bound approval contract 与 `execute_record_agent_memory_tree_llm_candidate_summary_with_approval` 调用骨架；工具注册、memory_worker 定义、adapter metadata 和批量准备测试已覆盖；后续已补独立 batch execute 写工具，prepare 本身仍保持只读。
- 2026-06-05: `AgentRunDrawer` 新增 Memory Tree LLM batch prepare 安全投影，消费 `prepare_record_agent_memory_tree_llm_candidate_summaries_batch` 输出并展示准备/跳过计数、章节、质量查询和执行标签；每个候选按钮触发对应 `execute_record_agent_memory_tree_llm_candidate_summary_with_approval` payload，同时隐藏 candidate_trace_id、approval hash 和 approval contract。
- 2026-06-05: `inspect_agent_memory_tree_llm_candidates` 新增候选物化状态回流，检查同 trace 是否已写入 `LongformMemory`，在 summary 中给出 pending/materialized 计数，并对已物化候选停止推荐 prepare；`prepare_record_agent_memory_tree_llm_candidate_summary` 对同 trace 重复物化返回 blocked，`AgentRunDrawer` 只显示“待物化/已物化/摘要冲突”等安全标签，不暴露 trace id、memory id 或 hash。
- 2026-06-05: Memory Tree LLM batch prepare 接入对话控制面：`IntentRouter` 新增 `memory_tree_llm_candidate_batch_prepare_intent`，自然语言“准备第 N 章记忆树 LLM 摘要候选批量审批 limit <n>”可规划到 `prepare_record_agent_memory_tree_llm_candidate_summaries_batch` direct read tool plan；同时补齐 LLM 摘要计划/候选生成/候选检查三个既有自然语言入口在 `plan_dialog_intent_agent_run` 中的 direct read 映射。
- 2026-06-05: 新增 `execute_record_agent_memory_tree_llm_candidate_summaries_batch_with_approval` 写工具，消费 batch prepare 产出的多个单候选 execute payload，逐条复用 `execute_record_agent_memory_tree_llm_candidate_summary_with_approval` 的 approval contract、mutation fingerprint 和 resource binding 校验后批量写入；Memory worker route、tool registry、write gate coverage 和 AgentRunDrawer batch execute 安全结果投影已覆盖。
- 2026-06-05: `inspect_agent_dogfood_evidence` 新增 `memory_tree_llm_candidate_batch_materialization_20260605` 能力证据，记录本地 fake-model 批量执行回归：2 个候选经 `prepare_record_agent_memory_tree_llm_candidate_summaries_batch` → `execute_record_agent_memory_tree_llm_candidate_summaries_batch_with_approval` 后成功写入 2 个章级 LongformMemory，summary-backed chapter 达到 2/2，quality diagnostics 为 0；剩余 open finding 仅保留真实模型质量尚未验证。
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
- [x] Memory Tree 质量审计意图：自然语言“检查第 N 章记忆树质量 query=<query>”可投影为 inspect_agent_memory_tree_quality 只读工具计划
- [x] Memory Tree LLM 摘要计划意图：自然语言“构建第 N 章记忆树 LLM 摘要计划 query=<query> max_chars <n>”可投影为 build_agent_memory_tree_llm_summary_plan 只读工具计划
- [x] Memory Tree LLM 摘要候选意图：自然语言“生成第 N 章记忆树 LLM 摘要候选 query=<query> max_chars <n>”可投影为 summarize_agent_memory_tree_llm_candidate 只读工具计划
- [x] Memory Tree LLM 摘要候选检查意图：自然语言“查看第 N 章记忆树 LLM 摘要候选 limit <n>”可投影为 inspect_agent_memory_tree_llm_candidates 只读工具计划
- [x] Memory Tree LLM 候选批量准备意图：自然语言“准备第 N 章记忆树 LLM 摘要候选批量审批 limit <n>”可投影为 prepare_record_agent_memory_tree_llm_candidate_summaries_batch 只读工具计划，只生成逐条审批执行骨架，不执行写入
- [x] Memory Route 只读诊断意图：自然语言“检查第3章长篇记忆路由，包含上下文摘要”可投影为 inspect_agent_memory_route 只读工具计划，Memory Route run 可在 AgentRunDrawer 独立 Panel 展示安全摘要
- [x] Memory Activation Plan 只读诊断意图：自然语言“检查第3章记忆激活计划：灯塔旧回声”可投影为 inspect_agent_memory_activation_plan 只读工具计划，Memory Activation Plan run 可在 AgentRunDrawer 独立 Panel 展示安全摘要
- [x] Knowledge Base Route 只读诊断意图：自然语言“检查第4章知识库路由 query=写法偏好 limit 9”可投影为 inspect_agent_knowledge_base_route 只读工具计划，Knowledge Base Route run 可在 AgentRunDrawer 独立 Panel 展示安全摘要
- [x] Post Chapter Memory Capture 只读规划意图：自然语言“规划第4章写后记忆沉淀”可投影为 plan_post_chapter_memory_capture 只读工具计划，Post Chapter Memory Capture run 可在 AgentRunDrawer 独立 Panel 展示安全摘要
- [x] World Model Route 只读诊断意图：自然语言“检查第2章 char.hero 世界模型路由 limit 7”可投影为 inspect_agent_world_model_route 只读工具计划，World Model Route run 可在 AgentRunDrawer 独立 Panel 展示安全摘要
- [x] World Model Semantic Check 只读 L5 意图：自然语言“语义检查第3章世界模型 subject=char.hero max_facts 6”可投影为 inspect_agent_world_model_semantic_check 只读工具计划，后端会记录模型 Trace 且不写入世界事实或提案，AgentRunDrawer 独立 Panel 可展示安全摘要且不泄露 trace/prompt/claim/evidence_refs
- [x] World Model Proposal Review 只读队列意图：自然语言“检查世界模型提案队列 limit 20”可投影为 review_world_model_proposals 只读工具计划，World Model Proposal Review run 可在 AgentRunDrawer 独立 Panel 展示安全摘要
- [x] World Model Proposal Resolution Plan 只读规划意图：自然语言“规划世界模型提案解决方案 offset 2 limit 7”可投影为 plan_world_model_proposal_resolution 只读工具计划，World Model Proposal Resolution Plan run 可在 AgentRunDrawer 独立 Panel 展示安全摘要
- [x] Retrieval Strategy / Prefetch 只读规划/复核意图：自然语言“规划第5章检索策略 query=旧灯塔回声 limit 6 candidate_limit 50”可投影为 inspect_agent_retrieval_strategy 只读工具计划，“复核第5章检索策略质量 query=旧灯塔回声 limit 6 candidate_limit 50”可投影为 inspect_agent_retrieval_strategy_quality 只读工具计划，“预取第5章检索上下文 query=旧灯塔回声 limit 6 candidate_limit 50”可投影为 inspect_agent_retrieval_prefetch_plan 只读工具计划，Retrieval Strategy run 可在 AgentRunDrawer 展示安全摘要
- [x] Retrieval Context 只读检索意图：自然语言“检索第3章前的上下文证据 query=灯塔旧回声 limit 5”可投影为 search_agent_retrieval_context 只读工具计划，Retrieval Context run 可在 AgentRunDrawer 展示安全摘要
- [x] Longform Context Summary 只读摘要意图：自然语言“汇总第3章长篇上下文 query=灯塔旧回声 max_chars 2000”可投影为 summarize_longform_context 只读工具计划，Longform Context Summary run 可在 AgentRunDrawer 展示安全摘要
- [x] ContextCompressor 只读自检意图：自然语言“检查上下文压缩/预算/窗口压力”可投影为 inspect_agent_context_compression_projection 只读工具计划，ContextCompressor Projection run 可在 AgentRunDrawer 独立 Panel 展示安全摘要
- [x] ContextCompressor dry-run payload 只读意图：自然语言“构建第3章上下文压缩 dry-run payload max_chars 2000 context_guard_failure_count 2”可投影为 build_agent_context_compression_payload 只读工具计划
- [x] preflight 上下文预算只读意图：自然语言“预检第3章上下文预算 max_context_chars 500 context_guard_failure_count 2”可投影为 preflight_writing 只读工具计划，并保留 max_context_chars / context_guard_failure_count，预算结果可在 AgentRunDrawer 独立 Panel 展示安全摘要
- [x] Worker Dispatch 只读审计意图：自然语言“检查 worker 分发/孤儿恢复”可投影为 inspect_agent_worker_dispatch 只读工具计划，AgentRunDrawer 与聊天 action descriptor 可展示分派状态、Worker/任务/问题计数、路由审计和孤儿恢复安全摘要
- [x] Agent Event Projection 只读审计意图：自然语言“检查 task-abc123 的 Agent 事件投影 limit 12”可投影为 inspect_agent_event_projection 只读工具计划，AgentRunDrawer 与聊天 action descriptor 可展示事件链安全摘要
- [x] Agent Job Projection 只读诊断意图：自然语言“检查第3章 generate_chapter failed 任务队列 limit 8”可投影为 inspect_agent_job_projection 只读工具计划，AgentRunDrawer 可展示队列、选中任务、章节占用、事件摘要和推荐工具安全摘要
- [x] Chapter Conflict Recovery 只读恢复计划意图：自然语言“规划第3章章节冲突恢复”可投影为 plan_chapter_conflict_recovery 只读工具计划，AgentRunDrawer 与聊天 action descriptor 可展示章节占用和恢复计划安全摘要
- [x] Trace Audit 只读审计意图：自然语言“检查 run trace/执行链路/失败原因”可投影为 inspect_agent_trace_audit 只读工具计划，Trace Audit run 可在 AgentRunDrawer 独立 Panel 展示安全摘要
- [x] Trace Anomaly Trends 只读审计意图：自然语言“检查第4章 Trace 异常趋势 limit 9 baseline 6”可投影为 inspect_agent_trace_anomaly_trends 只读工具计划，Trace Anomaly Trends run 可在 AgentRunDrawer 独立 Panel 展示趋势、基线、阈值信号、阈值校准和阈值固化策略安全摘要
- [x] Trace Anomaly Long Run Samples 只读采样意图：自然语言“检查第4章 Trace 异常长跑样本 limit 9”可投影为 inspect_agent_trace_anomaly_long_run_samples 只读工具计划，统计当前项目候选 run/step 样本、状态分布、entrypoint 分布和推荐 threshold review 窗口，AgentRunDrawer 独立 Panel 可展示长跑采样安全摘要且不暴露 run/step id
- [x] Trace Anomaly Threshold Review 只读复核意图：自然语言“复核第4章 Trace 异常阈值样本 limit 9 baseline 6”可投影为 inspect_agent_trace_anomaly_threshold_review 只读工具计划，基于 trends 的 calibration.policy 输出安全人工复核摘要、阈值候选和 prepare_record_agent_trace_anomaly_threshold_config 推荐调用，不执行写入；AgentRunDrawer 独立 Panel 可展示阈值复核安全摘要
- [x] Write Gate Coverage 只读审计意图：自然语言“检查写入工具的审批门禁覆盖”可投影为 inspect_agent_write_gate_coverage 只读工具计划，AgentRunDrawer 可展示写入门禁覆盖安全摘要
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
- [x] Reference Alignment 只读审计意图：自然语言“检查参考项目模式对齐/开源项目适配”可投影为 inspect_agent_reference_alignment 只读工具计划；AgentRunDrawer 与聊天 action descriptor 可展示参考项目数、模式数、决策数、能力域、适配工具、模式来源、能力域状态和推荐后续，同时隐藏 source_path/source_refs/module_paths/trace version
- [x] Dogfood Evidence 只读审计意图：自然语言“检查 dogfood pressure-test 证据覆盖”可投影为 inspect_agent_dogfood_evidence 只读工具计划，并覆盖 Trace anomaly threshold calibration/policy/config/review/long-run sample/long-run execution、Memory Tree quality/materialize recheck/LLM summary plan/LLM candidate/LLM candidate materialization 证据
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

- 2026-06-05: `plan_chapter_conflict_recovery` 新增 AgentRunDrawer 与聊天 action descriptor 安全投影，可展示计划状态、目标章节、占用状态、占用任务数、恢复状态、下一工具、计划工具数、恢复选项、任务来源/章节范围/状态和恢复选项标签，同时隐藏 task id、`next_params`、trace/version 与原始工具参数。
- 2026-06-05: `inspect_agent_event_projection` 新增 AgentRunDrawer 与聊天 action descriptor 安全投影，可展示投影状态、事件总数、后台任务/运行/工具事件计数、工具错误、事件类型、来源类型、工具名、章节、状态、错误预览和推荐后续，同时隐藏 project/selector/event/source/run/task/step/trace id、version 与 trace source。
- 2026-06-05: `inspect_agent_worker_dispatch` 新增 AgentRunDrawer 与聊天 action descriptor 安全投影，可展示分派状态、Worker/计划任务/阻塞任务/问题计数、路由审计、未路由工具、孤儿恢复计数、Worker 角色、问题码和推荐后续，同时隐藏 `definition_registry`、`task_envelopes`、run/task id、version 与原始 route/tool 参数。
- 2026-06-05: `IntentRouter` 新增 `retrieval_strategy_quality_intent`，可将“复核第5章检索策略质量 query=旧灯塔回声 limit 6 candidate_limit 50”等自然语言投影为 `inspect_retrieval_strategy_quality` action；`plan_dialog_intent_agent_run` 对该只读 action 生成无需审批的 `inspect_agent_retrieval_strategy_quality` 工具计划，并保留 chapter_index、query、limit、candidate_limit。
- 2026-06-05: `IntentRouter` 新增 `retrieval_prefetch_plan_intent`，可将“预取第5章检索上下文 query=旧灯塔回声 limit 6 candidate_limit 50”等自然语言投影为 `inspect_retrieval_prefetch_plan` action；`plan_dialog_intent_agent_run` 对该只读 action 生成无需审批的 `inspect_agent_retrieval_prefetch_plan` 工具计划，并保留 chapter_index、query、limit、candidate_limit。
- 2026-06-03: `IntentRouter` 新增 `preflight_context_budget_intent`，可将“预检第3章上下文预算 max_context_chars 500 context_guard_failure_count 2”等自然语言投影为 `preflight_context_budget` action；`plan_dialog_intent_agent_run` 对该只读 action 生成无需审批的 `preflight_writing` 工具计划，并保留 chapter_index、max_context_chars 与 context_guard_failure_count，补齐从对话到 preflight 预算 Drawer 安全摘要的直达链路。
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
- [x] Worker 分发/孤兒恢复只读入口：自然语言“检查 worker 分发/孤儿恢复”可直接规划到 inspect_agent_worker_dispatch，AgentRunDrawer 与聊天 fallback projection 可安全展示 Worker dispatch/孤儿恢复摘要
- [x] Agent Event Projection 只读入口：自然语言可直接规划到 inspect_agent_event_projection，审计后台任务、Agent run 和 step 推导出的事件流，AgentRunDrawer 与聊天 fallback projection 可安全展示事件链摘要
- [x] Agent Job Projection/章节冲突恢复只读入口：自然语言可直接规划到 inspect_agent_job_projection 和 plan_chapter_conflict_recovery，检查后台任务队列、章节占用与恢复工具计划；Agent Job Projection run 可在 AgentRunDrawer 展示队列和任务恢复安全摘要，章节冲突恢复 run 可在 AgentRunDrawer 与聊天 fallback projection 展示安全摘要

### 下一步任务

| 优先级 | 任务 | 完成标准 | 状态 |
|--------|------|---------|------|
| P1 | Worker 定义配置化 | AgentDefinition 文件格式标准化，支持 TOML/YAML | ✅ 已完成（基础版） |
| P2 | 孤兒 Worker 恢复 | Worker 失效后自动检测、清理、重新分配 | ✅ 已完成（基础闭环） |
| P3 | Worker 并行度控制 | 基于系统资源的 worker 并发限制 | 🔴 待开始 |

### 阻塞项

- 无

### 最近完成

- 2026-06-05: `inspect_agent_job_projection` 接入 AgentRunDrawer 安全投影，展示状态、队列深度、活跃/终止/返回任务数、选中任务状态/章节/范围/下一章/已完成章节/恢复能力、错误摘要、控制面缺口、命令契约、章节占用、事件摘要和推荐工具，同时不暴露 project/selector/task/run/event/trace id、version、control_plane、params、mutability 与原始恢复原因。
- 2026-06-05: `plan_chapter_conflict_recovery` 接入 AgentRunDrawer 与聊天 fallback projection，展示计划状态、目标章节、占用状态、占用任务数、恢复状态、下一工具、计划工具数、恢复选项、任务来源/章节范围/状态和恢复选项标签，同时不暴露 task id、`next_params`、trace/version 与原始工具参数。
- 2026-06-05: `inspect_agent_event_projection` 接入 AgentRunDrawer 与聊天 fallback projection，展示事件投影状态、事件总数、后台任务/运行/工具事件计数、工具错误、事件类型、来源类型、工具名、章节、状态、错误预览和推荐后续，同时不暴露 project/selector/event/source/run/task/step/trace id、version 与 trace source。
- 2026-06-05: `inspect_agent_worker_dispatch` 接入 AgentRunDrawer 与聊天 fallback projection，展示分派状态、Worker/任务/问题计数、路由审计、孤儿恢复计数、Worker 角色、问题码和推荐后续，同时不暴露 `definition_registry`、`task_envelopes`、run/task id、version 与原始 route/tool 参数。
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
- [x] 写作质量诊断：dogfood_evidence_projection，可由自然语言“检查 dogfood pressure-test 证据覆盖”直接规划到 inspect_agent_dogfood_evidence，并暴露 Trace anomaly threshold calibration/policy/config/review/long-run sample/long-run execution 覆盖，以及 Memory Tree quality 真实长篇诊断

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
- [x] Trace Audit 自然语言只读入口：自然语言“检查 run trace/执行链路/失败原因”可直接规划到 inspect_agent_trace_audit，后端可输出安全 intent_chain 摘要（意图规则、计划工具、执行匹配）、end_to_end_chain 摘要（意图→计划→执行→模型 Trace→结果消息覆盖）和 anomaly_summary 摘要（失败步骤、失败模型 Trace、缺 Trace 绑定、未执行计划、缺结果消息、截断上下文），AgentRunDrawer 独立 Panel 可展示安全摘要、intent_chain 意图链路、端到端链路、异常摘要、失败原因、推荐动作、事件链、上下文块和模型 Trace 概览
- [x] Trace Anomaly Trends / Long Run Samples / Threshold Review 自然语言只读入口：自然语言“检查第 N 章 Trace 异常趋势 limit <n> baseline <n>”可直接规划到 inspect_agent_trace_anomaly_trends；自然语言“检查第 N 章 Trace 异常长跑样本 limit <n>”可直接规划到 inspect_agent_trace_anomaly_long_run_samples；自然语言“复核第 N 章 Trace 异常阈值样本 limit <n> baseline <n>”可直接规划到 inspect_agent_trace_anomaly_threshold_review。后端可聚合最近 run 的受影响数量、严重度、问题类型、主要问题、baseline window、rate delta、项目配置化阈值、阈值信号、阈值校准建议、误报/漏报 guard、阈值固化策略，统计当前项目候选 run/step 样本，并输出安全人工复核摘要、阈值候选和 prepare 调用建议；人工复核后的阈值可通过 `prepare_record_agent_trace_anomaly_threshold_config` → `execute_record_agent_trace_anomaly_threshold_config_with_approval` 审批链写入项目配置；AgentRunDrawer 可展示趋势、长跑采样和阈值复核安全摘要、阈值来源和固化策略，三段 Trace Anomaly 已迁出为独立 Panel，并隐藏 raw run/step/trace/context/calibration/policy/config 内部字段
- [x] 基础上下文压缩：对话历史长度限制
- [x] 长篇上下文摘要：longform_context_summary
- [x] ContextCompressor 基础计划投影：context pressure 下输出头尾保护预修剪、target_max_chars 和 summarize_longform_context 工具计划
- [x] ContextCompressor Drawer 安全投影：AgentRunDrawer 可展示 inspect_agent_context_compression_projection 的状态、章节、粒度、保护策略、上下文字符/预算/使用率、截断分区、Guard 失败次数、目标预算、头尾保护计数、预修剪计数、LLM 摘要需求、推荐工具和风险摘要，并隐藏 project id、memory_provenance、trace/version、source_ref/source_type/source id 和 payload params
- [x] ContextCompressor dry-run payload：build_agent_context_compression_payload 输出头尾保护、summary 注入、pretrim evidence 和无副作用 trace，并成为 context pressure 的推荐恢复入口
- [x] ContextCompressor preflight runtime gate：preflight_writing 输出 context_compression 检查、warning issue、recommended_next_tools 和裁剪后的 payload preview；ContextGuard opened 时作为 blocker 处理
- [x] ContextCompressor 章节 prompt block 压缩：章节生成上下文构建在 longform 压力下用 dry-run compressed_context 替换原始 longform block，并在 trace metadata 记录压缩来源
- [x] ContextCompressor 持久摘要写入工具：record_agent_context_compression_summary 将 ready payload 的 compressed_context 幂等写入 LongformMemory，作为后续恢复、审计和复用工件
- [x] ContextCompressor 持久摘要自动复用：章节生成在 longform 压力下优先复用同章节同预算的 context_compression_summary，未命中再回退 dry-run payload builder
- [x] ContextCompressor preflight 持久摘要推荐链：preflight_writing 在窗口压力且 payload ready 时推荐 record_agent_context_compression_summary，并在 preview 中暴露该后续工具
- [x] ContextCompressor preflight 持久摘要复用：preflight_writing 在窗口压力下先查同章节同预算 context_compression_summary，命中时暴露脱敏 preview 并推荐 prepare_generate_chapter_execution
- [x] preflight 上下文预算 Drawer 投影：AgentRunDrawer 独立 Panel 可从 preflight_writing 的 context_compression 检查展示状态、章节、上下文字符/预算/使用率、目标预算、压缩 preview 状态、压缩字符、推荐工具和压力 issue，并隐藏 compressed_context、summary、scope_key、trace/version 与内部 suggested_params
- [x] preflight 上下文预算自然语言入口：IntentRouter 可将“预检第 N 章上下文预算 max_context_chars <n> context_guard_failure_count <n>”规划为无需审批的 preflight_writing read plan

### 下一步任务

| 优先级 | 任务 | 完成标准 | 状态 |
|--------|------|---------|------|
| P1 | 智能上下文压缩（借鉴 hermes-agent） | 预修剪 + LLM 摘要 + 头尾保护 | 🟡 进行中（preflight persistent reuse） |
| P2 | 端到端 Trace 链路 | 从用户意图→计划→工具调用→模型调用→结果的一条链 | ✅ 已完成（Trace Audit end_to_end_chain + 独立 Panel 覆盖意图→计划→执行→模型 Trace→结果消息） |
| P3 | 上下文预算管理 | 可视化 Token 使用量 + 接近上限时的警告 | 🟡 进行中（preflight intent + Drawer budget warning） |
| P4 | Trace 聚合异常检测 | 单 run 异常摘要 + 跨 run 趋势和异常统计 | ✅ 已完成（单 run anomaly_summary + 最近 run anomaly trends + baseline/threshold signals + runtime calibration/policy + long-run sample 只读采集入口 + threshold review 只读复核入口 + 项目级阈值配置读取 + approval-gated 阈值写入/维护流程 + Drawer + dogfood calibration evidence + 真实长跑样本执行证据已完成；后续只按新 dogfood 问题增量演进） |

### 阻塞项

- 无

### 最近完成

- 2026-06-05: `inspect_agent_trace_anomaly_long_run_samples` 与 `inspect_agent_trace_anomaly_threshold_review` 接入 AgentRunDrawer 安全投影，展示长跑采样状态、候选运行/最低样本/缺失样本/工具步骤/章节集合、状态分布、复核窗口、阈值复核状态、策略决策、样本窗口、已复核样本、阈值信号、阈值候选和推荐工具，同时不暴露 run/step/trace id、trace version、`recommended_next_tool_calls`、raw params、policy/config 内部字段和直接写入 reason。
- 2026-06-04: `inspect_agent_dogfood_evidence` 新增 `trace_anomaly_long_run_samples_20260604` 证据记录，source_ref 指向 `docs/archive/superpowers/notes/long-memory-agent/2026-06-04-trace-anomaly-long-run-samples-dogfood.md`，记录隔离 dogfood DB 中 14 个真实 Writing Agent run、31 个 step、12 个 dogfood entrypoint run、第 1-3 章样本覆盖，并将 `trace_anomaly_threshold_long_run_sample_execution` 从 open finding 中移除。
- 2026-06-04: 新增 `inspect_agent_trace_anomaly_long_run_samples` 只读采样投影，按当前项目和可选章节统计有 step 的 Writing Agent run 样本、状态分布、entrypoint 分布、章节集合和 threshold review 推荐窗口，不暴露 run/step id。
- 2026-06-04: `IntentRouter` / `plan_dialog_intent_agent_run` / `recovery_worker` 新增 Trace anomaly long-run sample 自然语言入口和 worker 路由；`inspect_agent_dogfood_evidence` 同步记录 long_run_sample_collection_projection / intent / worker_route 指标，当时剩余缺口收敛为真实长跑 dogfood 样本执行。
- 2026-06-04: 新增 `inspect_agent_trace_anomaly_threshold_review` 只读复核投影，复用 Trace Anomaly Trends 的 calibration.policy 输出人工复核状态、样本数、阈值候选、推荐 prepare 调用和 side_effects 空/跳过摘要，不暴露 raw run/step/trace/context。
- 2026-06-04: `IntentRouter` / `plan_dialog_intent_agent_run` / `recovery_worker` 新增 Trace anomaly threshold review 自然语言入口和 worker 路由；`inspect_agent_dogfood_evidence` 同步记录 threshold_review_projection / intent / worker_route 指标，当时剩余缺口收敛为真实长跑 dogfood 样本采集。
- 2026-06-04: 新增 `record_agent_trace_anomaly_threshold_config` direct write guard，以及 `prepare_record_agent_trace_anomaly_threshold_config` / `execute_record_agent_trace_anomaly_threshold_config_with_approval` 审批链；执行前校验 Agent plan approval contract、mutation fingerprint 和 resource binding，执行后只写 `Project.style_config.agent_trace_anomaly_thresholds` 并推荐回到 `inspect_agent_trace_anomaly_trends`。
- 2026-06-04: `inspect_agent_write_gate_coverage`、`mutation_fingerprint`、`recovery_worker` 路由和 worker definition 已纳入 Trace anomaly threshold config 写入维护链路，direct write 会显示为 approval_required_redirect，execute-with-approval 显示为 stateless Agent plan gate enforced。
- 2026-06-04: `inspect_agent_dogfood_evidence` 的 Trace anomaly threshold calibration 证据新增 threshold_config_approval_chain / write_gate / worker_route 指标，并记录 prepare/execute 审批工具已覆盖；当时剩余缺口收敛为真实长跑 dogfood 样本复核。
- 2026-06-04: `inspect_agent_trace_anomaly_trends` 新增 `Project.style_config.agent_trace_anomaly_thresholds` 项目级阈值读取，`thresholds` 会优先使用已固化配置并通过 `threshold_config` 安全投影来源；未配置项目保持内置默认阈值。
- 2026-06-04: `AgentRunDrawer` 新增 Trace Anomaly Trends 阈值来源安全投影，只展示“项目配置/内置默认/部分配置”，不渲染原始 `Project.style_config...` 路径或内部配置 key。
- 2026-06-04: `inspect_agent_dogfood_evidence` 的 Trace anomaly threshold calibration 证据新增 threshold_config_projection 与 drawer_threshold_config_projection 指标，覆盖阈值配置化应用的回归证据。
- 2026-06-03: `inspect_agent_trace_anomaly_trends` 新增 `calibration.policy` 安全投影，基于样本量、建议阈值和 false_positive/false_negative guard 输出 collect/review/keep 策略、复核样本数、是否可固化和后续工具；`AgentRunDrawer` 同步展示固化策略、决策、复核样本和固化候选，同时隐藏 policy 内部 id。
- 2026-06-03: `inspect_agent_dogfood_evidence` 的 Trace anomaly threshold calibration 证据新增 threshold_policy_projection 与 drawer_policy_projection 指标，覆盖阈值固化策略只读投影。
- 2026-06-03: `inspect_agent_trace_anomaly_trends` 新增阈值校准摘要，基于 recent/baseline 真实运行窗口输出当前信号数、建议阈值、false_negative_guard、false_positive_guard 和推荐后续工具；`AgentRunDrawer` 同步展示校准状态、样本量、建议阈值和 guard，并隐藏 project/run/step/trace/context/calibration 内部字段。
- 2026-06-03: `inspect_agent_dogfood_evidence` 的 Trace anomaly threshold calibration 证据升级到 runtime calibration 覆盖，新增 threshold_calibration_projection 与 drawer_calibration_projection 指标，并将当时 open finding 收窄为真实长跑 dogfood 样本复核。
- 2026-06-03: `inspect_agent_dogfood_evidence` 建立 Trace anomaly threshold calibration 基础证据，记录 Trace Anomaly Trends baseline/threshold regression、Drawer 投影和误报/漏报 guard 覆盖。
- 2026-06-03: `inspect_agent_trace_anomaly_trends` 新增 baseline window 与阈值信号，`baseline_limit` 默认跟随 `limit`，可从自然语言 `baseline 6` 抽取；输出最近窗口、基线窗口、affected/issue/critical rate delta、阈值配置和 `affected_run_rate_spike` / `critical_issue_rate_spike` 安全信号，不暴露 run/step/trace id。
- 2026-06-03: `AgentRunDrawer` 的 Trace Anomaly Trends 安全投影新增基线与阈值展示，显示基线运行数、基线受影响数、异常率/问题率 delta、阈值信号标题、严重度和阈值，同时隐藏 signal 内部 trace/step id。
- 2026-06-03: `inspect_agent_trace_anomaly_trends` 新增最近 run 安全异常趋势聚合，按可选 `chapter_index` 与 `limit` 汇总受影响 run、严重/警告/提示计数、问题类型计数、主要问题和推荐后续工具；`IntentRouter` / `plan_dialog_intent_agent_run` 可将“检查第4章 Trace 异常趋势 limit 9”规划为无需审批的只读工具计划，并由 `recovery_worker` 执行。
- 2026-06-03: `AgentRunDrawer` 新增 Trace Anomaly Trends 安全投影，展示趋势状态、章节、运行/受影响/问题/严重度计数、主要问题、问题类型、受影响 run 摘要和推荐下一步工具，同时隐藏 project id、run/step/trace id、context key 与原始上下文字段。
- 2026-06-03: `inspect_agent_trace_audit` 新增 `anomaly_summary` 单 run 安全异常摘要，聚合 failed/blocked step、failed model trace、缺 Trace 绑定、未执行计划工具、缺 result_message 和截断上下文；`AgentRunDrawer` 新增异常摘要展示，同时隐藏 run/step/trace/message/source id、context key 与原始上下文正文。
- 2026-06-03: `inspect_agent_trace_audit` 新增 `end_to_end_chain` 安全摘要，按 intent、planned_tools、executed_tools、model_traces、result_message 五段输出覆盖状态、计数和 result action/status；`AgentRunDrawer` 新增端到端链路展示，同时隐藏 trace/message/run/step id 和原始参数。
- 2026-06-03: `AgentRunDrawer` 的 Trace Audit 安全投影新增 `intent_chain` 意图链路摘要，展示规则、intent class、章节、planned/executed/matched 计数和计划工具状态，同时隐藏 planner source、原始 params、source_plan_id、run/step 内部 id。
- 2026-06-03: `inspect_agent_trace_audit` 新增后端 `intent_chain` 安全摘要，从 `run.input.planner` 白名单提取意图规则、intent class、章节号和计划工具，并与实际 `WritingAgentStep` 匹配输出 planned/executed/matched 计数；摘要不暴露原始 params、上下文正文或内部 id。
- 2026-06-03: `IntentRouter` / `plan_dialog_intent_agent_run` 新增 preflight 上下文预算只读入口，自然语言可直达 `preflight_writing` 并保留 `chapter_index`、`max_context_chars` 与 `context_guard_failure_count`，让预算压力检查能从对话直接进入 AgentRunDrawer 的预算安全摘要。
- 2026-06-03: `AgentRunDrawer` 新增 preflight 上下文预算安全投影，消费 `preflight_writing` 输出的 `checks.context_compression` 与脱敏 `context_compression_payload_preview`，展示状态、章节、上下文字符/预算/使用率、目标预算、压缩 preview 状态、压缩字符、推荐后续工具和 `context_compression_*` 压力 issue，同时隐藏 `compressed_context`、持久摘要正文、scope key、trace/version、`context_guard_failure_count` 与 `suggested_params` 等内部字段。
- 2026-06-03: `AgentRunDrawer` 新增 ContextCompressor Projection 安全投影，消费 `inspect_agent_context_compression_projection` 输出并展示状态、章节、粒度、保护当前章节判断、上下文字符/预算/使用率、截断分区、Guard 失败次数、目标预算、头尾保护计数、预修剪计数、LLM 摘要需求、推荐工具和风险摘要，同时隐藏 project id、memory_provenance、trace/version、source_ref/source_type/source id、`include_prompt_context` 与 `context_guard_failure_count` 等内部参数。
- 2026-06-03: `AgentRunDrawer` 新增 Trace Audit 安全投影，消费 `inspect_agent_trace_audit` 输出并展示审计状态、目标、intent_chain 意图链路、end_to_end_chain 端到端链路、步骤/Trace/事件/上下文/控制面缺口、失败摘要、推荐动作、事件链、上下文块、工具步骤和模型 Trace 概览，同时隐藏 run/step/trace/message/task/source id 与内部上下文 key。
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
- [x] AgentRunDrawer Memory Tree 投影：展示 inspect_agent_memory_tree 的状态、查询条件、导航模式、推荐展开数、节点列表和项目级会话浏览历史，并可通过自由查询、推荐 drilldown 或返回节点展开发起只读浏览 run；Hermes 已注册 Memory 主工作区，子导航常驻 Memory Tree 面板可切入工作区、直接提交只读搜索 run、按 parent/children 展示当前返回节点层级树、从结果节点发起只读展开并显示当前展开节点，也可从历史入口重新打开对应 run；工作区中带 chapter_index 的节点可跳转并加载正文章节，也可从安全节点标签发起 Retrieval 证据只读 run、Longform Context Summary 只读 run、Memory Activation Plan 只读 run、Knowledge Base Route 只读 run、Post Chapter Memory Capture 写后记忆沉淀规划 run、Trace Audit 章节审计 run 或 Athena 世界模型路由 run；Retrieval Strategy run、Retrieval Strategy Quality run、Retrieval Context run、Longform Context Summary run、Post Chapter Memory Capture run、Memory Activation Plan run、Memory Route run、Knowledge Base Route run、Trace Audit run、World Model Route run、World Model Semantic Check run、World Model Proposal Review run、World Model Proposal Resolution Plan run 与 Memory Tree LLM 候选检查 run 可展示安全摘要，其中 Memory Route、Knowledge Base Route、Post Chapter Memory Capture、World Model Route、World Model Semantic Check、World Model Proposal Review、World Model Proposal Resolution、Trace Audit 与 Memory Tree LLM 候选检查已迁出为独立 Panel；Memory Tree LLM 候选检查可为多个未物化 ready 候选逐项触发候选摘要 prepare continuation，并展示待物化/已物化安全状态，batch prepare run 可展示逐条候选执行准备并触发对应 execute-with-approval payload，batch execute run 可展示成功/阻塞计数、逐候选章节、创建/更新计数和质量标签；写后记忆捕获候选可在 Drawer 中继续准备知识库候选写入审批，并在待审批写入区显示候选标题、触发已审批执行 payload，执行成功后展示写入结果和推荐下一步工具，并可继续只读检查 Knowledge Base Route
- [x] AgentRunDrawer 投影拆分约束：ADR-010 已明确 Drawer Shell + Projection Panel + Shared Projector 架构；新增复杂投影优先拆为独立小组件和专属测试，避免继续向 7000 行级 Drawer 主文件堆叠逻辑；Write Gate Coverage、Reference Alignment、Agent Event Projection、Agent Job Projection、Chapter Conflict Recovery、Worker Dispatch、Retrieval Strategy、Retrieval Strategy Quality、Retrieval Prefetch Plan、Retrieval Context、Longform Context Summary、Context Compression、preflight Context Budget、Memory Activation、Memory Route、Knowledge Base Route、Post Chapter Memory Capture、World Model Route、World Model Semantic Check、World Model Proposal Review、World Model Proposal Resolution、Trace Audit、Trace Anomaly Trends、Trace Anomaly Long Run Samples、Trace Anomaly Threshold Review、Memory Tree LLM candidate、batch prepare 与 batch execute 安全投影已按该约束落地，Drawer 主文件已降到 3000 行级
- [x] Agent 能力纵切架构与文件规模预算：ADR-011 已明确 Capability Slice + Thin Shell + Explicit Budget，ADR-012 与 [08-实施架构框架](./08-implementation-architecture.md) 已把它提升为后续代码推进的前置框架；触碰 2000 行以上文件时原则上不得净增长，新增超过约 50 行能力逻辑应先拆能力文件或说明原因，当前已完成 Trace Anomaly 系列与 Memory Tree LLM candidate / batch prepare / batch execute 投影迁出，并已将 Memory Tree LLM、Memory Tree 只读、Post Chapter Memory Capture、Knowledge Base、recommended followup / recovery、planner preview 与 route upgrade Drawer 测试 fixture 迁入 `agentRunFixtures`；后端 `test_writing_agent_runs.py` 已开始按 API 能力拆分 revision draft / revision patch / chapter resize expand / chapter resize compress / pending world proposal guard / world model proposal review-plan / preview 切片与共享 test_support helper；后续优先按 08 继续压缩 AgentRunDrawer、AgentRunDrawer.test、test_writing_agent_runs.py、test_writing_agent_tool_executor.py 和剩余大型 fixture
- [x] AgentRunDrawer preflight 上下文预算投影：已迁出为 AgentRunPreflightContextBudgetPanel，展示 preflight_writing 的 context_compression 预算状态、使用率、压缩 preview、推荐后续和压力 issue，同时隐藏 payload/trace 内部字段
- [x] AgentRunTraceAnomalyTrendsPanel 投影：展示 inspect_agent_trace_anomaly_trends 的趋势状态、运行/受影响/问题/严重度计数、问题类型、baseline window、rate delta、阈值信号、阈值校准、误报/漏报 guard、阈值固化策略、受影响 run 摘要和推荐后续，同时隐藏 project/run/step/trace/context/signal/calibration/policy 内部字段
- [x] Athena 世界模型面板（实体 + 提案审阅）
- [x] Model Trace 抽屉
- [x] 前端请求隔离（request lane + project scope version）
- [x] Agent 诊断信息展示（dogfood evidence 等）

### 下一步任务

| 优先级 | 任务 | 完成标准 | 状态 |
|--------|------|---------|------|
| P1 | Agent 执行计划可视化 | 对话中展示当前执行计划、工具调用进度 | 🟡 进行中（Drawer per-tool progress + followup pending confirmation fallback） |
| P2 | Memory Tree 可视化 | 前端展示分层摘要树、支持浏览和搜索 | 🟡 进行中（Drawer read-only projection + free search + recommended/node drilldown + project-scoped history + Hermes Memory workspace + subnav search/history/hierarchical results/expand state + chapter/retrieval strategy drawer projection/retrieval strategy quality drawer projection/retrieval prefetch drawer projection/retrieval drawer projection/context-summary drawer projection/context-compression drawer projection/post-capture drawer projection/memory-route drawer projection/memory-activation drawer projection/Memory Tree LLM candidate independent panel + materialization status + multi-candidate prepare continuation + batch prepare independent panel + per-candidate execute handoff + batch execute independent panel/knowledge-base/trace audit independent panel/trace anomaly independent panels/world model route independent panel/world model semantic check independent panel/world proposal review independent panel/world proposal resolution independent panel；更完整树工作区能力待补） |
| P3 | 面板整合 | Athena 面板、Memory 面板、Trace 面板的统一导航 | 🟡 进行中（Memory workspace → content/reference alignment drawer projection/retrieval strategy drawer projection/retrieval strategy quality drawer projection/retrieval prefetch drawer projection/retrieval drawer projection/longform context summary drawer projection/context compression drawer projection/post chapter memory capture drawer projection/memory route drawer projection/memory activation drawer projection/Memory Tree LLM candidate independent panel prepare continuation/batch prepare independent panel/per-candidate execute handoff/batch execute independent panel/knowledge base route drawer projection/knowledge candidate prepare approval/execute approval payload/execution result projection/knowledge base route verification/trace audit independent panel/trace anomaly independent panels/world model route independent panel/world model semantic check independent panel/world proposal review independent panel/world proposal resolution independent panel；更完整导航体验待补） |

### 最近完成

- 2026-06-06: `world_model_proposal_preview_runs` 按 [08-实施架构框架](./08-implementation-architecture.md) 迁出 8 个 `preview_world_model_proposal_resolution` / plan-preview API run 回归到 `test_writing_agent_runs_world_model_proposals.py`；触碰超预算文件 `backend/tests/test_writing_agent_runs.py` 从 8541 行降到 7304 行，targeted 验证 `pytest tests/test_writing_agent_runs_world_model_proposals.py tests/test_writing_agent_runs.py -q` 通过（182 passed）；剩余风险是 apply/draft 世界模型提案决策链仍在旧巨型文件中。
- 2026-06-06: `world_model_proposal_review_plan_runs` 按 [08-实施架构框架](./08-implementation-architecture.md) 迁出 `review_world_model_proposals` 与 `plan_world_model_proposal_resolution` 的 9 个只读/阻断/串联 API run 回归到 `test_writing_agent_runs_world_model_proposals.py`，并将 `approved_generate_chapter_tool` 收敛到 `test_support/writing_agent_run_helpers.py`；触碰超预算文件 `backend/tests/test_writing_agent_runs.py` 从 8889 行降到 8541 行，targeted 验证 `pytest tests/test_writing_agent_runs_world_model_proposals.py tests/test_writing_agent_runs.py -q` 通过（182 passed）；剩余风险是 preview/apply/draft 世界模型提案决策链仍在旧巨型文件中。
- 2026-06-06: `pending_world_proposal_guard` 按 [08-实施架构框架](./08-implementation-architecture.md) 迁出 chapter resize 的 expand/compress pending world proposal 阻断回归到 `test_writing_agent_runs_chapter_resize.py`，并将 `seed_pending_world_proposal` 收敛到 `test_support/writing_agent_run_helpers.py`；触碰超预算文件 `backend/tests/test_writing_agent_runs.py` 从 9015 行降到 8889 行，targeted 验证 `pytest tests/test_writing_agent_runs_chapter_resize.py tests/test_writing_agent_runs.py -q` 通过（201 passed）；剩余风险转为 world model proposal resolution 大段回归仍在旧巨型文件中。
- 2026-06-06: `chapter_resize_compress` 按 [08-实施架构框架](./08-implementation-architecture.md) 迁出 13 个压缩章节 API run 回归到 `test_writing_agent_runs_chapter_resize.py`，并将 compress approval helper 收敛到 `test_support/writing_agent_run_helpers.py`；触碰超预算文件 `backend/tests/test_writing_agent_runs.py` 从约 9794 行降到 9015 行，targeted 验证 `pytest tests/test_writing_agent_runs_chapter_resize.py tests/test_writing_agent_runs.py -q` 通过（201 passed）；pending world proposal 阻断用例随后已由 `pending_world_proposal_guard` 切片迁出。
- 2026-06-06: 新增 [08-实施架构框架](./08-implementation-architecture.md) 与 ADR-012，将后续长期 goal 的代码推进约束为先定义 slice、文件预算、测试闭环和文档记录；超 5000/8000 行文件列为高风险/关键风险，后续触碰 `test_writing_agent_runs.py`、`test_writing_agent_tool_executor.py`、`AgentRunDrawer.test.ts`、`AgentRunDrawer.vue` 时优先拆分或止血。
- 2026-06-06: 新增 ADR-011，将后续 Agent 能力推进约束为 Capability Slice + Thin Shell + Explicit Budget：触碰超 2000 行文件时原则上不得净增长，新增复杂能力逻辑优先拆独立能力文件、专属测试、fixture 或 projector。
- 2026-06-06: `test_writing_agent_runs.py` 按 ADR-011 迁出 chapter resize 的 expand API 回归到 `test_writing_agent_runs_chapter_resize.py`，并将 expand approval helper 收敛到 `test_support/writing_agent_run_helpers.py`；旧巨型测试文件继续净删 203 行，pending world proposal 阻断用例暂留原文件，相关 210 个后端用例通过。
- 2026-06-06: `test_writing_agent_runs.py` 按 ADR-011 迁出 revision patch API 回归到 `test_writing_agent_runs_revision_patch.py`，并将 revision patch approval helper 收敛到 `test_support/writing_agent_run_helpers.py`；旧巨型测试文件继续净删 120 行，相关 210 个后端用例通过。
- 2026-06-06: `test_writing_agent_runs.py` 按 ADR-011 迁出 revision draft API 回归到 `test_writing_agent_runs_revision_draft.py`，并将长篇项目 seed 与 revision draft approval helper 收敛到 `test_support/writing_agent_run_helpers.py`；旧巨型测试文件净删 340 行，相关 210 个后端用例通过。
- 2026-06-06: `AgentRunDrawer.test.ts` 按 ADR-011 迁出 planner preview、planner approval hash 缺失和 route upgrade contract preview 的 run fixture 与 expected payload 到 `agentRunFixtures/plannerRuns.ts`；Drawer 测试主文件降到 3528 行。
- 2026-06-06: `AgentRunDrawer.test.ts` 按 ADR-011 迁出 recommended followup、recovery preview/execute 与 recommended followup chapter approval 的 run fixture 和 expected payload 到 `agentRunFixtures/followupRuns.ts`；Drawer 测试主文件降到 3639 行。
- 2026-06-06: `AgentRunDrawer.test.ts` 按 ADR-011 迁出 Post Chapter Memory Capture、Knowledge Base candidate prepare/execute/route continuation 与 Knowledge Base Route 的 run fixture 和 expected payload 到 `agentRunFixtures/knowledgeBaseRuns.ts`；Drawer 测试主文件降到 3988 行。
- 2026-06-06: `AgentRunDrawer.test.ts` 按 ADR-011 迁出 Memory Tree 只读投影、推荐展开、节点展开、浏览历史和自由搜索的 run fixture 与 expected payload 到 `agentRunFixtures/memoryTreeRuns.ts`；Drawer 测试主文件降到 4428 行，继续减少超预算测试文件的内联数据。
- 2026-06-06: `AgentRunDrawer.test.ts` 按 ADR-011 迁出 Memory Tree LLM candidate / batch prepare / batch execute 的大型 run fixture 和 expected payload 到 `agentRunFixtures/memoryTreeLlmRuns.ts`；Drawer 测试主文件降到 4900 行级，后续继续拆剩余跨能力 fixture。
- 2026-06-06: `inspect_agent_memory_tree_llm_candidates` 安全候选投影按 ADR-011 从 `AgentRunDrawer` 主文件迁出为 `AgentRunMemoryTreeLlmCandidatePanel`，新增专属脱敏测试覆盖 trace、scope_key、candidate_trace_id 和 approval contract 内部字段隐藏；Drawer 集成测试收窄为 prepare payload 转发验证，主文件降到 3000 行级。
- 2026-06-06: `prepare_record_agent_memory_tree_llm_candidate_summaries_batch` 安全准备投影按 ADR-011 从 `AgentRunDrawer` 主文件迁出为 `AgentRunMemoryTreeLlmCandidateBatchPreparePanel`，新增专属脱敏测试覆盖 candidate trace、approval hash 和 approval contract 内部字段隐藏；Drawer 集成测试收窄为 execute payload 转发验证，主文件降到 3100 行级。
- 2026-06-06: `execute_record_agent_memory_tree_llm_candidate_summaries_batch_with_approval` 安全结果投影按 ADR-011 从 `AgentRunDrawer` 主文件迁出为 `AgentRunMemoryTreeLlmCandidateBatchExecutePanel`，新增专属脱敏测试覆盖 candidate trace、approval、resource binding 和 memory id 内部字段隐藏；Drawer 集成测试收窄为面板挂载验证，主文件降到 3200 行级。
- 2026-06-06: `inspect_agent_trace_anomaly_long_run_samples` 与 `inspect_agent_trace_anomaly_threshold_review` 安全投影按 ADR-011 从 `AgentRunDrawer` 主文件迁出为独立 Panel，新增专属脱敏测试覆盖 run/step/trace/version/entrypoint/recommended_next_tool_calls/params/mutability/policy/config 内部字段隐藏；Drawer 集成测试收窄为面板挂载验证，主文件降到 3300 行级。
- 2026-06-06: `inspect_agent_trace_anomaly_trends` 安全投影按 ADR-011 从 `AgentRunDrawer` 主文件迁出为 `AgentRunTraceAnomalyTrendsPanel`，新增专属脱敏测试覆盖 run/step/trace/project/context/signal/calibration/policy/config 内部字段隐藏；Drawer 集成测试收窄为面板挂载验证，主文件降到 3600 行级。
- 2026-06-06: `inspect_agent_trace_audit` 安全投影按 ADR-010 从 `AgentRunDrawer` 主文件迁出为 `AgentRunTraceAuditPanel`，新增专属脱敏测试覆盖 run/step/trace/message/task/target/context key、planner source、source_plan_id、raw params 和上下文正文隐藏；Drawer 集成测试收窄为面板挂载验证，主文件降到 4100 行级，Drawer 测试移除重复 Trace Audit 细节断言后降到 5600 行级。
- 2026-06-06: `plan_world_model_proposal_resolution` 安全投影按 ADR-010 从 `AgentRunDrawer` 主文件迁出为 `AgentRunWorldModelProposalResolutionPanel`，新增专属脱敏测试覆盖 project/profile/cluster/item/bundle id、profile_version、item_ids、bundle_ids、allowed_actions、plan_only 与 report_only 隐藏；Drawer 集成测试收窄为面板挂载验证，主文件降到 4700 行级。
- 2026-06-06: `review_world_model_proposals` 安全投影按 ADR-010 从 `AgentRunDrawer` 主文件迁出为 `AgentRunWorldModelProposalReviewPanel`，新增专属脱敏测试覆盖 project/profile/cluster/item/bundle id、profile_version、item_ids、bundle_ids 与 report_only 隐藏；Drawer 集成测试收窄为面板挂载验证，主文件降到 4900 行以下。
- 2026-06-06: `inspect_agent_world_model_semantic_check` 安全投影按 ADR-010 从 `AgentRunDrawer` 主文件迁出为 `AgentRunWorldModelSemanticCheckPanel`，新增专属脱敏测试覆盖 project/profile/claim/trace id、prompt contract、template hash、raw prompt、evidence_refs 与 world_profile 内部引用隐藏；Drawer 集成测试收窄为面板挂载验证，主文件约 5020 行，后续继续拆 World Model Proposal 与 Trace 类投影。
- 2026-06-06: `plan_post_chapter_memory_capture` 安全投影按 ADR-010 从 `AgentRunDrawer` 主文件迁出为 `AgentRunPostChapterMemoryPanel`，新增专属脱敏测试覆盖 project/chapter/review step id、source_ref/source_refs/source_type、memory_provenance、next_tool_call、target_type 和 tool/provenance version 隐藏；Drawer 集成测试收窄为面板挂载验证，记忆闭环区仍保留候选 prepare action。
- 2026-06-06: `inspect_agent_knowledge_base_route` 安全投影按 ADR-010 从 `AgentRunDrawer` 主文件迁出为 `AgentRunKnowledgeBaseRoutePanel`，新增专属脱敏测试覆盖 PromptRule id/source_ref、candidate id/source_refs、chapter_content source、Project.style_config 与 FewShotExampleLibrary 隐藏；Drawer 集成测试收窄为面板挂载验证，主文件降到 5200 行以下。
- 2026-06-06: `inspect_agent_memory_route` 安全投影按 ADR-010 从 `AgentRunDrawer` 主文件迁出为 `AgentRunMemoryRoutePanel`，新增专属脱敏测试覆盖 project id、memory_provenance sources/windows/trace、source_ref/source_type、provenance/route version、Athena/world_model 与 longform_memory_retrieval_and_maintenance_diagnostics 隐藏；Drawer 集成测试收窄为面板挂载验证。
- 2026-06-06: `inspect_agent_memory_activation_plan` 安全投影按 ADR-010 从 `AgentRunDrawer` 主文件迁出为 `AgentRunMemoryActivationPanel`，新增专属脱敏测试覆盖 project/memory/candidate/world/node id、source_ref/source_refs/source_type、prompt_block、provenance/trace version、future_leak_guard 和 prompt-only raw context 隐藏；Drawer 集成测试收窄为面板挂载验证，主文件仅保留记忆闭环摘要所需的激活状态、长篇记忆计数和知识库计数。
- 2026-06-06: `inspect_agent_world_model_route` 安全投影按 ADR-010 从 `AgentRunDrawer` 主文件迁出为 `AgentRunWorldModelRoutePanel`，新增专属脱敏测试覆盖 project/profile/fact/claim/cluster/item/bundle id、evidence_refs、trace source/version 与 world_profile 内部引用隐藏；Drawer 集成测试收窄为面板挂载验证，主文件约 5130 行，后续继续拆 World Model Semantic/Proposal 与 Trace 类投影。
- 2026-06-06: `preflight_writing` 上下文预算安全投影按 ADR-010 从 `AgentRunDrawer` 主文件迁出为 `AgentRunPreflightContextBudgetPanel`，新增专属脱敏测试覆盖 compressed_context、持久摘要正文、scope_key、trace/version、suggested_params、context_guard_failure_count 和 preview 内部来源隐藏；`AgentRunDrawer` 集成测试收窄为面板挂载验证，并把上下文压缩状态/严重度/脱敏 helper 收敛到 `agentRunProjection/contextCompressionProjection`。
- 2026-06-06: `inspect_agent_context_compression_projection` 安全投影按 ADR-010 从 `AgentRunDrawer` 主文件迁出为 `AgentRunContextCompressionPanel`，新增专属脱敏测试覆盖 project/memory/source id、source_ref/source_type、memory_provenance、projection version、runtime behavior flag、include_prompt_context、context_guard_failure_count 与 raw compressed context 隐藏；Drawer 集成测试收窄为面板挂载验证，随后 preflight 上下文预算投影也已独立迁出。
- 2026-06-06: `summarize_longform_context` 安全投影按 ADR-010 从 `AgentRunDrawer` 主文件迁出为 `AgentRunLongformContextPanel`，新增专属脱敏测试覆盖 project/memory/source id、scope key、source_ref/source_type、source_sections、source_section_keys、longform_context_package、provenance/summary version、Athena boundary 和 raw prompt context 隐藏；Drawer 集成测试收窄为面板挂载验证。
- 2026-06-06: `search_agent_retrieval_context` 安全投影按 ADR-010 从 `AgentRunDrawer` 主文件迁出为 `AgentRunRetrievalContextPanel`，新增专属脱敏测试覆盖 project/source/retrieval id、source_ref/source_type 原始字段、retrieval debug、memory_provenance、retrieval_items 和 projection version 隐藏；Drawer 集成测试收窄为面板挂载验证，记忆闭环摘要只保留返回数、首条安全来源和推荐工具。
- 2026-06-06: `inspect_agent_retrieval_prefetch_plan` 安全投影按 ADR-010 从 `AgentRunDrawer` 主文件迁出为 `AgentRunRetrievalPrefetchPanel`，新增专属脱敏测试覆盖 project id、recommended_next_tool_calls、tool_calls、strategy/prefetch/recommended source_ref 和 projection version 隐藏；Drawer 集成测试收窄为面板挂载验证，主文件继续向 6500 行以下收敛。
- 2026-06-06: `inspect_agent_retrieval_strategy_quality` 安全投影按 ADR-010 从 `AgentRunDrawer` 主文件迁出为 `AgentRunRetrievalStrategyQualityPanel`，新增专属脱敏测试覆盖 project id、recommended_next_tool_calls、source_ref、dogfood source、diagnostics internal message 和 projection version 隐藏；Drawer 集成测试收窄为面板挂载验证，主文件继续下降到 6600 行以下。
- 2026-06-06: `inspect_agent_retrieval_strategy` 安全投影按 ADR-010 从 `AgentRunDrawer` 主文件迁出为 `AgentRunRetrievalStrategyPanel`，新增专属脱敏测试覆盖 project id、recommended_next_tool_calls、source_ref 和 projection version 隐藏；Drawer 集成测试收窄为面板挂载验证，主文件继续下降到 6700 行以下。
- 2026-06-06: `inspect_agent_worker_dispatch` 安全投影按 ADR-010 从 `AgentRunDrawer` 主文件迁出为 `AgentRunWorkerDispatchPanel`，新增专属脱敏测试覆盖 run/task/background task id、projection version、definition registry、task_envelopes、secret params 和 route internals 隐藏；Drawer 集成测试收窄为面板挂载验证，主文件继续下降到 6800 行以下。
- 2026-06-06: `inspect_agent_job_projection` 与 `plan_chapter_conflict_recovery` 安全投影按 ADR-010 从 `AgentRunDrawer` 主文件迁出为 `AgentRunJobProjectionPanel` / `AgentRunChapterConflictRecoveryPanel`，新增专属脱敏测试覆盖 task/run/event/trace id、projection version、control plane、selector、params 和 recovery internals 隐藏；Drawer 集成测试收窄为面板挂载验证，主文件降到 7000 行以下。
- 2026-06-06: `inspect_agent_event_projection` 安全投影按 ADR-010 从 `AgentRunDrawer` 主文件迁出为 `AgentRunEventProjectionPanel`，新增专属脱敏测试覆盖 project/task/run/step/trace id、projection version、trace source 和 selector 隐藏；Drawer 集成测试收窄为面板挂载验证，主文件降到 7000 行以下。
- 2026-06-06: `inspect_agent_reference_alignment` 安全投影按 ADR-010 从 `AgentRunDrawer` 主文件迁出为 `AgentRunReferenceAlignmentPanel`，新增专属脱敏测试覆盖 source_path/source_refs/module_paths/trace version/pattern id 隐藏；Drawer 集成测试收窄为面板挂载验证，并新增 `agentRunProjection/safeProjection` 共享安全取值 helper。
- 2026-06-06: `AgentRunDrawer` 新增 Write Gate Coverage 安全投影，并拆出 `AgentRunWriteGateCoveragePanel` 与专属测试；ADR-010 已记录 Drawer Shell + Projection Panel + Shared Projector 架构，Drawer 主文件只保留工具输出定位和组件挂载，后续新增复杂投影应延续小组件拆分，避免继续扩大巨型文件。
- 2026-06-05: `AgentRunDrawer` 与聊天 action descriptor 新增 Reference Alignment 安全投影，消费 `inspect_agent_reference_alignment` 输出并展示参考项目数、模式数、决策数、能力域、适配工具、模式来源、applied patterns、能力域状态和推荐后续工具，同时隐藏 source_path、source_refs、module_paths、pattern_id 和 trace/version 等内部定位字段。
- 2026-06-05: `AgentRunDrawer` 与聊天 action descriptor 新增 Retrieval Prefetch Plan 安全投影，消费 `inspect_agent_retrieval_prefetch_plan` 输出并展示预取状态、模式、策略名、query、目标章节、章节窗口、只读工具数、检索文档数和推荐后续工具，同时隐藏 project id、trace/version、raw tool_calls、recommended_next_tool_calls 和 source_ref 等内部字段。
- 2026-06-05: `AgentRunDrawer` 新增 Retrieval Strategy Quality 安全投影，消费 `inspect_agent_retrieval_strategy_quality` 输出并展示质量状态、策略名、query、章节窗口、检索文档数、Dogfood ready/evidence 覆盖、开放问题和推荐后续工具，同时隐藏 project id、trace/version、dogfood source、source_ref、recommended_next_tool_calls 和诊断内部消息；聊天 action descriptor 也可生成不泄露 dogfood/raw call 的检索策略质量摘要。
- 2026-06-05: `AgentRunDrawer` 新增 Retrieval Strategy 安全投影，消费 `inspect_agent_retrieval_strategy` 输出并展示策略状态、策略名、query、章节窗口、limit/candidate_limit 和推荐后续工具，同时隐藏 project id、recommended_next_tool_calls、trace/version 和 source_ref 等内部字段；聊天 action descriptor 也可生成不泄露 raw call 的检索策略摘要。
- 2026-06-05: `AgentRunDrawer` 新增 Memory Tree LLM 候选摘要安全投影，消费 `inspect_agent_memory_tree_llm_candidates` 输出并展示候选/可准备/已物化计数、章节、摘要、salient terms、来源字数、质量预检和物化状态；按钮读取 `recommended_next_tool_calls` 创建 `prepare_record_agent_memory_tree_llm_candidate_summary` read-only continuation，现已覆盖多个未物化 ready 候选的逐项 prepare payload，并隐藏 candidate_trace_id / scope_key / approval contract / memory id / hash；batch prepare 输出也可在 Drawer 中安全展示，并逐条触发 execute-with-approval payload。
- 2026-06-03: `AgentRunDrawer` 新增 Trace Anomaly Trends 阈值固化策略安全投影，展示 policy 状态、决策、复核样本和固化候选，同时隐藏 policy run/trace/step 内部字段。
- 2026-06-03: `AgentRunDrawer` 新增 Trace Anomaly Trends 阈值校准安全投影，展示校准状态、recent/baseline 样本量、当前信号数、建议异常/严重阈值和误报/漏报 guard，同时隐藏 calibration project/run/step/trace/context 内部字段。
- 2026-06-03: `AgentRunDrawer` 新增 Trace Anomaly Trends 基线与阈值安全投影，展示 baseline window、异常率/问题率 delta、阈值信号和推荐后续工具，同时隐藏 project id、run/step/trace id、context key、signal 内部 id 和原始上下文字段。
- 2026-06-03: `AgentRunDrawer` 新增 Trace Anomaly Trends 安全投影，消费 `inspect_agent_trace_anomaly_trends` 输出并展示趋势状态、章节、运行/受影响/问题/严重度计数、主要问题、问题类型、受影响 run 摘要和推荐后续工具，同时隐藏 project id、run/step/trace id、context key 和原始上下文字段。
- 2026-06-03: `AgentRunDrawer` 的 Trace Audit 安全投影新增 `anomaly_summary` 异常摘要区，展示单 run 的问题数、严重/警告/提示计数、失败步骤、失败 Trace、缺 Trace、未执行计划、缺结果消息、截断上下文和最多 8 条安全问题摘要，同时隐藏 run/step/trace/message/source id、context key 和上下文正文。
- 2026-06-03: `AgentRunDrawer` 新增 preflight 上下文预算安全投影，消费 `preflight_writing` 输出的 context_compression 检查和脱敏 preview，展示预算压力、目标预算、压缩字符、推荐工具和压力 issue，同时隐藏压缩正文、持久摘要正文、scope key、trace/version 与内部 suggested params。
- 2026-06-03: `AgentRunDrawer` 新增 ContextCompressor Projection 安全投影，消费 `inspect_agent_context_compression_projection` 输出并展示状态、章节、粒度、保护策略、上下文字符/预算/使用率、截断分区、Guard 失败次数、目标预算、头尾保护计数、预修剪计数、LLM 摘要需求、推荐工具和风险摘要，同时隐藏 project id、memory_provenance、trace/version、source_ref/source_type/source id 和 payload params。
- 2026-06-03: `AgentRunDrawer` 新增 World Model Proposal Resolution Plan 安全投影，消费 `plan_world_model_proposal_resolution` 输出并展示计划状态、人工确认需求、自动应用判断、生成阻断判断、返回/总待审数量、高优先级步骤数、批量步骤数、风险计数、审阅模式计数、推荐动作/后续工具和最多 5 条安全步骤摘要，同时隐藏 project/profile/cluster/item/bundle id、profile_version、item_ids、bundle_ids、allowed_actions、plan_only 和 report_only 内部字段。
- 2026-06-03: `AgentRunDrawer` 新增 World Model Proposal Review 安全投影，消费 `review_world_model_proposals` 输出并展示队列状态、生成阻断判断、返回/总待审数量、分页状态、风险计数、审阅模式计数、推荐动作和最多若干提案簇摘要，同时隐藏 project/profile/cluster/item/bundle id、profile_version、item_ids、bundle_ids 和 report_only 内部字段。
- 2026-06-03: `AgentRunDrawer` 新增 Post Chapter Memory Capture 安全投影，消费 `plan_post_chapter_memory_capture` 输出并展示状态、章节、沉淀状态、章节可用性、候选数、审稿证据数、来源覆盖、推荐工具和最多 5 条候选标题/类型/摘要/置信度，同时隐藏 project/chapter/review step id、source_ref/source_refs/source_type、memory_provenance、next_tool_call、target_type 和 tool/provenance version。
- 2026-06-03: `AgentRunDrawer` 新增 Retrieval Context 安全投影，消费 `search_agent_retrieval_context` 输出并展示状态、query、limit/candidate_limit/max_chapter_index/source_type 过滤、返回窗口、来源覆盖、推荐后续工具和最多 5 条证据摘要，同时隐藏 project/source/retrieval id、source_ref/source_type 原始字段、retrieval 原始调试信息、memory_provenance、窗口 key 和 provenance/tool version。
- 2026-06-03: `AgentRunDrawer` 新增 Longform Context Summary 安全投影，消费 `summarize_longform_context` 输出并展示状态、章节、目标、生成判断、生成进度、上下文字符/预算、来源覆盖、目标大纲、推荐动作、分区条目和诊断信息，同时隐藏 project/memory/source id、source_ref/source_type、source_sections/source_section_keys、longform_context_package、provenance/summary version、Athena 边界和 raw prompt context。
- 2026-06-03: `AgentRunDrawer` 新增 Memory Activation Plan 安全投影，消费 `inspect_agent_memory_activation_plan` 输出并展示状态、章节/query、长篇记忆/伏笔/Memory Tree/世界模型/知识库/风格激活数、来源覆盖、覆盖债务、推荐工具、激活摘要和风险信息，同时隐藏 project id、memory/proposal/candidate/node id、source_ref/source_refs/source_type、prompt_block、trace version 和 future leak guard 内部字段。
- 2026-06-03: `AgentRunDrawer` 新增 Memory Route 安全投影，消费 `inspect_agent_memory_route` 输出并展示路线状态、章节/query、长篇记忆覆盖、检索覆盖、维护状态、来源覆盖、推荐工具和诊断信息，同时隐藏 project id、memory_provenance.sources/windows/trace、source_ref/source_type、provenance version 与 Athena/world_model 内部边界。
- 2026-06-03: `AgentRunDrawer` 新增 World Model Route 安全投影，消费 `inspect_agent_world_model_route` 输出并展示状态、章节/subject_ref、确认事实窗口、待审提案压力、风险计数、推荐动作、事实摘要、提案簇和诊断信息，同时隐藏 project/profile/fact/claim/cluster/item/bundle id、evidence_refs 和 trace source/version。
- 2026-06-03: `AgentRunDrawer` 新增 Trace Audit 安全投影，消费 `inspect_agent_trace_audit` 输出并展示审计状态、intent_chain 意图链路、end_to_end_chain 端到端链路、失败摘要、推荐动作、事件链、上下文块、工具步骤和模型 Trace 概览，同时隐藏 run/step/trace/message/task/source id 与内部上下文 key。
- 2026-06-03: `AgentRunDrawer` 新增 Knowledge Base Route 安全投影，消费 `inspect_agent_knowledge_base_route` 输出并展示状态、章节/query、作者偏好数、学习规则窗口、知识库候选窗口、写法参考数、推荐工具、候选摘要、学习规则摘要和诊断信息，同时隐藏 PromptRule id、candidate id、source_ref/source_refs、Project.style_config 与 FewShotExampleLibrary 内部来源。
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
- 2026-06-02: `AgentRunDrawer` 知识库候选写入成功投影新增只读后续检查按钮，基于 `inspect_agent_knowledge_base_route` 推荐工具生成 continuation（title query + 可用 chapter_index + limit），可验证写入结果且不显示 candidate id、source_refs 或 approval hash。
- 2026-06-02: `HermesView` Memory Tree 工作区中带 `chapter_index` 的结果节点新增“审计 Trace”深链，创建 `inspect_agent_trace_audit` 只读 Agent run（chapter_index + limit），打开 Drawer 展示 Trace Audit run，并写入安全浏览历史；测试覆盖请求参数、Drawer 切换和不泄露 node id/source id。
- 2026-06-02: `HermesView` Memory Tree 工作区结果节点新增“检查世界模型”深链，基于安全标题或摘要创建 `inspect_agent_world_model_route` 只读 Agent run（subject_ref + limit，并在可用时带 chapter_index），打开 Drawer 展示 Athena 世界模型路由结果，并写入安全浏览历史；测试覆盖请求参数、Drawer 切换和不泄露 node id/source id。

### 阻塞项

- 独立 Memory Tree 面板仍需要前端交互契约：当前已有 Drawer 只读投影、自由搜索、推荐展开、节点展开、项目级会话浏览历史、Hermes Memory 主工作区、子导航搜索/历史/当前返回节点层级树/结果节点展开与当前展开状态、章节正文深链基础、Retrieval 证据只读 run 深链与 Drawer 安全摘要、Longform Context Summary 只读 run 深链与 Drawer 安全摘要、Post Chapter Memory Capture 独立 Panel 安全摘要、Memory Activation Plan 只读 run 深链与 Drawer 安全摘要、Memory Route 独立 Panel 安全摘要、Knowledge Base Route 独立 Panel 安全摘要、写后记忆候选 prepare approval continuation、execute approval payload、执行成功投影与写入后 Knowledge Base Route 只读检查、Trace Audit 独立 Panel 安全摘要、Athena 世界模型路由深链与独立 Panel 安全摘要、World Model Proposal Review 独立 Panel 安全摘要，以及 World Model Proposal Resolution Plan 独立 Panel 安全摘要；仍需补更完整树工作区能力和真实长篇数据下的可视化验证。

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
