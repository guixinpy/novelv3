# 06 · 架构决策记录 (ADR)

> **最后更新**: 2026-06-06
> **版本**: v1.0
> **用途**: 记录关键架构决策及其理由，防止重复讨论已解决的问题

---

## 使用说明

每个决策记录包含：
- **日期**：做出决策的时间
- **状态**：Accepted / Superseded / Deprecated
- **上下文**：当时的背景和约束
- **决策**：做了什么决定
- **理由**：为什么这样做
- **后果**：这个决策带来的影响

---

## ADR-001: 对话驱动架构

- **日期**: 2026-04
- **状态**: Accepted

### 上下文

项目早期考虑过两种交互模型：
1. **功能面板模型**：用户在各个功能面板（设定面板、大纲面板、正文面板、审稿面板）之间切换，手动触发操作
2. **对话驱动模型**：所有操作通过对话入口，Agent 编排工具调用

### 决策

选择对话驱动模型。所有用户操作通过 Chat 界面发起，后端通过 IntentRouter 识别意图并生成 Agent 执行计划。

### 理由

- 网文作者的心智模型是"和水友讨论剧情"而非"操作写作软件"
- 对话驱动允许 Agent 在未来自主建议下一步操作
- 降低前端复杂度（不需要为每个功能维护独立 UI 面板）

### 后果

- 前端必须展示 Agent 执行状态（当前通过 action cards + followup cards 实现）
- 意图路由的准确率直接影响用户体验
- 需要持续扩展 IntentRouter 的覆盖范围

---

## ADR-002: 提案审批门控世界模型

- **日期**: 2026-04
- **状态**: Accepted

### 上下文

AI 生成小说时最常见的失败模式是"世界设定漂移"——角色、地点、规则会随着上下文变化而前后不一致。直接的解决方案是让 AI 直接修改世界模型记录，但这会引入"AI 一句话毁掉 50 章积累的世界观"的风险。

### 决策

AI 对世界模型的任何修改都必须生成 `WorldProposalBundle`（提案包），经过用户或系统审阅后才能应用。提案可以：通过 / 带修改通过 / 拒绝 / 标记不确定 / 拆分 / 回滚。

### 理由

- 保护世界模型的一致性不被单次 AI 调用破坏
- 用户保留对世界观变更的最终决定权
- 提案历史本身就是世界演化的审计日志

### 后果

- 世界模型 API 必须拒绝操作非当前 profile 的提案
- 前端需要建设提案审阅面板
- 章节生成后的世界事实抽取必须进入提案流程，不能直接写入

---

## ADR-003: 工具三层架构（Descriptor + Adapter + Execution）

- **日期**: 2026-05
- **状态**: Accepted

### 上下文

Agent 需要调用大量不同的工具（生成章节、分析世界模型、检索记忆、审稿等）。早期每个工具都有独立的调用逻辑和参数处理方式，导致代码重复和注册混乱。

### 决策

所有 Agent 工具采用三层架构：
1. **Descriptor**（描述符）：定义工具的名称、参数 schema、权限级别、是否需审批
2. **Adapter**（适配器）：将 Agent 的工具调用请求转换为具体服务的输入格式
3. **Execution**（执行器）：执行实际业务逻辑并返回结果

### 理由

- 分离关注点：注册、转换、执行各司其职
- 工具注册中心可以统一发现和过滤工具
- 新增工具只需实现三层，注册后即可被 Agent 调用

### 后果

- `writing_agent/` 目录下存在大量 `*_tool_descriptors.py`、`*_tool_adapters.py`、`*_execution.py` 文件
- 需要确保三层的一致性和契约验证
- 目前存在双重登记（descriptor + adapter 分开），后续可考虑用装饰器简化

---

## ADR-004: 本地 Hash Embedding 作为默认检索方案

- **日期**: 2026-04
- **状态**: Accepted（有已知限制）

### 上下文

长篇小说的章节检索需要 embedding 来支持语义搜索。选择 embedding 方案时面临 tradeoff：高质量远程 embedding（OpenAI/其他）成本高、有延迟；本地方案质量较低但无成本、零延迟。

### 决策

默认使用本地 hash embedding，同时支持切换到 OpenAI-compatible remote embedding。

### 理由

- 开发阶段零成本、零延迟
- 对单用户场景足够稳定
- 保留切换更高能力 embedding 的接口

### 后果

- 默认 embedding 不是最高质量语义向量
- 在正式长篇创作中可能需要切换到远程 embedding
- embedding_service.py 已支持两种模式的切换

---

## ADR-005: 进程内后台任务

- **日期**: 2026-04
- **状态**: Accepted（标记为临时方案）

### 上下文

章节生成后的世界分析、一致性检查、检索索引更新等操作需要异步执行。需要一个任务队列。

### 决策

当前使用进程内异步任务（`BackgroundTask` + `local_task_runner`）。这是一个已知的临时方案。

### 理由

- 当前是单用户场景，不需要分布式队列
- 进程内方案开发复杂度最低
- 可以快速验证任务模型和状态机

### 后果

- 后端重启会丢失未完成的任务
- 不支持任务优先级和复杂的依赖管理
- **已知需要升级**：当多用户、长任务、高并发场景出现时，应迁移到 Celery / RQ / Arq

---

## ADR-006: Profile Version 隔离世界模型

- **日期**: 2026-04
- **状态**: Accepted

### 上下文

用户可能会修改世界设定（例如：改变某个角色的性格设定），这时旧的世界状态不应该混入新的设定。需要一种机制来隔离不同版本的世界状态。

### 决策

使用 `ProjectProfileVersion` 来管理世界模型的版本。每个项目的世界事实、事件、提案都绑定到特定的 profile version。API 层拒绝操作非当前 profile 的提案。

### 理由

- 防止"用户已切换版本但系统仍用旧数据"的严重 bug
- 保留世界设定的演进历史
- 未来可以支持"分支世界线"（不同版本的世界设定并存对比）

### 后果

- 所有世界模型操作都需要 profile version 上下文
- 世界模型 API 需要显式校验 profile version

---

## ADR-007: 前端请求 Lane 隔离

- **日期**: 2026-05
- **状态**: Accepted

### 上下文

用户快速切换项目时，前端可能同时发出多个异步请求。如果处理不当，旧项目的响应可能在切换到新项目后才到达，导致新项目的 UI 显示旧项目的数据。

### 决策

使用 request lane 机制：每个请求带上 requestId 和 project scope version。迟到的请求（project scope 不匹配）的结果被丢弃，不会写入 store。

### 理由

- 避免"A 项目的世界模型显示在 B 项目"的 bug
- 不需要在组件层手动管理请求取消
- store 层统一处理更可靠

### 后果

- 每个 Pinia store 的异步请求必须走 request lane
- 参考实现：worldModel store

---

## ADR-008: 不纳入 vendor 依赖的参考项目

- **日期**: 2026-05
- **状态**: Accepted

### 上下文

openclaw、hermes-agent、openhuman 三个参考项目提供了大量可借鉴的代码和模式。考虑是否将它们作为 vendored 依赖纳入 novelv3。

### 决策

不纳入。参考项目源码快照放在 `references/agent-projects/`，但不纳入 Git 追踪，不作为 novelv3 的依赖。只提取模式，不直接引用代码。

### 理由

- 三个项目有各自的许可证和依赖树
- vendoring 会增加维护负担和安全风险
- novelv3 只需要思想和模式，不需要源码级复用
- 保持 novelv3 代码库的独立性和可控性

### 后果

- `references/agent-projects/` 需要手动更新
- 提取模式需要人工做适配判断
- `docs/archive/others/01-reference-patterns-report.md` 是模式提取的主要输出

---

## ADR-009: AgentDefinition 使用 YAML 主格式并兼容 TOML

- **日期**: 2026-06-01
- **状态**: Accepted

### 上下文

Worker/子代理需要配置化定义能力、工具范围和写入策略。openhuman 使用 `agent.toml` 作为内置 AgentDefinition 的数据入口；novelv3 当前已经有 `agent_definitions/*.yaml`，并且这些 YAML 已经接入 worker dispatch、profile policy 和健康审计。

### 决策

保留 YAML 作为 novelv3 现有 AgentDefinition 的主格式，同时在 loader 层兼容 `.toml`。注册表审计输出 `source_format`，用于区分 YAML/TOML 来源。暂不支持 JSON。

### 理由

- YAML 已经在当前仓库运行并被测试覆盖，迁移会制造无收益 churn
- TOML 兼容能直接吸收 openhuman 的 `agent.toml` 模式
- JSON 对人工维护的 worker 能力列表可读性较差，且当前没有实际需求
- 在 loader 层兼容格式，比在运行时硬编码 worker enum 更符合数据驱动方向

### 后果

- 新增 AgentDefinition 时优先使用 YAML；需要导入 openhuman 风格定义时可以使用 TOML
- loader 必须保持 YAML/TOML 字段语义一致
- worker 注册表、route 审计和健康面板可以通过 `source_format` 识别定义来源

---

## ADR-010: 前端 Agent Run 投影拆分架构

- **日期**: 2026-06-06
- **状态**: Accepted

### 上下文

`frontend/src/components/writingAgent/AgentRunDrawer.vue` 与对应测试已经增长到 7000 行级别。继续把每个 Agent 工具投影的解析、脱敏、标签映射、模板和测试全部堆进 Drawer，会让后续功能变成不可维护的巨型文件，并增加内部字段泄漏、回归测试脆弱和上下文压缩后误改的风险。

同时，AgentRunDrawer 仍是当前用户理解 Agent 执行状态的关键入口，不能用一次性大重写打断既有行为。架构调整必须能增量落地，并允许旧投影逐步迁移。

### 决策

采用 **Drawer Shell + Projection Panel + Shared Projector** 的前端 Agent Run 投影架构：

1. `AgentRunDrawer.vue` 是 Shell：负责 Modal 布局、run/step 基础状态、找到最新工具输出、承载通用操作和挂载投影面板。
2. 每个复杂工具投影必须有独立 Panel 组件：组件接收单个工具输出或已清洗 view model，只展示安全摘要，不直接暴露 raw output。
3. 投影解析优先放在 Panel 内的局部纯函数；当两个以上 Panel 复用同一类解析或标签映射时，再提取到 `frontend/src/components/writingAgent/agentRunProjection/` 或同等 shared projector 模块。
4. Drawer 集成测试只验证“某工具输出能挂到正确面板”和关键入口文案；字段脱敏、计数、标签和边界数据由对应 Panel 的专属测试覆盖。
5. 新增复杂投影不得继续把大段 computed/template/test 加进 `AgentRunDrawer.vue` 或 `AgentRunDrawer.test.ts`。若单次改动会向任一文件新增超过约 50 行投影逻辑，必须先拆 Panel。

目标目录形态：

```
frontend/src/components/writingAgent/
  AgentRunDrawer.vue                  # Shell：布局、基础 run 状态、面板挂载
  AgentRunDrawer.test.ts              # Shell 集成与关键回归
  AgentRunWriteGateCoveragePanel.vue  # 已落地的独立投影面板示例
  AgentRunWriteGateCoveragePanel.test.ts
  agentRunProjection/                 # 共享 projector/label/sanitizer，按真实复用再提取
  agentRunPanels/                     # 面板数量继续增长后迁入的目标目录
```

### 理由

- Shell 与 Panel 分离后，新增 Agent 能力不再天然扩大 Drawer 主文件。
- 安全投影的脱敏规则能靠专属测试精确覆盖，减少 raw internal 字段被 UI 泄漏的概率。
- 先抽新增投影、再逐步迁移旧投影，风险比一次性重写低，也符合当前长期 goal 的持续推进方式。
- 与后端工具三层架构一致：后端 descriptor/adapter/execution 分离，前端也应将 run shell、projection sanitization 和 panel rendering 分离。

### 后果

- 后续新增 Frontend Agent UX 功能时，要优先创建小组件和专属测试；Drawer 只做路由和组合。
- 历史巨型 Drawer 不要求一次性拆完，但每次触碰某个投影时，应优先评估能否顺手迁出，至少不能让主文件继续显著增长。
- 共享 projector 只能在真实重复出现后抽取，避免为了“架构漂亮”提前制造空抽象。
- 评审和提交说明需要显式说明：新增投影放在 Shell、Panel 还是 Shared Projector 的哪一层，以及为什么。

---

## ADR-011: Agent 能力纵切与文件规模预算

- **日期**: 2026-06-06
- **状态**: Accepted

### 上下文

长期 Agent 化推进已经暴露出明显结构风险：少数 Vue 组件和测试文件达到数千行，继续把每个工具的契约解析、脱敏、UI 状态和回归样例堆在同一文件，会让上下文压缩后的恢复成本越来越高，也会削弱后续审计、拆分和验证的可信度。

架构约束不能只停留在“拆某个 Drawer”。后续新增能力需要按业务纵切落地：一个能力从后端 descriptor/adapter/execution，到 planner route、只读审计、前端安全投影和测试，都应该有明确所有权边界。

### 决策

采用 **Capability Slice + Thin Shell + Explicit Budget** 的长期推进框架：

1. 每个 Agent 能力按纵切能力命名和记录，例如 `trace_audit`、`memory_route`、`world_model_proposal_resolution`；实现时优先保持 descriptor、adapter、execution、projection、panel、test 的边界清晰。
2. Shell 文件只承载组合职责：路由、布局、挂载、通用状态和少量 glue code；不得承载某个能力的详细领域解析。
3. Projection/Panel 文件承载单一能力的安全摘要和本地标签映射；当同类映射在两个以上能力中复用时，再提取到 shared projector。
4. 测试按职责拆分：Shell 测试验证挂载和关键入口；能力测试验证字段脱敏、计数、标签、空状态和边界样例；大型 fixture 需要向专属 helper 或 fixture 文件迁移。
5. 文件规模作为架构健康信号纳入验收：新增或触碰 2000 行以上文件时，本轮改动原则上不得让该文件净增长；若需要新增超过约 50 行能力逻辑，必须先拆出能力文件或说明不可拆原因。
6. 目标预算不是硬性一次性重写门槛，而是持续迁移方向：Shell 逐步降到 1500 行以下，单个复杂 Panel 优先控制在 600 行级，单个测试文件优先控制在 800 行级；超过预算时下一轮优先拆 projector、fixture 或子面板。

推荐目录形态：

```
frontend/src/components/writingAgent/
  AgentRunDrawer.vue                  # Thin shell
  AgentRunDrawer.test.ts              # Shell integration only
  agentRunProjection/                 # Shared pure projectors and safe value helpers
  agentRunPanels/                     # Target home for capability panels once panel count grows
  agentRunFixtures/                   # Target home for large reusable test fixtures

backend/app/services/agent/
  descriptors/                        # Tool/action metadata and contracts
  adapters/                           # Request/response normalization
  execution/                          # Side effect or read-only implementation
  projection/                         # Read-only audit/projection view models when shared
```

### 理由

- 纵切能力能让后续上下文恢复直接定位到某个能力，而不是重新阅读巨型 UI 或 service 文件。
- Thin Shell 降低 UI 改动的合并冲突和误删风险，能力 Panel 可以独立测试、独立审计。
- Explicit Budget 把“文件越来越大”变成每轮都能检查的工程信号，而不是等到不可维护后再重写。
- 预算是迁移压力阀，不是为了追求形式化架构。已有巨型文件继续按触碰范围渐进拆分，避免一次性大重写破坏行为。

### 后果

- 后续提交需要在进度文档中说明本轮能力属于哪个 slice，以及是否触碰超预算文件。
- 对超预算文件的改动需要优先做到净减少；无法减少时必须补充理由和后续拆分目标。
- 新增 Agent 能力前先定义 slice 边界和验证标准，再进入代码实现。
- 当前 Frontend Agent UX 的优先拆分对象是 `AgentRunDrawer.vue`、`AgentRunDrawer.test.ts` 和剩余 Drawer fixture；Memory Tree LLM candidate / batch prepare / batch execute、Trace Audit 与 Trace Anomaly 系列已迁出为独立 Panel，Memory Tree LLM、Memory Tree 只读、Post Chapter Memory Capture、Knowledge Base、recommended followup / recovery、planner preview 与 route upgrade Drawer fixture 已迁出到 `agentRunFixtures`，并应继续向 fixture/projector 拆分收敛。
- 当前 Backend Agent Tests 的优先拆分对象是 `test_writing_agent_runs.py` 与 `test_writing_agent_tool_executor.py`；`test_writing_agent_runs.py` 已先迁出 revision draft / revision patch / chapter resize expand / chapter resize compress / pending world proposal guard / world model proposal review-plan / preview / apply-draft / planner continuation / longform batch queue-preflight / execution / review-route API 回归和共享 test_support helper，`test_writing_agent_tool_executor.py` 已先迁出 adapter boundary 与 route opt-in plan/preview/contract/approval 契约切片，后续继续按 direct chapter recovery、通用 Agent run API、chapter generation/review 残留测试与 executor static metadata、dialog intent、tool handling 等能力切片拆分。

---

## ADR-012: 实施架构框架先于继续堆代码

- **日期**: 2026-06-06
- **状态**: Accepted

### 上下文

长期 goal 已经进入持续代码推进阶段，但当前仓库存在多个 3000 行、5000 行甚至 8000 行以上的代码和测试文件。仅靠“下一轮顺手拆一点”不足以防止能力继续堆进巨型文件，也无法让上下文压缩后的 codex 快速判断某个改动该落在哪一层。

ADR-010 和 ADR-011 已经定义了前端投影拆分和能力纵切预算，但仍缺一份横跨后端、前端、测试、文档和验证的实施框架，来指导每次代码改动的进入条件、目录职责、文件预算和收尾记录。

### 决策

新增 [08-实施架构框架](./08-implementation-architecture.md)，并把它作为继续推进长期 goal 的前置规则：

1. 新增或重构 Agent 能力前，先定义稳定 slice 名称、入口、计划、适配、执行、写入门禁、审计、前端投影、测试、文档和文件预算。
2. 不做一次性目录重写；短期沿用 `backend/app/services/writing_agent/` 的现有命名前缀和 `frontend/src/components/writingAgent/` 的 Panel/fixture/projector 模式。
3. 触碰超 2000 行文件时，默认要求净不增长；触碰 5000 行以上文件时，优先拆分、止血或做极小关键修复；8000 行以上文件列为关键风险。
4. 进度文档必须记录本轮 slice、超预算文件净增/净减、验证命令和剩余拆分目标。
5. 代码实现不得先于架构框架：如果 slice 边界、验证标准或文件预算说不清楚，先补文档或缩小任务范围。

### 理由

- 先有实施框架，后续才能持续推进 Agent 能力，而不是把每个新功能继续塞进最熟悉的巨型文件。
- 文件预算把架构健康变成每轮都能检查的事实，减少“之后再拆”的延期风险。
- 框架明确保留增量策略，不借架构之名进行大范围重排，符合当前已有测试和上线风险。
- 文档化 slice 契约能让上下文丢失后的 agent 直接恢复执行边界。

### 后果

- 后续每次继续长期 goal 时，先读 05 和 08，再选择下一条 slice。
- `test_writing_agent_runs.py`、`test_writing_agent_tool_executor.py`、`AgentRunDrawer.test.ts`、`AgentRunDrawer.vue` 等超预算文件的新增能力必须优先外迁。
- 如果真实代码现状证明 08 的某条规则不合适，先更新 08 或新增 ADR，再推进实现。

---

## 待记录的决策

以下是尚未正式记录但可能需要记录的决策：

- [ ] Memory Tree 的数据结构和持久化方案
- [ ] Worker 通信协议（进程内 vs 消息队列 vs HTTP）
- [ ] 上下文压缩的策略和触发条件
- [ ] 长篇 smoke 测试的设计原则和覆盖范围
