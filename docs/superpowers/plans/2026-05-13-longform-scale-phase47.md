# Longform Scale Phase 47: 后台范围任务进度压缩

## 目标

长篇分析、索引、修复任务通常按章节顺序推进。当前范围任务会在 `result.progress.completed_chapter_indexes` 中保存每个已完成章节，千章任务会把任务状态 JSON 线性放大。本阶段对顺序完成的大范围任务改用紧凑 checkpoint。

## 验收标准

1. 小范围任务仍保留 `completed_chapter_indexes`，兼容现有 UI 和测试。
2. 大范围顺序任务用 `completed_until_chapter_index`、首尾章节和计数表达进度。
3. `next_chapter_index`、`completed_count`、`can_resume` 语义不变。
4. 失败任务重试仍从 `next_chapter_index` 恢复。
5. 后端测试、前端测试、类型检查和构建通过。
