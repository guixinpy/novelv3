# Phase 133: 长篇 rollup 保留近期章末线索

## 背景

长篇上下文的全书、卷、剧情弧 rollup 会聚合最近章节记忆。
章节记忆本身已经保留开头和结尾，但 rollup 在格式化近期章节摘要时又使用了只保留开头的 80 字预览。

结果是：章末反转、钩子、揭示虽然进入了章节记忆，却可能在全书/卷/弧上下文中再次丢失。

## 修复

- rollup 中的近期章节摘要改用首尾保留预览。
- `_chapter_content_preview` 调整为严格遵守传入长度预算。
- 保持 rollup 查询方式不变，不增加数据库读取量。

## 验证

- 先新增失败测试：
  - `backend/tests/test_longform_scale.py::test_longform_context_rollups_keep_recent_chapter_ending_clue`
  - RED：旧 rollup summary 不包含 `卷末钩子`。
- 修复后通过：
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_context_rollups_keep_recent_chapter_ending_clue -q`
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_chapter_memory_keeps_chapter_ending_clue backend\tests\test_longform_scale.py::test_longform_context_rollups_include_recent_memory_summaries -q`
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py -q`

## 后续观察

- 后续如果引入结构化章节摘要，可把“章末钩子/未解决问题/下一章承接点”拆成单独字段。
- 当前修复保证现有文本记忆链路不会在二次 rollup 时丢失尾部信息。
