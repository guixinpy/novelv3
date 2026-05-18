# Phase 207 - 长篇记忆正文前缀投影

## 目标

长篇记忆重建和单章刷新只需要章节正文的短摘要，但旧实现会在 SQL 查询中投影完整 `chapter_contents.content`。在千章、百万字项目中，这会让维护任务的内存与传输成本随全文长度线性增长。

## 变更

- 为长篇记忆维护新增 `CHAPTER_MEMORY_CONTENT_QUERY_CHARS = 1200`。
- `_chapters()` 和 `_chapter_for_memory()` 改为使用 `substr(chapter_contents.content, 1, 1200)`，保留章节记忆摘要所需的正文前缀。
- 保持章节记忆摘要逻辑不变：仍由 `_chapter_content_preview(..., 180)` 生成最终摘要。

## 测试

- RED：`test_rebuild_longform_memory_uses_bounded_content_projection` 先确认旧实现直接投影完整 `chapter_contents.content`。
- GREEN：改为 SQL 前缀投影后，该测试通过，并确认章节记忆仍保留前缀线索。
- 回归：`test_refresh_longform_memory_for_chapter_avoids_full_content_scan` 确认单章刷新路径也只读取必要正文字段。

## 后续验证

- 已运行：`backend\.venv\Scripts\python.exe -m pytest backend/tests/test_longform_scale.py -q`
- 结果：`40 passed`
