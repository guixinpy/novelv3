# 08 · 参考项目学习吸收定稿（三轮学习 + 实施批次）

学习目标（2026-08-02 goal）：以 **hermes 第一优先 → openhuman 第二 → openclaw 第三**，充分吸收各模块优点，特化适配"专精于长篇网络小说创作的 agent"，不盲目照抄，架构保持优秀干净。

本文件是当前权威版本（07-reference-takeaways.md 为第一轮提炼，本文件吸收其结论并补充二、三轮成果）。

---

## 一、三轮学习进度

| 轮次 | 时间 | 方法 | 成果 |
|---|---|---|---|
| 第一轮 | 2026-06-11 | 深度拆解三个项目 | 07-reference-takeaways.md（模式级提炼） |
| 第二轮 | 2026-08-02 | 子代理对照审计新架构落实率 | openclaw ~65% / hermes ~67% / openhuman ~30%（结构层） |
| 第三轮 | 2026-08-02 | 子代理源码精读 + 自读核实 | 本文件（模块级细节 + 定稿清单） |

> 实现原则（用户指导）：子代理报告只是索引，实施任何吸收前必须**亲自阅读参考项目源码与本项目对应模块**。第二轮审计曾误判 openhuman 3 处（封箱/级联摘要/配额强制其实均已实现），教训即源于未覆盖 `learning/` 与 `agent/harness/` 目录。

## 二、第三轮精读要点（按优先级）

### hermes（第一优先：Python 实现模式）

**07 之外的新发现**：
1. **空响应恢复阶梯**（conversation_loop.py:6427-6700）——7 级有序恢复：部分流恢复 → 前置回合回退（仅限管家工具回合）→ 工具后空响应 nudge → thinking-only 续写 → 空重试 ×3 → fallback provider → 终局 `(empty)` 哨兵（不持久化为真实内容）。网文"写一半停"场景直接对应。**本项目缺失，本轮吸收最小版（nudge 重试）**。
2. **压缩摘要语义**（context_compressor.py:96-122）——摘要以 `[CONTEXT COMPACTION — REFERENCE ONLY]` 开头，语义："摘要中的请求已处理，只响应摘要之后的最新用户消息（latest message WINS）；反向信号（stop/undo）立即终止在途工作；工具仍全量可用"。历史事故：缺"工具仍可用"句曾导致压缩后 7 轮纯叙述不调工具。**本项目缺失权威语义句，本轮吸收**。
3. **防抖压缩守卫 + 探针恢复**（context_compressor.py:2572-2632）——连续 2 次节省 <10% 阻塞自动压缩 + 惰性武装恢复时钟 + 到期放行一次探针尝试；摘要 LLM 429 后 cooldown。本项目已有防抖/冷却（compaction.py:59-68），缺探针恢复（确定性摘要失败率低，价值有限，不吸收）。
4. **工具结果形状契约**（registry.py:646-675）——handler 只允许返回 str 或带 `_multimodal` 信封的 dict，违规转结构化错误。**本项目已落实**（tools/base.py:108 `_normalize_handler_result`）。
5. **回合退出诊断枚举**（conversation_loop.py:1271 `_turn_exit_reason`）——每次循环退出写具名原因（interrupted_by_user/budget_exhausted/guardrail_halt/…）。本项目已有 StopReason 六值枚举 + exit_detail（loop.py:42），形态等价，不吸收。
6. **check_fn 抖动吸收**（registry.py:216-279）——工具可用性探测 30s TTL + 失败后 60s 宽限期（宽限内抖动不剥工具）。本项目无外部探测工具，暂不适用；接入图片生成/外部检索时启用。
7. **工具副作用前增量持久化**（conversation_loop.py:6159-6185）——执行有副作用工具前先把工具调用回合落盘，持久化失败则断回合。本项目为回合末落盘（harness.py:311），崩溃会丢工具调用记录。**列入 B 类**。
8. **出站字节稳定性归一化**（conversation_loop.py:1713-1750）——出站消息 strip + tool arguments 规范化 json.dumps。本项目纯云端 DeepSeek + system 字节冻结契约（harness.py:243），等价已覆盖，不吸收。

### openhuman（第二优先：记忆机制）

**第二轮审计修正**（本快照实测）：①封箱已实现且按 token 强制（`INPUT_TOKEN_BUDGET=50_000`，L≥1 按 `SUMMARY_FANOUT=10`，3h 调度 + 7d 龄期兜底）；②摘要确有内容级联（LLM 聚合子条目，temperature=0）；③多通道召回配额**全部代码强制**（`WORKING_MEMORY_LIMIT=3` 等常量 + 2000 字符全局预算 + 分数过滤），非提示语。

**七机制要点**（精读 self）：

| 机制 | 核心实现 | 网文适配判断 |
|---|---|---|
| 1 确定性 chunk ID | `sha256(kind\|id\|seq_be\|content)` 前 32 hex；来源级原子认领去重 | 章级幂等重处理可用；本项目已有 content-hash 跳过（athena_retrieval.py:1215），评估后再定 |
| 2 层级摘要级联 | 50k token L0 门 + fanout 10 + LLM 聚合 + 原子提交（摘要+实体+向量+边） | **部分吸收**：50k≈16-25 章≈一卷量级，阈值形态合适；注意 **openhuman 已删除全书梗概**，网文最需要它 → 自建 |
| 3 多通道召回配额 | 工作记忆 3 / 前对话 3（仅 high 前缀）/ 跨聊 3（240 字符截断）/ 语义 5 + 全局 2000 字符预算 + min_relevance 过滤 | 映射：设定卡/人物卡/前文/跨卷通道，**吸收**（B 类，与记忆系统开发一并做） |
| 4 实体共现图 | 同节点实体两两成对建无向边（存最近时间戳），与实体索引同事务；`pair_distances` 有界 BFS 关联召回 | **吸收**（B 类）：改存 (count, last_ts) 双字段；网文人名识别用领域词表+regex |
| 5 证据加权稳定性 | 权重表 Explicit 1.0/Structural 0.9/Behavioral 0.7/Recurrence 0.6 + `exp(-Δt/半衰期)` 衰减 + τ=1.5/0.7/0.4 + 类预算 + Pinned 恒 Active | **吸收**（B 类）：映射"设定可靠性"，per-book 自优化核心机制 |
| 6 廉价信号 + LLM 边界准入 | ≥0.85 直接收 / ≤0.15 直接丢 / 中间才调 LLM（单次 JSON 输出 NER+重要性），0.3 终审 | **吸收**（B 类）：信号替换为网文特征（对话密度/来源权重/实体密度） |
| 7 不可信背景标记 | `<untrusted-source source=…>` 包裹 + `&<>` 转义防提前闭合 + default-deny namespace | **吸收**（B 类）：建议直接做 typed Provenance 枚举（openhuman 自承的临时启发式的正解） |

### openclaw（第三优先：内核工程结构）

1. **完整钩子体系**（agent-loop.ts types.ts:169-339）——11 个钩子位：convertToLlm/transformContext/getApiKey/beforeToolCall/resolveDeferredTool/afterToolCall/afterToolOutcome/prepareNextTurn/shouldStopAfterTurn/getSteeringMessages/getFollowUpMessages。契约：**工具链钩子异常隔离**（变错误 toolResult 进历史），**回合链钩子 must-not-throw**（冒泡则整 run 失败）。本项目只有 before_tool_call 单钩子位。**列入 B 类（内核 API 演进，需设计评审）**。
2. **afterToolCall 字段级部分覆盖**（types.ts:80-89）——content/details/isError/terminate 各自 `??` 保留原值，不深合并；仅执行过的调用才进 afterToolCall（未执行走 afterToolOutcome）；批次内全部 terminate 才停。网文场景：章节工具原始输出 → 规范化结构再入上下文。
3. **prepareNextTurn 调参**（types.ts:158-165）——每回合一次，仅 context/model/thinkingLevel 三字段；预算止步用 shouldStopAfterTurn。网文：起草章便宜模型 / 正文贵模型的跨回合换模。
4. **save_point 结论**：**openclaw 自身没有显式 save_point**——逐条落盘 + boundary 条目（compaction/reset）承担恢复角色，全量历史永不删除（docs/concepts/compaction.md:19 "Compaction only changes what the model sees"）。本项目压缩检查点 + 逐条落盘已等价；卷/章级命名回滚属 P2 待定（前端需要时设计）。
5. **消息 ID**：无稳定消息 ID；条目短 ID + parentId 链 + `firstKeptEntryId` 锚点。本项目全量快照落盘是超集，不吸收；章节级寻址需求出现时再设计。
6. **三队列精确语义**——steering（回合间注入）/ follow-up（内层循环退出后）/ next-turn（下一次外部 prompt 时附带）；排空模式 `"all"|"one-at-a-time"`；"连写 N 章"= 会话层 continue 循环。本项目双队列已覆盖全部语义（next-turn 合并入 follow-up），不吸收。
7. **周边**：turnTainted 污染传播（web 素材场景可用）、"先记忆后压缩"（压缩前静默 memory flush——网文长卷连载可借鉴，B 类）、分回合摘要（一章写不完的截断场景）、`/compact 聚焦点`。

## 三、吸收定稿清单

### A 类：立即吸收（低风险纯工程，本轮实施）

| # | 吸收项 | 出处 | 落点 | 状态 |
|---|---|---|---|---|
| A1 | 空响应最小恢复（nudge 重试 ×2） | hermes | loop.py + turn_state.py | 本轮 |
| A2 | 压缩摘要"最新消息唯一权威"语义 | hermes | compaction.py | 本轮 |

### B 类：需设计讨论（涉及功能设计/内核 API，先讨论需求再实施）

| # | 吸收项 | 出处 | 状态 |
|---|---|---|---|
| B1 | 钩子体系扩展（afterToolCall/transformContext/shouldStopAfterTurn/afterToolOutcome）+ 护栏钩子化 | openclaw | **护栏钩子化已完成**（guard_system 注入，2026-08-02）；剩余钩子位无消费方暂缓 |
| B2 | 工具副作用前增量持久化 | hermes | 条件触发（write_chapter 幂等已覆盖边际价值；断点恢复需求出现时） |
| B3 | 多通道召回配额代码强制 | openhuman | **已完成**（memory_service._cap_by_channel，2026-08-02） |
| B4 | 层级摘要内容级联 + 全书梗概自建 | openhuman | 待定（LLM 聚合成本需确认；写作经验 MVP 未含） |
| B5 | 实体共现图 | openhuman | **已完成**（entity_relation 模型 + 建边/查询 + get_entities 接线，2026-08-02） |
| B6 | 证据加权稳定性检测 | openhuman | **特化完成**（writing_experience 信任度记账 new/reinforce/override + 30 章衰减 + pinned，09 定稿） |
| B7 | 廉价信号 + LLM 边界准入 | openhuman | **特化完成**（自省 LLM 顺带准入，不做三带打分——自省已是 LLM 的适配结论，09 定稿） |
| B8 | 不可信背景标记（typed Provenance） | openhuman | **部分完成**（快照经验段"仅供参考"标记 + 自省纪律防情节内容；typed Provenance 枚举留待外部资料导入） |
| B9 | "先记忆后压缩" | openclaw | 条件触发（压缩链强化时） |
| B10 | check_fn 抖动吸收 | hermes | 条件触发（接入外部探测工具时） |

### C 类：不吸收（已有替代 / 价值有限 / 与原则冲突），记档备查

- hermes 工具 import 自注册——本项目中央装配点显式优于隐式（新增工具改动 agent.py 一处即可，代价可控）
- hermes 三层系统提示——与 KV-cache 前缀冻结契约冲突，2 层形态（system 冻结 + 动态尾部 user）已有合理理由
- hermes 出站字节归一化、压缩旁路计数、守卫闸——已有等价/不适用
- openclaw 消息 ID、三队列、save_point、分回合摘要的机制本身——已有替代或 P2 待定
- openhuman 全书梗概——非"不吸收"，而是 openhuman 已删、需自建（归 B4）
- 全部特化词表/题材档案类实现——与六项工程不变量（题材无关）原则冲突，永久不吸收

## 四、实施记录

- 2026-08-02：**A1、A2 完成**（含测试，91 passed）
  - A1 空响应最小恢复：`core/loop.py` 空响应时注入引导 user 消息重试（上限 2 次，防"写一半停"静默结束）；`core/turn_state.py` 加 `empty_response_retries` 计数。测试：`test_empty_response_nudged_then_completed` / `test_empty_response_exhausted_ends_turn`
  - A2 压缩摘要语义：`core/context/compaction.py` 新增 `REFERENCE_ONLY_NOTE`（"摘要中的请求均已处理完毕，不要继续执行摘要中描述的任务；请只响应摘要之后的最新用户消息"）注入摘要首段。测试：`test_summary_includes_reference_only_semantics`
  - 验证：91 passed / ruff 无新增错误
- 2026-08-02：**B3 + B1 部分（护栏注入化）完成**（95 passed）
  - B3 记忆通道配额强制（openhuman）：`domain/memory/memory_service.py` 新增 `_CHANNEL_LIMITS`（arc_summary≤3 / plotline≤5 / 其他≤3）+ `_cap_by_channel`——混合查询时每通道硬截断，guideline 从提示语变为代码；单类型查询不受影响。测试：`tests/agent/test_memory_service.py`（3 个）
  - B1 部分（openclaw 钩子化）：`core/loop.py` `run_turn` 新增 `guard_system` 注入参数（默认五级护栏不变），护栏从引擎内硬实例化变为可注入。测试：`test_custom_guard_system_injected`
  - B2 暂缓：write_chapter 按 chapter_index 幂等（更新而非新建，writing_tools.py:58-80），崩溃重试不产生重复章节，增量持久化边际价值被幂等覆盖——条件触发（断点恢复需求出现时）
  - 验证：95 passed
- 2026-08-02：**B5 实体共现图（数据层）完成**（98 passed）
  - 新模型 `app/models/entity_relation.py`（EntityRelation：project/entity_a/entity_b 唯一 + count + last_chapter——openhuman 边表特化，存 (count, last_ts) 双字段）
  - `domain/retrieval/entity_miner.py` 新增 `record_entity_cooccurrences`（同章两两建边，同章不累计、新章 count+1，无向按字典序）+ `related_entities`（按共现次数降序，默认 only_promoted 挡噪声边）
  - 工具接线：`get_entities` 提供文本时登记候选后同步建边（返回形状不变）；查询侧消费接线（如人物关联注入）留待记忆系统开发时设计
  - 测试：`tests/agent/test_entity_relations.py`（3 个）
  - 验证：98 passed
