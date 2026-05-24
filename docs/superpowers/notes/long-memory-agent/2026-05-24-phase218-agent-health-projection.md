# Phase218 Report: Agent Health Projection

## Scope

本阶段新增只读 Agent health projection，让 Writing Agent 能从一个工具面读取：

- profile/tool policy 一致性；
- 对话路由偏好；
- 工具契约覆盖；
- 写入门禁覆盖；
- 可选 latest run Trace profile policy evidence。

这不是新的执行中心，也不改变 planner、executor、route、profile filtering 或写入门禁。它只聚合已有 projection，让 Agent 在规划前能自己诊断工具面风险。

## Plan

见 `docs/superpowers/plans/long-memory-agent/2026-05-24-phase218-agent-health-projection.md`。

## Subagent Review

子代理提醒：Phase218 不应重新发明 route/health 模块，而应把 `profile_policy_audit` 从“实现已返回”补齐到“契约可依赖、run health 可看见、followup 可规划”。

本阶段吸收为：

- 新 health projection 只复用现有 projection，不重新定义路由逻辑。
- 补齐 `inspect_agent_trace_audit` descriptor 的 `profile_policy_audit` output schema。
- 把 `inspect_agent_health_projection` 和 `inspect_agent_route_preference_projection` 加入 safe read-only recommended followups。
- 不输出 raw `delegate_edges`。

## RED

新增 `backend/tests/test_writing_agent_health_projection.py`：

- `inspect_agent_health_projection()` 初始导入失败，证明 service 不存在。
- 测试 profile policy issue 会进入 compact diagnostics，且不泄露 raw `delegate_edges`。
- 测试传入 `run_id` 时，会读取 `inspect_agent_trace_audit` 的 compact profile policy status。

## Implementation

- `backend/app/services/writing_agent/agent_health_projection.py`
  - 新增 `inspect_agent_health_projection()`。
  - 聚合 `build_agent_tool_plan`、`inspect_agent_route_preference_projection`、`build_agent_tool_contract_snapshot`、`inspect_agent_write_gate_coverage`、可选 `inspect_agent_trace_audit`。
  - 输出 `status`、compact sections、`diagnostics`、`recommended_tools`、`recommended_next_tools`。
- `backend/app/services/writing_agent/agent_core_tool_descriptors.py`
  - 注册 `inspect_agent_health_projection` descriptor。
- `backend/app/services/writing_agent/agent_core_tool_adapters.py`
  - 注册 static read adapter。
- `backend/app/services/writing_agent/agent_memory_trace_tool_descriptors.py`
  - 补齐 `inspect_agent_trace_audit.output_schema.profile_policy_audit`。
- `backend/app/services/writing_agent/recommended_followup_planner.py`
  - 允许 health projection 和 route preference projection 作为安全只读 followup。
- Tests
  - 增加 service、registry、adapter metadata、dispatch、safe followup 覆盖。

## Validation

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_health_projection.py backend\tests\test_writing_agent_tool_executor.py backend\tests\test_writing_agent_tool_registry.py -k "agent_health_projection or profile_policy_audit or plan_recommended_followups_allows_health or static_adapter_names" -q`
  - 8 passed, 214 deselected.
- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_health_projection.py backend\tests\test_writing_agent_tool_executor.py -k "agent_health_projection or static_adapter_names" -q`
  - 5 passed, 152 deselected.
- `backend\.venv\Scripts\python.exe -m compileall backend\app\services\writing_agent`
  - passed.
- `git diff --check`
  - passed.
- DeepSeek key prefix scan:
  - `$pat='sk-'+'f6aa'; rg -n $pat backend frontend docs --glob '!frontend/node_modules/**'`
  - no matches.

## Review

这一阶段把 Phase217 的 Trace profile policy evidence 往上接了一层：Agent 现在有一个可调用的健康投影工具，能在继续编排前发现 profile policy、route preference、tool contracts 和 write gates 的风险。

它仍然只读；风险只变成诊断和 recommended followups，不会自动执行 route opt-in 或 guarded write。

## Novel Progress

本阶段不推进正文生成。原因：当前目标仍是把 novelv3 转成可自主编排的写作 Agent；health projection 是后续低细节用户输入下自主规划和长篇稳定生成的前置能力。

## Next

- 把 health projection 接入 `plan_writing_agent_run` 的 preflight trace，让 planner 在选定 profile/工具链时带上健康摘要。
- 为 health projection 增加 UI/run detail compact 展示，但保持完整诊断只在 Agent tool output 中可查。
- 后续可把 run detail 的 `continuation_state` 接上 `profile_policy_health`，让用户和 Agent 都能看到下一步是否应先诊断。
