# Phase 11: Memory Route Provenance

## 背景

Phase 10 将 longform context exhausted 状态导向 `inspect_agent_memory_route`。但该工具当前只返回散落的 `longform_memory`、`longform_maintenance`、`retrieval` 和 `diagnostics`，还没有统一 provenance / coverage contract。

本阶段强化 `inspect_agent_memory_route`，让它成为 Agent 可读的长篇记忆诊断入口。

## 参考项目取舍

- 采用 `openhuman` 的 provenance/citation 旁路字段：输出来源、覆盖率和边界。
- 采用 `openclaw` 的 active memory status 思路：把 blocked/sparse/degraded/available 表达为结构化状态。
- 不新增数据库字段，不新增检索，保持只读。

## 范围

修改 `backend/app/services/writing_agent/agent_memory_route.py`：

1. 新增 `memory_provenance`。
2. provenance 包含：
   - `sources`: `LongformMemory`、`LongformMaintenance`、`RetrievalDocument`
   - `coverage`: chapter count、memory count、retrieval document count、ready_for_writing
   - `recovery`: blocked 时给出 `repair_longform_maintenance`
   - `boundaries.world_truth`: 世界事实仍以 Athena/world-model 为准
3. status 规则：
   - `blocked`: maintenance 不可写
   - `sparse`: 尚无正文或长篇记忆为空
   - `degraded`: 有正文但检索索引为空
   - `available`: 记忆和检索可用

测试修改 `backend/tests/test_writing_agent_memory_route.py`：

1. 缺少长篇记忆时验证 blocked provenance。
2. 空项目时验证 sparse provenance。

## 验证

RED：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_memory_route.py -q
```

GREEN：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_memory_route.py -q
```

## 成功标准

- `inspect_agent_memory_route` 输出可直接被 Agent planner 消费的 provenance。
- 维护阻塞、空项目两类状态均可被结构化识别。
- 工具仍保持只读，不触发 context summary。
