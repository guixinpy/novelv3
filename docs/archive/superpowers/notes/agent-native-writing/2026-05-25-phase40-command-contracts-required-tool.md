# Phase40: Command Contracts Required Tool Report

## 目标

把 Phase39 引入的 `inspect_agent_command_contracts` 显式写入 `/status` 和 `/continue` 的 required tools，修复命令目录可用性与真实运行依赖之间的漂移。

## 变更

- `CONTINUE_REQUIRED_AGENT_TOOLS` 新增 `inspect_agent_command_contracts`。
- 新增 `STATUS_REQUIRED_AGENT_TOOLS`：
  - `inspect_agent_health_projection`
  - `inspect_agent_command_contracts`
- 命令目录和命令契约快照会把该依赖反映到 `/continue`、`/status`。
- 当 `inspect_agent_command_contracts` adapter 缺失时，`/continue` 与 `/status` 均从 public available command list 中隐藏。

## RED 证据

- `pytest backend/tests/test_agent_command_catalog.py backend/tests/test_agent_command_contracts.py backend/tests/test_dialogs.py -k "chat_command_catalog or agent_command_contracts" -q`
  - 失败原因：
    - `/continue.required_agent_tools` 缺少 `inspect_agent_command_contracts`
    - `inspect_agent_command_contracts` adapter 缺失时 `/status` 仍可用

## GREEN 证据

- `pytest backend/tests/test_agent_command_catalog.py backend/tests/test_agent_command_contracts.py backend/tests/test_dialogs.py -k "chat_command_catalog or agent_command_contracts" -q`
  - `7 passed, 102 deselected`
- `git diff --check`
  - passed；仅保留既有提示：`backend/tests/test_writing_agent_runs.py` CRLF 将被 Git 转为 LF。

## 下一阶段建议

下一步可以把 `inspect_agent_command_contracts` 加入 Agent 的推荐 followup / 健康预检链路，使自动继续和恢复规划更早发现命令控制面缺口。
