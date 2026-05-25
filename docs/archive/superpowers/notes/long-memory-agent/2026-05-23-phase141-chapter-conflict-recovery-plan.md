# Phase141 Report: Chapter Conflict Recovery Plan

## 阶段目标

把章节目标冲突从“可观察”推进到“可规划恢复”：Agent 输入目标章节后，可以得到一个只读恢复工具计划，决定是继续生成，还是先检查占用任务并等待处理。

## 实际完成

- `backend/app/services/writing_agent/chapter_conflict_recovery_planner.py`
  - 新增 `plan_chapter_conflict_recovery(...)`。
  - 复用 `inspect_agent_job_projection(..., chapter_index=...)` 的占用投影。
  - 目标章节可用时，返回 `generate_chapter` 工具计划。
  - 目标章节被占用时，返回 `inspect_agent_job_projection` 工具链和 `wait_for_occupying_task` 恢复选项。
- `backend/app/services/writing_agent/tool_executor.py`
  - 新增 `plan_chapter_conflict_recovery` static adapter。
- `backend/app/services/writing_agent/tool_registry.py`
  - 新增 `plan_chapter_conflict_recovery` 工具描述、输入/输出 schema、非阻塞报告属性。
- `backend/tests/test_chapter_conflict_recovery_planner.py`
  - 覆盖章节可用与章节被 running range task 占用两种路径。
- `backend/tests/test_writing_agent_tool_executor.py`
  - 覆盖 adapter 对 `chapter_index` 的透传。
- `backend/tests/test_writing_agent_tool_registry.py`
  - 覆盖 registry schema 和 allowed/non-blocking 集合。

## 设计约束

- 本阶段保持只读计划，不取消任务、不重排队列、不绕过用户确认执行写动作。
- 当章节被占用时，不建议跳写后续章节，避免破坏长篇顺序连续性。
- 恢复计划保留机器可读结构：`conflict`、`recovery`、`tools`、`recovery_options`、`trace`。

## 小说进度

本阶段没有生成新章节。原因：当前阶段继续补齐长篇自动生成的任务冲突恢复能力，避免后续真实生成时因重复章节目标导致队列混乱。

## 已修复的问题

- Agent 能查到章节占用后，仍缺少一个把占用状态转成下一步工具链的统一入口。
- 章节目标可用与被占用时的下一步动作没有统一结构，难以被上层 Agent 编排。

## 未修复但记录的问题

- 尚未实现确认后取消 pending 占用任务的写入工具。
- 尚未为写入动作生成 `mutation_fingerprint`，失败恢复仍可能缺少精确目标身份。
- 工具结果还没有统一 `llm_summary/markdown_summary`，大结果压缩策略后续需要补齐。

## 参考项目吸收

本阶段派发只读子代理检查 `openclaw`、`hermes-agent`、`openhuman`。可迁移结论：

- 工具计划应分层输出 visible/blocked/diagnostics，而不是只列可用工具。
- 写路径应坚持“只读计划 -> 显式确认/哈希校验 -> 执行”。
- 写动作需要 mutation fingerprint，避免恢复逻辑跨目标误清失败。
- 失败恢复建议应结构化输出，包含 error_code/recoverable/recovery_action/recommended_next_tools。
- 工具结果应同时服务程序和 LLM，保留 JSON 的同时提供摘要，避免上下文膨胀。

本阶段采用了“只读计划先行”的模式，后续阶段应继续推进 mutation fingerprint 和结构化恢复错误。

## 验证证据

- RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapter_conflict_recovery_planner.py backend\tests\test_writing_agent_tool_executor.py::test_tool_executor_dispatches_plan_chapter_conflict_recovery_adapter backend\tests\test_writing_agent_tool_registry.py::test_agent_tool_registry_includes_plan_chapter_conflict_recovery -q`
  - 结果：`1 error`。
  - 失败原因：`ModuleNotFoundError: No module named 'app.services.writing_agent.chapter_conflict_recovery_planner'`。
- GREEN:
  - 同一 targeted 命令结果：`4 passed in 0.38s`。
- Regression:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapter_conflict_recovery_planner.py backend\tests\test_writing_agent_tool_executor.py backend\tests\test_writing_agent_tool_registry.py backend\tests\test_writing_agent_job_projection.py -q`
  - 结果：`125 passed in 7.07s`。
- Hygiene:
  - `git diff --check`
  - 退出码 0，无输出。
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`
  - 退出码 1，无匹配。

## 下一阶段建议

Phase142 建议实现写动作 mutation fingerprint 的只读投影或契约检查，先覆盖 `generate_chapter`、`generate_chapter_range` 和 `apply_world_model_proposal_resolution`，为后续安全恢复和失败去重打基础。
