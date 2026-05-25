# Phase40: Command Contracts Required Tool

## 背景

Phase39 已经让 `inspect_agent_health_projection` 汇总 `inspect_agent_command_contracts`。因此 `/status` 的实际运行时依赖不再只是 health projection 本身；如果命令契约自检工具缺失，`/status` 的 Agent 健康判断也会缺失关键子视图。

本阶段把 `inspect_agent_command_contracts` 明确写入 Agent 命令目录的 required tools，使命令目录、可用性守卫和运行时依赖保持一致。

## 成功标准

1. `/status.required_agent_tools` 包含：
   - `inspect_agent_health_projection`
   - `inspect_agent_command_contracts`
2. `/continue.required_agent_tools` 包含 `inspect_agent_command_contracts`，因为 `/continue` 以 health projection 作为首要控制入口。
3. 当 `inspect_agent_command_contracts` adapter 缺失时，`/status` 和 `/continue` 都从 public available candidates 中隐藏。
4. 命令契约自检快照中的 `/continue`、`/status` 反映新的 required tools。

## TDD 计划

1. 后端 RED：
   - 更新 `test_agent_command_catalog.py`、`test_agent_command_contracts.py`、`test_dialogs.py`，断言新增 required tool。
   - 新增 catalog 测试：缺少 `inspect_agent_command_contracts` adapter 时，`status` 与 `continue` 不可用。
2. 实现：
   - 在 `chat_commands.py` 中增加 `COMMAND_CONTRACT_REQUIRED_AGENT_TOOLS` 或直接写入 tuple。
3. 验证：
   - `pytest backend/tests/test_agent_command_catalog.py backend/tests/test_agent_command_contracts.py backend/tests/test_dialogs.py -k "chat_command_catalog or agent_command_contracts" -q`
   - `git diff --check`

## 非目标

- 不改 `/status` 响应结构。
- 不改命令契约自检服务逻辑。
- 不改前端 UI。
