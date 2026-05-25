# Phase39: Command Contracts Health Projection

## 背景

Phase38 新增了 `inspect_agent_command_contracts`，但 `/status` 使用的 Agent 健康投影仍只汇总 profile policy、route preference、tool contracts、write gate 和 trace audit。命令控制面如果缺投影类型或缺 adapter，Agent 健康状态不会直接反映。

本阶段把命令控制面契约纳入 `inspect_agent_health_projection`，让 `/status` 和 Agent 自检能看到命令控制面是否可编排。

## 成功标准

1. `inspect_agent_health_projection` 输出新增 `command_contracts`。
2. `command_contracts.summary.gap_count > 0` 时新增诊断：
   - `code: agent_command_contract_gaps`
   - `severity: warning`
3. 推荐工具包含 `inspect_agent_command_contracts`。
4. 现有 ready 健康测试不因命令契约引入误报。

## TDD 计划

1. 后端 RED：扩展 `test_writing_agent_health_projection.py`，模拟命令控制面有 gap，断言健康投影包含 `command_contracts`、诊断和推荐工具。
2. 实现：
   - import `inspect_agent_command_contracts`
   - 增加 `_command_contract_summary`
   - `_diagnostics` 增加 `command_contracts` 参数和诊断规则
   - `_recommended_tools` 增加诊断到工具映射
3. 验证：
   - `pytest backend/tests/test_writing_agent_health_projection.py backend/tests/test_agent_command_contracts.py -q`
   - `pytest backend/tests/test_dialogs.py -k "status_command_routes_through_agent_health_projection" -q`
   - `git diff --check`

## 非目标

- 不改变命令契约工具输出。
- 不改变 `/status` 文案，只改变 meta 中的健康投影结构。
- 不自动修复命令缺口。
