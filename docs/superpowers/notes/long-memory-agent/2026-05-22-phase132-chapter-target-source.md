# Phase132 Report: Chapter Target Source

## 阶段目标

继续降低用户输入门槛：支持 `下一章` 这类更短的续写请求，并让 pending action 能解释章节号来自用户显式指定还是系统推断。

## 实际完成

- `backend/app/core/intent_router.py`
  - `preview_chapter` candidate params 新增 `chapter_index_source`。
  - 显式章节号输入标记为 `explicit_user`。
  - 无显式章节号但命中确定性章节规则时标记为 `router_default`。
  - 低细节续写短语新增：`下一章`、`接着写`、`继续下一章`。
- `backend/app/api/dialogs.py`
  - `_chapter_action_params_for_project(...)` 在系统根据 outline/正文推断下一章时，标记 `chapter_index_source = "inferred_next_unwritten"`。
  - 用户显式指定章节号时，标记 `chapter_index_source = "explicit_user"`。
- `backend/tests/test_dialogs.py`
  - 新增 router 测试覆盖 `下一章`。
  - 更新 projection 测试覆盖显式来源。
  - 新增 endpoint 测试覆盖系统推断来源。

## 设计约束

- 来源字段只做可审计说明，不改变执行语义。
- 仍然不让 `IntentRouter` 访问数据库。
- dialog API 是章节目标最终补全层，pending action 保存最终可执行参数。

## 小说进度

本阶段没有生成新章节。原因：该阶段继续强化 Agent 自动续写入口和可解释性，是长篇生成前的控制面能力。

## 已修复的问题

- `下一章` 这类真实短输入会掉入 free chat。
- 用户和系统都可能给出章节号，但 pending action 之前无法说明目标来源。

## 未修复但记录的问题

- `接着来一章`、`继续往后` 等更口语化表达还没有覆盖。
- `chapter_index_source` 尚未进入前端 UI 展示和 trace audit 汇总。
- 章节目标推断没有检查正在运行的后台任务；后续可避免并发续写重复目标。

## 验证证据

- RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_intent_router_next_chapter_phrase_uses_chapter_when_outline_ready backend\tests\test_dialogs.py::test_intent_router_projection_explains_chapter_route backend\tests\test_dialogs.py::test_chat_text_next_chapter_uses_inferred_chapter_source -q`
  - 结果：`3 failed`
  - 失败原因：
    - `下一章` 未命中 intent。
    - projection 缺少 `chapter_index_source`。
    - endpoint 返回 free chat，没有 pending action。
- GREEN:
  - 同一 targeted 命令。
  - `3 passed in 0.20s`
- Dialog regression:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py -q`
  - `71 passed in 29.60s`
- Hygiene:
  - `git diff --check`
  - 退出码 0，无输出。
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`
  - 退出码 1，无匹配。

## 下一阶段建议

Phase133 建议把 `chapter_index_source` 接入 trace audit 或 action result view，让用户确认和后续 Agent 审计都能看到“为什么选中这一章”。
