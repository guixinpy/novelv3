# Phase180 Agent Generation Tool Modules Report

## Goal

将 Writing Agent 的 Agent-native generation / outline maintenance 工具拆成独立能力域模块，为后续 Agent 自主执行“生成前审批 -> 执行章节生成 -> 后续审稿修订”链路打基础。

## Scope

本阶段处理 5 个工具：

- `generate_chapter`
- `prepare_generate_chapter_execution`
- `execute_generate_chapter_with_approval`
- `expand_outline_window`
- `backfill_outline_gaps`

其中 `backfill_outline_gaps` 是 maintenance，但它属于 outline 写路径，与 `expand_outline_window` 同阶段迁出。

## Non-Scope

未纳入本阶段：

- `generate_setup`
- `generate_storyline`
- `generate_outline`

这三个仍是 legacy action-backed descriptors，没有 static Agent-native adapter。为避免扩大语义范围，本阶段不补 adapter、不迁移 action execution 语义。

## Changes

- 新增 `backend/app/services/writing_agent/agent_generation_tool_descriptors.py`
  - 承载 5 个 Agent-native generation/outline descriptor。
  - 本地拥有 chapter/window/output schema。
- 新增 `backend/app/services/writing_agent/agent_generation_tool_adapters.py`
  - 提供 `build_agent_generation_tool_adapters(...)`。
  - 通过 `approval_tool_metadata_provider` 注入当前 adapter metadata，避免反向依赖 executor 全局状态。
- 更新 `backend/app/services/writing_agent/tool_registry.py`
  - 聚合 `AGENT_GENERATION_TOOL_DESCRIPTORS`。
  - 移除 inline generation/outline descriptor。
- 更新 `backend/app/services/writing_agent/tool_executor.py`
  - 聚合 `build_agent_generation_tool_adapters(...)`。
  - 移除 inline generation/outline handler 和 adapter entry。
- 更新测试：
  - 新增 generation descriptor module boundary test。
  - 新增 generation adapter module boundary test。

## TDD Evidence

RED：

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_agent_generation_tool_descriptors_live_in_dedicated_module -q
```

结果：失败，`ModuleNotFoundError: No module named 'app.services.writing_agent.agent_generation_tool_descriptors'`。

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py::test_agent_generation_tool_adapters_live_in_dedicated_module -q
```

结果：失败，`ModuleNotFoundError: No module named 'app.services.writing_agent.agent_generation_tool_adapters'`。

GREEN：

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_agent_generation_tool_descriptors_live_in_dedicated_module -q
```

结果：`1 passed in 0.04s`。

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py::test_agent_generation_tool_adapters_live_in_dedicated_module -q
```

结果：`1 passed in 0.06s`。

## Verification

T1 generation subset:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "agent_generation or generate_chapter or prepare_generate_chapter_execution or execute_generate_chapter_with_approval or expand_outline_window or backfill_outline_gaps" -q
```

结果：`8 passed, 87 deselected in 0.56s`。

T1 registry/executor:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py -q
```

结果：`138 passed in 4.89s`。

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

## Subagent Findings

只读子代理确认：

- Phase180 应只处理 5 个 Agent-native generation/outline 工具。
- `generate_setup`、`generate_storyline`、`generate_outline` 是 legacy action-backed descriptors，不应在本阶段补 static adapter。
- `execute_generate_chapter_with_approval` 必须继续通过 provider 获取当前 `_STATIC_TOOL_ADAPTERS` metadata。
- 不应统一 `command_args` 和 `chapter_index` 行为；本阶段只迁移，不改变既有参数语义。
- `generate_chapter` 的 static adapter 仍必须在 internal gate 之前被检查，当前 executor 顺序保持不变。

## Next Phase Suggestion

剩余内联工具主要是 task queue / job projection：

- `inspect_agent_job_projection`
- `plan_chapter_conflict_recovery`

下一阶段可将它们迁到 task queue projection 模块，使 `tool_executor.py` 进一步只保留聚合和 injected `preflight_writing` special-case。
