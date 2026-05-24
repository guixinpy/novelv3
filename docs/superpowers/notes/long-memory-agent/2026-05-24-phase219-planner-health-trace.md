# Phase219 Report: Planner Health Trace

## Scope

本阶段把 Phase218 的 `inspect_agent_health_projection` 接入 planner trace。现在 `build_writing_agent_run_plan()` 会在计划里附带 compact `trace.agent_health_projection`，让 Agent 在执行前看到当前工具面、profile、路由和写入门禁健康状态。

本阶段仍然只读、非阻塞：不改变 selected tools、route behavior、profile filtering、approval contract 或 risk flags。

## Plan

见 `docs/superpowers/plans/long-memory-agent/2026-05-24-phase219-planner-health-trace.md`。

## RED

扩展 `test_planner_builds_ready_next_chapter_tool_chain()`：

- 断言 `plan["trace"]["agent_health_projection"]` 存在。
- 断言它是 compact projection，不包含完整 `profile_policy`。
- 保持原有工具链断言不变，确保 health trace 不改变 planner 行为。

初始失败符合预期：

```text
KeyError: 'agent_health_projection'
```

## Implementation

- `backend/app/services/writing_agent/agent_health_projection.py`
  - `inspect_agent_health_projection()` 新增可选 `tool_plan` 参数。
  - planner 传入现有 `tool_plan` 时不会重复构建工具计划。
- `backend/app/services/writing_agent/planner.py`
  - 新增 `_planner_health_projection()`。
  - 计划 trace 增加 compact `agent_health_projection`：
    - `version`
    - `status`
    - `diagnostic_count`
    - `diagnostics`
    - `recommended_tools`
  - 不将 health diagnostics 写入 `risk_flags`。
- `backend/tests/test_writing_agent_planner.py`
  - 覆盖 planner trace health evidence 和工具链不变。

## Validation

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_planner.py backend\tests\test_writing_agent_health_projection.py -k "health_projection or ready_next_chapter" -q`
  - 3 passed, 7 deselected.
- `backend\.venv\Scripts\python.exe -m compileall backend\app\services\writing_agent`
  - passed.
- `git diff --check`
  - passed.
- DeepSeek key prefix scan:
  - `$pat='sk-'+'f6aa'; rg -n $pat backend frontend docs --glob '!frontend/node_modules/**'`
  - no matches.

## Review

Planner 现在不再只是生成工具链，也携带一份健康证据。这对后续 Agent 化很关键：当用户只说“继续写”时，Agent 可以在计划层看到工具契约、路由偏好、profile policy 或写入门禁是否有风险，而不必靠人工翻多个诊断工具。

本阶段刻意没有让 health 影响 status，避免把观测信号直接变成执行阻塞。下一步可以基于真实 dogfood 观察哪些 health diagnostics 应进入 planner decision。

## Novel Progress

本阶段不推进正文生成。原因：仍在夯实 Agent 自主规划基础，让后续真实长篇生成能由系统自身发现工具/路由/记忆风险。

## Next

- 将 `trace.agent_health_projection` 显示到 run detail compact view，方便用户和 Agent 共同检查计划健康。
- 评估哪些 health diagnostics 应成为 planner risk flags，哪些只作为 recommended followups。
- 继续真实长篇 dogfood 时，把 health trace 与章节质量问题关联起来。
