# Phase39: Command Contracts Health Projection Report

## 目标

把 Phase38 的 `inspect_agent_command_contracts` 纳入 Agent 健康投影，使 `/status` 和 Agent 自检可以发现 Hermes 命令控制面缺口。

## 变更

- `inspect_agent_health_projection` 新增 `command_contracts` 摘要。
- 健康诊断新增：
  - `agent_command_contract_gaps`
  - severity: `warning`
  - 推荐工具：`inspect_agent_command_contracts`
- `agent_health_projection` descriptor output schema 增加 `command_contracts`。
- 现有 ready 健康测试通过 `_patch_ready_sources` 显式模拟命令控制面无缺口。

## RED 证据

- `pytest backend/tests/test_writing_agent_health_projection.py -q`
  - 失败原因：模拟命令契约缺口后，健康状态仍为 `ready`，说明命令控制面未纳入诊断。

## GREEN 证据

- `pytest backend/tests/test_writing_agent_health_projection.py backend/tests/test_agent_command_contracts.py -q`
  - `5 passed`
- `pytest backend/tests/test_dialogs.py -k "status_command_routes_through_agent_health_projection" -q`
  - `1 passed, 102 deselected`
- `git diff --check`
  - passed；仅保留既有提示：`backend/tests/test_writing_agent_runs.py` CRLF 将被 Git 转为 LF。

## 下一阶段建议

下一步可以把 `inspect_agent_command_contracts` 加入 planner 的健康预检推荐或 `/continue` 的 required tool 集合，让命令控制面缺口在自动继续前被 Agent 明确感知。
