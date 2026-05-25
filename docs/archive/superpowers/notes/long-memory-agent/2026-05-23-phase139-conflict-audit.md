# Phase139 Report: Conflict Audit

## 阶段目标

保留章节目标冲突的审批后审计信息，让用户确认冲突操作后，系统仍能在结果视图和 Agent trace audit 中追溯冲突来源。

## 实际完成

- `backend/app/api/dialogs.py`
  - 新增 `_approval_chapter_target_conflict(...)`。
  - `approval_decision` 会保存清洗后的 `chapter_target_conflict`。
- `backend/app/services/actions/action_result_view.py`
  - 审批结果详情新增 `章节冲突` 行，显示 `source_label`。
- `backend/app/services/writing_agent/agent_trace_audit.py`
  - 新增 `_chapter_target_conflict_summary(...)`。
  - `approval_events` 和 `event_chain` 均投影同一份冲突摘要。
- `backend/tests/test_dialogs.py`
  - 新增确认章节冲突后保留审批元数据和结果视图行的测试。
- `backend/tests/test_writing_agent_trace_audit.py`
  - 扩展 trace audit 测试，覆盖审批事件和事件链。

## 设计约束

- 不改变冲突检测与冲突处理策略；仍然只提示，不阻断。
- 不暴露 task id、approval hash 等敏感或低层实现细节。
- 审计对象只保留 `status/chapter_index/reason/source/source_label`。

## 小说进度

本阶段没有生成新章节。原因：该阶段继续补齐 Agent 长篇控制面的审计链路。

## 已修复的问题

- 用户确认一个已有冲突提示的章节生成后，冲突来源会在审批结果里丢失。
- `inspect_agent_trace_audit` 无法解释该审批当时是否存在章节目标冲突。

## 未修复但记录的问题

- 任务列表仍缺少从冲突来源跳转到占用任务的 UI。
- 章节冲突确认后仍没有提供“取消占用任务/改选目标章节”的二次操作分支。

## 验证证据

- RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_resolve_chapter_conflict_confirmation_records_decision_metadata backend\tests\test_writing_agent_trace_audit.py::test_inspect_agent_trace_audit_includes_dialog_approval_events_without_raw_hash -q`
  - 结果：`2 failed`。
  - 失败原因：`approval_decision` 缺少 `chapter_target_conflict`；trace audit 未投影冲突对象。
- GREEN:
  - 同一 targeted 命令结果：`2 passed in 0.38s`。
- Regression:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py backend\tests\test_writing_agent_trace_audit.py -q`
  - 结果：`80 passed in 27.70s`。
- Hygiene:
  - `git diff --check`
  - 退出码 0，无输出。
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`
  - 退出码 1，无匹配。

## 下一阶段建议

Phase140 建议继续把冲突审计转化为 Agent 可执行恢复动作：查看占用任务、取消占用任务、改选目标章节，优先服务长篇自动生成时的队列恢复能力。
