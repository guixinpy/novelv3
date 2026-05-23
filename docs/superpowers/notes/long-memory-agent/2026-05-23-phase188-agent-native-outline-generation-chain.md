# Phase188 Agent-Native Outline Generation Chain Report

## Scope

为 legacy `generate_outline` 增加 Agent-native 受控执行链：

- `preview_generate_outline_execution`：只读预览 outline 写入计划。
- `prepare_generate_outline_execution`：只读生成审批契约。
- `execute_generate_outline_with_approval`：在 `confirm_execute`、`approval_contract_hash`、`approval_contract` 均验证后调用现有 `app.api.outlines.generate_outline`。

旧 `generate_outline` descriptor 保留，静态 executor 仍不直接处理它，slash/dialog 路由未切换。

## Implementation

- 新增 `outline_generation_tool_descriptors.py`，承载 outline generation 三个 Agent 工具描述符。
- 新增 `outline_generation_tool_adapters.py`，承载三个静态 adapter，并注入 approval metadata provider。
- 新增 `outline_generation_execution.py`，实现 preview / prepare / execute 门禁链。
- 在 `tool_registry.py` 汇总 outline generation descriptors。
- 在 `tool_executor.py` 汇总 outline generation adapters。
- 在 `mutation_fingerprint.py` 为 `generate_outline` / `execute_generate_outline_with_approval` 增加 `outline:{project_id}` mutation target。

## Validation

RED:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py -k "outline_generation" -q
# ModuleNotFoundError: outline_generation_tool_descriptors

pytest backend/tests/test_writing_agent_tool_executor.py -k "outline_generation or generate_outline_with_approval or preview_generate_outline or prepare_generate_outline" -q
# ModuleNotFoundError: outline_generation_execution
```

GREEN / T1:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py -k "outline_generation" -q
# 2 passed, 50 deselected

pytest backend/tests/test_writing_agent_tool_executor.py -k "outline_generation or generate_outline_with_approval or preview_generate_outline or prepare_generate_outline" -q
# 5 passed, 111 deselected

python -m compileall backend/app/services/writing_agent
# exit 0
```

T2:

```powershell
pytest backend/tests/test_writing_agent_tool_aggregation_boundaries.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py -q
# 172 passed

python -m compileall backend/app/services/writing_agent
# exit 0
```

## Novel Progress

本阶段未推进小说正文生成。原因：Phase188 是 Hermes outline 写入工具化阶段，验证重点是 Agent 能否安全接管章节大纲生成入口。

## Next Phase

建议 Phase189 做三项收敛检查：

- 更新 legacy Hermes migration projection，使 `generate_setup`、`generate_storyline`、`generate_outline` 显示为 Agent wrapper ready，而不是仍显示 legacy-only。
- 用 contract snapshot 验证三个基础生成入口均具备审批 wrapper、mutation target、resource binding。
- 评估是否开始把 slash/dialog route preference 指向新的 prepare/execute 链路，或先增加 route projection。
