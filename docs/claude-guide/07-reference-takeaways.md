# 07 · 参考项目核心优点提炼

三个参考项目快照位于 `references/agent-projects/`（commit 见该目录 README）。本文档是 2026-06-11 深度拆解的结论：**采纳什么、如何适配、明确不抄什么**。上一版的分析报告（`../archive/others/01-reference-patterns-report.md`）部分结论已吸收，本文档为当前权威版本。

---

## hermes-agent（Python，与我们形态最接近）

### 采纳

| 模式 | 出处 | 落点 |
| --- | --- | --- |
| 工具自注册（模块 import 时 register，无中央清单） | `tools/registry.py` | `tools/` 全目录（CADR-003） |
| 三层系统提示（稳定/上下文/易变），稳定层吃 prefix cache | `agent/system_prompt.py` | `agent/context.py`；百章长会话省 75% 输入 token |
| 迭代预算 + refund + 一次性恢复守卫（TurnRetryState） | `agent/iteration_budget.py` | `agent/budget.py`；只读工具调用退还额度 |
| ProviderTransport 抽象（子类只做格式转换） | `agent/transports/base.py` | `agent/providers/`（CADR-006） |
| 辅助模型上下文压缩（头尾保护 + 中段摘要 + REFERENCE ONLY 标记） | `agent/context_compressor.py` | `agent/compaction.py`；75% 阈值触发 |
| 流式 + 打断 + steering 消息排空 | `agent/conversation_loop.py` | `harness.py`；作者可中途插话改方向 |

### 不抄

- 11 个 provider 适配迷宫（我们 1+1 个）
- 完整 TUI、ACP 适配器、多平台接入
- 4245 行的 conversation_loop 体量——我们的内核目标 ≤800 行

---

## openclaw（TypeScript，工程结构最佳）

### 采纳

| 模式 | 出处 | 落点 |
| --- | --- | --- |
| loop（无状态纯引擎）与 harness（有状态外壳）分离 | `agent-core/src/agent-loop.ts` | `agent/loop.py` + `agent/harness.py`；回合逻辑可独立测试 |
| 三队列消息注入（steering / follow-up / next-turn） | agent-loop 270-387 行 | `harness.py`；「连写 N 章」= follow-up 队列驱动（M3） |
| 钩子扩展（beforeToolCall 可拦截、afterToolCall 可修补、prepareNextTurn 可调参） | `harness/agent-harness.ts` | 审批门与护栏全部以钩子实现，不做配置表 |
| JSONL 追加式会话日志 + 回合边界落盘 + save_point | `harness/session/session.ts` | `harness.py`（CADR-004）；断点恢复 |
| 压缩条目入会话日志（摘要 + 首保留条目 ID，可回放） | `harness/compaction/compaction.ts` | `agent/compaction.py` |
| 消息双段变换（transformContext 域内 / convertToLlm 供应商） | `types.ts` 139-244 行 | `agent/context.py`；记忆注入与供应商格式解耦 |

### 不抄

- Gateway 多用户分布式协议、进程租约/收割器
- 插件签名校验、provider 注册市场
- 会话分支树（线性会话 + 显式版本快照足够；写作「多结局探索」需求出现时重审）

---

## openhuman（Rust，记忆架构最深）

### 采纳（主要落在 M4）

| 模式 | 出处 | 落点 |
| --- | --- | --- |
| 确定性 chunk ID（sha256(source|seq)），幂等重入 | `memory_store/chunks/` | `domain/memory/append()`；章节重处理安全 |
| 层级摘要级联（L0 桶满封箱 → L1 → L2，自动维护全书梗概） | `memory_tree/tree/bucket_seal.rs` | `domain/memory/cascade()`；章→卷→书三级 |
| 多通道上下文召回（语义/工作记忆/跨会话/历史，各通道独立配额） | `agent_memory/memory_loader.rs` | `domain/memory/recall()`；适配为语义/实体/情节线/工作记忆四通道 |
| 实体索引 + 共现图（chunk 标注实体，同叶共现即边） | `memory_entities/` | M4 实体状态卡与关系查询 |
| 证据加权的稳定性检测（显式 1.0 > 结构 0.9 > 行为 0.7 > 复现 0.6，半衰期衰减） | `learning/candidate.rs` | 「该人物性格是否已确立」的置信度模型（M5 候选） |
| 廉价信号优先、LLM 仅评边界样本的准入打分 | `memory_tree/score/` | 控制百万字级归档的 LLM 成本 |
| 记忆内容标注为「不可信背景数据」注入 | `harness/memory_context_safety.rs` | 防记忆内容劫持指令 |

### 不抄 / 需自建补足

- 多源连接器（Gmail/Slack 等）——无关
- 后台 subconscious 引擎——M3 的护栏检查点形态更可控，长程反思在 M5 重审
- **openhuman 没有的、我们必须自建的**：情节线/伏笔追踪、人物弧线模型（「性格应该如何变化」而不仅是「性格是什么」）。它管事实，不管叙事。

---

## 综合：三项目分工

```
openclaw   → 内核工程结构（loop/harness/钩子/会话持久化/队列）
hermes     → Python 实现模式（工具注册/提示词分层/预算/压缩/provider）
openhuman  → 记忆与一致性（确定性归档/摘要级联/多通道召回/实体图/稳定性）
自建        → 叙事领域层（伏笔、弧线、节奏、网文文体）+ 移植旧版护栏算法
```
