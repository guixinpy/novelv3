# 00 · 后端架构总览

> 状态：与 main 同步（2026-08-10）｜154 passed / ruff 全过

## 一、三层架构

```
backend/
├── core/        领域无关内核 —— 不感知"网文"，可复用于任何 agent
├── domain/      网文领域层 —— writing / memory / retrieval 业务
└── app/         数据模型（SQLAlchemy）+ FastAPI v2 API
```

**依赖方向单向**：core ← domain ← app。core 不 import domain（快照注入通过回调接口解耦）。

## 二、核心设计原则

| 原则 | 落点 |
|---|---|
| 事件流唯一事实 | 所有消费者（SSE/持久化/观测）消费同一事件流（core/events.py） |
| 无状态内核 | run_turn 不持有会话状态，状态由 harness 持有、事件经 sink 发出 |
| 工具描述与业务分离 | domain/tools 只做 pydantic 校验 + 服务调用，业务在 domain/ 服务层 |
| KV-cache 契约 | system prompt 首轮构建字节冻结，动态内容（快照）骑尾部 user 消息 |
| 题材无关 | 任何提示词/示例不含具体小说元素；规则只保留对所有题材成立的工程不变量 |
| fail-open 哲学 | 自省/聚合/快照失败只记日志，不阻塞写作流程 |

## 三、一次写作回合的数据流

```
POST /api/v2/agent/sessions/{id}/messages
  → AgentHarness.send（写锁 + 幂等键）
    → 构建 system prompt + 项目快照（project_snapshot）→ transcript.messages
    → run_turn 循环：
        provider.stream（DeepSeek，部分流恢复）→ 事件 → 工具执行（审批门拦截 write）
        ← 护栏（循环风险/预算/墙钟）→ steering 注入
    → 事件流 → SSE 推送（agent_start → turn_start → … → turn_end → agent_end）
  → BackgroundTasks：章末自省（经验记账 + 伏笔提取）+ 弧线聚合（流外，客户端断开不受影响）
  → 下一回合快照自动携带：写作经验（信任度记账）+ 到期伏笔清单
```

## 四、core/ 模块

| 模块 | 职责 |
|---|---|
| `loop.py` | **无状态回合引擎**：LLM 调用→工具执行→观察回填循环；停止原因分类；部分流恢复；空响应 nudge；护栏注入 |
| `harness.py` | **有状态外壳**：转录持有、steer/follow-up 双队列、压缩状态（实例级）、幂等键、写锁、快照/护栏注入点 |
| `events.py` | 事件模型（agent_start/AssistantDelta/ToolFinished/…）：SSE 与持久化的唯一事实流 |
| `session/transcript.py` | append-only JSONL 转录 + 压缩检查点 + ephemeral 单点拦截（内部消息不落盘） |
| `context/compaction.py` | 上下文压缩：用量预检、Token 预算尾部保护、压缩后循环守卫 |
| `context/estimate.py` | CJK-aware token 估算（启发式） |
| `guards/loop_guards.py` | 五级循环风险检测（重复工具/错误循环等），可注入替换 |
| `guards/budget.py` | 迭代/令牌预算（consume/refund，只读工具返还额度） |
| `turn_state.py` | 回合状态对象（墙钟/错误/护栏记录收敛为可单测对象） |
| `approval.py` | **审批门**（线程安全）：write 工具调用拦截 → Pending 事件 → approve/reject |
| `providers/base.py` | Provider 抽象：格式转换与流解析归一化、retryable 错误分类 |
| `providers/deepseek.py` | DeepSeek 实现（流式/工具调用/用量归一） |
| `tools/base.py` | 工具框架：注册、权限分级（read/write）、pydantic schema 校验、失败分类 |
| `tools/artifact.py` | Artifact 落盘路径校验（fail-closed 防路径逃逸） |
| `workflow/base.py` | 工作流图机制（plan → execute ⇄ review → finalize，供 pipeline 用） |

## 五、domain/ 模块

### writing（写作）
| 模块 | 职责 |
|---|---|
| `pipeline.py` | 章节写作管线（workflow 图落地）：plan（组上下文）→ execute（生成）→ review（格式校验，不过则 REVISE）→ finalize |
| `chapter_gen.py` | 最小上下文生成（大纲章节 + 上章摘要 + 项目快照）→ 章节文本 |
| `format_checker.py` | 输出格式校验纯函数（全角引号/markdown 残留/备选词等确定性规则） |
| `structural_similarity.py` | 结构级重复检测（标题重复防循环） |
| `prompt_budget.py` | 上下文预算截断（priority 排序 + 头尾保留） |
| `chapter_utils.py` | 章节辅助函数 |

### memory（记忆）
| 模块 | 职责 |
|---|---|
| `memory_service.py` | **记忆服务中枢**：弧线（plan_arc）、伏笔账本（track_plotline + plotline_apply_updates）、记忆查询（query_memory，通道配额）、记忆树、弧线聚合 |
| `writing_experience.py` | **per-book 自优化**（09 定稿）：章末自省（LLM 短调用）→ 经验记账（信任度：new/reinforce/override + 30 章惰性衰减 + 预算淘汰）→ 注入条目；**伏笔提取**（同一次调用顺带输出 plotline_updates） |
| `project_snapshot.py` | 回合级项目状态快照（章节进度/活跃弧线/最近 3 章/**到期伏笔清单**/事实表/写作经验），拼进 system 消息 |
| `longform_memory.py` | 跨章记忆维护：get_or_create/重建/章节记忆刷新/上下文包组装/维护诊断 |
| `outline_lookup.py` | 大纲章节查找（含正文回填大纲） |
| `project_stats.py` | 项目统计（字数等） |

### retrieval（检索）
| 模块 | 职责 |
|---|---|
| `athena_retrieval.py` | **检索主服务**：倒排索引（分词→term 索引）、章节/记忆/设定卡多源检索、查询感知上下文组装、索引重建 |
| `entity_miner.py` | 实体候选提取（姓氏白名单 + 模式），跨 ≥2 章转正 |
| `embedding_service.py` | 向量：本地哈希 provider（默认）/ OpenAI 兼容远程；tokenize/归一化/余弦相似度 |
| `few_shot_library.py` | few-shot 示例库（记忆提示用） |
| `text_mentions.py` | 确定性提取共用文本工具 |

### tools（工具层，模型可调用）
| 工具 | 权限 | 作用 |
|---|---|---|
| `write_chapter` | write（审批） | 生成结果落库 + artifact 落盘 |
| `check_chapter_format` | write | 格式守门员 |
| `plan_arc` | write | 弧线定义/进度/列出 |
| `track_plotline` | write | 伏笔 open/close/**postpone**/query（含到期标记） |
| `query_memory` | read | 记忆检索（通道配额强制） |
| `memory_tree` | read | 层级记忆树（project → arc → chapter → plotline） |
| `get_entities` | read | 实体挖掘候选 + 转正查询 |
| `retrieve` | read | 多源检索 |

## 六、app/ 模块

| 模块 | 职责 |
|---|---|
| `main.py` | FastAPI 入口（仅挂 v2 API；旧 v1 已退役） |
| `api/v2/agent.py` | **v2 API**：项目/会话创建、消息发送（SSE 流）、steer/follow-up、审批四端点、事件重放；会话注册表（进程内 + 磁盘懒重建 + 空闲淘汰）；章末自省后台任务触发点 |
| `db.py` | 引擎 + Session 工厂（WAL/外键/busy_timeout） |
| `config.py` | API key 加载等 |
| `models/` | 数据表（见下） |

### 数据表
| 表 | 作用 |
|---|---|
| `projects` | 项目 |
| `chapter_contents` | 章节正文 |
| `outlines` | 大纲 |
| `setups` | 设定卡（角色/世界观/格式规范） |
| `longform_memories` | **记忆主表**：arc_summary / story_arc / plotline（伏笔账本）/ writing_experience / introspect_log，字段扩展走 memory_metadata JSON |
| `retrieval_documents` / `retrieval_chunks` / `retrieval_terms` / `retrieval_embeddings` | 检索索引（文档/分块/倒排 term/向量） |
| `entity_candidates` / `entity_relations` | 实体挖掘候选与关系 |

## 七、关键机制速览

| 机制 | 位置 | 说明 |
|---|---|---|
| SSE 事件协议 | app/api/v2/agent.py | 事件带稳定 id（{session}-evt-{offset}），前端按 `10-frontend-api-contract.md` 对接 |
| 审批门 | core/approval.py | write 工具拦截 → Pending 事件 → 前端 approve/reject；线程安全（threading.Event + to_thread） |
| 自省触发点 | agent.py BackgroundTasks | SSE 流外执行，差集推导未自省章（乱序写章不漏检），每批 ≤3 章，fail-open |
| 伏笔账本 | memory_service + writing_experience | 自省同调用提取 open/close/postpone → memory_metadata（expected_resolve_chapter/payoff）→ 快照到期清单（超期优先 ≤3 条） |
| 部分流恢复 | core/loop.py | 仅 retryable 错误且有流式文本时保留已生成内容 |
| ephemeral 拦截 | transcript.py 单点 | 内部注入（nudge/恢复建议/steering）不落盘不重放 |

## 八、文档索引

| 文档 | 内容 |
|---|---|
| `09-per-book-self-optimization.md` | 自优化系统设计定稿（自省/信任度/注入） |
| `11-plotline-ledger.md` | 伏笔账本设计定稿 |
| `10-frontend-api-contract.md` | 前后端对接契约（9 端点 + SSE 事件 + 7 表） |
| `08-learning-absorption.md` | 三开源项目吸收清单（hermes/openhuman/openclaw） |
| `05-progress-tracker.md` | 200 章实验验证记录 |
