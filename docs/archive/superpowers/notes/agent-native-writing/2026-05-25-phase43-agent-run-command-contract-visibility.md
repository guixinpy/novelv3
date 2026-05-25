# Phase43: Agent Run Command Contract Visibility Report

## 目标

把 Phase38-42 形成的命令契约健康摘要从 planner 内部 trace 提升到 Agent run 详情和前端运行抽屉可见面。

## 变更

- `WritingAgentRunDetail` 新增 `agent_command_contracts` 投影字段。
- `detail_payload(...)` 从 `run.input.planner.trace.agent_health_projection.command_contracts` 抽取轻量摘要：
  - `total_commands`
  - `public_commands`
  - `agent_control_commands`
  - `available_commands`
  - `gap_count`
- `AgentRunDrawer` 展示命令契约摘要：
  - `命令契约: 已投影`
  - `控制命令`
  - `契约缺口`
- 前端类型 `WritingAgentRunDetail` 同步补齐 `agent_command_contracts`。

## RED 证据

- `pytest backend/tests/test_writing_agent_runs.py -k "agent_run_detail_exposes_agent_profile_projection_for_auto_plan" -q`
  - 失败原因：`KeyError: 'agent_command_contracts'`。
- `cd frontend; .\node_modules\.bin\vitest run src/components/writingAgent/AgentRunDrawer.test.ts -t "renders command contract summary"`
  - 失败原因：抽屉未展示 `已投影` 等命令契约摘要字段。

## GREEN 证据

- `pytest backend/tests/test_writing_agent_runs.py -k "agent_run_detail_exposes_agent_profile_projection_for_auto_plan" -q`
  - `1 passed, 184 deselected`
- `cd frontend; .\node_modules\.bin\vitest run src/components/writingAgent/AgentRunDrawer.test.ts`
  - `14 passed`
- `cd frontend; .\node_modules\.bin\vue-tsc --noEmit`
  - 通过
- `git diff --check`
  - 通过；仅保留既有提示：`backend/tests/test_writing_agent_runs.py` CRLF 将被 Git 转为 LF。

## 下一阶段建议

下一步可以把命令契约投影接入聊天侧 Agent run feedback 或 `/status` 卡片的摘要逻辑，形成“当前对话控制面”和“历史 run 控制面”的一致展示。
