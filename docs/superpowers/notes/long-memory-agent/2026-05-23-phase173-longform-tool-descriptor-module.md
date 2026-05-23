# Phase173 Longform Tool Descriptor Module Report

## Scope

本阶段将后端长篇批次 Agent tool descriptor 从通用 `tool_registry.py` 拆到独立模块。目标是让 registry 继续承担公开查询和可见性诊断职责，而不是继续积累某一类工具的完整契约定义。

## Reference Learning

快速检查了 `references/agent-projects/hermes-agent/AGENTS.md` 中的工具组织说明：Hermes 将工具实现拆到独立文件，由中央 registry 收集和暴露，并通过 toolset 控制可用范围。本阶段只吸收这个“工具契约按能力域分文件、中央 registry 聚合”的边界思路，没有引入其插件注册机制或运行时依赖。

## Changes

- `backend/app/services/writing_agent/tool_descriptor_types.py`
  - 新增 `AgentToolDescriptor`。
  - 新增公共 `object_schema()` helper。
- `backend/app/services/writing_agent/longform_tool_descriptors.py`
  - 新增 `LONGFORM_AGENT_TOOL_DESCRIPTORS`。
  - 迁入八个长篇批次工具 descriptor：
    - `plan_longform_chapter_batch`
    - `enqueue_longform_chapter_batch`
    - `inspect_longform_chapter_batch`
    - `execute_longform_chapter_batch_preflight`
    - `prepare_longform_chapter_batch_execution`
    - `execute_longform_chapter_batch`
    - `review_longform_chapter_batch_execution`
    - `route_longform_chapter_batch_after_review`
- `backend/app/services/writing_agent/tool_registry.py`
  - 从 descriptor types 模块导入 `AgentToolDescriptor` 和 `_object_schema`。
  - 聚合 `LONGFORM_AGENT_TOOL_DESCRIPTORS`。
  - 删除八个 inline longform descriptor。
  - 保持 `AgentToolDescriptor` 从 `tool_registry.py` 的既有导入路径可用。
- `backend/tests/test_writing_agent_tool_registry.py`
  - 新增长篇 descriptor 模块边界测试。
- `backend/tests/test_writing_agent_tool_executor.py`
  - 修正一个既有精确字典断言；当前审批验证事件会携带 `resource_bindings` 和 `tool_call_ids`，测试改为断言核心字段和资源绑定字段。

## Validation

### RED

Command:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_longform_tool_descriptors_live_in_dedicated_module -q
```

Expected failure observed:

- `ModuleNotFoundError: No module named 'app.services.writing_agent.longform_tool_descriptors'`

### GREEN

Command:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_longform_tool_descriptors_live_in_dedicated_module -q
```

Result:

- 1 test passed.

### T1 Regression

Command:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py -q
```

Result:

- 37 tests passed.

Command:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -q
```

Initial result:

- 1 stale assertion failed in `test_execute_generate_chapter_with_approval_records_verification_event`.
- Root cause: current production contract includes `resource_bindings` in `approval_verification_event`; this was unrelated to descriptor extraction.

Final result:

- 85 tests passed.

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

继续拆分后端 Agent 工具执行层。`tool_executor.py` 仍集中维护大量 `_tool_name -> WritingAgentToolAdapter` 映射，下一阶段建议先把长篇批次 static adapter 迁入专门模块，再由 executor 聚合，形成 descriptor 与 adapter 都按能力域分文件的结构。
