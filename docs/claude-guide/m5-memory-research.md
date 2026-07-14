# M5 记忆系统研究笔记

从参考项目（hermes-agent, openclaw, openhuman）中提取可应用于 novelv3 的长记忆设计模式。

## 来源项目

| 项目 | 版本 | 关键贡献 |
|------|------|----------|
| hermes-agent | `fe54960` | 三层记忆体系 + 上下文压缩算法 + Frozen Snapshot |
| openclaw | `0bcabea` | 三阶段梦境巩固 + Score-Gated Promotion + Memory Flush |
| openhuman | `07e60af` | 两阶段摄取 + 层级摘要树 + 按需知识图谱 + 来源标记(Taint) |

## hermes-agent 核心模式

### 1. Frozen Snapshot（冻结快照）
- **做法**：工具写入立即持久化到磁盘，但系统提示词中的记忆快照只在会话开始时加载一次
- **收益**：保持整个会话的提示词前缀缓存有效，避免每次写入后重新缓存
- **novelv3 适用**：当前 LongformMemory 每次查询都是实时的 — 可考虑在 harness 初始化时加载记忆快照

### 2. Token-Budget Tail Protection（令牌预算尾部保护）
- **做法**：压缩时不固定保留最后 N 条消息，而是从末尾向前累加令牌直到达到窗口的 20%
- **收益**：自适应不同模型的上下文窗口，确保最后一条用户消息始终在尾部
- **novelv3 适用**：compaction.py 当前只是预检（warning），可改为主动压缩 + token-budget 尾部保护

### 3. Anti-Thrashing Guard（防抖保护）
- **做法**：追踪最近 2 次压缩效果，如果每次只节省 <10%，则跳过压缩
- **收益**：避免工具 schema 等高开销内容导致的无限压缩循环
- **novelv3 适用**：可直接移植

### 4. Deterministic Fallback Summary（确定性回退摘要）
- **做法**：LLM 摘要不可用时，从本地可提取信息（用户提问、工具动作、文件名、错误文本）构建结构化交接
- **novelv3 适用**：novelv3 不需要 LLM 来做压缩摘要（领域专精），但确定性回退思路可用于章节记忆摘要

### 5. Three-Tier System Prompt（三层提示词）
- **Stable 层**：身份、工具指引 — 永不变
- **Context 层**：项目上下文 — 跨会话变
- **Volatile 层**：记忆快照、时间戳 — 仅压缩时变
- **novelv3 适用**：当前 system prompt 不分层，可引入分层以提升缓存命中率

### 6. Memory Store 条目管理
- 用 `\n§\n` 分隔条目
- 字符限制（而非令牌限制）：MEMORY.md 2200 字符，USER.md 1375 字符
- `add`/`replace`/`remove` 通过子串匹配
- **novelv3 适用**：当前 LongformMemory 是 SQL 行级管理，比文件更精确

## novelv3 可立即采用的改进

### P0: 弧线记忆持久化
当弧线完成时，自动生成弧线摘要存入 LongformMemory（memory_type="arc_summary"）

### P1: 压缩算法增强
- Token-budget 尾部保护（替换当前固定策略）
- 防抖保护
- 章节记忆压缩（不依赖 LLM，用确定性方法）

### P2: 提示词分层
引入 Stable/Context/Volatile 三层，提升 DeepSeek API 前缀缓存命中率

### P3: 质量趋势记忆
`check_quality_trend` 的结果持久化到 LongformMemory，跨会话可见

---

## openhuman 核心模式

### 1. 两阶段摄取（Hot + Cold Path）
- **热路径**：规范化 → 分块 → 快速评分 → 持久化（同步，即时完成）
- **冷路径**：实体提取（LLM）→ 准入评分 → 树缓冲 → 桶密封级联 → 每日摘要（异步作业队列）
- **novelv3 适用**：章节写入后可走热路径（即时 track_plotline + query_memory），弧线完成时走冷路径（LLM 摘要 + 实体索引更新）

### 2. MemoryTaint 来源标记
- 区分 `Internal`（用户直接写入）vs `ExternalSync`（外部源同步）来源
- 外部标记的内容在 subconscious 处理时自动降权，防止外部来源触发有副作用的工具调用
- **novelv3 适用**：区分「作者明确设定」vs「Agent 推理」的记忆来源，防止 Agent 把自己的推测当作设定事实

### 3. 层级摘要树（Memory Tree）
- `root → year → month → day → hour (leaf)`，每层通过 LLM 折叠子节点为父节点摘要
- 桶密封（bucket_seal）：缓冲达到阈值 → 触发级联密封
- 热信号追踪：哪些节点正在被访问
- **novelv3 适用**：可将弧线 → 章节 → 场景建模为三层树，弧线完成时密封桶 → LLM 生成弧线摘要

### 4. 按需知识图谱（On-Demand Graph）
- 不存储独立图数据库，实体共现边在查询时从树节点推导
- `co_occurring_entities()` 检查两个实体是否在同一叶子节点出现
- **novelv3 适用**：world_checker 不需要独立的实体图，查询时从 LongformMemory + chapters 中推导实体共现

### 5. 上下文注入上限（Constrained Injection）
- [Memory context]: 最多 5 条，min_relevance >= 0.4
- [User working memory]: 最多 3 条
- [Cross-chat context]: 最多 3 条，每条 ≤240 字符
- **novelv3 适用**：每次 LLM 调用前注入的记忆条目应有严格上限，用质量替代数量

### 6. Archivist 自动归档
- 对话通过 archivist 自动写入摘要树和 episodic 存储，无需 agent 显式调用 memory_store
- **novelv3 适用**：增强 arc_consolidation，让 arc_summary 的生成更自动化（当前需手动触发 plan_arc progress）

---

## 跨项目模式对比

| 模式 | hermes-agent | openclaw | openhuman | novelv3 现状 |
|------|-------------|----------|-----------|-------------|
| **记忆持久化** | 文件(MEMORY.md) | 文件(MEMORY.md) | SQLite+向量 | LongformMemory (SQLite) |
| **上下文压缩** | Token-budget tail | 双模式 (default/safeguard) | 树形摘要 | ✅ 已增强 (M5) |
| **跨会话** | 会话 lineage DAG | 会话 DAG + 梦境 | FTS5 跨会话搜索 | ❌ 无 |
| **来源标记** | Threat scanner | MemoryTaint (subconscious)  | ✅ MemoryTaint | ❌ 无 |
| **知识图谱** | 无 | 无 | ✅ 按需推导 | ❌ 无 |
| **记忆巩固** | Frozen Snapshot | ✅ 三阶段梦境 | ✅ 两阶段摄取 | 🔶 弧线巩固 (M5) |
| **注入控制** | 字符限制 | Token budget aware | ✅ 严格上限 (3+3+5) | ❌ 无上限 |

---

## 下一步优先级（跨项目综合）

### P0: 上下文注入上限 (openhuman 模式)
每次 LLM 调用前通过 query_memory 注入的相关记忆 ≤5条，每类记忆有明确上限

### P1: 来源标记 (MemoryTaint)  
区分 author_explicit（作者显式设定）vs agent_inferred（Agent 推理），防止推理被当作事实

### P2: 按需实体共现 (openhuman On-Demand Graph)
world_checker 查询时不依赖预建图，从 LongformMemory 动态推导实体关系

### P3: 跨会话记忆 (hermes-agent session DAG)
不同写作会话之间共享弧线摘要和设定记忆，支持长期项目
