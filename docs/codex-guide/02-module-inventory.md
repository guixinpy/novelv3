# 02 · 模块清单与状态

> **最后更新**: 2026-06-06
> **版本**: v1.0
> **用途**: 快速了解任何模块的当前状态、目标状态和关键文件路径

---

## 使用说明

每个模块按以下格式描述：

```
模块名
├── 当前状态：[L0-L5] 简短描述
├── 目标状态：[L0-L5] 目标描述
├── 关键文件：核心代码路径
├── Agent 化缺口：距离目标还缺什么
└── 关联模块：与其他模块的依赖关系
```

Agent 化成熟度等级定义见 [01-愿景与架构目标](./01-vision.md#四agent-化成熟度模型)。

---

## 一、核心 Agent 模块

### 1.1 Writing Agent（Agent 核心编排层）

```
当前状态：L2-L3 对话意图→计划→工具执行链路已打通，支持设定/大纲/正文生成/审稿/恢复
目标状态：L3 完整的 LLM 驱动编排，自主推理+工具选择+错误恢复
关键文件：
  backend/app/services/writing_agent/
  ├── planner.py                          # 写作计划生成主入口
  ├── dialog_intent_planner.py            # 对话意图 → Agent 计划
  ├── run_service.py                      # Agent 运行服务
  ├── tool_registry.py                    # 工具注册中心
  ├── tool_executor.py                    # 工具执行器
  ├── tool_policy.py                      # 工具策略（权限/循环检测）
  ├── tool_contracts.py                   # 工具契约快照与迁移差距
  ├── tool_lifecycle_hooks.py             # 工具生命周期钩子
  ├── tool_recommendations.py             # 工具推荐
  ├── reference_pattern_projection.py      # 三参考项目模式映射与采纳建议
  ├── dogfood_evidence_projection.py       # 真实长篇 dogfood / pressure-test 证据覆盖投影
  ├── agent_loop_risk.py                  # 循环风险检测
  ├── agent_stop_hooks.py                 # 停止条件策略层
  ├── agent_health_projection.py          # Agent 健康自检投影
  ├── agent_control_plane_readiness.py    # 控制面就绪度自检
  ├── agent_memory_route.py               # 长篇记忆/检索维护路由诊断
  ├── memory_activation.py                # 写前长记忆激活计划
  ├── agent_step_binding.py               # Agent step 绑定
  ├── agent_command_catalog.py            # 命令目录
  ├── agent_command_contracts.py          # 命令契约
  ├── agent_tool_surface_policy.py        # 工具暴露策略
  ├── agent_worker_dispatch.py            # Worker 分发
  ├── agent_worker_recovery.py            # Worker 孤兒恢复审计 + 确认式写入清理
  ├── agent_definitions.py                # Agent 定义加载
  ├── agent_definitions/                  # Agent 定义文件目录
  ├── approval_contract.py                # 审批契约
  ├── mutation_fingerprint.py             # 写入工具稳定变更指纹
  ├── approval_tool_metadata.py           # 审批工具元数据
  ├── approval_verification_event.py      # 审批验证事件
  ├── write_gate_coverage.py              # 写入工具审批门禁覆盖审计
  ├── recovery_planner.py                 # 恢复计划器
  ├── recovery_policy.py                  # 恢复策略
  ├── slash_command_route.py              # 斜杠命令路由、统一 dialog route 与 route preference 投影
  ├── worker_route_registry_projection.py # Worker 路由注册投影
  ├── ...（大量工具 descriptor/adapter/execution）...
  └── agent_definitions.py
Agent 化缺口：
  - 五级循环检测已具备 generic_repeat、ping-pong、unknown_tool_repeat、known_poll_no_progress、global_circuit_breaker
  - StopHooks 已具备 critical loop、BudgetCap、MaxTurns、ContextGuard、approval、memory provenance 策略；后续可继续扩展为真正的运行中断控制点
  - Agent loop budget 已具备 read 工具 refund 投影（used/charged/refunded/remaining iterations）
  - 工具契约快照已有只读审计和自然语言只读入口，可直接检查工具契约覆盖率和迁移差距
  - Reference Alignment 已有只读审计、自然语言只读入口、AgentRunDrawer 安全投影和聊天 action descriptor，可直接检查参考项目模式对齐、已采纳决策、能力域覆盖和下一步适配建议，同时隐藏 source_path/source_refs/module_paths/trace version 等内部定位字段
  - Dogfood Evidence 已有只读审计和自然语言只读入口，可直接检查真实长篇 dogfood / pressure-test 证据覆盖，并纳入 Trace anomaly threshold calibration/policy/config/review/long-run execution/approval-chain 与 Memory Tree LLM candidate batch materialization 证据
  - Route Preference 已有只读审计和自然语言只读入口，可直接检查 text_intent/slash_command/button_action 路由偏好和 Agent 审批链迁移建议
  - Route Approval Opt-in / Pending Action approval opt-in 已有只读规划、应用预览、契约生成和 Agent plan approval prepare 自然语言入口；prepare 输出会携带仍需确认的 execute-with-approval 调用骨架，推荐规范化、followup planner 与对话 action_result_view 会保留/展示该 pending confirmation handoff，可直接检查 pending_action 迁入 Agent 审批链的 plan/preview/contract/prepare/execute handoff
  - 命令契约快照已有只读审计和自然语言只读入口，可直接检查 slash command 投影、依赖工具和缺口
  - Slash Command Route 已有只读审计和自然语言只读入口，可直接检查 `/continue` 等斜杠命令到 Agent 工具的路由投影
  - Dialog Route Projection 已有只读审计和自然语言只读入口，可直接检查 text_intent/button_action/slash_command 的统一对话路由投影
  - Intent Projection 已有只读审计和自然语言只读入口，可直接检查指定自然语言输入经 IntentRouter 的规则匹配投影
  - Memory Route 已有只读诊断、自然语言只读入口和 Drawer 安全投影，可直接检查长篇记忆、检索索引、维护状态与上下文摘要路由
  - Memory Activation Plan 已有只读诊断、自然语言只读入口和 Drawer 安全投影，可直接检查指定章节的写前记忆激活计划
  - World Model Route 已有只读诊断、自然语言只读入口和 Drawer 安全投影，可直接检查指定章节/subject_ref 的世界模型 profile、事实和待审提案压力
  - World Model Proposal Review/Resolution Plan 已有只读入口和 Drawer 安全投影，可直接检查待审世界模型提案队列、风险/审阅模式统计、推荐动作、提案簇摘要，并生成带高优先级/批量步骤统计和安全步骤摘要的提案处理计划
  - Retrieval Context 与 Longform Context Summary 已有只读工具和自然语言只读入口，可直接检索上下文证据并汇总指定章节长篇上下文；Retrieval Context run 可在 AgentRunDrawer 展示查询/过滤条件、返回窗口、证据条目、来源覆盖和推荐后续的安全摘要；Longform Context Summary run 可展示章节目标、生成进度、来源覆盖、预算截断、分区条目和诊断安全摘要
  - Dialog Control Plane Projection 已有只读审计和自然语言只读入口，可直接检查 generate_chapter 等 pending action 的当前运行工具与推荐审批工具链
  - Mutation Fingerprints 已有只读审计和自然语言只读入口，可直接检查 generate_chapter 等写入工具的稳定变更指纹
  - 写入门禁覆盖已有只读审计、自然语言只读入口和 AgentRunDrawer 安全投影，可直接检查写入工具的 Agent 计划审批 gate coverage、风险目标和推荐补齐动作，同时隐藏 adapter/handler、gate version/type、raw write policy、confirmation_fields、indirect_coverage、trace coverage_basis 与 mutability 等内部字段
  - Worker dispatch 已实现基础分发，子 Agent 孤兒恢复已有只读审计、自然语言只读入口、确认式 blocked 清理和 pending redispatch run 创建；AgentRunDrawer 与聊天 fallback projection 可安全展示分派状态、Worker/任务/问题计数、路由审计和孤儿恢复摘要
  - 后续可继续扩展 refund 规则，例如对白名单程序化 write 工具或批处理子步骤细分计费
关联模块：Hermes、Athena、Retrieval、TaskQueue、Trace、Memory
```

### 1.2 Hermes（创作流程控制）

```
当前状态：L2 诊断项目状态、管理 pending action、提供 ui_hint 和 refresh_targets
目标状态：L3-L4 自主诊断+建议+有条件自动执行低风险操作
关键文件：
  backend/app/core/intent_router.py       # 意图路由
  backend/app/core/state_diagnosis.py     # 项目状态诊断
  backend/app/services/actions/
  ├── action_proposal_service.py          # 动作提案服务
  ├── action_execution_service.py         # 动作执行服务
  ├── action_result_service.py            # 动作结果服务
  ├── action_result_view.py              # 动作结果视图
  ├── pending_action_projection.py       # 待处理动作投影
  ├── descriptions.py                     # 动作描述
  └── refresh_targets.py                  # 前端刷新目标
  backend/app/services/dialog/
  ├── session.py                          # 对话 session 管理
  └── messages.py                         # 消息管理
Agent 化缺口：
  - 意图路由覆盖不完整（部分写作意图尚未接入；Agent Health、Control Plane 就绪度、Dialog Control Plane Projection、Mutation Fingerprints、Tool Contracts、Command Contracts、Slash Command Route、Dialog Route Projection、Intent Projection、Reference Alignment、Dogfood Evidence、Route Preference、Legacy Hermes Migration、Route Approval Opt-in/Pending Action approval opt-in、Memory Tree 只读浏览、Memory Tree LLM 摘要计划/候选生成/候选检查/batch prepare/batch execute、Memory Route、Memory Activation Plan、World Model Route、World Model Proposal Review/Resolution Plan、Retrieval Context、Longform Context Summary、ContextCompressor 自检、dry-run payload 与 preflight 上下文预算预检、Worker Dispatch/孤儿恢复审计、Agent Event Projection、Agent Job Projection、Chapter Conflict Recovery、Trace Audit、Trace Anomaly Trends、Trace Anomaly Long Run Samples、Trace Anomaly Threshold Review 与 Write Gate Coverage 已可由自然语言投影到对应只读工具）
  - 缺少 LLM 驱动的"模糊意图"解析
  - pending_action 机制未与 Agent tool approval 统一；已有 legacy Hermes action 迁移路线图只读审计和 pending action route approval opt-in plan/preview/contract/prepare 自然语言只读链路，可先检查 setup/storyline/outline 生成动作的 Agent-native preview/approval/execute 覆盖，预览 pending_action 迁入 Agent 审批链的应用差异与确认契约，进入 Agent plan approval prepare，并在 recommended followup/dialog action result 视图中保留带双契约参数、仍需确认的 execute-with-approval handoff
关联模块：WritingAgent、Athena、前端 Chat
```

### 1.3 Athena（世界模型）

```
当前状态：L2 结构化世界实体 + 事件账本 + 提案审批 + layered checker（L0-L4 已实现，L5 已有只读 LLM 语义一致性检查入口，L6 预留）；World Model Route、L5 Semantic Check 与提案队列/解决规划可由自然语言只读意图触达，AgentRunDrawer 可展示 World Model Route 安全摘要、确认事实、待审提案压力、推荐动作和诊断信息，也可展示 L5 Semantic Check 的状态、章节/主体、事实窗口、issue、证据摘录和推荐后续工具，并展示 review_world_model_proposals 的待审队列状态、风险/审阅模式统计、推荐动作和提案簇安全摘要，以及 plan_world_model_proposal_resolution 的处理计划状态、人工确认/自动应用判断、高优先级/批量步骤计数、推荐动作/后续工具和安全步骤摘要
目标状态：L3 LLM 驱动的语义一致性检查 + 主动矛盾发现
关键文件：
  backend/app/core/athena_*.py            # 世界模型核心服务（多个文件）
  backend/app/models/ 中的 world_*.py     # 世界实体模型（约 15+ 实体）
  backend/app/api/athena_*.py             # 世界模型 API
  backend/app/services/writing_agent/
  ├── agent_world_model_route.py          # 世界模型路由
  ├── world_model_analysis_execution.py   # 世界模型分析执行
  ├── world_model_analysis_tool.py        # 世界模型分析工具
  ├── world_model_resolution_apply_*.py   # 世界模型决议应用
  └── world_model_tool_*.py              # 世界模型工具适配器
Agent 化缺口：
  - L5 语义检查已有 `inspect_agent_world_model_semantic_check` 基础版：对已生成章节和确认世界事实窗口执行 Trace-bound LLM JSON 检查，只返回语义冲突 issue，不写入世界事实或提案；L6 治理检查仍是预留层
  - 世界模型路由已有只读诊断、自然语言入口和 Drawer 安全投影，可检查 profile、确认事实、待审提案压力和下一步建议；L5 语义检查已有 Drawer 安全投影，可展示状态、事实窗口、issue、证据摘录和推荐后续工具，同时隐藏 project/profile/claim/trace/prompt/evidence_refs 等内部字段；提案队列 review run 与 resolution plan run 已有 Drawer 安全投影，可检查待审数量、风险/审阅模式统计、推荐动作、提案簇摘要和处理步骤摘要
  - 世界模型提案队列审阅、提案解决规划和 L5 语义检查已有自然语言只读入口，可在应用决议前先查看待处理提案、生成 offset/limit 范围内的处理计划，或对第 N 章与确认事实窗口做 LLM 语义冲突审查；Drawer 会隐藏 project/profile/cluster/item/bundle id 与 allowed_actions/plan_only/report_only 等内部字段
  - 章节事实抽取质量需要持续改进
  - 跨章节叙事一致性已有单章事实窗口 L5 起点和前端安全投影，仍缺真实 dogfood 与跨章事实链
  - 世界模型分析需要更多真实长篇压测
关联模块：Retrieval、Writing、Review、Trace
```

---

## 二、记忆与检索模块

### 2.1 Retrieval System（检索系统）

```
当前状态：L2 本地 hash embedding + 可切换远程 embedding，支持 lexical + vector score；inspect_agent_retrieval_strategy 已能按章节/query/维护状态只读选择 query-aware retrieval、章节上下文摘要或维护诊断，inspect_agent_retrieval_strategy_quality 已能在只读策略规划基础上汇总 dogfood evidence 开放问题并给出质量复核状态，inspect_agent_retrieval_prefetch_plan 已能把策略输出转成章节生成前的只读预取工具调用；章节生成 planner 已从固定 search 步骤升级为先规划检索预取再进入长篇上下文摘要；Retrieval Strategy、Retrieval Strategy Quality、Retrieval Prefetch Plan 与 Retrieval Context 均可由自然语言只读意图触达，AgentRunDrawer 与聊天 action descriptor 可展示检索策略、策略质量复核、预取计划和检索证据安全摘要
目标状态：L3 混合检索（语义+全文+Memory Tree）+ 主动预取
关键文件：
  backend/app/core/athena_retrieval.py    # Athena 检索
  backend/app/core/embedding_service.py   # Embedding 服务
  backend/app/models/ 中的 retrieval_*.py # 检索相关模型
Agent 化缺口：
  - 默认 embedding 质量有限
  - 检索策略已有只读 planner、质量复核、预取计划、自然语言入口、retrieval_worker 路由和 Drawer 安全投影，可按 query、chapter_index、limit、candidate_limit 与维护状态推荐 search_agent_retrieval_context、summarize_longform_context 或维护诊断；质量复核会复用策略输出、检索/维护诊断和 dogfood evidence 摘要，遇到开放 finding 时返回 needs_dogfood_review，并在 Drawer / 聊天 action descriptor 中只展示状态、策略、检索文档数、dogfood 覆盖和推荐后续，不泄露 trace、source_ref 或 raw recommended_next_tool_calls；预取计划会过滤为只读工具调用并已被章节生成 planner 消费，Drawer / 聊天 action descriptor 只展示预取状态、模式、策略、query、章节窗口、只读工具数、检索文档数和推荐后续，不泄露 raw tool_calls、trace/version 或 source_ref；检索上下文已有只读工具、自然语言入口和 Drawer 安全投影，可按 query、limit、source_type、max_chapter_index 检索证据，并展示返回窗口、来源类型、章节窗口、分数、摘要和推荐后续工具
  - 主动预取仍停留在只读计划层，尚未执行预取缓存、真实 strategy dogfood 反馈或 LLM 策略质量评估
  - 检索策略质量复核仍是确定性策略 + dogfood summary 聚合；下一步可接入 LLM/真实 strategy dogfood 反馈做更细粒度策略质量评估
关联模块：Athena、Memory Tree、Writing
```

### 2.2 Memory Tree（分层记忆树）

```
当前状态：L2 框架 + 卷/章摘要持久化基础版 + 基础浏览，摘要写入 LongformMemory 后再投影回 Memory Tree；query 支持精确匹配失败后的确定性语义评分、层级后代匹配回流、local hash vector_score 信号与 drilldown 推荐，并可进入写前 memory_activation；inspect_agent_memory_tree_quality 已可只读审计节点覆盖、摘要支撑、semantic probe 和真实长篇诊断；build_agent_memory_tree_llm_summary_plan 已可只读生成章级 evidence window、Trace-required prompt contract、quality precheck/postcheck 和候选生成/检查后续；summarize_agent_memory_tree_llm_candidate 可基于同一证据窗口执行 `memory_tree_summary_generation` Trace、把候选写入 Trace metadata 并返回 LLM 摘要候选，inspect_agent_memory_tree_llm_candidates 可按章节只读检查这些候选并为检查窗口内每个未物化 ready 候选输出 prepare recommended_next_tool_calls，多个未物化 ready 候选时推荐 prepare_record_agent_memory_tree_llm_candidate_summaries_batch，并在执行后回流 pending/materialized 状态；AgentRunDrawer 可安全展示多个候选摘要、来源字数、quality precheck 和物化状态并逐项触发 prepare continuation；record_agent_memory_tree_llm_candidate_summary 直接写入口保持审批 redirect，prepare_record_agent_memory_tree_llm_candidate_summary / execute_record_agent_memory_tree_llm_candidate_summary_with_approval 可把候选 trace id 与候选摘要 hash 绑定进审批契约，prepare 会输出携带 approval contract/hash 的 execute recommended_next_tool_calls，prepare_record_agent_memory_tree_llm_candidate_summaries_batch 可为多个候选批量生成逐条 trace-bound approval contract 与 execute 调用骨架但不写入，也可由自然语言直接规划成只读 batch prepare run；execute_record_agent_memory_tree_llm_candidate_summaries_batch_with_approval 可消费这些逐条 execute payload，逐候选复用单候选 approval、mutation fingerprint 与 resource binding 校验后批量写入章级 LongformMemory；AgentRunDrawer 可安全展示 batch prepare 结果、逐条 execute handoff 和 batch execute 写入摘要；本地 fake-model 批量回归已证明两个章级候选物化后 Memory Tree quality ready；Memory Route 与 Longform Context Summary 可由自然语言只读意图触达；AgentRunDrawer 可展示 inspect_agent_memory_route 的长篇记忆/检索/维护安全摘要、inspect_agent_memory_activation_plan 的写前激活安全摘要、search_agent_retrieval_context 的检索证据安全摘要、summarize_longform_context 的长篇上下文安全摘要、plan_post_chapter_memory_capture 的写后记忆沉淀安全摘要，也可展示 inspect_agent_memory_tree 的只读节点投影、查询条件、导航模式和推荐展开数，并可从推荐 drilldown、带 children 的返回节点或自由查询创建新的只读浏览 run；projectWorkspace 会按项目保留 Memory Tree continuation 浏览历史，Hermes 已注册 Memory 主工作区，子导航常驻 Memory Tree 面板可切入工作区、直接提交只读搜索 run、按 parent/children 展示当前返回节点层级树、从带 children 的结果节点发起只读展开 run 并显示当前展开节点，也可从历史入口重新打开对应 run；工作区中带 chapter_index 的节点可跳转并加载正文章节，也可从安全节点标签发起 search_agent_retrieval_context 只读检索证据 run（Drawer 可展示安全摘要）、summarize_longform_context 长篇上下文摘要 run（Drawer 可展示安全摘要）、inspect_agent_memory_activation_plan 写前记忆激活计划 run、inspect_agent_knowledge_base_route 知识库路由 run、plan_post_chapter_memory_capture 写后记忆沉淀规划 run（Drawer 可展示安全摘要）、inspect_agent_trace_audit 章节 Trace 审计 run（Drawer 可展示安全摘要）或 inspect_agent_world_model_route Athena 世界模型路由 run（Drawer 可展示安全摘要）
目标状态：L3 卷→章→节→段落分层，支持语义浏览和按需展开
关键文件：
  backend/app/services/writing_agent/
  ├── memory_tree.py                      # Memory Tree 核心
  ├── memory_tree_tool_adapters.py        # Memory Tree 工具适配器
  ├── memory_tree_tool_descriptors.py     # Memory Tree 工具描述符
  ├── memory_activation.py                # 记忆激活
  ├── longform_context_summary.py         # 长篇上下文摘要
  └── post_chapter_memory_capture.py      # 章节后记忆捕获
Agent 化缺口：
  - 更细粒度的分层摘要树（当前持久化到卷/章两级）
  - 更强语义导航（当前已支持按节点展开、深度裁剪、搜索祖先上下文、确定性 token-overlap 召回、后代强匹配回流到过滤层级、弱匹配降噪、写前激活消费和自然语言只读浏览入口；后续接入向量/LLM 语义搜索）
  - 前端独立 Memory Tree 面板已具备 Hermes Memory 主工作区、子导航只读搜索、历史入口、当前返回节点层级树、安全摘要、结果节点只读展开、当前展开状态、章节正文深链基础、Retrieval 证据只读 run 深链与 Drawer 安全摘要、Longform Context Summary 只读 run 深链与 Drawer 安全摘要、Memory Activation Plan 只读 run 深链与 Drawer 安全摘要、Memory Route Drawer 安全摘要、Knowledge Base Route 只读 run 深链、Post Chapter Memory Capture 只读 run 深链与 Drawer 安全摘要、Trace Audit 只读 run 深链与 Drawer 安全摘要，以及 Athena 世界模型路由深链与 Drawer 安全摘要；仍缺更完整的独立树工作区能力
  - 与 Retrieval 的深度整合
  - LLM 摘要质量仍未完成；真实长篇验证入口已存在，原始 dogfood DB 暴露 `memory_tree_summary_gap` 与 `memory_tree_semantic_probe_miss`，临时副本已通过审批式 `prepare_record_agent_memory_tree_summaries` / `execute_record_agent_memory_tree_summaries_with_approval` 物化摘要并复核 quality 为 ready；`inspect_agent_memory_tree` 的 semantic relevance 已暴露本地 hash embedding `vector_score` 与 embedding 元数据；`build_agent_memory_tree_llm_summary_plan` 已能把该缺口转成 Trace-required LLM 摘要计划，`summarize_agent_memory_tree_llm_candidate` 已用临时副本 + fake model 证明 Trace/candidate 路径和 0 记忆写入边界，`inspect_agent_memory_tree_llm_candidates` 已能从 Trace metadata 读回多个候选并为每个未物化 ready trace 输出 prepare 调用对象，执行后会报告 pending/materialized 计数并停止重复推荐同 trace prepare；`prepare_record_agent_memory_tree_llm_candidate_summaries_batch` 已能为多个候选批量生成逐条 trace-bound approval contract 和 execute 调用骨架，并已接入自然语言 direct read plan，AgentRunDrawer 已能安全投影 batch prepare 并逐条触发 execute-with-approval payload；`execute_record_agent_memory_tree_llm_candidate_summaries_batch_with_approval` 可消费多个已准备的单候选 execute payload，逐候选复用 approval contract、mutation fingerprint 和 resource binding 校验后批量物化，AgentRunDrawer 已能安全投影 batch execute 写入结果；候选专用审批链已能将单个候选 trace 物化为章级 LongformMemory，prepare 可输出 pending-confirmation execute 调用对象，并让对应 semantic probe 命中；本地 fake-model 批量回归已证明两个章级候选物化后可清空 fixture 的 summary gap；下一步应接入真实模型质量验证、远程向量/LLM 语义归纳或真实 dogfood 批量质量复核
关联模块：Retrieval、Athena、Writing
```

### 2.3 Knowledge Base（知识库）

```
当前状态：L1-L2 基本知识条目管理 + 候选生成；Knowledge Base Route 与写后记忆捕获计划可由自然语言只读意图触达；AgentRunDrawer 可结构化展示 inspect_agent_knowledge_base_route 的状态、章节/query、作者偏好、学习规则、知识库候选、写法参考、推荐工具和诊断摘要；AgentRunDrawer 可展示 plan_post_chapter_memory_capture 的章节可用性、审稿证据、候选标题/类型/摘要/置信度、来源覆盖和推荐工具安全摘要，并可从写后记忆捕获候选的 next_tool_call 发起 prepare_record_agent_knowledge_base_candidate 只读审批准备 continuation，在待审批写入区显示清洗后的候选标题、触发 execute_record_agent_knowledge_base_candidate_with_approval 已审批执行 payload；执行成功后可展示知识库候选写入结果、候选类型、数量和推荐下一步工具，并可从 inspect_agent_knowledge_base_route 推荐发起只读检查 continuation
目标状态：L2-L3 Agent 可自主拓展知识库（从章节中提取、从用户反馈中学习）
关键文件：
  backend/app/services/writing_agent/
  ├── agent_knowledge_base_route.py       # 知识库路由
  ├── agent_knowledge_base_candidates.py  # 知识库候选
  ├── knowledge_base_candidate_execution.py # 候选执行
  ├── knowledge_base_tool_adapters.py     # 知识库工具适配器
  └── knowledge_base_tool_descriptors.py  # 知识库工具描述符
Agent 化缺口：
  - 知识库路由已有只读诊断、自然语言入口和 Drawer 安全投影，可检查作者偏好、项目策略、学习规则、知识库候选和写法参考
  - 写后记忆捕获已有只读规划、自然语言入口和 Drawer 安全投影，可根据已生成章节与审稿证据规划知识库候选沉淀，前端可展示候选标题/类型/摘要/置信度与来源覆盖，并从规划候选继续准备知识库候选写入审批；审批执行前后展示候选标题/类型/数量而不泄露 source_refs / approval hash；执行成功后可直接继续只读检查 Knowledge Base Route
  - 自动从章节中提取知识
  - 知识的时效性管理（某些知识在特定章节后才成立）
关联模块：Athena、Retrieval、Memory Tree
```

---

## 三、写作与审稿模块

### 3.1 Chapter Generation（章节生成）

```
当前状态：L2 模板化章节生成，含上下文构建（设定+大纲+前章摘要+世界模型+检索证据）
目标状态：L3 LLM 自适应风格调整 + 多 worker 并行生成 + 质量自评
关键文件：
  backend/app/services/writing_agent/
  ├── chapter_generation_execution.py     # 章节生成执行
  ├── chapter_generation_tool.py          # 章节生成工具
  ├── chapter_expansion_tool.py           # 章节扩展工具
  ├── outline_window_expansion_execution.py # 大纲窗口扩展
  ├── outline_window_tool.py              # 大纲窗口工具
  ├── setup_generation_execution.py       # 设定生成执行
  ├── storyline_generation_execution.py   # 故事线生成执行
  ├── outline_generation_execution.py     # 大纲生成执行
  └── outline_backfill_execution.py       # 大纲回填执行
Agent 化缺口：
  - 章节生成目前是单次模型调用，缺少真正的"写作 Agent 子循环"
  - 质量自评和自动修订不够成熟
  - 多章连续生成缺少进度管理和暂停/恢复
关联模块：Hermes、Athena、Retrieval、Trace
```

### 3.2 Review & Revision（审稿与修订）

```
当前状态：L1-L2 基础一致性检查（L1 同步 + L2 后台）+ 修订任务管理
目标状态：L3 多维度语义审稿（一致性/节奏/风格/爽点）+ 智能修订建议
关键文件：
  backend/app/services/writing_agent/
  ├── batch_post_generation_review.py     # 生成后审稿
  ├── review_revision_tool_adapters.py    # 审稿修订工具适配器
  ├── review_revision_tool_descriptors.py # 审稿修订工具描述符
  ├── revision_draft_execution.py         # 修订稿执行
  ├── revision_draft_tool.py              # 修订稿工具
  ├── revision_patch_execution.py         # 修订补丁执行
  └── revision_patch_tool.py              # 修订补丁工具
  backend/app/services/writing/
  └── chapter_revision_*.py               # 章节修订服务
Agent 化缺口：
  - 缺少 LLM 驱动的多维度语义审稿
  - 审稿结果到修订建议的转换不够智能
  - 缺少对"爽点密度""起伏节奏"等网文特有维度的评估
关联模块：Athena、Writing、Trace
```

---

## 四、运行控制模块

### 4.1 Task Queue（任务队列）

```
当前状态：L1 进程内异步任务（BackgroundTask），支持 pending/running/completed/failed；Agent Event/Job Projection 可由自然语言只读意图触达
目标状态：L2-L3 健壮的任务队列（考虑 Celery/RQ/Arq），支持优先级、重试、可观测
关键文件：
  backend/app/services/tasks/
  ├── background_task_service.py          # 后台任务服务
  └── local_task_runner.py               # 本地任务运行器
  backend/app/services/writing_agent/
  ├── agent_task_queue_tool_adapters.py   # 任务队列工具适配器
  ├── agent_task_queue_tool_descriptors.py # 任务队列工具描述符
  ├── batch_enqueue.py                    # 批量入队
  ├── batch_enqueue_execution.py          # 批量入队执行
  ├── batch_execution.py                  # 批量执行
  ├── batch_planner.py                    # 批量计划器
  ├── batch_preflight.py                  # 批量预检
  └── batch_queue_inspector.py            # 队列检查器
Agent 化缺口：
  - 任务事件投影已有只读工具和自然语言入口，可按 task_id/run_id/limit 查看后台任务、Agent run 与 step 推导出的事件流
  - 后台任务队列已有只读投影和自然语言入口，可按章节、任务类型、状态和 limit 检查任务进度与恢复建议
  - 目前是进程内任务，非生产级队列
  - 缺少任务优先级和依赖管理
  - Worker 崩溃后缺少自动恢复
关联模块：WritingAgent、所有生成模块
```

### 4.2 Trace & Audit（追踪与审计）

```
当前状态：L2-L3 AIModelCallTrace 记录每次 AI 调用的详细信息；inspect_agent_trace_audit 已可由自然语言只读意图触达，用于审计 run/step/model trace/context blocks，并输出安全 intent_chain 摘要（规则、意图、计划工具、执行匹配数）、end_to_end_chain 摘要（意图→计划→执行→模型 Trace→结果消息覆盖）和 anomaly_summary 摘要（失败步骤、失败模型 Trace、缺 Trace 绑定、未执行计划、缺结果消息、截断上下文）；inspect_agent_trace_anomaly_trends 已可按最近 run、可选章节与 baseline window 聚合异常状态、严重度、问题类型、受影响 run 摘要、基线对比、项目配置化阈值、阈值信号、阈值校准建议、误报/漏报 guard、阈值固化策略投影和推荐后续；inspect_agent_trace_anomaly_long_run_samples 已可由自然语言触达，统计当前项目有 step 的长跑候选 run 样本、状态分布、entrypoint 分布、章节集合和 threshold review 推荐窗口；inspect_agent_trace_anomaly_threshold_review 已可由自然语言触达，基于 trends 的 calibration.policy 输出安全人工复核摘要、阈值候选和 prepare_record_agent_trace_anomaly_threshold_config 推荐调用，不执行写入；人工复核后的阈值可通过 prepare/execute approval chain 写入 Project.style_config；AgentRunDrawer 可展示 Trace Audit、Trace Anomaly Trends、Trace Anomaly Long Run Samples 与 Trace Anomaly Threshold Review 安全摘要、intent_chain 意图链路、端到端链路、异常摘要、趋势基线、阈值信号、阈值来源、阈值校准、固化策略、长跑采样窗口、阈值复核候选、失败原因、推荐动作、事件链、上下文块和模型 Trace 概览
目标状态：L3 全链路 trace（用户意图→计划→工具调用→模型调用→结果）
关键文件：
  backend/app/core/model_call_trace.py    # Model Call Trace 核心
  backend/app/api/model_call_traces.py    # Trace API
  backend/app/models/ 中的 trace_*.py     # Trace 数据模型
  backend/app/services/writing_agent/
  ├── agent_trace_audit.py                # Agent 追踪审计
  ├── agent_trace_threshold_config_execution.py # Trace 阈值配置审批写入
  ├── agent_memory_trace_tool_adapters.py # 记忆追踪工具适配器
  └── agent_memory_trace_tool_descriptors.py # 记忆追踪工具描述符
  frontend/src/components/modelTrace/     # 前端 Trace 抽屉
  frontend/src/stores/modelTraces.ts     # 前端 Trace Store
Agent 化缺口：
  - trace 已有"用户意图→计划工具→执行 step→模型 trace→result_message"的后端 end_to_end_chain 安全摘要和 Drawer 展示
  - trace 已有单 run anomaly_summary 安全异常摘要，可聚合失败步骤、失败模型 Trace、缺 Trace 绑定、未执行计划、缺结果消息和截断上下文，并在 Drawer 展示
  - trace 已有最近 run anomaly trends 安全聚合，可统计受影响 run、严重度、问题类型、baseline window、rate delta、项目配置化阈值、阈值信号、阈值校准建议、误报/漏报 guard、阈值固化策略和推荐后续，并在 Drawer 展示阈值来源
  - trace 已有 long-run sample 只读采集投影，可从自然语言进入 recovery_worker，统计当前项目候选 run/step 样本并推荐 threshold review window，不暴露 run/step id
  - trace 已有 threshold review 只读复核投影，可从自然语言进入 recovery_worker，输出复核状态、复核样本数、阈值候选和 prepare 调用建议，同时保持 side_effects 空/跳过写入
  - trace 阈值配置写入已具备 direct write guard、prepare/execute approval chain、mutation fingerprint、resource binding、write-gate coverage 和 recovery_worker 路由；执行后只写 Project.style_config.agent_trace_anomaly_thresholds 并推荐回到趋势检查
  - Dogfood Evidence 已纳入 Trace anomaly threshold calibration/policy/config/review/long-run sample/long-run execution/approval-chain 证据；真实长跑样本执行已由隔离 dogfood DB 的只读查询说明归档
关联模块：所有 AI 调用模块
```

### 4.3 Context Compression（上下文压缩）

```
当前状态：L1 对话历史长度限制 + 基础压缩；ContextCompressor 已具备窗口压力/ContextGuard 投影、头尾保护预修剪计划、只读 dry-run payload builder、推荐恢复入口，并已接入 preflight_writing 运行时检查、自然语言只读自检入口、自然语言 dry-run payload 直达入口、自然语言 preflight 上下文预算预检入口、AgentRunDrawer 安全摘要、preflight 上下文预算安全摘要、ready payload 后续持久摘要推荐、preflight 持久摘要优先复用、章节生成 longform prompt block 压缩、LongformMemory 持久摘要工件写入与章节 prompt 自动复用
目标状态：L2-L3 LLM 摘要压缩 + 头尾保护 + Token 预算管理
关键文件：
  backend/app/services/writing_agent/
  ├── agent_context_compression_projection.py # 上下文压缩投影 + dry-run payload + 持久摘要写入
  ├── run_service.py                       # preflight_writing 暴露压缩检查/preview
  └── longform_context_summary.py         # 长篇上下文摘要
  backend/app/prompting/providers/chapter.py # 章节 prompt longform block 压力触发压缩替换
  backend/app/services/dialog/session.py  # Session 管理含历史限制
Agent 化缺口：
  - 已有计划到 payload、preflight runtime gate、自然语言只读自检、dry-run payload 与 preflight 预算预检直达、Drawer 安全摘要、preflight 预算警告摘要、ready payload 写入推荐、preflight/章节 prompt 持久摘要复用、章节 prompt block 替换、持久摘要工件写入基础，仍缺少真正 LLM 摘要质量闭环
  - 缺少 TokenJuice 机制（openhuman）
  - 压缩粒度已有 longform block、持久工件和章节 prompt 复用入口，仍需按重要性继续分层到更多上下文构建路径
关联模块：Dialog、WritingAgent
```

---

## 五、数据与基础设施模块

### 5.1 Data Models（数据模型）

```
当前状态：L2 SQLAlchemy + Alembic migration，核心实体模型完整
目标状态：维持现状 + 新功能增量迁移
关键文件：
  backend/app/models/                     # 所有数据模型
  backend/alembic/versions/              # 迁移历史
  backend/app/schemas/                   # Pydantic API schema
Agent 化缺口：
  - 部分新功能的模型尚未建立；Memory Tree 基础持久化复用 LongformMemory，后续若扩展节/段落或向量索引再补迁移
关联模块：所有模块
```

### 5.2 Version & Recovery（版本与恢复）

```
当前状态：L2 Version + rollback + ChapterRevision 已实现；章节冲突恢复计划可由自然语言只读意图触达
目标状态：L2-L3 更细粒度的操作回滚（不只是内容，还包括世界模型变更）
关键文件：
  backend/app/services/writing/
  └── version_*.py / chapter_revision_*.py
  backend/app/services/writing_agent/
  ├── recovery_planner.py                 # 恢复计划器
  ├── recovery_policy.py                  # 恢复策略
  ├── chapter_conflict_recovery_planner.py # 章节冲突恢复
  └── direct_generation_write_guard.py    # 生成写入守卫
Agent 化缺口：
  - 章节冲突恢复已有只读计划器、自然语言入口和 Drawer/聊天安全摘要，可根据章节占用投影生成恢复工具计划，并展示目标章节、占用状态、恢复建议和安全任务摘要
  - 世界模型变更的回滚（提案级别的回滚）
  - 跨模块的原子化操作和回滚
关联模块：WritingAgent、Athena
```

---

## 六、前端模块

### 6.1 Chat View（对话视图）

```
当前状态：L2 对话界面含 action cards、followup、trace 入口，AgentRunDrawer 可展示计划工具/执行进度/下一步、逐项工具状态、Retrieval Strategy / Retrieval Strategy Quality / Retrieval Context 安全摘要、Memory Activation Plan 安全摘要、Memory Route 安全摘要、Longform Context Summary 安全摘要、Post Chapter Memory Capture 安全摘要、Knowledge Base Route 安全摘要、Write Gate Coverage 安全摘要、Agent Event Projection 安全摘要、Agent Job Projection 安全摘要、Chapter Conflict Recovery 安全摘要、Trace Audit 安全摘要、Trace Anomaly Trends 安全摘要、World Model Route 安全摘要、World Model Semantic Check 安全摘要、Memory Tree 只读节点投影和 Memory Tree LLM 候选摘要投影，并支持自由搜索、推荐 drilldown 或返回节点展开继续发起只读浏览 run；Memory Tree LLM 候选检查可在 Drawer 中展示待物化/已物化状态，并从多个 recommended_next_tool_calls 逐项触发 prepare_record_agent_memory_tree_llm_candidate_summary continuation，batch prepare run 可在 Drawer 中展示逐条候选执行准备并触发对应 execute-with-approval handoff，batch execute run 可展示安全写入结果；projectWorkspace 会在同一项目内保留安全的 Memory Tree 浏览历史，Hermes 已注册 Memory 主工作区，子导航常驻 Memory Tree 面板可切入工作区、直接搜索、按 parent/children 展示当前返回节点层级树、从结果节点发起只读展开并显示当前展开节点，也可从历史入口重新打开对应 run；Memory Tree 工作区中带 chapter_index 的节点可跳转并加载正文章节，也可从安全节点标签发起 Retrieval 证据只读 run、Longform Context Summary 只读 run、Memory Activation Plan 只读 run、Knowledge Base Route 只读 run、Post Chapter Memory Capture 写后记忆沉淀规划 run、Trace Audit 章节审计 run 或 Athena 世界模型路由 run；AgentRunDrawer 的写后记忆候选可继续准备知识库候选写入审批 run，并在待审批写入区展示候选标题、触发 execute_record_agent_knowledge_base_candidate_with_approval；执行成功后展示知识库候选写入结果与推荐下一步工具，并可发起只读 Knowledge Base Route 检查；recommended followup fallback view 可展示待确认后继并阻止 pending-only 自动执行
目标状态：L2-L3 更丰富的 Agent 状态可视化（当前执行计划、工具调用进度等）
关键文件：
  frontend/src/views/                     # 页面视图
  frontend/src/components/                # 包含聊天组件、modelTrace 等
  frontend/src/stores/                    # Pinia 状态管理
Agent 化缺口：
  - Agent 执行计划的可视化仍需继续增强（已具备计划工具/已执行/已完成/进行中/下一步摘要和逐项工具状态）
  - 工具调用进度实时展示（当前是 Drawer 详情内静态状态映射，仍缺流式刷新）
  - World Model / Memory 面板的整合（Memory Tree 当前已有 Drawer 只读投影、自由搜索、推荐展开、返回节点展开、Memory Tree LLM 候选摘要 Drawer 安全投影、物化状态、安全去重与多候选 prepare continuation、batch prepare Drawer 投影与逐条 execute handoff、batch execute 结果投影、项目级会话浏览历史、Hermes Memory 主工作区、子导航搜索/历史/当前返回节点层级树/结果节点展开与当前展开状态、章节正文深链基础、Retrieval 策略/策略质量/证据只读 run 深链与 Drawer 安全摘要、Longform Context Summary 只读 run 深链与 Drawer 安全摘要、Memory Activation Plan 只读 run 深链与 Drawer 安全摘要、Memory Route Drawer 安全摘要、Knowledge Base Route 只读 run 深链与 Drawer 安全摘要、Post Chapter Memory Capture 只读 run 深链与 Drawer 安全摘要、写后记忆候选 prepare approval continuation、execute approval payload、执行成功投影与写入后 Knowledge Base Route 只读检查、Trace Audit 只读 run 深链与 Drawer 安全摘要，以及 Athena 世界模型路由深链与 L5 语义检查 Drawer 安全摘要；仍缺更完整独立树工作区能力）
关联模块：Dialog Control Plane、Trace
```

### 6.2 Athena Panel（世界模型面板）

```
当前状态：L2 世界实体 + 提案审阅面板
目标状态：L2-L3 更直观的世界模型可视化（关系图、时间线等）
关键文件：
  frontend/src/components/ 中的 Athena 相关组件
  frontend/src/stores/ 中的 Athena Store
Agent 化缺口：
  - 缺少实体关系可视化
  - 缺少世界事实的全文搜索
关联模块：Athena
```

---

## 七、模块依赖关系

```
Chat (前端)
  └── Dialog Control Plane (Hermes)
        └── Writing Agent (编排核心)
              ├── Chapter Generation ──── Retrieval
              │     └── Athena (世界上下文)
              ├── Review & Revision ──── Athena (一致性检查)
              ├── Memory Tree ────────── Retrieval
              ├── Knowledge Base
              ├── Task Queue
              └── Trace & Audit ──────── (横切关注点，覆盖所有)

Data & Recovery ─── (横切关注点，覆盖所有写入操作)
```

---

## 八、状态变更日志

| 日期 | 模块 | 变更 |
|------|------|------|
| 2026-06-06 | Frontend Agent UX | AgentRunDrawer 新增 inspect_agent_write_gate_coverage 安全投影，展示写入工具数、Agent 审批覆盖、确认守卫、门禁缺口、高风险直写、风险目标和推荐动作，同时隐藏 adapter/handler、gate version/type、raw write policy、confirmation_fields、indirect_coverage、trace coverage_basis 与 mutability 等内部字段；新增投影拆为独立小组件以避免继续膨胀 Drawer 主文件 |
| 2026-06-05 | Frontend Agent UX | AgentRunDrawer 新增 inspect_agent_trace_anomaly_long_run_samples 与 inspect_agent_trace_anomaly_threshold_review 安全投影，展示长跑采样状态、候选运行/步骤/章节/复核窗口、状态分布、阈值复核样本、策略决策、阈值候选和推荐工具，同时隐藏 run/step/trace id、trace version、raw recommended_next_tool_calls params、policy/config 内部字段 |
| 2026-06-05 | Frontend Agent UX | AgentRunDrawer 新增 inspect_agent_job_projection 安全投影，展示队列深度、活跃/终止任务、返回任务数、选中任务状态/章节/范围/恢复能力、控制面与命令契约缺口、章节占用、事件摘要和推荐工具，同时隐藏 project/selector/task/run/event/trace id、version、control_plane 与原始 params |
| 2026-06-05 | Frontend Agent UX | AgentRunDrawer 与聊天 action descriptor 新增 plan_chapter_conflict_recovery 安全投影，展示计划状态、目标章节、占用状态、占用任务数、恢复状态、下一工具、计划工具数、恢复选项、任务来源/章节范围/状态和恢复选项标签，同时隐藏 task id、next_params、trace/version 与原始工具参数 |
| 2026-06-05 | Frontend Agent UX | AgentRunDrawer 与聊天 action descriptor 新增 inspect_agent_event_projection 安全投影，展示事件投影状态、事件总数、后台任务/运行/工具事件计数、工具错误、事件类型、来源类型、工具名、章节、状态、错误预览和推荐后续，同时隐藏 project/selector/event/source/run/task/step/trace id、version 与 trace source |
| 2026-06-05 | Frontend Agent UX | AgentRunDrawer 与聊天 action descriptor 新增 inspect_agent_worker_dispatch 安全投影，展示分派状态、Worker/计划任务/阻塞任务/问题计数、路由审计、未路由工具、孤儿恢复计数、Worker 角色、问题码和推荐后续，同时隐藏 definition_registry、task_envelopes、run/task id、version 与原始 route/tool 参数 |
| 2026-06-05 | Frontend Agent UX | AgentRunDrawer 与聊天 action descriptor 新增 inspect_agent_retrieval_prefetch_plan 安全投影，展示预取状态、模式、策略、query、目标章节、章节窗口、只读工具数、检索文档数和推荐后续，同时隐藏 trace/version、raw tool_calls、recommended_next_tool_calls 与 source_ref |
| 2026-06-05 | Frontend Agent UX | AgentRunDrawer 新增 inspect_agent_world_model_semantic_check 安全投影，展示 L5 语义检查状态、事实窗口、issue、证据摘录和推荐后续工具，同时隐藏 project/profile/claim/trace/prompt/evidence_refs 等内部字段 |
| 2026-06-05 | Frontend Agent UX | AgentRunDrawer 与聊天 action descriptor 新增 inspect_agent_retrieval_strategy_quality 安全投影，展示复核状态、策略、query、章节窗口、检索文档数、dogfood 覆盖和推荐后续，同时隐藏 trace/version、source_ref、dogfood source 和 raw recommended_next_tool_calls |
| 2026-06-05 | Athena | 新增 inspect_agent_world_model_semantic_check 只读 L5 语义一致性检查，基于已生成章节和确认事实窗口执行 Trace-bound LLM JSON 审查，不写世界事实或提案，并接入自然语言入口、world_model_worker、followup safe list 和 loop risk known poll |
| 2026-06-05 | Retrieval | 新增 inspect_agent_retrieval_prefetch_plan 只读主动预取计划，将检索策略输出过滤成章节生成前可执行的只读工具调用，并将章节生成 planner 从策略规划步骤升级为预取计划步骤；自然语言入口、retrieval_worker、followup safe list 与 loop risk known poll 已同步覆盖 |
| 2026-06-05 | Retrieval | 新增 inspect_agent_retrieval_strategy 只读检索策略规划，支持按章节/query/维护状态推荐 query-aware 检索、上下文摘要或维护诊断，并接入自然语言入口、retrieval_worker 和 Drawer 安全投影 |
| 2026-06-05 | Retrieval | 新增 inspect_agent_retrieval_strategy_quality 只读质量复核，结合检索策略、检索/维护诊断与 dogfood evidence 开放 finding 输出 needs_dogfood_review/ready 状态，并接入自然语言入口、retrieval_worker、followup safe list 与 loop risk known poll |
| 2026-06-05 | Long Memory | Memory Tree semantic relevance 新增 local hash `vector_score` 与 embedding 元数据输出，为远程向量召回前提供可审计基线 |
| 2026-06-05 | Long Memory | Dogfood Evidence 新增 Memory Tree LLM candidate batch materialization 证据，记录两个 fake-model 候选经 batch prepare/batch execute 后写入 2 个章级摘要并复核 quality ready |
| 2026-06-01 | 全部 | 初始版本 |
| 2026-06-04 | Trace & Audit | Dogfood Evidence 新增 Trace anomaly long-run sample execution 证据，记录隔离 dogfood DB 中 14 个真实 run、31 个 step、12 个 dogfood entrypoint run 和第 1-3 章样本覆盖 |
| 2026-06-04 | Trace & Audit | 新增 inspect_agent_trace_anomaly_long_run_samples 只读采样投影、自然语言入口和 recovery_worker 路由，Dogfood Evidence 记录 long-run sample collection 覆盖 |
| 2026-06-04 | Trace & Audit | 新增 inspect_agent_trace_anomaly_threshold_review 只读复核投影、自然语言入口和 recovery_worker 路由，Dogfood Evidence 记录 threshold review 覆盖 |
| 2026-06-04 | Trace & Audit | 新增 Trace anomaly threshold config direct write guard、prepare/execute approval chain、write-gate 覆盖和 recovery_worker 路由，人工复核后的阈值可审批写入项目配置 |
| 2026-06-04 | Trace & Audit | inspect_agent_trace_anomaly_trends 新增项目级阈值配置读取与 threshold_config 安全投影，AgentRunDrawer 展示阈值来源，Dogfood Evidence 记录 threshold config / drawer config 覆盖 |
| 2026-06-03 | Trace & Audit | inspect_agent_trace_anomaly_trends 新增 calibration.policy 安全投影，基于样本量、误报/漏报 guard 和建议阈值判断 collect/review/keep 策略，并在 AgentRunDrawer 展示固化策略摘要 |
| 2026-06-03 | Trace & Audit | inspect_agent_trace_anomaly_trends 新增阈值校准摘要，基于 recent/baseline 运行窗口输出建议阈值、误报/漏报 guard 和推荐后续，并在 AgentRunDrawer 展示安全校准投影 |
| 2026-06-03 | Trace & Audit | inspect_agent_trace_anomaly_trends 新增 baseline window、rate delta 与阈值信号，并在 AgentRunDrawer 展示基线/阈值安全摘要 |
| 2026-06-03 | Trace & Audit | 新增 inspect_agent_trace_anomaly_trends 最近 run 异常趋势只读聚合、自然语言入口、recovery_worker 路由和 AgentRunDrawer 安全摘要 |
| 2026-06-03 | Trace & Audit | inspect_agent_trace_audit 新增 intent_chain、end_to_end_chain 与 anomaly_summary 安全摘要，并在 AgentRunDrawer 展示意图规则、计划工具、执行匹配、模型 Trace、结果消息覆盖和单 run 异常聚合 |
