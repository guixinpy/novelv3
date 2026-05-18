# Phase 138: 重启后清理 pending 后台任务

## 背景

后台任务服务会在应用启动时把中断的 `running` 任务标记为 failed。
但 `pending` 同样属于 active task。进程在任务提交后、runner 真正 mark running 前重启时，pending 任务会永久保留。

长篇生成任务通常带 idempotency key。
如果旧 pending 不清理，用户再次触发同一范围任务时会复用这个永远不会执行的任务，造成“看起来已有任务，但实际没有推进”的卡死。

## 修复

- `fail_interrupted_running_tasks` 内部扫描 `ACTIVE_TASK_STATUSES`。
- 重启恢复时同时清理：
  - `pending`
  - `running`
- 保留原方法名，避免修改启动入口。

## 验证

- 先新增失败测试：
  - `backend/tests/test_background.py::test_background_task_service_marks_interrupted_pending_tasks_failed`
  - RED：旧实现 count 为 0，pending 任务仍占用 idempotency key。
- 修复后通过：
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_background.py::test_background_task_service_marks_interrupted_pending_tasks_failed backend\tests\test_background.py::test_background_task_service_marks_interrupted_running_tasks_failed -q`
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_background.py -q`

## 后续观察

- 可在 UI 中区分“重启中断失败”和业务失败，前者优先显示“可重试”。
- 如果未来引入外部队列，pending/running 的恢复策略应迁移到队列消费者所有权检测。
