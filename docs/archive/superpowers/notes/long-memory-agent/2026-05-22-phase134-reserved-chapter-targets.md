# Phase134 Report: Reserved Chapter Targets

## 阶段目标

避免低细节续写请求在已有 pending action 或 active task 占用章节时重复选择同一章。

## 实际完成

- `backend/app/api/dialogs.py`
  - 引入 `BackgroundTask` 查询。
  - 新增 `_reserved_chapter_indexes(...)`。
  - 新增 `_pending_chapter_action_indexes(...)`，扫描 pending `preview_chapter/generate_chapter` action。
  - 新增 `_active_chapter_task_indexes(...)`，扫描 active `generate_chapter/writing_agent_run` task。
  - 新增 `_chapter_indexes_from_task_payload(...)` 和 `_optional_positive_int(...)` 做 JSON 参数解析与净化。
  - `_first_unwritten_outline_chapter_index(...)` 现在跳过已生成章节和已占用章节。
- `backend/tests/test_dialogs.py`
  - 新增 pending action 占用第 2 章时，`继续吧` 选择第 3 章的测试。
  - 新增 running `writing_agent_run` 占用第 2 章时，`继续吧` 选择第 3 章的测试。

## 设计约束

- 不引入锁、迁移或全局调度器改造。
- 只在“章节目标推断”时避让占用目标。
- 保留显式章节号优先：如果用户明确要求第 N 章，本阶段不替用户改目标。

## 小说进度

本阶段没有生成新章节。原因：该阶段处理长篇连续生成时的重复目标风险，是自动续写稳定性基础。

## 已修复的问题

- 第 2 章已有未确认 pending action 时，新的 `继续吧` 仍会选择第 2 章。
- 第 2 章已有 active writing agent task 时，新的 `继续吧` 仍会选择第 2 章。

## 未修复但记录的问题

- 显式指定章节号时仍可能撞上 active task；后续需要在确认前给出冲突提示。
- reservation 扫描是应用层判断，不是数据库互斥锁；高并发下仍需要后续加更强约束。
- 章节范围任务 `generate_chapter_range` 暂未纳入占用计算。

## 验证证据

- RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_chat_text_continue_skips_reserved_pending_chapter backend\tests\test_dialogs.py::test_chat_text_continue_skips_active_chapter_task -q`
  - 结果：`2 failed`
  - 失败原因：两个场景都仍返回 `chapter_index == 2`。
- GREEN:
  - 同一 targeted 命令。
  - `2 passed in 0.24s`
- Dialog regression:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py -q`
  - `73 passed in 29.94s`
- Hygiene:
  - `git diff --check`
  - 退出码 0，无输出。
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`
  - 退出码 1，无匹配。

## 下一阶段建议

Phase135 建议处理显式章节冲突提示：当用户明确指定的章节已有 pending/running 目标时，不自动改章，而是给出确认前冲突说明。
