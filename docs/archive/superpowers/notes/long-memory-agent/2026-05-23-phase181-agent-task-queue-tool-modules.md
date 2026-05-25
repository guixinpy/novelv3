# Phase181 Agent Task Queue Tool Modules Report

## Goal

将 Writing Agent 剩余内联 task queue / job projection 工具拆成独立能力域模块，让 `tool_registry.py` 与 `tool_executor.py` 继续收敛为聚合层。

## Scope

本阶段处理 2 个工具：

- `inspect_agent_job_projection`
- `plan_chapter_conflict_recovery`

## Non-Scope

未纳入本阶段：

- `generate_setup`
- `generate_storyline`
- `generate_outline`

这三个仍是 legacy Hermes action-backed descriptors，不属于 task queue / Agent job projection。

## Changes

- 新增 `backend/app/services/writing_agent/agent_task_queue_tool_descriptors.py`
  - 承载 `AGENT_TASK_QUEUE_TOOL_DESCRIPTORS`。
  - 保留两个工具原有 category、target type、schema、sort key 和 availability checks。
- 新增 `backend/app/services/writing_agent/agent_task_queue_tool_adapters.py`
  - 承载 `AGENT_TASK_QUEUE_TOOL_ADAPTERS`。
  - 保留 `task_id` / `task_type` / `status` 字符串裁剪和 `limit` / `chapter_index` 整数转换语义。
- 更新 `backend/app/services/writing_agent/tool_registry.py`
  - 聚合 `AGENT_TASK_QUEUE_TOOL_DESCRIPTORS`。
  - 移除这两个工具的 inline descriptor。
- 更新 `backend/app/services/writing_agent/tool_executor.py`
  - 聚合 `AGENT_TASK_QUEUE_TOOL_ADAPTERS`。
  - 移除这两个工具的 inline handler 和 adapter entry。
- 更新测试：
  - 新增 task queue descriptor module boundary test。
  - 新增 task queue adapter module boundary test。

## TDD Evidence

RED：

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_agent_task_queue_tool_descriptors_live_in_dedicated_module -q
```

结果：失败，`ModuleNotFoundError: No module named 'app.services.writing_agent.agent_task_queue_tool_descriptors'`。

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py::test_agent_task_queue_tool_adapters_live_in_dedicated_module -q
```

结果：失败，`ModuleNotFoundError: No module named 'app.services.writing_agent.agent_task_queue_tool_adapters'`。

GREEN：

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_agent_task_queue_tool_descriptors_live_in_dedicated_module -q
```

结果：`1 passed in 0.04s`。

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py::test_agent_task_queue_tool_adapters_live_in_dedicated_module -q
```

结果：`1 passed in 0.06s`。

## Verification

T1 task queue subset：

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "agent_task_queue or inspect_agent_job_projection or plan_chapter_conflict_recovery" -q
```

结果：`5 passed, 91 deselected in 0.31s`。

T1 registry/executor：

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py -q
```

结果：`140 passed in 4.69s`。

Compile：

```powershell
python -m compileall backend/app/services/writing_agent
```

结果：exit 0。

Hygiene：

```powershell
git diff --check
```

结果：exit 0，无输出。

```powershell
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

结果：exit 1，无输出，未发现提交范围内的 DeepSeek/OpenAI 风格密钥。

## Subagent Findings

只读子代理确认：

- Phase181 最小边界只应包含 `inspect_agent_job_projection` 和 `plan_chapter_conflict_recovery`。
- longform batch queue 工具已经在 dedicated longform 模块中，不应重拆。
- `generate_setup`、`generate_storyline`、`generate_outline` 是 legacy Hermes generation descriptors，不应在本阶段移动。
- `preflight_writing` 是 injected special-case，不属于 task queue adapter。

## Next Phase Suggestion

`tool_registry.py` 当前剩余 inline descriptor 主要是 legacy Hermes generation actions：

- `generate_setup`
- `generate_storyline`
- `generate_outline`

下一阶段可以评估是否将它们拆到 legacy/Hermes action descriptor 模块；若要继续 Agent 化，还应先明确这些 legacy actions 是否需要补 static adapter，还是只做 registry 模块拆分。
