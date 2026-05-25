# Phase 5 Report: Longform Context Provenance

## 目标

把 Phase 4 的知识库 provenance contract 扩展到 `summarize_longform_context`，让 Agent 使用长篇上下文时能看到来源、窗口、截断、维护阻塞和恢复建议。

## 参考项目取舍

本阶段并行审计了两个参考项目：

- `openhuman`：采用 bounded recall、citation/provenance、动态记忆旁路字段的设计；不照搬 Memory Tree、Obsidian、前端 citation chips 或 pinned/forgotten UI。
- `openclaw`：采用 active memory 的状态化召回与 fallback 语义；不照搬 active-memory 子 Agent、chat/session allowlist、XML prompt 注入或 circuit breaker。

最终选择：只在 novelv3 现有 `summarize_longform_context` 输出上增加结构化 `memory_provenance`，不改变召回算法，不引入新依赖。

## 改动

- `backend/app/services/writing_agent/longform_context_summary.py`
  - 新增 `LONGFORM_MEMORY_PROVENANCE_VERSION = "phase223.longform_memory_provenance.v1"`。
  - 输出新增 `memory_provenance`。
  - provenance 包含：
    - `sources`: 从 `source_sections` 派生的 `longform_context_package:<section_key>`。
    - `windows.sections`: 每个 section 的 `total / returned / limit / has_more`。
    - `prompt_context`: `chars / max_chars / included / truncated`。
    - `boundaries.world_truth`: 明确世界事实 canonical source 是 `Athena/world_model`。
    - `recovery`: 维护阻塞时推荐 `repair_longform_maintenance`；截断时提供可选 `summarize_longform_context` 重试建议。
  - 状态规则：
    - `blocked`: 长篇维护阻塞。
    - `truncated`: section 或 prompt context 被截断。
    - `sparse`: 没有任何 source section。
    - `available`: 正常可用。

- `backend/tests/test_writing_agent_runs.py`
  - 正常上下文摘要验证 provenance source/window/boundary。
  - 伪造溢出 section 验证 window `has_more` 和 prompt truncation。
  - auto-plan 维护阻塞路径验证 provenance recovery。

## 验证

RED：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_runs.py -k "summarize_longform_context or longform_context_provenance or auto_plan_longform_context_blocks_stale_maintenance_before_generation" -q
```

结果：`3 failed, 180 deselected`，失败点均为缺少 `memory_provenance`。

GREEN：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_runs.py -k "summarize_longform_context or longform_context_provenance or auto_plan_longform_context_blocks_stale_maintenance_before_generation" -q
```

结果：`3 passed, 180 deselected`。

相关工具适配：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_tool_executor.py -k "summarize_longform_context" -q
```

结果：`2 passed, 153 deselected`。

综合相关筛选：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_runs.py -k "memory_provenance or summarize_longform_context or longform_context_provenance or auto_plan_longform_context_blocks_stale_maintenance_before_generation" -q
```

结果：`3 passed, 180 deselected`。

## 仍未解决

- provenance 还没有覆盖 Athena retrieval 的每条 source citation 细节，只覆盖被选入 context package 的 section 级别。
- 记忆治理状态还只是 `state=active` 的扩展位，尚未接入 pinned / forgotten / candidate 等治理。
- Agent planner 还没有根据 `memory_provenance.status` 自动选择恢复或缩小上下文窗口。

## 下一阶段建议

Phase 6 应把 `memory_provenance.status/recovery` 接入 planner/run loop：当 longform context 返回 `blocked` 时自动进入恢复计划；当返回 `truncated` 时给出更窄 query 或章节窗口的 retry plan。该阶段更接近 openclaw 的 active memory fallback，但仍应保持确定性工具编排，不引入模型驱动子召回。
