# Phase187 Agent-Native Storyline Generation Chain Report

## Scope

为 legacy `generate_storyline` 增加 Agent-native 受控执行链：

- `preview_generate_storyline_execution`：只读预览 storyline 写入计划。
- `prepare_generate_storyline_execution`：只读生成审批契约。
- `execute_generate_storyline_with_approval`：在 `confirm_execute`、`approval_contract_hash`、`approval_contract` 均验证后调用现有 `app.api.storylines.generate_storyline`。

旧 `generate_storyline` descriptor 保留，静态 executor 仍不直接处理它，slash/dialog 路由未切换。

## Implementation

- 新增 `storyline_generation_tool_descriptors.py`，承载 storyline generation 三个 Agent 工具描述符。
- 新增 `storyline_generation_tool_adapters.py`，承载三个静态 adapter，并注入 approval metadata provider。
- 新增 `storyline_generation_execution.py`，实现 preview / prepare / execute 门禁链。
- 在 `tool_registry.py` 汇总 storyline generation descriptors。
- 在 `tool_executor.py` 汇总 storyline generation adapters。
- 在 `mutation_fingerprint.py` 为 `generate_storyline` / `execute_generate_storyline_with_approval` 增加 `storyline:{project_id}` mutation target。

## Debug Note

测试阶段出现一次数据夹具错误：`Project.id` 需要先 flush/commit 后才能用于 `Setup.project_id`。修正为先提交 `Project`，再创建 `Setup`。功能实现未因此调整。

## Validation

RED:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py -k "storyline_generation" -q
# ModuleNotFoundError: storyline_generation_tool_descriptors

pytest backend/tests/test_writing_agent_tool_executor.py -k "storyline_generation or generate_storyline_with_approval" -q
# ModuleNotFoundError: storyline_generation_execution
```

GREEN / T1:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "storyline_generation or generate_storyline_with_approval or preview_generate_storyline or prepare_generate_storyline" -q
# 5 passed, 105 deselected

pytest backend/tests/test_writing_agent_tool_registry.py -k "storyline_generation" -q
# 2 passed, 48 deselected
```

T2:

```powershell
pytest backend/tests/test_writing_agent_tool_aggregation_boundaries.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py -q
# 164 passed

python -m compileall backend/app/services/writing_agent
# exit 0
```

## Novel Progress

本阶段未推进小说正文生成。原因：Phase187 是 Hermes storyline 写入工具化阶段，验证重点是 Agent 能否安全接管故事线生成入口。

## Next Phase

建议 Phase188 迁移 `generate_outline`：

- 复用 Phase186/187 的 preview / prepare / execute 审批 wrapper 模式。
- 保留旧 `generate_outline` legacy fallback。
- 将审批计划绑定到底层 `generate_outline` 写入意图，并用 `approval_executor_tool_name` 指向新的 execute wrapper。
