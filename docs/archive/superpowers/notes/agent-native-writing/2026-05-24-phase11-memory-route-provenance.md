# Phase 11 Report: Memory Route Provenance

## 目标

Phase 10 将 longform context exhausted 状态导向 `inspect_agent_memory_route`。本阶段强化该工具，使它输出统一 `memory_provenance`，让 Agent 能直接判断长篇记忆、检索索引和维护状态的覆盖率。

## 参考项目取舍

- 采用 `openhuman` 的 provenance/citation 旁路字段：来源、覆盖率、边界结构化输出。
- 采用 `openclaw` 的 active memory status 思路：blocked/sparse/degraded/available 明确区分。
- 不新增数据库字段，不触发写操作，不默认 include context summary。

## 改动

- `backend/app/services/writing_agent/agent_memory_route.py`
  - 新增 `AGENT_MEMORY_ROUTE_PROVENANCE_VERSION = "phase224.agent_memory_route_provenance.v1"`。
  - `inspect_agent_memory_route` 输出新增 `memory_provenance`。
  - provenance 包含：
    - `sources`: `LongformMemory`、`LongformMaintenance`、`RetrievalDocument`
    - `coverage`: chapter count、longform memory count、retrieval document count、ready_for_writing
    - `boundaries.world_truth`: canonical source 为 `Athena/world_model`
    - `recovery`: blocked 时推荐 `repair_longform_maintenance`
  - status 规则：
    - `blocked`: route blocked
    - `sparse`: 无正文或长篇记忆为空
    - `degraded`: 有记忆但检索文档为空
    - `available`: 记忆和检索均可用

- `backend/tests/test_writing_agent_memory_route.py`
  - 缺少长篇记忆用例断言 blocked provenance 和 recovery tool。
  - 空项目用例断言 sparse provenance 和 coverage。

## 验证

RED：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_memory_route.py -q
```

结果：`2 failed`，失败点均为 `KeyError: 'memory_provenance'`。

GREEN：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_memory_route.py -q
```

结果：`2 passed`。

相关回归：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_memory_route.py tests/test_writing_agent_runs.py -k "memory_route or longform_context_provenance_exhausts_retry_at_max_window or recommended_followup" -q
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_tool_executor.py -k "inspect_agent_memory_route or summarize_longform_context" -q
```

结果：

- `9 passed, 177 deselected`
- `4 passed, 151 deselected`

## 仍未解决

- `degraded` 状态还没有单独测试覆盖。
- memory route provenance 还未进入前端展示。
- memory route 的 recommended next steps 仍主要依赖 route/recovery，尚未细化成章节分片或检索重建计划。

## 下一阶段建议

Phase 12 应补 `degraded` 状态和检索覆盖诊断：当有 longform memory 但 retrieval index 为空或不足时，Agent 应得到明确的 read/write 分离建议。只读建议可以先 inspect，写建议必须走 maintenance/confirmation。
