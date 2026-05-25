# Phase 5: Longform Context Provenance

## 背景

Phase 4 已给 `inspect_agent_knowledge_base_route` 增加统一 `memory_provenance`。Phase 5 将同一 contract 扩展到 `summarize_longform_context`，让 Agent 在使用长篇上下文时能判断：

- 每个上下文 section 来自哪里。
- 每个 section 是否被窗口限制截断。
- prompt context 是否超过预算。
- 长篇记忆维护是否阻塞写作。
- 世界事实仍应通过 Athena/world-model 维护，而不是由长篇摘要直接写入。

## 参考项目取舍

- 采用 `openhuman` 的 bounded recall / citation / provenance 思路：所有召回结果必须带来源、窗口和可调试边界。
- 采用 `openclaw` 的 active memory fallback 思路：当上下文维护失败、召回过少或输出被截断时，Agent 应拿到下一步恢复建议。
- 不照搬通用 Agent 的完整记忆层级和权限系统。本阶段只做只读投影，不改变数据库和召回算法。

## 范围

修改 `backend/app/services/writing_agent/longform_context_summary.py`：

1. 新增 `memory_provenance` 输出。
2. 将 `source_sections` 转成统一 `sources`。
3. 为每个 section 输出 `total / returned / limit / has_more`。
4. 为 prompt context 输出 `chars / max_chars / included / truncated`。
5. 当维护阻塞或截断发生时，输出 `recovery` 建议。
6. 明确 `world_truth` 边界。

测试修改 `backend/tests/test_writing_agent_runs.py`：

1. 正常上下文摘要返回 `memory_provenance`。
2. 维护阻塞路径返回 `memory_provenance.recovery`。
3. 截断 section 能在 provenance window 中体现。

## 验证

- RED：新增测试后先运行相关 `pytest`，预期因缺少 `memory_provenance` 失败。
- GREEN：实现后运行：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_runs.py -k "summarize_longform_context or auto_plan_longform_context_blocks_stale_maintenance_before_generation" -q
```

- T1 补充运行：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_tool_executor.py -k "summarize_longform_context" -q
```

## 成功标准

- Agent run 中的 longform context step 包含 `memory_provenance`。
- `memory_provenance.sources` 与 `source_sections` 对齐。
- section 超过 `SECTION_ITEM_LIMIT` 时，`windows.sections[section_key].has_more == true`。
- 维护阻塞时，`recovery.status == "recommended"`，并给出 `repair_longform_maintenance`。
