# Phase57: Trace / Job 命令契约投影

## 背景

Phase56 已把 `run.input.planner.trace.agent_health_projection.command_contracts` 抽成共享投影模块，但只有 run detail 使用该模块。Trace audit 与 Job projection 仍只能看到控制面就绪度，无法直接判断 `/` 命令向 Agent 控制命令迁移后的契约健康度。

## 目标

在 Trace audit 与 Job projection 中复用 `command_contracts_from_run_input()`，展示有界命令契约摘要，并在命令契约存在 gap 时推荐 `inspect_agent_command_contracts`。

## 范围

1. `inspect_agent_trace_audit` 输出新增 `command_contracts`。
2. Trace audit 的 `audit` 摘要新增命令契约统计字段。
3. Trace audit 在 command contract gap 存在时推荐 `inspect_agent_command_contracts`。
4. `inspect_agent_job_projection` 的 selected task 和 `agent_runs` 新增有界 `command_contracts`。
5. Job projection 在 command contract gap 存在时推荐 `inspect_agent_command_contracts`。

## 非目标

- 不改变命令契约生成工具本身。
- 不暴露原始 `commands` 列表。
- 不改前端展示；本阶段只补后端投影能力。

## 验证

- TDD RED: 新增/扩展 Trace audit 与 Job projection 测试，先验证失败。
- T0: `pytest backend/tests/test_writing_agent_trace_audit.py -k "command_contracts" -q`
- T0: `pytest backend/tests/test_writing_agent_job_projection.py -k "command_contracts" -q`
- T1: `pytest backend/tests/test_writing_agent_trace_audit.py -k "control_plane_readiness or command_contracts" -q`
- T1: `pytest backend/tests/test_writing_agent_job_projection.py -k "active_control_plane or command_contracts" -q`
- T0: `git diff --check`
