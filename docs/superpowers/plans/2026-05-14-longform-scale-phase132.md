# Phase 132: Prompt 预算截断保留尾部上下文

## 背景

章节生成 prompt 已经有上下文预算器，会按优先级保留重要块并截断超预算块。
但旧截断策略对单个超长上下文块只保留开头。

长篇写作中，长篇记忆、Athena 上下文、检索证据常把近期章节、最新变化或关键证据放在块的后段。
预算压力下只保留开头，会丢掉更接近当前章节的尾部信息。

## 修复

- `PromptBudgeter` 对单块截断改为首尾保留。
- 当预算足够放置分隔符时，输出 `head + "\n...\n" + tail`。
- 当预算极小时仍保持原来的开头截断，避免分隔符占满上下文。
- 不改变块优先级、不改变块选择顺序。

## 验证

- 先新增失败测试：
  - `backend/tests/test_prompting_contracts.py::test_budgeter_truncated_block_preserves_ending_context`
  - RED：旧实现截断后不包含 `末尾钩子`。
- 修复后通过：
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_prompting_contracts.py -q`
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_prompting_chapter_migration.py -q`
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py -q`
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py -q`

## 后续观察

- 后续可针对不同上下文块增加 `truncate_strategy`，例如检索证据优先保留 top result，长篇记忆优先保留 recent section。
- 当前阶段先使用通用首尾保留策略，减少长篇承接信息丢失。
