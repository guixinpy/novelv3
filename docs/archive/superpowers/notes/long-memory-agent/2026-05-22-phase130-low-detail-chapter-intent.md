# Phase130 Report: Low Detail Chapter Intent

## 阶段目标

让用户在项目已经具备设定、故事线和大纲后，只说 `继续吧` 这类低细节自然语言，也能进入章节生成 pending action，而不是退回普通聊天。

## 实际完成

- `backend/app/core/intent_router.py`
  - 新增低细节章节继续规则。
  - 当 `outline` 已完成，且输入不指向设定/故事线/大纲等其它规划层时，`继续吧/继续写吧/开始写吧/开写吧/往下写/推进吧/继续推进/可以开始了/开始吧` 会被路由为 `preview_chapter`。
  - 默认 `chapter_index = parse_chapter_index(text) or 1`。
  - 新 match evidence：`low_detail_continue_phrase`。
- `backend/tests/test_dialogs.py`
  - 新增 router 单测，验证 `继续吧` 在 outline ready 时命中章节 intent。
  - 新增 dialog endpoint 测试，验证真实项目状态下 `继续吧` 创建 `preview_chapter` pending action，并保留 `command_args`。

## 关键发现

当前 `build_project_diagnosis(...)` 在 outline 已生成但还没有正文时，仍可能返回 `suggested_next_step="preview_outline"`。因此低细节章节规则不能依赖 `suggested_next_step == "preview_chapter"`，否则端点层不会触发。

本阶段采用更直接的条件：`outline` 已完成，并排除明确指向设定/故事线/大纲的输入。

## 小说进度

本阶段没有生成新章节。原因：本阶段修复的是用户自然语言到 Agent 工具链的路由能力，避免后续真实写作必须依赖 `/chapter` 命令。

## 已修复的问题

- `/chapter` 能触发章节 pending action，但 `继续吧` 这类真实用户低细节输入会掉到 free chat。
- Agent 自主推进能力过度依赖用户显式命令的问题得到一处收敛。

## 未修复但记录的问题

- `chapter_index` 仍默认 1，尚未根据已有正文自动推断“下一章”。
- 低细节规则目前是确定性短语匹配，还没有接入更完整的 dialog intent planner 自主规划。
- `build_project_diagnosis(...)` 对 content 缺失时的 `suggested_next_step` 仍可能偏保守，后续可以单独评估。

## 验证证据

- RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_intent_router_low_detail_continue_uses_chapter_when_outline_ready backend\tests\test_dialogs.py::test_chat_text_low_detail_continue_creates_pending_chapter_action -q`
  - 失败原因：
    - router 返回 `None`
    - dialog endpoint 返回 `pending_action: null`
- GREEN:
  - 同一 targeted 命令。
  - `2 passed in 0.15s`
- Dialog regression:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py -q`
  - `67 passed in 24.29s`
- Hygiene:
  - `git diff --check`
  - 退出码 0。
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`
  - 无匹配。

## 下一阶段建议

Phase131 建议解决“下一章推断”：当用户说 `继续吧` 或 `下一章` 时，Agent 应根据已有 `ChapterContent` 和 `Outline` 自动选择第一个未生成章节，而不是默认第 1 章。
