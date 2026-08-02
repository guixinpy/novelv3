# Design: agent 架构重构设计

> 输入：现有架构盘点（backend/app 依赖图 + 缺陷清单）+ 三份参考研究报告（hermes-agent / openclaw / openhuman）
> 用户决策：设计先行+骨架新建 / API 完全自由 / 测试重写为主纯函数移植 / 核心链保留扩展归档

## 1. 目标架构总览

```
backend/
├── core/                     ← agent 内核（领域无关，零业务依赖，可独立测试）
│   ├── loop.py               无状态回合引擎
│   ├── harness.py            有状态外壳（会话/队列/压缩调度/持久化）
│   ├── turn_state.py         回合状态对象（吸收 hermes TurnRetryState）
│   ├── providers/            Provider 抽象 + 归一化（stream/重试/用量）
│   ├── tools/                工具框架（注册/schema 校验/权限/结果治理）
│   ├── guards/               护栏家族（循环风险 + 预算 + 断路器）
│   ├── context/              上下文管理（CJK 估算/压缩/注入/状态重注入）
│   ├── events.py             事件模型（LoopEvent + 稳定 event id）
│   ├── session/              会话持久化（transcript JSONL + 元数据）
│   └── workflow/             工作流图机制（plan→execute⇄review→finalize）
├── domain/                    ← 领域层（小说业务，全部通过工具/回调进入内核）
│   ├── writing/              章节生成/格式校验/结构校验/评审/修订
│   ├── memory/               长期记忆/项目快照/大纲窗口
│   ├── retrieval/            检索/实体挖掘/embedding
│   └── tools/                领域工具实现（桥接：domain → core.tools 注册）
├── api/                       ← 组装层（新 API，完全自由设计）
├── models/                   SQLAlchemy 模型
└── data/                     SQLite（保留）
```

**架构原则（从三份研究提炼的共识）**：
1. 循环要薄，策略在宿主层（openclaw ~460 行 / openhuman 委托框架）——我们内核保持 ~2k 行
2. 事件流 = 唯一事实流（UI/持久化/观测消费同一事件流）
3. 错误编码为消息而非异常（卡住是报告不是静默）
4. 护栏家族而非单一 try/except
5. 机制与领域解耦，测试与真实 agent 解耦（mock 注入）

## 2. 内核设计（core/）

### 2.1 循环引擎（loop.py）——保留 + 三处吸收

**保留**：无状态 run_turn、事件 sink、iteration/token 双预算、steer 注入、guard 触发 break 全回合。

**吸收**：
- **turn_state.py（hermes #1）**：把循环内散落的临时状态（重试计数、压缩标记、错误样本）收敛为 `TurnState` 对象——一次性 guard 可命名、可单测。直接解决"590 测试但循环测试少"的病根。
- **失败分类学（openhuman #10）**：`ToolResult` 增加结构化失败分类 `ClassifiedFailure {error_code, category, next_action, recoverable}`（如 `unknown_tool` / `validation` / `transient` / `permission`），替代 L4 guard 的 `"不存在" in text` 字符串耦合（修现有缺陷 #3）。
- **固定返回结构 + 退出原因追踪（hermes #8）**：`TurnResult` 扩展 `exit_detail` 字典（stop_reason 已枚举化，补：压缩次数、工具错误数、guard 诊断），诊断第一眼可读。

### 2.2 护栏家族（guards/）——保留五级 + 吸收三项

**保留**：L1 重复调用 / L2 乒乓 / L3 无进展轮询 / L4 幻觉工具（改错误码）/ L5 全局熔断。

**吸收**：
- **wall-clock 上限（openhuman）**：turn 级时间上限 + 每 provider 调用独立 timeout——修"模型流挂死"（deepseek.py 已有 300s timeout，补 turn 级总控）。
- **优雅暂停（openhuman）**：到迭代上限时产出部分结果 + `paused` 状态而非硬失败——长章节写一半可 checkpoint 续写。
- **压缩后循环守卫（openclaw）**：压缩后立刻死循环检测（压缩本身不该引发重试风暴）。

### 2.3 上下文管理（context/）——重构核心（修两个架构级缺陷）

- **CJK-aware token 估算（hermes #2 + openclaw #4 综合）**：ASCII 4 字符/token、CJK 1 字 ≈ 1.5 token（保守系数，取两报告 1~4 的中值）、图片按固定 1500 token/张；**指纹缓存**（消息未变 O(1) 命中）。修复 `len//2` 粗糙估算（缺陷 #2）。
- **压缩状态实例化（修缺陷 #1）**：`CompactionState` 挂 harness 实例，多会话并发不再互相污染。
- **压缩护栏（openclaw #5 + hermes #3）**：失败冷却（摘要失败 30-60s 不再自动压缩）+ 无效压缩计数（压缩不生效则止住空转）+ 合理性校验（压缩后比压缩前大 → 拒绝）+ 写锁。
- **状态重注入（hermes #4）**：设定/大纲/人物卡等跨压缩存活状态以固定 header 重注入——这是小说 agent 最关键的上下文设计。
- **api_content sidecar（hermes #5）**：持久化存干净内容，API 发送存精确字节（含临时注入），注入内容永不污染存储。
- **KV-cache 契约（openhuman #1）**：system prompt 首轮构建后字节冻结，动态内容（快照/检索结果/steer）全部以用户消息附加——现已有 snapshot 临时拼入 system（harness.py:213），改为附加在尾部用户消息。

### 2.4 事件系统（events.py）——保留 + 小修

- **保留**：LoopEvent 事件模型、JSONL append-only、compaction 检查点作为真相源。
- **吸收**：稳定 event id（`{session_id}-evt-{offset}`，openhuman）、sink 异常隔离（一个消费者崩不影响后续，openclaw）、事件 payload 凭证打码（RedactingSink）。

### 2.5 会话持久化（session/）——保留 + 吸收

- **保留**：JSONL append-only transcript + compaction 记录（原始行不丢，openhuman 同款已验证）+ 前向兼容（_extra catch-all）。
- **吸收**：幂等键（user 消息重复投递安全，openclaw）、会话写锁、meta 进 SQLite（已有 agent_sessions 表）、**树形预留**：消息带 `parent_id` 字段（章节分叉/回滚的持久化基础，openclaw #6——本次只落字段不落 UI）。

### 2.6 工具框架（tools/）——保留 + 三处吸收

**保留**：@tool 自注册、三级权限（read/propose/write）、参数校验（带示例回填）、错误回填模型、事务 rollback。

**吸收**：
- **schema 从 pydantic 模型生成**（修缺陷 #4）：工具参数用 pydantic model 定义，JSON-schema 由模型生成——消除手写 schema 与实现漂移。
- **工具结果三级治理（openhuman #4）**：per-call 字节截断 → 超限摘要 → **artifact 落盘回传路径指针**——章节草稿/设定文档写文件、回传 `[artifact] path=... bytes=...`，大产出移出上下文。
- **能力探测 check_fn + TTL + 失败宽容（hermes #7）**：工具按运行环境自检可用性（本地/远程模型差异），30s 缓存 + 60s last-good 宽容防抖动。
- **结果归一化契约（hermes #6）**：handler 返回值收敛为 str 或结构化信封，违规转结构化错误。

### 2.7 Provider 层（providers/）——保留，预留扩展

**保留**：stream 优先/complete 派生、重试在 provider 层（含部分流拒绝重试保护）、ToolCall 容错解析、Usage 契约。

**预留**：ProviderProfile 声明式 quirk 描述（hermes #11）、provider-string + 抽象 tier（`draft/planning/review` 意图映射模型，openhuman #9）——本次实现配置层，多 provider 后续接入。

### 2.8 工作流图机制（workflow/）——全新，小说工作流的机制底座

**吸收 openhuman #3**：`plan → execute ⇄ review → finalize` durable 图：

```
plan ─▶ execute ─▶ review ──approved/maxed──▶ finalize ─▶ END
          ▲                   │
          └─────revise────────┘
```

- 条件路由 + 修订递归上限 + checkpoint + **per-step provenance**（每步 prompt+result 逐条记录，可审计可回滚）
- **机制与真实 agent 解耦**：节点 worker 注入（测试用确定性 mock，生产注入真实生成/评审实现）
- 小说映射：大纲 → 撰写 → 评审（一致性/格式/文风检查）⇄ 修订 → 定稿
- 这是领域无关的通用机制（任何题材的写作流程同构），符合六项工程不变量原则

## 3. 领域层设计（domain/）

| 子域 | 迁入内容（现有文件） | 说明 |
|---|---|---|
| writing/ | generation/、format_checker、structural_similarity、checkers、chapter_quality_review、chapter_continuity_review、chapter_revision_*、prompt_budget、dialog_prompts | 写作核心链：生成→校验→评审→修订 |
| memory/ | longform_memory、longform_context_summary、project_snapshot、narrative_plan_window、outline_lookup、memory_provenance_contract | 跨章记忆 |
| retrieval/ | athena_retrieval、entity_miner、embedding_service、few_shot_library、text_mentions、athena_entity_resolver | 检索与实体 |

**归档**（docs/archive/）：world_* 全套（~6k 行）、revision_feedback、self_optimization、prompt_optimizer、writing_scheduler（~2k 行）——用户已确认。

**边界规则**：
- domain 不 import core 的 harness/loop（只能通过工具注册 + 回调）
- core 零依赖 domain（保持 CADR-005）
- 领域工具（domain/tools/）是唯一桥：注册进 core.tools 的 registry

## 4. API 层设计（新 API，完全自由）

会话中心设计，事件流优先：

```
POST /api/v2/agent/sessions              创建会话（选项目/模型 tier）
POST /api/v2/agent/sessions/{id}/messages 发送消息 → SSE 事件流
POST /api/v2/agent/sessions/{id}/steer    生成中注入方向（steer 队列）
POST /api/v2/agent/sessions/{id}/followup 完成后追加要求（follow-up 队列）
POST /api/v2/agent/sessions/{id}/approve|reject   工具审批
GET  /api/v2/agent/sessions/{id}/events   事件重放（journal）
GET  /api/v2/agent/sessions/{id}/workflow 工作流图状态（plan/review 进度）
GET  /api/v2/projects/{id}/chapters      章节列表（写作成果）
```

- 事件协议：openclaw 风格 `agent_start → turn_start → ... → turn_end → agent_end`
- 错误编码进流（stopReason 归一化），调用方只处理一种流结束态

## 5. 数据层

- SQLite（data/mozhou.db）保留：projects/setups/outlines/chapter_contents/longform_memories/entity_candidates 等表结构不动（数据兼容）
- transcript 保持 JSONL（append-only + compaction 记录）
- 新增：artifact 落盘索引表（工具产出文件 → 路径/摘要/会话/章节）

## 6. 吸收点映射表（验证覆盖）

| 吸收项 | 来源 | 落点 | 状态 |
|---|---|---|---|
| TurnRetryState 对象化 | hermes #1 | core/turn_state.py | 新 |
| CJK token 估算 + 指纹缓存 | hermes #2 / openclaw #4 | core/context/estimate.py | 新（修缺陷#2） |
| 压缩失败冷却 + 无效计数 | hermes #3 | core/context/compaction.py | 新 |
| 状态重注入（设定/大纲） | hermes #4 | core/context/inject.py | 新 |
| api_content sidecar | hermes #5 | core/session/ | 新 |
| 工具结果归一化 | hermes #6 | core/tools/result.py | 新 |
| check_fn 能力探测 | hermes #7 | core/tools/ | 新 |
| 固定返回 + 退出原因 | hermes #8 | core/loop.py | 改 |
| 声明式 schema + 自动列补齐 | hermes #9 | models/ | 新 |
| 失败分类学 + root-cause | openhuman #10 | core/tools/result.py | 新（修缺陷#3） |
| 护栏家族（wall-clock/优雅暂停） | openhuman #2 | core/guards/ | 改 |
| plan→execute⇄review→finalize | openhuman #3 | core/workflow/ | 新 |
| 工具结果三级治理 | openhuman #4 | core/tools/artifact.py | 新 |
| 事件 journal + 稳定 id | openhuman #8 | core/events.py | 改 |
| 抽象 tier + provider-string | openhuman #9 | core/providers/config | 预留 |
| steer/followUp 双队列 | openclaw #1 | core/harness.py | 改 |
| 错误编码进流 | openclaw #2 | core/providers/base.py | 已有，强化 |
| compaction 护栏（写锁/合理性） | openclaw #5 | core/context/compaction.py | 新 |
| 树形 transcript 预留 | openclaw #6 | core/session/ | 预留 |
| 幂等键 + 写锁 | openclaw #5 | core/session/ | 新 |
| 测试双轨（mock LLM 测循环） | 三者共识 | tests/ | 新 |

## 7. 实施阶段（骨架新建路径）

```
阶段 0：归档准备 —— world_*/revision 等归档 docs/archive；现有测试全绿快照
阶段 1：内核骨架新建 —— core/（loop/turn_state/context/guards/events/session/tools/providers/workflow）
        + mock provider 测试设施（scripted 响应序列 + 请求形状断言）
        —— 验证：内核单测全绿（mock LLM 驱动循环，含重试/guard/压缩路径）
阶段 2：最小闭环 —— 新 API 层 + writing 最小链路（生成→格式校验→评审）+ 1 次真实生成验证
        —— 验证：一次真实 dogfood 生成 1-2 章
阶段 3：领域迁入 —— memory → retrieval → entities（逐子域迁移，纯函数测试随身移植）
        —— 验证：迁移后 200 章数据可读、原功能等价
阶段 4：旧代码清理 —— 旧 core/api/tools 删除，旧测试归档
        —— 验证：新架构全量测试绿 + 无死 import
阶段 5：回归与 dogfood —— 新一轮长程实验对比改进效果
```

## 8. 风险与权衡

| 风险 | 缓解 |
|---|---|
| 骨架新建期间系统不可用 | 旧后端保持可运行直至阶段 4（并行共存：新 API 独立前缀） |
| 领域迁移丢失行为契约 | 纯函数测试随身移植（用户已确认策略）；阶段 3 每子域有验证点 |
| 工作流图机制过度设计 | 只实现轻量版（线性 4 节点 + 修订循环），不加 fan-out/并行 |
| 工具结果落盘引入文件管理 | artifact 路径解析 fail-closed（拒绝绝对路径/`..`，openhuman 同款） |
| 树形 transcript 预留过深 | 只落 parent_id 字段，分支 UI/回滚功能不进本次范围 |

## 9. 明确不做（Out of Scope）

- 子代理/多 agent 编排（openclaw push 模型 / openhuman tier 规则）——本次只预留 registry 扩展点
- 前端（用户后续直接重写）
- goal 轻量目标系统（openclaw #8）——设计预留，不进骨架
- MCP 接入、OAuth、多 provider 全家桶
