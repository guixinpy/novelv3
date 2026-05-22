# Phase135 Report: Explicit Chapter Conflict Warning

## 阶段目标

当用户明确指定的章节已经被 pending/running 生成目标占用时，不擅自改章，但在确认前给出冲突提示。

## 实际完成

- `backend/app/api/dialogs.py`
  - `_chapter_action_params_for_project(...)` 在显式章节号命中 reserved target 时，写入 `chapter_target_conflict`。
  - 新增 `_chapter_target_conflict(...)`，输出净化后的冲突对象。
- `backend/app/services/actions/descriptions.py`
  - `preview_chapter` 和 `generate_chapter` 描述支持追加冲突提示。
  - 提示文案：`注意：第N章已有待确认或运行中的生成任务，请确认是否仍要继续。`
- `backend/tests/test_dialogs.py`
  - 新增 `/chapter 2` 撞上 running task 时保留第 2 章并显示冲突提示的测试。

## 设计约束

- 显式用户意图优先，不自动跳到其它章节。
- 冲突提示只影响 pending action 参数和描述，不阻断执行。
- 冲突对象不包含任务 ID、prompt 或其它敏感内容。

## 小说进度

本阶段没有生成新章节。原因：这是续写控制面安全提示，用于避免长篇连续创作中误触重复生成。

## 已修复的问题

- 用户显式指定第 2 章，而第 2 章已有 active task 时，系统仍给出普通确认文案，没有任何冲突提示。

## 未修复但记录的问题

- 目前冲突仍允许用户继续确认；后续可提供“查看占用任务/取消旧任务/继续覆盖”的分支决策。
- 前端没有为 `chapter_target_conflict` 做专门警示样式，只能通过描述文本显示。
- `generate_chapter_range` 任务仍未纳入冲突提示。

## 验证证据

- RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_chapter_command_explicit_reserved_target_adds_conflict_warning -q`
  - 结果：`1 failed`
  - 失败原因：pending params 缺少 `chapter_target_conflict`。
- GREEN:
  - 同一 targeted 命令。
  - `1 passed in 0.24s`
- Dialog regression:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py -q`
  - `74 passed in 28.16s`
- Hygiene:
  - `git diff --check`
  - 退出码 0，无输出。
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`
  - 退出码 1，无匹配。

## 下一阶段建议

Phase136 建议把 `chapter_target_conflict` 接入前端 ChatMessage 的可见 detail/warning 样式，避免用户只在长描述里扫到风险。
