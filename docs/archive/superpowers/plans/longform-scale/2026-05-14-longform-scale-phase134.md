# Phase 134: 章节生成正文入库前清洗

## 背景

章节生成模型有时会返回 markdown 代码围栏、`# 第1章 标题` 这类标题行，或者把正文包在 ` ```markdown ` 中。
旧逻辑直接把模型返回值写入 `ChapterContent.content`，会导致正文污染，并影响字数统计、检索索引、长篇记忆和后续修订。

## 修复

- 在章节生成保存前规范化模型输出。
- 去掉包裹全文的 markdown 代码围栏。
- 去掉首行单独成行的章节标题。
- 不删除普通正文中的“第一章正文内容”等句子，避免误伤。
- 字数统计使用清洗后的正文。

## 验证

- 先新增失败测试：
  - `backend/tests/test_chapters.py::test_generate_chapter_strips_markdown_fence_and_heading_before_saving`
  - RED：旧实现保存内容仍包含代码围栏和标题。
- 修复后通过：
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py::test_generate_chapter_strips_markdown_fence_and_heading_before_saving -q`
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py -q`
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_prompting_chapter_migration.py backend\tests\test_longform_scale.py -q`
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapter_revisions.py -q`

## 后续观察

- 后续可把正文清洗扩展到章节修订结果，但应单独测试，避免误删作者主动写入的格式。
- 如果未来支持 Markdown 正文格式，应把“正文格式”作为项目配置，而不是默认保存围栏。
