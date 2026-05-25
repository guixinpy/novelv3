# Phase175 Knowledge Base Tool Modules Report

## Scope

本阶段将 Writing Agent 知识库能力域从通用 registry/executor 中拆出。知识库是长期记忆 Agent 的核心边界：它承载作者偏好、项目策略、学习规则和参考写法，不应与世界模型真相混在同一职责层。

## Changes

- `backend/app/services/writing_agent/knowledge_base_tool_descriptors.py`
  - 新增 `KNOWLEDGE_BASE_AGENT_TOOL_DESCRIPTORS`。
  - 迁入：
    - `inspect_agent_knowledge_base_route`
    - `record_agent_knowledge_base_candidate`
- `backend/app/services/writing_agent/knowledge_base_tool_adapters.py`
  - 新增 `KNOWLEDGE_BASE_AGENT_TOOL_ADAPTERS`。
  - 迁入：
    - `_inspect_agent_knowledge_base_route`
    - `_record_agent_knowledge_base_candidate`
  - 本地保留参数解析 helper，避免反向依赖通用 executor 私有函数。
- `backend/app/services/writing_agent/tool_registry.py`
  - 聚合知识库 descriptor 模块。
  - 删除 inline 知识库 descriptor blocks。
- `backend/app/services/writing_agent/tool_executor.py`
  - 聚合知识库 adapter 模块。
  - 删除 inline 知识库 handler 和 adapter entries。
  - 清理迁移后无用的 `_optional_float()`。
- `backend/tests/test_writing_agent_tool_registry.py`
  - 新增知识库 descriptor 模块边界测试。
- `backend/tests/test_writing_agent_tool_executor.py`
  - 新增知识库 adapter 模块边界测试。

## Validation

### RED

Commands:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_knowledge_base_tool_descriptors_live_in_dedicated_module -q
pytest backend/tests/test_writing_agent_tool_executor.py::test_knowledge_base_tool_adapters_live_in_dedicated_module -q
```

Expected failures observed:

- `ModuleNotFoundError: No module named 'app.services.writing_agent.knowledge_base_tool_descriptors'`
- `ModuleNotFoundError: No module named 'app.services.writing_agent.knowledge_base_tool_adapters'`

### GREEN

Commands:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_knowledge_base_tool_descriptors_live_in_dedicated_module -q
pytest backend/tests/test_writing_agent_tool_executor.py::test_knowledge_base_tool_adapters_live_in_dedicated_module -q
```

Result:

- Both focused tests passed.

### T1 Regression

Command:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py -q
```

Result:

- 38 tests passed.

Command:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -q
```

Result:

- 87 tests passed.

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

继续按能力域拆分 Agent 工具边界。下一组优先候选是世界模型工具，因为它们数量更多且会继续服务 Athena/长期记忆 Agent 的事实一致性维护。
