# 03 · 参考项目模式映射

> **最后更新**: 2026-06-01
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
| Worker 定义配置化 | openhuman | **高** | 用 AgentDefinition 文件定义 worker 的能力、工具集、模型 |
| 孤兒恢复 | openclaw | **中** | worker 进程失效后自动检测和清理 |
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
| 工具权限分级 | openhuman PermissionLevel | 已完成基础版：内部枚举 + 公开字符串兼容 | 已完成基础版 |
| 审批门控 | openclaw ownerOnly + hermes-agent require_confirm | 已有 approval_contract | 已基本满足 |
| 审计日志 | openhuman | 已有 AIModelCallTrace | 已基本满足 |
| 安全意识 | openclaw 脱敏 | 已有 trace 脱敏 | 已满足 |

novelv3 当前 trace + approval 体系已经较完整。权限分级已先在核心 descriptor/contract 层升级为枚举，后续若要继续深化，应再把 planner、approval、前端展示等消费端逐步切到显式类型，而不是一次性破坏公开 JSON 契约。

---

## 六、上下文与恢复机制

### 6.1 上下文管理

| 机制 | 借鉴来源 | 优先级 | 说明 |
|------|---------|--------|------|
| ContextCompressor | hermes-agent | **高** | 预修剪 + LLM 摘要 + 头尾保护 |
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

### 立即实现（当前开发周期）

- 暂无固定单项；按代码现状、dogfood 结果和进度文档从短期清单中持续选择最高价值增量。

### 短期实现（1-2 个开发周期）

5. **openhuman Worker 定义配置化** → AgentDefinition 文件格式
6. **openhuman Memory Tree 分层摘要** → 完善 memory_tree.py
7. **hermes-agent ContextCompressor** → 增强上下文压缩
8. **openclaw 孤兒恢复** → worker 失效检测和清理

### 中期实现（3-5 个开发周期）

9. **hermes-agent Jittered Backoff** → 重试退避

### 暂缓（等待真实需求触发）

10. **openhuman TokenJuice** → 等待上下文管理成为实际瓶颈
11. **hermes-agent AST 扫描** → Python 装饰器已足够
12. **openclaw 网关角色** → novelv3 是单用户场景
