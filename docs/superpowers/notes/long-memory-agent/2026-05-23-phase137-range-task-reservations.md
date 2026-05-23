# Phase137 Report: Range Task Reservations

## 阶段目标

把 active `generate_chapter_range` 批量章节任务纳入章节目标占用计算，避免单章续写和批量生成撞车。

## 实际完成

- `backend/app/api/dialogs.py`
  - `_active_chapter_task_indexes(...)` 现在扫描 `generate_chapter_range`。
  - `_chapter_indexes_from_task_payload(...)` 支持解析 `payload.chapter_range.start/end`。
  - 有效章节范围会展开为占用章节集合。
  - 继续保留单章 payload 和 writing agent tool params 的解析。
- `backend/tests/test_dialogs.py`
  - 新增 active range task 覆盖第 2-3 章时，`继续吧` 自动选择第 4 章的测试。

## 设计约束

- 不改变批量任务创建、执行和重试逻辑。
- 只把 range task 作为章节目标推断时的 reservation 来源。
- 只解析 `start <= end` 的正整数范围。

## 小说进度

本阶段没有生成新章节。原因：这是长篇批量生产与单章续写并行时的调度安全补强。

## 已修复的问题

- `generate_chapter_range` 正在运行第 2-3 章时，用户说 `继续吧` 仍会选择第 2 章，导致单章生成和批量任务潜在冲突。

## 未修复但记录的问题

- range 很大时会展开为集合；当前千章级可接受，后续如果支持更大范围可改为区间判断。
- 显式 `/chapter N` 与 range task 冲突时会复用 Phase135 的提示，但尚未为 range 来源提供更具体的“被批量任务占用”文案。
- 任务取消/替换仍需后续独立能力。

## 验证证据

- RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_chat_text_continue_skips_active_chapter_range_task -q`
  - 结果：`1 failed`
  - 失败原因：仍返回 `chapter_index == 2`。
- GREEN:
  - 同一 targeted 命令。
  - `1 passed in 0.18s`
- Dialog regression:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py -q`
  - `75 passed in 23.28s`
- Hygiene:
  - `git diff --check`
  - 退出码 0，无输出。
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`
  - 退出码 1，无匹配。

## 下一阶段建议

Phase138 建议把章节目标冲突的来源类型细化到 pending action、single task、range task，供前端和 trace audit 展示更准确的风险说明。
