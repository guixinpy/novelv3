# Agent-Native Writing Agent Goal

本文档覆盖 2026-05-24 开启的新长期 goal。旧的长记忆写作 goal 经验继续保留，但本轮主目标更明确：先把 novelv3 改造成专精网文写作的长期记忆 Agent，再用真实长篇创作验证它。

## 目标

将 novelv3 从“带对话入口和若干 AI 写作模块的工具”重构为“以对话驱动、具备长期记忆、可自主编排工具、专精网络小说创作的 Agent 系统”。

系统最终应具备：

- Agent 主脑：理解用户高层意图，规划任务，选择工具，审查结果，沉淀经验。
- 长期记忆：区分世界事实、作者偏好、项目策略、参考拆书、写法模式、审稿教训和历史决策。
- 工具编排：Hermes、Athena/世界模型、检索、知识库、审稿、任务队列、Trace、导出等模块都能以清晰契约被 Agent 调用。
- 运行循环：每次 Agent run 有预算、退出原因、工具调用诊断、失败恢复和可追踪状态。
- 领域专精：不追求通用 Agent，优先服务百万字、千章级网文长期稳定创作。

小说生成仍然重要，但它在本轮 goal 中是 pressure-test 和 problem-discovery spine，不是独立主交付。所有小说生成都应服务于验证 Agent 是否能在低细节用户输入下自主规划、召回记忆、组织上下文、调用工具、审稿修订和沉淀经验。

## 参考项目学习边界

本轮持续参考本地源码：

- `references/agent-projects/openclaw`
- `references/agent-projects/hermes-agent`
- `references/agent-projects/openhuman`

这些项目只作为工程学习材料，不作为依赖，不直接复制目录结构。每个阶段都应明确从参考项目吸收了什么，并转译成 novelv3 的领域能力。

### openclaw 应吸收的部分

- 工具可见性、权限、循环检测和工具策略。
- 上下文装配生命周期，而不是简单 prompt 拼接。
- active memory 的超时、缓存、allowlist、fallback。
- commitments/open loops，可转译为伏笔、未兑现承诺、待揭示真相和角色承诺。

### hermes-agent 应吸收的部分

- Agent loop 的预算、退出原因和循环诊断。
- 工具调用前验证：未知工具、参数错误、截断参数、失败重试。
- 内部状态工具：todo、memory、session search、delegation。
- 上下文压缩保留首尾、当前任务和恢复状态。

### openhuman 应吸收的部分

- 分层长期记忆：profile、episodic、semantic、graph、KV、digest。
- 用户偏好结构化 facet，而不是一个大段提示词。
- bounded recall、memory citation、provenance 和可调试记忆 UI。
- pinned、muted、forgotten 等记忆治理状态。

## novelv3 的目标架构

```text
用户对话
  -> Writing Agent Core
      -> 意图理解
      -> 长期记忆召回
      -> 任务规划
      -> 工具选择与权限判断
      -> 工具执行循环
      -> 结果审查与失败恢复
      -> 经验沉淀
  -> Agent Tools
      -> Hermes 创作执行
      -> Athena / 世界模型事实工具
      -> Retrieval / Longform Context
      -> Knowledge Base 创作记忆
      -> Review / Revision
      -> Task Queue 长流程
      -> Trace / Audit
      -> Manuscript / Export
```

核心判断标准：用户给出脑洞、世界观或阶段目标后，Agent 应能自主决定下一步工具链。不能把“让用户写更详细提示词”当成长篇稳定性的主要解决方案。

## 模块改造原则

- 原模块不是不可动边界。凡是不适合 Agent 编排的模块，都可以重构、拆分、精简或换接口。
- 所有能力优先变成 Agent-callable capability，而不是继续只服务页面按钮或旧 action。
- 工具必须具备名称、类别、输入 schema、输出 schema、可见性、权限级别、mutability、Trace、失败语义和恢复建议。
- 写操作必须有审批、hash、幂等或资源绑定策略。
- 运行状态必须可审计：每次 run 说明输入、工具链、消耗、退出原因、失败点和下一步。

## 阶段流程

每个阶段必须文档驱动：

1. 写阶段计划，说明本阶段吸收哪个参考项目能力、改 novelv3 哪个切面、验证到什么程度。
2. 执行实现或审计。
3. 补阶段报告，记录代码改动、验证证据、仍未解决的问题和下一阶段建议。

阶段文档目录：

- `docs/superpowers/plans/agent-native-writing/`
- `docs/superpowers/notes/agent-native-writing/`

验证采用 T0/T1/T2/T3：

- T0：静态检查、单文件或纯函数测试。
- T1：相关后端/前端单元测试。
- T2：关键 API 或页面 smoke。
- T3：里程碑级完整验证。

避免每个小改动都跑完整前后端测试。高风险重构、阶段收口和合并前再执行更完整验证。

## Phase 1 目标

Phase 1 不尝试一次性重写 Agent Core。先补齐运行时可观测性，把当前“静态计划 + 顺序工具执行”的 run 显式暴露为一个可演进的 Agent loop contract。

Phase 1 应完成：

- 对照三个参考项目做能力差距审计。
- 明确当前最关键缺口：运行循环缺少预算、退出原因、循环/工具诊断和恢复语义。
- 在 run output / continuation state 中加入 Agent loop 诊断投影。
- 用针对性后端测试验证成功、阻塞、失败路径都有明确 exit reason。
- 写阶段报告，作为后续真正 runtime loop、memory recall loop、tool validation loop 的基础。
