# 08 · 实施架构框架

> **最后更新**: 2026-06-06
> **版本**: v1.0
> **前置阅读**: [01-愿景与架构目标](./01-vision.md)、[04-开发规则与约束](./04-development-rules.md)、[06-架构决策记录](./06-architecture-decisions.md)
> **重要性**: ★★★★★（开始长期代码推进前必读）

---

本文档把愿景、ADR、模块清单和进度记录转成每次代码推进都能执行的架构框架。它不是一次性目录重写计划，而是后续所有 Agent 化改动的落地约束：先定义能力边界，再改代码，再用测试和文档闭环证明没有继续堆积。

---

## 一、适用假设

1. 当前长期目标仍是推进 novelv3 的 Agent 化，而不是构建通用 Agent 框架。
2. 代码现实优先于文档设想；如果文档方向与源码或 dogfood 证据冲突，先修正文档再推进。
3. 架构演进必须增量落地，避免大规模搬目录、大重写和无测试的结构调整。
4. 巨型文件是架构风险信号；触碰它们时，默认任务目标包含止血或拆分。
5. 每轮工作都要能在上下文丢失后恢复：能力边界、验证结果和剩余风险必须写回 codex-guide。

---

## 二、目标实施形态

```
Conversation Entry
  -> Dialog Control Plane
  -> Agent Run Loop
  -> Capability Slices
  -> Guarded Writes / Read Projections
  -> Safe UI Projection
  -> Verification & Progress Ledger
```

| 层 | 职责 | 不应该承载 |
|----|------|------------|
| Conversation Entry | 接收自然语言、展示 action、承接 followup | 领域写入逻辑、复杂投影解析 |
| Dialog Control Plane | 意图识别、计划生成、审批入口 | 直接修改章节、世界模型或记忆 |
| Agent Run Loop | step 状态、预算、循环风险、trace 绑定、工具执行编排 | 单个能力的业务细节 |
| Capability Slice | 单一 Agent 能力的 descriptor、adapter、execution、projection、test | 跨能力的大杂烩 helper |
| Guarded Writes | 世界模型提案、章节版本、知识库写入、记忆物化等受控写入 | 绕过审批或 trace 的隐式副作用 |
| Safe UI Projection | 安全摘要、脱敏、空状态、用户可见推荐动作 | raw output、内部 id、trace 私有字段 |
| Verification Ledger | 测试结果、文件规模变化、剩余风险、下一步 | 只写完成感受，不写证据 |

---

## 三、能力切片契约

新增或重构任一 Agent 能力前，先给它定义一个 slice。slice 名称使用稳定、可搜索的 snake_case，例如 `chapter_resize_compress`、`memory_tree_llm_candidate_batch_execute`、`trace_anomaly_threshold_review`。

每个 slice 至少要回答这些问题：

| 项 | 必填内容 |
|----|----------|
| 入口 | 用户自然语言、slash command、followup、drawer action 或后台任务触发点 |
| 计划 | planner route、tool descriptor、approval contract 或 command contract |
| 适配 | adapter 如何归一化请求、校验参数和暴露用户可理解错误 |
| 执行 | execution 是否只读、是否写入、是否可重试、失败后能否恢复 |
| 写入门禁 | 是否涉及世界模型、章节版本、知识库、Memory Tree、任务队列或文件系统 |
| 审计 | 需要哪些 AIModelCallTrace、tool step、approval verification 或 dogfood evidence |
| 前端投影 | 是否需要独立 Panel、shared projector、fixture、action descriptor |
| 测试 | shell 集成测试、slice 专属测试、边界样例、失败路径、脱敏断言 |
| 文档 | 需要更新 02 模块清单、05 进度、06 ADR 或本文件的哪一节 |
| 预算 | 触碰哪些超 2000 行文件，本轮是否净减少，不能减少时的理由 |

没有清楚 slice 的改动不进入代码阶段。紧急 bugfix 可以例外，但提交说明和进度记录里必须写清楚为什么没有先拆 slice。

---

## 四、目录与职责框架

当前仓库已经在 `backend/app/services/writing_agent/` 形成按文件名前缀分层的现实结构，短期不做大规模目录迁移。后续新增或拆分时优先沿用现有命名约定，而不是引入新的抽象树。

### 4.1 后端能力文件

| 文件类型 | 责任 | 命名倾向 |
|----------|------|----------|
| Descriptor | 工具元数据、用户可见说明、参数 schema、审批契约入口 | `*_tool_descriptors.py`、`*_tool.py` |
| Adapter | 请求归一化、参数校验、调用 execution、转成 tool result | `*_tool_adapters.py` |
| Execution | 具体只读或写入逻辑、事务、重试、恢复 | `*_execution.py` |
| Projection | 只读审计、安全摘要、健康面板数据 | `*_projection.py` |
| Policy / Guard | 预算、循环检测、写入门禁、权限策略 | `*_policy.py`、`*_guard.py` |
| Registry | 注册、路由、能力发现、worker definition 加载 | `*_registry.py`、`agent_definitions/` |

规则：

1. 不新增笼统的 `utils.py`、`helpers.py` 来承载跨能力逻辑；除非已有两个以上 slice 真实复用。
2. 单个能力先按前缀保持可搜索性，例如 `chapter_compression_tool.py`、`chapter_expansion_tool.py`。
3. 写入逻辑不得藏在 descriptor、projection 或 planner 中。
4. 只读 projection 不返回内部定位字段给前端，必要时只给安全摘要。

### 4.2 前端 Agent 投影

| 文件类型 | 责任 |
|----------|------|
| `AgentRunDrawer.vue` | Thin Shell：modal、通用 run 状态、查找 tool output、挂载 Panel |
| `AgentRun*Panel.vue` | 单一工具或 slice 的安全摘要和用户可见 action |
| `AgentRun*Panel.test.ts` | 脱敏、标签、计数、空状态、边界样例 |
| `agentRunProjection/*` | 至少两个 Panel 复用后的纯 projector、label、safe value helper |
| `agentRunFixtures/*Runs.ts` | 大型 run fixture、expected payload、复用测试样例 |
| `AgentRunDrawer.test.ts` | Shell 集成：确认输出能挂到正确 Panel，关键 action 能转发 |

规则：

1. Drawer 不继续吸收复杂 computed、模板分支和脱敏逻辑。
2. 新增复杂投影默认先建 Panel；只有非常小的状态文案可以留在 Shell。
3. raw output、trace 内部字段、source_ref、prompt context、approval hash 默认不进 UI。
4. fixture 超过约 80 行时优先迁出到 `agentRunFixtures`。

### 4.3 测试文件

| 测试类型 | 目标形态 |
|----------|----------|
| API run 测试 | `test_writing_agent_runs_<slice>.py` |
| tool executor 测试 | `test_writing_agent_tool_executor_<slice>.py` 或按工具族拆分 |
| 共享 seed / approval helper | `backend/test_support/`，只放两个以上测试模块复用的 helper |
| 前端 Panel 测试 | 每个 Panel 一个专属测试文件 |
| Shell 测试 | 只保留路由、挂载、关键动作转发 |

规则：

1. 测试文件不是第二个实现文件；大型业务样例应抽 fixture 或 builder。
2. 迁移测试时不改行为，先保持原断言，再做必要去重。
3. 超巨型测试文件每次触碰都优先净减少。

---

## 五、文件规模预算

文件行数不是绝对质量指标，但它是当前仓库最明显的可维护性风险信号。

| 文件规模 | 处理规则 |
|----------|----------|
| 0-800 行 | 正常范围，仍需保持单一职责 |
| 800-1500 行 | 注意增长，新增复杂逻辑前考虑拆局部 helper、fixture 或子组件 |
| 1500-2000 行 | 警戒范围，本轮改动应说明为什么仍留在该文件 |
| 2000-3000 行 | 超预算，触碰时原则上不得净增长 |
| 3000-5000 行 | 高风险，触碰时优先拆分或迁出测试/fixture |
| 5000-8000 行 | 严重风险，只做拆分、止血或极小关键修复 |
| 8000 行以上 | 关键风险，下一轮优先治理；除紧急修复外，不向内新增能力 |

每次提交前至少检查被触碰的大文件：

```
git diff --stat
rg --files | ForEach-Object { ... line count ... }
```

进度记录必须写明：本轮触碰了哪些超预算文件，净增还是净减，下一步拆分对象是什么。

---

## 六、推进流程

每轮代码推进按以下顺序执行：

1. **定义 slice**：写清能力边界、完成标准、受影响文件和预算。
2. **读源码**：确认现有模式、测试覆盖和超预算文件，不凭文档想象改代码。
3. **先设验证点**：bugfix 先补复现测试，重构先确定现有测试和 targeted 测试。
4. **小步编辑**：一次只迁移一个 slice 或一个清晰子能力，避免跨域重构。
5. **运行 targeted 验证**：优先跑被触碰模块的 pytest/vitest。
6. **运行完整验证**：按 [04-开发规则](./04-development-rules.md) 和项目记忆中的完整序列执行。
7. **更新文档**：05 记录进度，02 记录模块状态变化，06 记录架构决策，本文件记录框架变化。
8. **提交推送**：commit 只包含一个逻辑变更，提交前后确认工作区状态。

---

## 七、反模式

以下做法会把项目推向不可维护：

1. 在 Shell 中继续写能力细节。
2. 把多个 slice 的 fixture、builder、approval helper 堆进一个巨型测试文件。
3. 为了“架构漂亮”提前创建没人复用的抽象层。
4. 用通用 helper 隐藏领域语义，让失败测试无法看出业务意图。
5. 在 projection 或 UI 中暴露 raw output、prompt、source_ref 或内部 id。
6. 把真实行为改动和大规模重排混在同一个 commit。
7. 文档只写“已完成”，不写验证命令、文件规模变化和剩余风险。

---

## 八、当前优先治理对象

| 优先级 | 对象 | 治理方向 |
|--------|------|----------|
| P0 | `backend/tests/test_writing_agent_tool_executor.py` | 按工具族或 slice 拆出 executor 契约测试 |
| P0 | `backend/tests/test_writing_agent_runs.py` | 继续按 direct chapter recovery、通用 Agent run API、chapter generation/review 等残留切片拆分 |
| P1 | `frontend/src/components/writingAgent/AgentRunDrawer.test.ts` | 继续迁出大型 fixture 和重复细节断言 |
| P1 | `frontend/src/components/writingAgent/AgentRunDrawer.vue` | 保持 Thin Shell，只在触碰旧投影时迁出 |
| P2 | `backend/tests/test_dialogs.py` | 按对话入口、project scope、action descriptor、regression fixture 拆分 |
| P2 | `frontend/src/components/writingAgent/AgentRunDrawer.vue` 周边 Panel | 当多个 Panel 出现重复解析时再提取 shared projector |

---

## 九、文档记录模板

每个涉及架构或大文件的 commit，在 05 进度中使用这种信息密度：

```markdown
- 2026-06-06: `<slice>` 按 08 实施架构框架完成 `<具体变更>`；
  触碰超预算文件 `<path>` 从 `<before>` 行到 `<after>` 行；
  targeted 验证 `<command>` 通过；剩余风险 `<next split>`。
```

模块清单日志使用一行摘要，ADR 只记录会影响后续多轮工作的决策。

---

## 十、上下文恢复顺序

当 codex 上下文丢失或长期 goal 续跑时，按这个顺序恢复：

1. [README](./README.md)：确认文档体系和使用边界。
2. [05-进度追踪](./05-progress-tracker.md)：确认最近完成、当前优先级和验证证据。
3. 本文档：确认实施架构、slice 契约和文件预算。
4. [06-架构决策记录](./06-architecture-decisions.md)：确认 ADR-010、ADR-011 以及后续决策。
5. [02-模块清单](./02-module-inventory.md)：定位具体模块和文件状态。

恢复后先检查 `git status`，再继续代码推进。
