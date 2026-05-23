# Phase176 World Model Tool Modules Report

## Scope

本阶段将 Athena/世界模型 Writing Agent 工具域从通用 `tool_registry.py` 和 `tool_executor.py` 中拆出。世界模型是长篇稳定性的事实层能力，后续 Agent 自主编排章节生成、冲突审查和提案处理时，需要这个能力域具备清晰的工具边界。

## Subagent Evidence

使用只读 explorer sidecar 复核拆分边界。结论与本地源码一致：本阶段应包含 10 个世界模型工具，`generate_chapter` 只依赖或提示 world-model，不纳入本次拆分。

## Changes

- `backend/app/services/writing_agent/world_model_tool_descriptors.py`
  - 新增 `WORLD_MODEL_AGENT_TOOL_DESCRIPTORS`。
  - 迁入世界模型工具 descriptor：
    - `import_setup_world_model`
    - `analyze_chapter_world_model`
    - `review_world_model_proposals`
    - `inspect_agent_world_model_route`
    - `plan_world_model_proposal_resolution`
    - `preview_world_model_proposal_resolution`
    - `apply_world_model_proposal_resolution`
    - `draft_world_model_proposal_resolution_decisions`
    - `draft_high_value_world_proposal_resolution_decisions`
    - `seed_continuity_anchor_proposals`
  - 本地保留世界模型专用输出 schema。
- `backend/app/services/writing_agent/world_model_tool_adapters.py`
  - 新增 `WORLD_MODEL_AGENT_TOOL_ADAPTERS`。
  - 迁入上述 10 个工具的 static adapter handlers。
- `backend/app/services/writing_agent/tool_registry.py`
  - 聚合世界模型 descriptor 模块。
  - 删除 inline 世界模型 descriptor blocks 和已迁移 schema constants。
- `backend/app/services/writing_agent/tool_executor.py`
  - 聚合世界模型 adapter 模块。
  - 删除 inline 世界模型 handler 和 adapter entries。
- `backend/tests/test_writing_agent_tool_registry.py`
  - 新增世界模型 descriptor 模块边界测试。
- `backend/tests/test_writing_agent_tool_executor.py`
  - 新增世界模型 adapter 模块边界测试。

## Validation

### RED

Commands:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_world_model_tool_descriptors_live_in_dedicated_module -q
pytest backend/tests/test_writing_agent_tool_executor.py::test_world_model_tool_adapters_live_in_dedicated_module -q
```

Expected failures observed:

- `ModuleNotFoundError: No module named 'app.services.writing_agent.world_model_tool_descriptors'`
- `ModuleNotFoundError: No module named 'app.services.writing_agent.world_model_tool_adapters'`

### GREEN

Commands:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_world_model_tool_descriptors_live_in_dedicated_module -q
pytest backend/tests/test_writing_agent_tool_executor.py::test_world_model_tool_adapters_live_in_dedicated_module -q
```

Result:

- Both focused tests passed.

### T1 Regression

Command:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py -q
```

Result:

- 39 tests passed.

Command:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -q
```

Result:

- 88 tests passed.

Command:

```powershell
python -m compileall backend/app/services/writing_agent
```

Result:

- Compile completed with exit code 0.

## Hygiene

Command:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

Result:

- `git diff --check`: no output.
- Secret scan: no matches.

## Next Recommendation

能力域模块化已经覆盖长篇批次、知识库和世界模型。下一阶段建议转向审稿/修订工具域，将质量审查、连续性审查、修订计划与修订执行工具从通用 executor/registry 中拆出，继续减少 Agent 工具核心文件的耦合。
