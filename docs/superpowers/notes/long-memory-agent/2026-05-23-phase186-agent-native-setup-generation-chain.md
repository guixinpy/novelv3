# Phase186 Agent-Native Setup Generation Chain Report

## Scope

为 legacy `generate_setup` 增加 Agent-native 受控执行链：

- `preview_generate_setup_execution`：只读预览 setup 写入计划。
- `prepare_generate_setup_execution`：只读生成审批契约。
- `execute_generate_setup_with_approval`：在 `confirm_execute`、`approval_contract_hash`、`approval_contract` 均验证后调用现有 `app.api.setups.generate_setup`。

旧 `generate_setup` descriptor 保留，静态 executor 仍不直接处理它，slash/dialog 路由未切换。

## Implementation

- 新增 `setup_generation_tool_descriptors.py`，承载 setup generation 三个 Agent 工具描述符。
- 新增 `setup_generation_tool_adapters.py`，承载三个静态 adapter，并注入 approval metadata provider。
- 新增 `setup_generation_execution.py`，实现 preview / prepare / execute 门禁链。
- 在 `tool_registry.py` 汇总 setup generation descriptors。
- 在 `tool_executor.py` 汇总 setup generation adapters。
- 在 `mutation_fingerprint.py` 为 `generate_setup` / `execute_generate_setup_with_approval` 增加 `setup:{project_id}` mutation target。
- 在 `approval_tool_metadata.py` 增加 `approval_executor_tool_name` 支持，使 server-derived 计划可以把 legacy 写入意图绑定到 Agent approval wrapper。
- 在 `approval_contract.py` 保留 `approval_executor_tool_name`，让审批契约显式记录实际执行 wrapper。

## Debug Note

初版计划把 `execute_generate_setup_with_approval` 自己作为被审批写入步骤，导致审批校验要求该执行工具自身的 `confirm_execute` / `approval_contract_hash` / `approval_contract` 字段，形成自引用并触发 `tool_contract_drift`。

修正后，审批计划绑定到底层写入意图 `generate_setup`，并通过 `approval_executor_tool_name = execute_generate_setup_with_approval` 声明 Agent wrapper。该模式与已存在的 `generate_chapter` 审批链一致。

## Validation

RED:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py -k "setup_generation" -q
pytest backend/tests/test_writing_agent_tool_executor.py -k "setup_generation or generate_setup_with_approval" -q
```

GREEN / T1:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "prepare_generate_setup_execution or generate_setup_with_approval" -q
# 2 passed, 102 deselected

pytest backend/tests/test_writing_agent_tool_executor.py -k "setup_generation or generate_setup_with_approval" -q
# 3 passed, 101 deselected

pytest backend/tests/test_writing_agent_tool_registry.py -k "setup_generation" -q
# 2 passed, 46 deselected

python -m compileall backend/app/services/writing_agent
# exit 0
```

T2:

```powershell
pytest backend/tests/test_writing_agent_tool_aggregation_boundaries.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py -q
# 156 passed
```

## Novel Progress

本阶段未推进小说正文生成。原因：Phase186 是 Hermes setup 写入工具化阶段，验证重点是 Agent 能否安全接管项目基础设定生成入口。

## Next Phase

建议 Phase187 迁移 `generate_storyline`：

- 复用 Phase186 的 preview / prepare / execute 审批 wrapper 模式。
- 保留旧 `generate_storyline` legacy fallback。
- 将审批计划绑定到底层 `generate_storyline` 写入意图，并用 `approval_executor_tool_name` 指向新的 execute wrapper。
