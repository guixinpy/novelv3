# Phase138 Report: Conflict Source Labels

## 阶段目标

细化章节目标冲突来源，让用户能区分冲突来自待确认操作、单章生成任务还是批量生成任务。

## 实际完成

- `backend/app/api/dialogs.py`
  - 新增 `CHAPTER_TARGET_SOURCE_LABELS`。
  - 新增 `_reserved_chapter_index_sources(...)`，把 reservation 从集合升级为章节号到来源的映射。
  - 新增 pending action、active task、task payload 的 source map helper。
  - `chapter_target_conflict` 新增 `source` 和 `source_label`。
- `backend/app/services/actions/descriptions.py`
  - 冲突文案使用具体来源，例如 `已有单章生成任务`、`已有批量生成任务`。
- `frontend/src/components/chat/ActionCard.vue`
  - warning 区块读取 `source_label`。
  - 普通描述去重 regex 支持具体来源文案。
- `backend/tests/test_dialogs.py`
  - 新增 range task 冲突来源测试。
  - 更新单章 active task 冲突测试契约。
- `frontend/src/components/chat/ChatMessage.test.ts`
  - 新增前端来源标签显示测试。

## 设计约束

- 不改变冲突处理策略；仍然只提示，不阻断。
- reservation set 行为保持兼容，由 source map 派生。
- 前端保留泛化 fallback：后端没有 `source_label` 时仍显示 `待确认或运行中的生成任务`。

## 小说进度

本阶段没有生成新章节。原因：该阶段继续强化长篇自动生成控制面的风险解释能力。

## 已修复的问题

- 所有章节冲突都显示成泛化“待确认或运行中的生成任务”，用户无法判断是单章任务还是批量任务占用。

## 未修复但记录的问题

- trace audit 尚未展示 `chapter_target_conflict.source`。
- 任务列表还没有直接反向链接到占用来源。
- 仍未提供“取消占用任务/查看任务详情”的前端操作分支。

## 验证证据

- RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_chapter_command_explicit_range_reserved_target_labels_conflict_source -q`
  - 结果：`1 failed`，缺少 `source/source_label`。
  - `npm run test:unit -- src/components/chat/ChatMessage.test.ts -t "renders pending chapter conflict source labels"`
  - 结果：`1 failed`，前端仍显示泛化来源。
- GREEN:
  - 后端 targeted：`1 passed in 0.23s`
  - 前端 targeted：`1 passed`
- Regression:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py -q`
  - 初次发现单章 active task 旧断言需要更新；更新后 `76 passed in 25.38s`
  - `npm run test:unit -- src/components/chat/ChatMessage.test.ts`
  - `12 passed`
- Frontend build:
  - `npm run build`
  - `vue-tsc --noEmit && vite build` 成功，Vite 输出 `✓ built in 4.84s`。
- Hygiene:
  - `git diff --check`
  - 退出码 0，无输出。
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`
  - 退出码 1，无匹配。

## 下一阶段建议

Phase139 建议把 `chapter_target_conflict` 接入 Agent trace audit 和 action result metadata，让冲突来源在确认后仍可追溯。
