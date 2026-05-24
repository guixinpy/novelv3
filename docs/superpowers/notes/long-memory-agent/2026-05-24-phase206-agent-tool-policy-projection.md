# Phase206 Agent Tool Policy Projection Report

## Scope

基于 Phase205 的 `agent_tool_surface`，增加只读的工具策略投影，让 Agent/planner 能直接看到工具读写、确认、并行和未分类状态。

## Plan

见 `docs/superpowers/plans/long-memory-agent/2026-05-24-phase206-agent-tool-policy-projection.md`。

## Reference Project Translation

- Hermes Agent：采用 tool registry / toolset exposure / tool execution 分层思想，本阶段只新增工具策略投影，不改变 executor。
- OpenHuman：吸收 tool scope / permission level / agent tier 的设计，先把可见工具与可执行风险变成稳定字段。
- OpenClaw：吸收 effective tools inventory 和多层 policy pipeline 思路，本阶段先做 inventory/projection，为后续 allow/deny/approval pipeline 打基础。

## RED

- `pytest backend/tests/test_writing_agent_tool_registry.py -k "tool_policy_projection" -q`
  - 初始失败：`KeyError: 'tool_policy_projection'`。
- `pytest backend/tests/test_writing_agent_planner.py -k "ready_next_chapter_tool_chain" -q`
  - 初始失败：`KeyError: 'tool_policy_projection'`。

## Implementation

- 新增 `agent_tool_surface_policy.py`，从 visible/hidden tools 的 `agent_tool_surface` 生成只读 policy projection。
- `build_agent_tool_plan()` 输出 `tool_policy_projection`。
- planner trace 携带 `tool_policy_projection`，用于后续 Agent loop / run trace 读取工具策略状态。
- projection 只包含计数、工具名列表和固定 policy rules，不复制 schema、diagnostics、项目正文、审批 hash 或知识库内容。
- 按审查反馈区分：
  - `approval_required_tools`：write / guarded_write 工具，符合执行层审批口径。
  - `explicit_confirmation_tools`：surface 明确 `requires_confirmation` 的 guarded 工具。

## Validation

- `pytest backend/tests/test_writing_agent_tool_registry.py -k "tool_policy_projection" -q`
  - 1 passed, 60 deselected.
- `pytest backend/tests/test_writing_agent_planner.py -k "ready_next_chapter_tool_chain" -q`
  - 1 passed, 6 deselected.
- `pytest backend/tests/test_writing_agent_tool_registry.py -k "tool_policy_projection or agent_tool_plan_exposes" -q`
  - 3 passed, 58 deselected.
- `pytest backend/tests/test_writing_agent_planner.py -q`
  - 7 passed.
- `pytest backend/tests/test_writing_agent_tool_executor.py -k "tool_executor_handles_describe_agent_tools" -q`
  - 1 passed, 149 deselected.
- `pytest backend/tests/test_writing_agent_runs.py -k "auto_plan or recovery" -q`
  - 20 passed, 155 deselected.
- `python -m compileall backend/app/services/writing_agent`
  - passed.
- `git diff --check`
  - passed.
- Sensitive DeepSeek key-prefix scan
  - no matches.

## Review

- 子代理审查结论：
  - Critical: 无。
  - Important: 原 `confirmation_required_tools` 容易和执行层口径混淆，因为普通 write 工具也需要审批。已改为 `approval_required_tools` 与 `explicit_confirmation_tools` 两个字段。
  - Minor: projection 是只读派生数据；输出规模有界；测试覆盖 registry 与 planner 路径。

## Novel Progress

本阶段不推进正文生成。原因：当前阶段继续补 Agent 工具编排基础设施，使后续真实长篇生成不再依赖用户视角手动挑工具。

## Next

- Phase207 建议开始设计最小 tool policy pipeline：按 Agent role/profile 对 `tool_policy_projection` 进行 allow/deny/filter，而不是直接让所有模块工具暴露给单一 Writing Agent。
