# Phase177 Review Revision Tool Modules Report

## Goal

将 Writing Agent 的章节审稿与修订工具拆成独立能力域模块，继续推进“原有模块工具化并服务 Agent 编排”的主线。

## Scope

本阶段只处理 review/revision 核心域的 7 个工具：

- `review_chapter_quality`
- `review_chapter_continuity`
- `plan_chapter_revision`
- `create_revision_draft`
- `apply_planner_revision_patch`
- `expand_chapter_to_target`
- `compress_chapter_to_target`

子代理只读审查确认：`review_longform_chapter_batch_execution`、`route_longform_chapter_batch_after_review` 属于 longform/task queue；`review_world_model_proposals` 属于 world-model，不纳入本阶段。

## Changes

- 新增 `backend/app/services/writing_agent/review_revision_tool_descriptors.py`
  - 承载 7 个审稿/修订工具 descriptor。
  - 本地拥有 `_STATUS_OUTPUT`、`_CHAPTER_PARAMS` 和修订类结构化输出 schema。
- 新增 `backend/app/services/writing_agent/review_revision_tool_adapters.py`
  - 承载 7 个审稿/修订工具 adapter handler。
  - 保留同步/异步 handler 形态，不改变执行行为。
- 更新 `backend/app/services/writing_agent/tool_registry.py`
  - 聚合 `REVIEW_REVISION_AGENT_TOOL_DESCRIPTORS`。
  - 移除 inline review/revision descriptor 和相关 schema 常量。
- 更新 `backend/app/services/writing_agent/tool_executor.py`
  - 聚合 `REVIEW_REVISION_AGENT_TOOL_ADAPTERS`。
  - 移除 inline review/revision handler 和 adapter entry。
- 更新测试：
  - `backend/tests/test_writing_agent_tool_registry.py`
  - `backend/tests/test_writing_agent_tool_executor.py`

## TDD Evidence

RED：

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_review_revision_tool_descriptors_live_in_dedicated_module -q
```

结果：失败，`ModuleNotFoundError: No module named 'app.services.writing_agent.review_revision_tool_descriptors'`。

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py::test_review_revision_tool_adapters_live_in_dedicated_module -q
```

结果：失败，`ModuleNotFoundError: No module named 'app.services.writing_agent.review_revision_tool_adapters'`。

GREEN：

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_review_revision_tool_descriptors_live_in_dedicated_module -q
```

结果：`1 passed in 0.02s`。

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py::test_review_revision_tool_adapters_live_in_dedicated_module -q
```

结果：`1 passed in 0.03s`。

## Verification

T1 targeted:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py -q
```

结果：`129 passed in 2.62s`。

T1 run-service related:

```powershell
pytest backend/tests/test_writing_agent_runs.py -k "review_chapter_quality or review_chapter_continuity or plan_chapter_revision or create_revision_draft or apply_planner_revision_patch or expand_chapter_to_target or compress_chapter_to_target" -q
```

结果：`58 passed, 117 deselected in 4.11s`。

Compile:

```powershell
python -m compileall backend/app/services/writing_agent
```

结果：exit 0。

Hygiene:

```powershell
git diff --check
```

结果：exit 0，无输出。

```powershell
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

结果：exit 1，无输出，未发现提交范围内的 DeepSeek/OpenAI 风格密钥。

## Notes

- 本阶段没有推进小说正文生成；原因是当前连续阶段重点是 Agent 工具域模块化，为后续真正由 Agent 自主编排长篇生成扫清结构障碍。
- 原计划中“从 `tool_contracts.py` 使用 `STATUS_OUTPUT`”不符合当前代码结构；实际采用与世界模型模块一致的本地 schema 常量，避免把 descriptor 模块反向耦合到 contract snapshot。
- `apply_planner_revision_patch` adapter metadata 仍是 `write`；contract snapshot 会按 descriptor 特征投影为 `guarded_write`，行为保持不变。

## Next Phase Suggestion

继续拆分 `tool_registry.py` / `tool_executor.py` 中剩余高价值工具域。优先候选：

1. `preflight` / planning / approval 工具域，包含 Agent plan、intent plan、approval preview/verify、tool contract/write gate/route preference inspection。
2. `trace` 与 `memory route` 工具域，进一步让 Trace 和长期记忆成为 Agent 可编排能力，而不是 executor 内部散落 handler。
