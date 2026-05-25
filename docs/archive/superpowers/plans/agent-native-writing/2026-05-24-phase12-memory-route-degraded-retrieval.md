# Phase12: Memory Route Degraded Retrieval Coverage

## 背景

当前 Agent 化目标要求系统能像写作 Agent 一样自主判断“能否继续写、需要先读什么、哪些写操作需要确认”。参考 openhuman 的有界召回和来源可解释性，以及 openclaw 的状态化 Active Memory fallback，本阶段处理 `inspect_agent_memory_route` 的一个缺口：长篇记忆存在且维护状态可写，但检索索引为空时，系统不应简单 blocked，也不应假装 fully available，而应暴露 `degraded` 状态和读写分离的恢复建议。

## 假设

- `LongformMemory` 已有章节级记忆，说明 Agent 仍具备继续写作的基础上下文。
- `RetrievalDocument` 为空会降低跨章节召回质量，但不必阻断所有写作。
- 自动 follow-up 只能安全执行只读诊断；索引修复类写操作必须保留为需要确认的建议。

## 目标

1. 当长篇记忆存在、维护状态 ready、检索文档为 0 时，`memory_provenance.status` 返回 `degraded`。
2. `memory_provenance.recovery` 提供只读诊断工具，便于 Agent 自动继续定位问题。
3. `memory_provenance.recovery.write_tools` 单独列出写入型修复工具，避免 Agent 在未确认时自动修改状态。

## 验证

- T0: `pytest tests/test_writing_agent_memory_route.py -k degraded -q`
- T1: `pytest tests/test_writing_agent_memory_route.py tests/test_writing_agent_tool_executor.py -k "memory_route or inspect_agent_memory_route" -q`

## 风险控制

- 不改动真实维护/检索构建逻辑，只改 Agent 路由输出契约。
- 不新增自动写入执行路径。
- 保持既有 blocked/sparse/available 状态不变。
