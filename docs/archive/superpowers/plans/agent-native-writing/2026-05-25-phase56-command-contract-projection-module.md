# Phase56: 命令契约投影模块

## 背景

`agent_command_contracts` 与 `agent_control_plane_readiness` 都来自 planner trace 的健康投影。控制面摘要已经抽成共享模块，命令契约摘要仍留在 `run_service` 私有函数中，后续若 Trace audit / Job projection 也需要展示命令契约，会继续复制逻辑。

## 目标

新增共享纯函数模块，统一从 `run.input.planner.trace.agent_health_projection.command_contracts` 提取有界命令契约摘要，并替换 `run_service` 中的私有实现。

## 范围

1. 新增 `command_contract_projection.py`。
2. 提供：
   - `COMMAND_CONTRACTS_SOURCE`
   - `command_contracts_from_run_input(run_input)`
3. 替换 `run_service.detail_payload()` 的 `agent_command_contracts` 来源。

## 非目标

- 不改变 API 输出字段。
- 不新增 Trace / Job 的命令契约展示。
- 不改变 `inspect_agent_command_contracts` 工具本身。

## 验证

- T0: `pytest backend/tests/test_command_contract_projection.py -q`
- T1: `pytest backend/tests/test_writing_agent_runs.py -k "agent_run_detail_exposes_agent_profile_projection_for_auto_plan" -q`
- T0: `git diff --check`
