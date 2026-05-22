# Phase133 Report: Chapter Target Audit

## 阶段目标

把 Phase132 产生的章节目标来源从 pending action 继续传递到审批元数据、用户可见结果视图和 Agent trace audit。

## 实际完成

- `backend/app/api/dialogs.py`
  - `_approval_decision_metadata(...)` 现在会从 pending params 中提取 `chapter_index` 和 `chapter_index_source`。
  - 只写入正整数章节号和非空来源字符串，不记录 prompt 或敏感内容。
- `backend/app/services/actions/action_result_view.py`
  - `detail_items` 新增“目标章节”。
  - 当来源存在时，新增“章节来源”。
  - 来源中文映射：`explicit_user -> 用户指定`，`inferred_next_unwritten -> 系统推断`，`router_default -> 默认目标`。
- `backend/app/services/writing_agent/agent_trace_audit.py`
  - `approval_events` 投影章节号、来源和来源中文标签。
  - `event_chain` 的 `approval_decision` 节点携带同样的章节目标字段。
  - 仍然不暴露 approval contract hash。
- `backend/tests/test_dialogs.py`
  - 扩展审批确认测试，覆盖视图和决策元数据。
- `backend/tests/test_writing_agent_trace_audit.py`
  - 扩展 trace audit 测试，覆盖 approval event 与 event chain。

## 设计约束

- 没有新增表和迁移；复用既有 `approval_decision` 事件载体。
- 只做可审计字段投影，不改变后台任务调度和执行逻辑。
- 来源缺失时不强行填充，以兼容旧 pending action。

## 小说进度

本阶段没有生成新章节。原因：这是 Agent 控制面可解释性增强，用于后续长篇生成时追踪“为什么这次写这一章”。

## 已修复的问题

- pending action 虽然知道 `chapter_index_source`，但确认后 action result 和 trace audit 丢失该信息。
- 用户看到“正文生成中...”时无法判断是自己指定章节，还是系统自动续写推断。

## 未修复但记录的问题

- 前端 chat 详情组件虽然能显示 `detail_items`，但没有专门的章节来源视觉层级。
- `chapter_index_source` 尚未接入后台任务列表或 Agent run 列表。
- 并发运行中仍可能出现两个续写请求选中同一章节，后续需结合 running task 检查。

## 验证证据

- RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_resolve_chapter_action_confirm_dispatches_prepare_tool backend\tests\test_writing_agent_trace_audit.py::test_inspect_agent_trace_audit_includes_dialog_approval_events_without_raw_hash -q`
  - 结果：`2 failed`
  - 失败原因：
    - action result view 只显示用户决策和审批模式。
    - trace audit approval event 缺少章节目标字段。
- GREEN:
  - 同一 targeted 命令。
  - `2 passed in 0.34s`
- Regression:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py backend\tests\test_writing_agent_trace_audit.py -q`
  - 初次发现既有审批元数据测试期望需要更新。
  - 更新后：`74 passed in 30.12s`
- Hygiene:
  - `git diff --check`
  - 退出码 0，无输出。
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`
  - 退出码 1，无匹配。

## 下一阶段建议

Phase134 建议处理并发续写目标冲突：当已有 `generate_chapter` pending/running task 指向第 N 章时，新的低细节续写请求应跳过或阻断，而不是再次选择同一章。
