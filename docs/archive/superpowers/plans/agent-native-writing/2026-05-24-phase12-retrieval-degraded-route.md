# Phase 12: Retrieval Degraded Route

## 背景

Phase 11 给 `inspect_agent_memory_route` 增加了 provenance/coverage，但 `degraded` 状态尚未被测试驱动细化。对于百万字长篇，长篇记忆存在但检索索引缺失会导致跨章节召回质量下降，Agent 不能把它误判为完全可用。

本阶段补齐 retrieval degraded 的 Agent-native 输出。

## 参考项目取舍

- 采用 `openclaw` 的状态化 degraded/fallback 思路：不是简单 ready，而是显式 degraded。
- 采用 `openhuman` 的 bounded/provenance 思路：诊断中明确来源和覆盖率。
- 不让只读 follow-up 自动执行写维护；写维护仍通过现有安全链路处理。

## 范围

修改 `backend/app/services/writing_agent/agent_memory_route.py`：

1. 当 `memory_provenance.status == "degraded"`：
   - `recovery.status = "optional"`
   - `reason = "retrieval_index_empty"`
   - `next_tools = ["inspect_agent_memory_route", "repair_longform_maintenance"]`
   - `tools` 仅包含只读 `inspect_agent_memory_route`
   - `write_tools` 单独列出 `repair_longform_maintenance`
2. blocked 路径保持已有 recovery。

测试修改 `backend/tests/test_writing_agent_memory_route.py`：

1. monkeypatch 构造 ready maintenance + longform memory 存在 + retrieval index 空。
2. 断言 provenance degraded。
3. 断言只读 tools 和写工具分离。

## 验证

RED/GREEN：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_memory_route.py -q
```

## 成功标准

- degraded 状态有测试覆盖。
- Agent 能看到检索覆盖不足。
- 只读诊断和写维护建议分离。
