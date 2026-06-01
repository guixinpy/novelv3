# 02 · 模块清单与状态

> **最后更新**: 2026-06-01
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
  ├── tool_lifecycle_hooks.py             # 工具生命周期钩子
  ├── tool_recommendations.py             # 工具推荐
  ├── agent_loop_risk.py                  # 循环风险检测
  ├── agent_stop_hooks.py                 # 停止条件策略层
  ├── agent_step_binding.py               # Agent step 绑定
  ├── agent_command_catalog.py            # 命令目录
  ├── agent_command_contracts.py          # 命令契约
  ├── agent_tool_surface_policy.py        # 工具暴露策略
  ├── agent_worker_dispatch.py            # Worker 分发
  ├── agent_worker_recovery.py            # Worker 孤兒恢复审计 + 确认式写入清理
  ├── agent_definitions.py                # Agent 定义加载
  ├── agent_definitions/                  # Agent 定义文件目录
  ├── approval_contract.py                # 审批契约
  ├── approval_tool_metadata.py           # 审批工具元数据
  ├── approval_verification_event.py      # 审批验证事件
  ├── recovery_planner.py                 # 恢复计划器
  ├── recovery_policy.py                  # 恢复策略
  ├── slash_command_route.py              # 斜杠命令路由
  ├── worker_route_registry_projection.py # Worker 路由注册投影
  ├── ...（大量工具 descriptor/adapter/execution）...
  └── agent_definitions.py
Agent 化缺口：
  - 五级循环检测已具备 generic_repeat、ping-pong、unknown_tool_repeat、known_poll_no_progress、global_circuit_breaker
  - StopHooks 已具备 critical loop、BudgetCap、MaxTurns、ContextGuard、approval、memory provenance 策略；后续可继续扩展为真正的运行中断控制点
  - Agent loop budget 已具备 read 工具 refund 投影（used/charged/refunded/remaining iterations）
  - Worker dispatch 已实现基础分发，子 Agent 孤兒恢复已有只读审计、确认式 blocked 清理和 pending redispatch run 创建
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
  - 意图路由覆盖不完整（部分写作意图尚未接入）
  - 缺少 LLM 驱动的"模糊意图"解析
  - pending_action 机制未与 Agent tool approval 统一
关联模块：WritingAgent、Athena、前端 Chat
```

### 1.3 Athena（世界模型）

```
当前状态：L2 结构化世界实体 + 事件账本 + 提案审批 + layered checker（L0-L4 已实现，L5-L6 预留）
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
  - L5 语义检查和 L6 治理检查仍是预留层
  - 章节事实抽取质量需要持续改进
  - 缺少 LLM 驱动的"跨章节叙事一致性"检查
  - 世界模型分析需要更多真实长篇压测
关联模块：Retrieval、Writing、Review、Trace
```

---

## 二、记忆与检索模块

### 2.1 Retrieval System（检索系统）

```
当前状态：L2 本地 hash embedding + 可切换远程 embedding，支持 lexical + vector score
目标状态：L3 混合检索（语义+全文+Memory Tree）+ 主动预取
关键文件：
  backend/app/core/athena_retrieval.py    # Athena 检索
  backend/app/core/embedding_service.py   # Embedding 服务
  backend/app/models/ 中的 retrieval_*.py # 检索相关模型
Agent 化缺口：
  - 默认 embedding 质量有限
  - 缺少主动预取（在章节生成前预测需要的上下文）
  - 检索策略不够智能（固定规则 vs LLM 选择检索策略）
关联模块：Athena、Memory Tree、Writing
```

### 2.2 Memory Tree（分层记忆树）

```
当前状态：L2 框架 + 卷/章摘要持久化基础版 + 基础浏览，摘要写入 LongformMemory 后再投影回 Memory Tree
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
  - 更强语义导航（当前已支持按节点展开、深度裁剪、搜索祖先上下文；后续接入向量/语义搜索）
  - 与 Retrieval 的深度整合
  - LLM 摘要质量与真实长篇数据验证
关联模块：Retrieval、Athena、Writing
```

### 2.3 Knowledge Base（知识库）

```
当前状态：L1-L2 基本知识条目管理 + 候选生成
目标状态：L2-L3 Agent 可自主拓展知识库（从章节中提取、从用户反馈中学习）
关键文件：
  backend/app/services/writing_agent/
  ├── agent_knowledge_base_route.py       # 知识库路由
  ├── agent_knowledge_base_candidates.py  # 知识库候选
  ├── knowledge_base_candidate_execution.py # 候选执行
  ├── knowledge_base_tool_adapters.py     # 知识库工具适配器
  └── knowledge_base_tool_descriptors.py  # 知识库工具描述符
Agent 化缺口：
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
当前状态：L1 进程内异步任务（BackgroundTask），支持 pending/running/completed/failed
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
  - 目前是进程内任务，非生产级队列
  - 缺少任务优先级和依赖管理
  - Worker 崩溃后缺少自动恢复
关联模块：WritingAgent、所有生成模块
```

### 4.2 Trace & Audit（追踪与审计）

```
当前状态：L2 AIModelCallTrace 记录每次 AI 调用的详细信息
目标状态：L3 全链路 trace（用户意图→计划→工具调用→模型调用→结果）
关键文件：
  backend/app/core/model_call_trace.py    # Model Call Trace 核心
  backend/app/api/model_call_traces.py    # Trace API
  backend/app/models/ 中的 trace_*.py     # Trace 数据模型
  backend/app/services/writing_agent/
  ├── agent_trace_audit.py                # Agent 追踪审计
  ├── agent_memory_trace_tool_adapters.py # 记忆追踪工具适配器
  └── agent_memory_trace_tool_descriptors.py # 记忆追踪工具描述符
  frontend/src/components/modelTrace/     # 前端 Trace 抽屉
  frontend/src/stores/modelTraces.ts     # 前端 Trace Store
Agent 化缺口：
  - trace 目前以单次模型调用为单位，缺少"用户请求→最终结果"的端到端链路
  - 缺少 trace 的聚合分析和异常检测
关联模块：所有 AI 调用模块
```

### 4.3 Context Compression（上下文压缩）

```
当前状态：L1 对话历史长度限制 + 基础压缩；ContextCompressor 基础计划投影已具备窗口压力、ContextGuard、头尾保护预修剪和摘要工具参数
目标状态：L2-L3 LLM 摘要压缩 + 头尾保护 + Token 预算管理
关键文件：
  backend/app/services/writing_agent/
  ├── agent_context_compression_projection.py # 上下文压缩投影
  └── longform_context_summary.py         # 长篇上下文摘要
  backend/app/services/dialog/session.py  # Session 管理含历史限制
Agent 化缺口：
  - 缺少真正 LLM 摘要写入/运行时压缩执行
  - 缺少 TokenJuice 机制（openhuman）
  - 压缩粒度已有基础计划，仍需按重要性分层落到实际上下文构建路径
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
当前状态：L2 Version + rollback + ChapterRevision 已实现
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
  - 世界模型变更的回滚（提案级别的回滚）
  - 跨模块的原子化操作和回滚
关联模块：WritingAgent、Athena
```

---

## 六、前端模块

### 6.1 Chat View（对话视图）

```
当前状态：L2 对话界面含 action cards、followup、trace 入口
目标状态：L2-L3 更丰富的 Agent 状态可视化（当前执行计划、工具调用进度等）
关键文件：
  frontend/src/views/                     # 页面视图
  frontend/src/components/                # 包含聊天组件、modelTrace 等
  frontend/src/stores/                    # Pinia 状态管理
Agent 化缺口：
  - Agent 执行计划的可视化不够
  - 工具调用进度实时展示
  - World Model / Memory 面板的整合
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
| 2026-06-01 | 全部 | 初始版本 |
