# Phase131 Report: Next Unwritten Chapter Target

## 阶段目标

让 `继续吧` 和无参数 `/chapter` 在项目已有正文时，自动选择第一个未写的章节，而不是固定落到第 1 章。

## 实际完成

- `backend/app/api/dialogs.py`
  - 新增 `_generated_chapter_indexes(...)`，从已有正文记录识别已写章节。
  - 新增 `_outline_chapter_indexes(...)`，从最新 generated outline 中读取章节顺序。
  - 新增 `_first_unwritten_outline_chapter_index(...)`，优先选择 outline 中第一个未写章节；如果 outline 全部已写，则回退到 `max(generated) + 1`。
  - 新增 `_chapter_action_params_for_project(...)`，仅在用户未显式指定章节号时进行项目状态感知补全。
  - text intent 和 slash command 两条 `preview_chapter` 路径都改用该补全。
- `backend/tests/test_dialogs.py`
  - 新增 `test_chat_text_low_detail_continue_uses_first_unwritten_outline_chapter`。
  - 新增 `test_chapter_command_without_index_uses_first_unwritten_outline_chapter`。

## 设计约束

- 显式章节号优先：`/chapter 2 ...`、`写第2章` 等已有行为不被覆盖。
- `IntentRouter` 继续保持无数据库依赖，只负责识别“要写章节”。
- 项目状态推断放在 dialog API 创建 pending action 前完成，pending action 中继续保存明确的 `chapter_index`。

## 小说进度

本阶段没有生成新章节。原因：该阶段修复的是 Agent 自主选择目标章节的基础能力，是后续真实长篇生成的前置稳定性问题。

## 已修复的问题

- 用户说 `继续吧` 时，即使第 1 章已生成，也会继续创建第 1 章 pending action。
- `/chapter` 无参数时同样固定默认第 1 章，不符合 Agent 化后的“自动续写”语义。

## 未修复但记录的问题

- `下一章` 这类更短输入还没有作为单独自然语言 intent 覆盖。
- “已写章节”的判断当前基于非空正文内容，后续可结合版本状态、草稿状态和任务运行态统一定义。
- 多 outline 版本的选择目前沿用最新 generated outline，后续如引入 outline versioning，应接入版本快照。

## 验证证据

- RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_chat_text_low_detail_continue_uses_first_unwritten_outline_chapter backend\tests\test_dialogs.py::test_chapter_command_without_index_uses_first_unwritten_outline_chapter -q`
  - 结果：`2 failed`
  - 失败原因：两个路径都仍返回 `chapter_index == 1`。
- GREEN:
  - 同一 targeted 命令。
  - `2 passed in 0.24s`
- Dialog regression:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py -q`
  - `69 passed in 26.95s`
- Hygiene:
  - `git diff --check`
  - 退出码 0，无输出。
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`
  - 退出码 1，无匹配。

## 下一阶段建议

Phase132 建议继续收敛低细节自然语言入口：支持 `下一章`、`接着写`、`继续下一章` 等更真实的用户输入，并在 intent projection 中标明章节号来源是“用户显式指定”还是“系统推断”。
