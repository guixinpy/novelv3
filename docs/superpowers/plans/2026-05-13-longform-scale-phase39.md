# Longform Scale Phase 39: 长篇热表补充版本与任务索引

## 目标

百万字项目会产生大量章节版本、回滚记录和后台任务。当前 `versions` 与 `background_tasks` 缺少面向常用查询路径的组合索引，长期使用后版本列表、版本号递增、任务列表和运行中任务恢复会变慢。

## 验收标准

1. `versions` 支持按 `project_id/node_type/node_id/created_at` 列表查询。
2. `versions` 支持按 `project_id/node_type/node_id/version_number` 查最大版本号。
3. `background_tasks` 支持按项目倒序列出任务。
4. `background_tasks` 支持按状态扫描运行中任务。
5. 热表索引测试和完整验证通过。
