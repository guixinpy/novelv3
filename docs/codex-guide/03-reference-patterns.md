# 03 · 参考项目模式映射

> **最后更新**: 2026-06-05
> **版本**: v1.0
> **前置阅读**: [01-愿景与架构目标](./01-vision.md)
> **关联文档**: `docs/archive/others/01-reference-patterns-report.md`（原始完整报告）

---

## 概述

novelv3 以三个本地参考项目为工程学习对象：

| 项目 | 语言 | 定位 | novelv3 适配度 |
|------|------|------|---------------|
| **openclaw** | TypeScript | 多通道 AI 网关 + 可扩展消息平台 | 高：抽象层次清晰 |
| **hermes-agent** | Python | 自改进 CLI Agent（Nous Research） | 最高：技术栈相同 |
| **openhuman** | Rust+TS | 桌面 AI 助手，带完整 UI | 中高：架构严谨 |

源码快照位于 `references/agent-projects/`。

**原则**：参考项目只提供模式启发，不提供优先级。模式必须先映射到 novelv3 当前缺口，再决定是否实现。不得因为参考项目存在某模式就默认需要重建同等复杂度。

当前 `inspect_agent_reference_alignment` 会把 openclaw、hermes-agent、openhuman 的可复用模式、novelv3 已采纳决策和下一步工具建议投影为只读审计结果；自然语言“检查参考项目模式对齐/开源项目适配”已可直接规划到该工具。

---

## 一、Agent 记忆系统

### 1.1 三项目模式对比

| 维度 | openclaw | hermes-agent | openhuman |
|------|----------|-------------|-----------|
| 分层方式 | 根记忆文件 → 插件记忆(SQLite+向量+FTS) → QMD 外部 | SessionDB(SQLite FTS5) → MemoryProvider 插件 | Key-Value → FTS5+向量搜索 → Memory Tree 分层摘要 |
| 检索机制 | MemorySearchManager + 语义搜索 | FTS5 全文搜索 + 外部 provider 预取 | 语义 recall + Tree 导航（顶层→深层 drill-down） |
| 注入策略 | buildMemoryPromptSection() → system prompt | `<memory-context>` fence 标签 + StreamingContextScrubber 防泄露 | memory_context.rs 在用户消息前注入 |

### 1.2 → novelv3 映射

novelv3 需要管理**四类记忆**，对应不同策略：

```
网文创作记忆分类          → 借鉴来源          实现方式
─────────────────────────────────────────────────────
世界观/设定记忆           → openhuman Memory Tree  分层摘要树
角色档案记忆             → openclaw 根记忆+向量   结构化条目 + 语义检索
章节/情节记忆            → hermes-agent FTS5      全文搜索
写作风格记忆             → openclaw 根记忆文件     持久化"写作圣经"
```

### 1.3 Memory Tree 模式（重点借鉴）

openhuman 的 Memory Tree 对网文创作天然适配：

- **卷→章→节→段落** 的层级结构本身就是一棵树
- 节点被分块、打分、汇总到分层摘要中
- Agent 可以浏览顶层概览，或在感兴趣的话题上 drill-down
- 当前 novelv3 已落地卷/章两级基础版：`record_agent_memory_tree_summaries` 将摘要 materialize 为 `LongformMemory`，直接写入口已改为审批链 redirect，`prepare_record_agent_memory_tree_summaries` / `execute_record_agent_memory_tree_summaries_with_approval` 会在审批契约验证后写入并返回 quality 复核；`inspect_agent_memory_tree` 再把持久化摘要投影回树节点，并在精确匹配失败时用确定性 relevance 评分、后代强匹配回流、local hash vector_score 和弱匹配阈值给出 drill-down 推荐；`inspect_agent_memory_tree_quality` 会只读审计节点覆盖、摘要支撑、semantic probe 和真实长篇诊断；`build_agent_memory_tree_llm_summary_plan` 会把真实质量缺口转成只读 evidence window、Trace-required prompt contract、quality gate 和候选生成/检查后续；`summarize_agent_memory_tree_llm_candidate` 可在不写 LongformMemory 的前提下执行 `memory_tree_summary_generation` Trace、把候选写入 Trace metadata 并返回摘要候选，`inspect_agent_memory_tree_llm_candidates` 可只读检查候选 Trace 并为检查窗口内每个未物化 ready trace 输出 prepare recommended_next_tool_calls，多个未物化 ready trace 会推荐 batch prepare 工具，执行后会回流 pending/materialized 状态并停止重复推荐同 trace prepare；自然语言也可直接规划到 batch prepare 只读 run；AgentRunDrawer 可安全展示多个候选、物化状态并逐项触发 prepare continuation，也可展示 batch prepare 结果并逐条触发 execute-with-approval payload；候选专用 `record_agent_memory_tree_llm_candidate_summary` / `prepare_record_agent_memory_tree_llm_candidate_summary` / `execute_record_agent_memory_tree_llm_candidate_summary_with_approval` 已把 trace id 与候选摘要 hash 绑定进审批契约，`prepare_record_agent_memory_tree_llm_candidate_summaries_batch` 可为多个候选批量生成逐条 trace-bound approval contract 与 execute 调用骨架，`execute_record_agent_memory_tree_llm_candidate_summaries_batch_with_approval` 可消费这些逐条 execute payload 并逐候选复用单候选 approval/resource 校验后批量写入章级 LongformMemory；本地 fake-model 回归已证明两个章级候选批量物化后 Memory Tree quality ready；高相关节点会进入 `build_memory_activation_plan` 的写前激活桶，且自然语言“浏览/搜索记忆树”“检查记忆树质量”“构建记忆树 LLM 摘要计划”“生成/查看记忆树 LLM 摘要候选”“准备记忆树 LLM 摘要候选批量审批”都可直接规划到只读 Memory Tree 工具

**已知 tradeoff**（来自 openhuman 实际运行经验）：
- 语义召回需要将检索到的记忆注入上下文
- 上下文压缩会破坏 KV-cache 前缀
- openhuman 通过限制注入量（默认 5 条、2000 字符）缓解
- novelv3 实现时需显式处理这个冲突

### 1.4 记忆系统目标架构

```
┌─────────────────────────────────────────┐
│         Memory Activation Layer          │
│     (决定哪些记忆在当前上下文激活)        │
├──────────┬──────────┬───────────────────┤
│ World    │ Character│ Chapter/Plot      │
│ Memory   │ Memory   │ Memory            │
│ (Tree)   │ (Vector) │ (FTS5)            │
├──────────┴──────────┴───────────────────┤
│         Style Memory (Anchor)           │
└─────────────────────────────────────────┘
```

---

## 二、Agent 运行循环

### 2.1 三项目模式对比

| 维度 | openclaw | hermes-agent | openhuman |
|------|----------|-------------|-----------|
| 循环结构 | 双层（外层重试 + 内层模型调用） | 单层 while(iteration_budget) | 单层 while(tool_iterations) + StopHooks |
| 迭代控制 | bootstrap-budget + context-window-guard | IterationBudget 消费/退款 | max_tool_iterations(默认10) + StopHooks |
| 终止条件 | 压缩耗尽/空闲超时/循环检测触发 | 无 tool_calls/budget 耗尽/用户中断 | 无 tool_calls/迭代耗尽/ContextGuard 断路器 |
| 特别机制 | post-compaction-loop-guard | refund() 机制 | StopHooks 策略层 |

### 2.2 → novelv3 映射

novelv3 当前 `_agent_loop_contract()` 已有迭代预算、五级循环检测、StopHooks 策略层和 read 工具 refund 预算投影。后续应增强：

| 增强点 | 借鉴来源 | 优先级 | 说明 |
|--------|---------|--------|------|
| 多级循环检测 | openclaw | 已完成 | generic_repeat、ping-pong、unknown_tool_repeat、known_poll_no_progress、global_circuit_breaker 已实现 |
| StopHooks 策略层 | openhuman | 已完成基础版 | 已包含 critical loop、BudgetCap、MaxTurns、ContextGuard、approval、memory provenance |
| refund 机制 | hermes-agent | 已完成基础版 | 成功 read 工具不消耗 charged iteration；后续可扩展程序化 write 白名单 |
| ContextGuard 断路器 | openhuman | **中** | 上下文即将溢出时的硬保护 |

### 2.3 openclaw 五级循环检测（优先实现）

```
Level 1: generic_repeat      — 连续 3 次相同或几乎相同的工具调用
Level 2: ping-pong           — A→B→A→B 交替调用
Level 3: unknown_tool_repeat — 频繁调用未知/不存在的工具
Level 4: known_poll_no_progress — 轮询工具连续多次无进展
Level 5: global_circuit_breaker — 单次运行超过 30 个工具调用，硬终止
```

novelv3 当前已实现五级检测：generic_repeat、ping-pong、unknown_tool_repeat、known_poll_no_progress、global_circuit_breaker。后续重点是让这些检测更深入地参与运行中断和恢复计划。

### 2.4 关键架构认知

**hermes-agent 的 `run_conversation()` 是"单次用户输入→多轮工具调用→返回"。** 百万字创作需要一个上层的故事编排循环，在每个"章节生成"迭代中调用 `run_conversation()`，而不是把整个百万字生成塞进一次调用。

novelv3 当前的 planner→run_service 架构已经体现了这种分层，应该保持并强化。

---

## 三、工具编排

### 3.1 三项目模式对比

| 维度 | openclaw | hermes-agent | openhuman |
|------|----------|-------------|-----------|
| 注册方式 | defineToolDescriptor() | registry.register() 自注册 + AST 扫描 | Box<dyn Tool> trait + 工厂函数 |
| 发现/过滤 | buildToolPlan() 按 availability 过滤 | get_tool_definitions(enabled/disabled_toolsets) | AgentDefinition 中的工具 scope 筛选 |
| 权限模型 | 网关角色+作用域 + ownerOnly | ToolGuardrails(pre_approve/deny/require_confirm) | PermissionLevel(None/ReadOnly/Write/Execute/Dangerous) |

### 3.2 → novelv3 映射

novelv3 当前工具系统（tool_registry + tool_descriptor + tool_adapter）已经比较完整。建议增强：

| 增强点 | 借鉴来源 | 优先级 | 说明 |
|--------|---------|--------|------|
| 权限分级 | openhuman | 已完成基础版 | descriptor/contract 内部使用 ToolMutability 与 ToolPermissionLevel；公开 surface 仍输出字符串以保持兼容 |
| 工具策略层 | openclaw | **中** | 按场景动态调整工具暴露（如"审稿模式"不暴露生成工具） |
| 自注册简化 | hermes-agent | **低** | 当前双重登记（descriptor + adapter）可考虑用装饰器简化 |

### 3.3 PermissionLevel 映射

```
openhuman 五级          →  novelv3 建议三级
─────────────────────────────────────────
None                    →  (不需要，工具不注册即可)
ReadOnly                →  Read       (只读操作：检索、查询状态)
Write                   →  Write      (写入操作：保存章节、更新设定)
Execute                 →  GuardedWrite (高风险写入：生成章节、修改世界真相)
Dangerous               →  GuardedWrite
```

---

## 四、子代理/Worker 管理

### 4.1 三项目模式对比

| 维度 | openclaw | hermes-agent | openhuman |
|------|----------|-------------|-----------|
| 子 Agent 创建 | spawn（完备） | delegate_task（leaf/orchestrator 分层）| AgentDefinition(TOML) |
| 注册/发现 | registry + announce | 无独立注册（task 即 agent） | AgentRegistry |
| 孤兒恢复 | orphan recovery（agent 失效后自动清理） | 无 | 无 |
| 级联控制 | 支持 | Kanban 状态机 | Chat/Reasoning/Worker 三级 |

### 4.2 → novelv3 映射

novelv3 当前 worker_dispatch 已实现基础分发。应增强：

| 增强点 | 借鉴来源 | 优先级 | 说明 |
|--------|---------|--------|------|
| Worker 定义配置化 | openhuman | 已完成基础版 | YAML 为主格式，TOML 兼容 openhuman agent.toml 形态；注册表审计会输出 source_format |
| 孤兒恢复 | openclaw | 已完成基础版 | 已有 orphan worker 审计、自然语言只读审计入口、确认式 blocked 清理和 pending redispatch run 创建；后续可接入后台执行与 UI 审批 |
| Worker 链追踪 | openclaw | **中** | 记录 worker 调用链：主 Agent → writing worker → review worker |
| 级联 Worker | openhuman | **低** | Chat/Reasoning/Worker 三级，novelv3 场景可能不需要这么复杂 |

### 4.3 novelv3 目标 Worker 架构

```
Main Agent (对话编排)
  ├── Writing Worker      (章节生成)
  │     └── Review Worker (生成后自动审稿)
  ├── World Model Worker  (世界提案分析)
  ├── Memory Worker       (记忆树维护)
  └── Knowledge Worker    (知识库更新)
```

---

## 五、权限与审计

### 5.1 → novelv3 映射

| 能力 | 借鉴来源 | 当前状态 | 优先级 |
|------|---------|---------|--------|
| 工具权限分级 | openhuman PermissionLevel | 已完成基础版：内部枚举 + 公开字符串兼容；工具/命令契约快照可自然语言只读审计 | 已完成基础版 |
| 审批门控 | openclaw ownerOnly + hermes-agent require_confirm | 已有 approval_contract + write gate coverage 审计 | 已基本满足 |
| 审计日志 | openhuman | 已有 AIModelCallTrace | 已基本满足 |
| 安全意识 | openclaw 脱敏 | 已有 trace 脱敏 | 已满足 |

novelv3 当前 trace + approval 体系已经较完整。权限分级已先在核心 descriptor/contract 层升级为枚举，Agent Health、Control Plane、Tool Contracts、Command Contracts、Trace Audit、Trace Anomaly Trends、Trace Anomaly Long Run Samples、Trace Anomaly Threshold Review 与 Write Gate Coverage 只读自检/审计也已可由自然语言直接规划到 `inspect_agent_health_projection` / `inspect_agent_control_plane_readiness` / `inspect_agent_tool_contracts` / `inspect_agent_command_contracts` / `inspect_agent_trace_audit` / `inspect_agent_trace_anomaly_trends` / `inspect_agent_trace_anomaly_long_run_samples` / `inspect_agent_trace_anomaly_threshold_review` / `inspect_agent_write_gate_coverage`；Trace Anomaly Trends 已有 baseline window、rate delta、项目级配置化阈值读取、阈值来源投影、阈值信号、阈值校准建议、误报/漏报 guard 和阈值固化策略的安全投影，Trace Anomaly Long Run Samples 会从当前项目 run/step 中统计可复核样本并推荐 review window，Trace Anomaly Threshold Review 会把 calibration.policy 收敛成只读人工复核摘要、阈值候选和 prepare 调用建议，人工复核后的阈值写入已接入 direct write guard、prepare/execute approval chain、mutation fingerprint、resource binding、write-gate coverage 和 recovery_worker 路由，Dogfood Evidence 也已记录其 threshold calibration/policy/config/review/long-run sample/long-run execution/approval-chain 证据，其中真实长跑样本执行来自隔离 dogfood DB 的只读查询归档。后续若要继续深化，应再把 planner、approval、前端展示等消费端逐步切到显式类型，而不是一次性破坏公开 JSON 契约。

---

## 六、上下文与恢复机制

### 6.1 上下文管理

| 机制 | 借鉴来源 | 优先级 | 说明 |
|------|---------|--------|------|
| ContextCompressor | hermes-agent | 进行中：持久工件闭环 | 已有头尾保护预修剪、摘要工具计划、dry-run payload builder、压力场景推荐入口，并在 preflight_writing 中输出压缩检查与 payload preview；自然语言“检查上下文压缩/预算/窗口压力”可直接规划到只读压缩投影工具，“构建上下文压缩 dry-run payload”可直达 `build_agent_context_compression_payload`；ready payload 会继续推荐写入 `record_agent_context_compression_summary`，preflight 与章节生成 longform block 都能优先复用同章节同预算持久摘要，章节生成缺摘要时仍可在压力下替换为 compressed_context；后续补真正 LLM 摘要质量闭环和更多上下文路径分层压缩 |
| TokenJuice | openhuman | **中** | Token 耗尽前自动压缩 |
| 断路器 | openhuman | **中** | 上下文即将溢出时的硬保护 |
| 上下文透明化 | novelv3 已有 | 已实现 | Trace drawer 展示 context blocks |

### 6.2 恢复机制

| 机制 | 借鉴来源 | 优先级 | 说明 |
|------|---------|--------|------|
| Checkpoint Resume | hermes-agent | **中** | 运行中断后从检查点恢复 |
| Jittered Backoff | hermes-agent | **低** | 重试时的抖动退避 |
| 世界模型回滚 | novelv3 已有 | 已实现 | 提案级别的拒绝和回滚 |
| 章节版本回滚 | novelv3 已有 | 已实现 | Version + rollback |

---

## 七、优先级汇总

### 已完成（当前代码具备）

1. **openclaw 五级循环检测** → `agent_loop_risk.py`
2. **openhuman StopHooks 策略层基础增强** → `agent_stop_hooks.py` 已含 BudgetCap、MaxTurns、ContextGuard
3. **hermes-agent refund 机制基础版** → read 工具成功调用不消耗 charged iteration
4. **openhuman 权限分级基础版** → `ToolMutability` / `ToolPermissionLevel`，内部枚举化，公开 surface/contract 保持字符串兼容
5. **openhuman Worker 定义配置化基础版** → YAML/TOML AgentDefinition loader + source_format 注册表审计
6. **openclaw 孤兒恢复基础审计** → orphan worker 检测 + mark-blocked/redispatch preview，并可由自然语言只读意图直接规划到 `inspect_agent_worker_dispatch`
7. **hermes-agent ContextCompressor persistent artifact loop** → context pressure 下输出头尾保护预修剪、summarize 工具计划、只读 dry-run payload、推荐恢复入口，在 `preflight_writing` 暴露压缩检查与 payload preview；自然语言“检查上下文压缩/预算/窗口压力”可直接规划到只读压缩投影工具，“构建上下文压缩 dry-run payload”可直达 `build_agent_context_compression_payload`；ready payload 后推荐 `record_agent_context_compression_summary`；写入 LongformMemory 持久工件后，preflight 与章节 prompt 均会优先复用匹配摘要，缺摘要时章节生成 longform block 仍可替换为 `compressed_context`
8. **openhuman Memory Tree 分层摘要基础版** → 卷/章摘要写入 LongformMemory，并通过 memory_worker 暴露审批式 materialize/recheck 工具链
9. **openhuman Memory Tree 基础浏览/激活/质量审计** → `inspect_agent_memory_tree` 支持按节点展开、深度裁剪、搜索命中祖先上下文、确定性 relevance drill-down、local hash vector_score、过滤层级的后代强匹配回流与弱匹配降噪，可由自然语言只读意图直接规划，并被 `build_memory_activation_plan` 消费；`inspect_agent_memory_tree_quality` 则提供真实长篇 quality baseline，当前 dogfood 已证明 summary backing 缺口可经审批式 materialize/recheck 闭环收敛
10. **openhuman Memory Tree LLM 摘要计划/候选层** → `build_agent_memory_tree_llm_summary_plan` 在真实 dogfood 缺口上输出章级 evidence window、Trace-required prompt contract、quality precheck/postcheck 和候选生成/检查后续；`summarize_agent_memory_tree_llm_candidate` 将同一证据窗口推进到可审计 `memory_tree_summary_generation` Trace、Trace metadata 候选持久化和候选返回，`inspect_agent_memory_tree_llm_candidates` 可按章节复核候选并为多个未物化 ready trace 产出 prepare 调用对象，多个未物化 ready trace 时推荐 batch prepare，执行后回流 pending/materialized 状态并抑制重复 prepare；`IntentRouter` 和 `plan_dialog_intent_agent_run` 已能从自然语言直达 batch prepare direct read plan；AgentRunDrawer 可安全展示多个候选、物化状态并发起逐项 prepare continuation，也可安全展示 batch prepare 结果并逐条触发 execute-with-approval payload；候选专用 prepare/execute 审批链可将选中候选物化为章级 Memory Tree 摘要，prepare 输出的 execute 调用对象保持 `requires_confirmation=true`；batch prepare 只生成逐条 trace-bound execute handoff 而不执行写入，batch execute 则逐候选复用单条审批校验并已有跨章 quality ready 回归证据
11. **openclaw 孤兒恢复写入闭环基础版** → `apply_agent_worker_orphan_recovery` 确认式标记 blocked，并创建 pending redispatch run
12. **Reference Alignment 只读审计入口** → `inspect_agent_reference_alignment` 将三参考项目模式、已采纳决策和下一步建议投影为可审计结果，并可由自然语言只读意图直接规划

### 立即实现（当前开发周期）

- 暂无固定单项；按代码现状、dogfood 结果和进度文档从短期清单中持续选择最高价值增量。

### 短期实现（1-2 个开发周期）

13. **openhuman Memory Tree 语义召回/摘要增强** → 在确定性层级 relevance、本地 hash vector_score、LLM-ready summary plan、traced fake-model candidate、候选 Trace 读回、trace-bound 候选审批物化、多候选 recommended_next_tool_calls handoff、batch prepare approval handoff、自然语言 batch prepare direct read、batch execute 逐候选审批物化、Drawer batch execute handoff/结果投影、执行后物化状态回流和跨章批量 quality ready 回归证据基础上继续推进真实模型质量验证、远程向量召回、真实 dogfood 批量质量复核和按需展开
14. **hermes-agent ContextCompressor 摘要质量与分层压缩** → 基于 preflight/章节 prompt 的持久压缩摘要推荐、写入、复用闭环继续推进 LLM 摘要质量闭环 + 更多实际上下文构建路径按重要性分层压缩
15. **openclaw 孤兒恢复后台执行整合** → 将 pending redispatch run 接入后台执行/前端审批入口
16. **Retrieval Strategy Planner** → 已先落地只读策略规划、质量复核与预取计划层：`inspect_agent_retrieval_strategy` 由策略结果推荐 query-aware retrieval、长篇上下文摘要或维护诊断；`inspect_agent_retrieval_strategy_quality` 会在同一输入上复用策略输出、检索/维护诊断和 dogfood evidence 摘要，遇到开放 finding 时返回 needs_dogfood_review 并保留下一步工具建议；`inspect_agent_retrieval_prefetch_plan` 会把策略推荐过滤成章节生成前可执行的只读工具调用，章节生成 planner 已先调用该预取计划再进入上下文摘要；后续再接 LLM/真实 strategy dogfood 反馈做更细粒度策略质量评估和真实预取缓存
17. **Athena L5 Semantic Check** → 已先落地只读 LLM 语义一致性检查：`inspect_agent_world_model_semantic_check` 对已生成章节和确认世界事实窗口执行 Trace-bound JSON 审查，只返回 L5 issue 和推荐后续审批工具，不写入世界事实或提案；AgentRunDrawer 已可安全展示状态、事实窗口、issue、证据摘录和推荐工具，并隐藏 trace/prompt/claim/evidence_refs 等内部字段；后续补真实 dogfood 与跨章事实链

### 中期实现（3-5 个开发周期）

14. **hermes-agent Jittered Backoff** → 重试退避

### 暂缓（等待真实需求触发）

15. **openhuman TokenJuice** → 等待上下文管理成为实际瓶颈
16. **hermes-agent AST 扫描** → Python 装饰器已足够
17. **openclaw 网关角色** → novelv3 是单用户场景
