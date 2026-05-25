# Phase140 Report: Chapter Reservation Projection

## 阶段目标

让 Writing Agent 在遇到章节目标冲突时，能通过只读工具查询“第 N 章当前被哪些后台任务占用”，为后续恢复动作提供依据。

## 实际完成

- `backend/app/services/writing_agent/agent_job_projection.py`
  - `inspect_agent_job_projection(...)` 新增 `chapter_index` 选择器。
  - 新增章节覆盖解析，支持 `chapter_range`、`chapter_index`、`action_params.chapter_index`、`tools[].params.chapter_index`。
  - 新增 `chapter_reservation` 顶层投影，列出活跃占用任务、来源标签、推荐工具和只读恢复选项。
- `backend/app/services/writing_agent/tool_executor.py`
  - `inspect_agent_job_projection` adapter 透传 `chapter_index`。
- `backend/app/services/writing_agent/tool_registry.py`
  - 工具输入 schema 增加 `chapter_index`。
  - 工具输出 schema 增加 `chapter_reservation`。
- `backend/tests/test_writing_agent_job_projection.py`
  - 新增按章节过滤活跃占用任务的服务测试。
- `backend/tests/test_writing_agent_tool_executor.py`
  - 新增 adapter 透传章节号测试。
  - 顺手修正 intent projection 旧断言，补上当前契约中的 `chapter_index_source`。
- `backend/tests/test_writing_agent_tool_registry.py`
  - 新增 schema 暴露 `chapter_index` 的测试。

## 设计约束

- 本阶段只读，不取消任务、不变更队列、不自动改选章节。
- `chapter_reservation.recovery_options` 只给出安全的 `inspect_occupying_task` 工具请求。
- 章节占用解析保持和 dialog reservation 解析同一语义，避免 Agent 工具看到的占用和对话冲突提示不一致。

## 小说进度

本阶段没有生成新章节。原因：该阶段继续强化长篇自动生成的任务冲突可观测性。

## 已修复的问题

- `chapter_target_conflict` 只能说明“被占用”，Agent 无法按章节查出占用任务。
- `inspect_agent_job_projection` 只能按任务 ID、类型、状态过滤，不能直接服务章节目标冲突排查。

## 未修复但记录的问题

- 仍未提供取消占用任务、等待占用任务结束、改选目标章节的写入型恢复工具。
- `agent_job_projection.py` 与 `dialogs.py` 存在相似的章节 payload 解析逻辑，后续可以考虑抽到共享 helper，避免长期漂移。

## 验证证据

- RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_job_projection.py::test_inspect_agent_job_projection_filters_active_chapter_reservation backend\tests\test_writing_agent_tool_executor.py::test_tool_executor_dispatches_inspect_agent_job_projection_with_chapter_index backend\tests\test_writing_agent_tool_registry.py::test_agent_tool_registry_inspect_agent_job_projection_accepts_chapter_index -q`
  - 结果：`3 failed`。
  - 失败原因：服务不接受 `chapter_index`；executor 未透传；registry schema 缺字段。
- GREEN:
  - 同一 targeted 命令结果：`3 passed in 0.23s`。
  - 修正旧 intent projection 断言后，相关 targeted 命令结果：`4 passed in 0.47s`。
- Regression:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_job_projection.py backend\tests\test_writing_agent_tool_executor.py backend\tests\test_writing_agent_tool_registry.py -q`
  - 结果：`121 passed in 8.07s`。
- Hygiene:
  - `git diff --check`
  - 退出码 0，无输出。
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`
  - 退出码 1，无匹配。

## 子代理审查

本阶段曾派发只读子代理审查当前 diff，但 180 秒内未返回结果，已关闭。最终以本地 TDD、受影响回归和 hygiene 作为提交依据。

## 下一阶段建议

Phase141 建议在此只读投影基础上设计写入型恢复能力：取消安全范围内的 pending 任务、等待/跳过活跃任务、或为 Agent 生成改选下一未写章节的恢复计划。
