# Longform Scale Phase 37: 章节摘要列表避免加载正文

## 目标

千章项目的章节列表、侧栏和跳转控件只需要章节元数据，不应该在分页摘要接口中读取完整正文。当前 `/chapters` 使用 `query(ChapterContent)` 并调用 `count()`，可能在 count 子查询和分页查询中携带 `content` 列，随着章节正文变长会放大无意义 IO。

## 验收标准

1. `/api/v1/projects/{project_id}/chapters` 返回结构保持不变。
2. 总数统计使用轻量 `count(id)`，不通过完整实体子查询。
3. 分页章节摘要只选择 `id/chapter_index/title/word_count/status`，不选择 `content`。
4. 相关导出/章节列表测试和完整验证通过。
