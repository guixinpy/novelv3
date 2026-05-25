# Phase 4 Report: Memory Provenance Projection

## 目标

将 `openhuman` 的 memory citation / provenance 思路转译到 novelv3 的知识库召回路径，让 Agent 在使用知识库时能看到来源、窗口限制和世界事实边界。

本阶段没有照搬 `openhuman` 的完整记忆层级，也没有引入新依赖。原因是 novelv3 已有明确的 Athena/world-model 和 knowledge-base 分工，本阶段更适合先补统一投影，再逐步扩展到长期上下文、检索和审稿记忆。

## 改动

- `backend/app/services/writing_agent/agent_knowledge_base_route.py`
  - 新增 `MEMORY_PROVENANCE_VERSION = "phase222.agent_memory_provenance.v1"`。
  - `inspect_agent_knowledge_base_route` 输出新增 `memory_provenance`。
  - provenance 汇总来源：
    - `Project`
    - `Project.style_config`
    - `PromptRule(rule_type=learned)`
    - `Project.style_config.knowledge_base_candidates`
    - `FewShotExampleLibrary`
  - provenance 暴露窗口：
    - learned rules 的 `total / returned / limit / has_more`
    - knowledge candidates 的 `total / returned / limit / has_more`
  - provenance 明确世界事实边界：
    - `canonical_source = "Athena/world_model"`
    - knowledge base 只作为作者偏好、项目策略、参考模式和经验教训来源。

- `backend/tests/test_writing_agent_knowledge_base_route.py`
  - 稀疏项目验证 `memory_provenance.status == "sparse"`。
  - 配置项目验证来源集合和窗口信息。
  - learned rules 截断场景验证 provenance window。

## 验证

RED：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_knowledge_base_route.py -q
```

结果：`3 failed, 3 passed`，失败点均为 `KeyError: 'memory_provenance'`，符合预期。

GREEN：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_knowledge_base_route.py -q
```

结果：`6 passed in 0.47s`。

相关路径：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_runs.py -k "auto_plan_executes_high_level_next_chapter_goal or auto_plan_longform_context_blocks_stale_maintenance_before_generation" -q
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_tool_executor.py -k "inspect_agent_knowledge_base_route" -q
```

结果：

- `2 passed, 180 deselected`
- `2 passed, 153 deselected`

## 仍未解决

- `summarize_longform_context` 已有 source sections，但还没有统一 `memory_provenance` 投影。
- 检索结果、审稿经验、Trace 历史还没有统一 citation 格式。
- 记忆治理状态仍不完整，后续应引入 pinned / muted / forgotten / candidate / accepted 等可审计状态。

## 下一阶段建议

Phase 5 应继续吸收 `openhuman` 的 bounded recall 和 governance 思路，把 `summarize_longform_context` 的 source sections 转成与知识库一致的 provenance contract；同时对照 `openclaw` 的 active memory/fallback 思路，明确当召回过少、过旧或被截断时 Agent 应如何恢复。
