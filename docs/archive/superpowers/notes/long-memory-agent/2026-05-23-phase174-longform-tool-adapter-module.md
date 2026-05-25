# Phase174 Longform Tool Adapter Module Report

## Scope

本阶段将后端长篇批次 Writing Agent static adapters 从 `tool_executor.py` 拆到独立模块。Phase173 已经把 descriptor 合约拆出，本阶段继续完成 executor 侧同类边界拆分，让长篇批次工具的契约和执行适配都按能力域组织。

## Changes

- `backend/app/services/writing_agent/tool_adapter_types.py`
  - 新增 `PreflightWriting`、`StaticToolAdapterOutput`、`StaticToolAdapterHandler`。
  - 新增 `WritingAgentToolContext`、`WritingAgentToolExecutionResult`、`WritingAgentToolAdapter`。
- `backend/app/services/writing_agent/longform_tool_adapters.py`
  - 新增 `build_longform_agent_tool_adapters(...)`。
  - 迁入八个长篇批次 handler：
    - `plan_longform_chapter_batch`
    - `enqueue_longform_chapter_batch`
    - `inspect_longform_chapter_batch`
    - `execute_longform_chapter_batch_preflight`
    - `prepare_longform_chapter_batch_execution`
    - `execute_longform_chapter_batch`
    - `review_longform_chapter_batch_execution`
    - `route_longform_chapter_batch_after_review`
  - 本地保留 `_optional_int()`，避免从通用 executor 反向引用私有 helper。
- `backend/app/services/writing_agent/tool_executor.py`
  - 从共享类型模块导入 adapter types。
  - 从 longform adapter 模块聚合长篇批次 adapter map。
  - 删除八个 inline longform handler 和对应 inline adapter entries。
  - 保持 `WritingAgentToolContext`、`WritingAgentToolAdapter` 等既有导入路径可用。
- `backend/tests/test_writing_agent_tool_executor.py`
  - 新增长篇 adapter 专用模块边界测试。

## Validation

### RED

Command:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py::test_longform_tool_adapters_live_in_dedicated_module -q
```

Expected failure observed:

- `ModuleNotFoundError: No module named 'app.services.writing_agent.longform_tool_adapters'`

### GREEN

Command:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py::test_longform_tool_adapters_live_in_dedicated_module -q
```

Result:

- 1 test passed.

### T1 Regression

Command:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -q
```

Result:

- 86 tests passed.

Command:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py -q
```

Result:

- 37 tests passed.

Command:

```powershell
python -m compileall backend/app/services/writing_agent
```

Result:

- Compile completed with exit code 0.

### Hygiene

Command:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

Result:

- `git diff --check`: no output.
- Secret scan: no matches.

## Next Recommendation

后端长篇批次工具已经完成 descriptor 和 adapter 的能力域拆分。下一阶段建议转向 `tool_executor.py` 里其它能力域的聚合压力，优先选择知识库、世界模型或审稿工具中最容易继续增长的一组，按同样方式拆出 descriptor/adapter 边界。
