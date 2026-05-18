# Longform Scale Phase 38: 长篇记忆检索同步批量删除旧文档

## 目标

长篇维护修复可能一次同步大量 `LongformMemory`。当前同步逻辑按每条记忆逐个查询并删除旧检索文档，千章项目中会形成 N+1 查询和重复 chunk 查询。本阶段将旧文档清理改为按 `source_ref` 批量删除，降低维护修复的查询放大。

## 验收标准

1. `sync_longform_memory_retrieval_documents()` 保持只重建指定记忆文档。
2. 删除旧长篇记忆检索文档时不再按单个 `source_ref = ?` 循环查询。
3. 相关长篇检索测试和完整验证通过。
