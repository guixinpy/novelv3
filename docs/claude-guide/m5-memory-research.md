# M5 记忆系统研究笔记

从参考项目（hermes-agent, openclaw, openhuman）中提取可应用于 novelv3 的长记忆设计模式。

## 来源项目

| 项目 | 版本 | 关键贡献 |
|------|------|----------|
| hermes-agent | `fe54960` | 三层记忆体系 + 上下文压缩算法 + Frozen Snapshot |
| openclaw | `0bcabea` | 三阶段梦境巩固 + Score-Gated Promotion + Memory Flush |
| openhuman | `07e60af` | (待分析) |

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
