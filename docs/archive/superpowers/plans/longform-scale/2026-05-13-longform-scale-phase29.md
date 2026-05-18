# Longform Scale Phase 29: 长篇热表查询索引

## 目标

千章/百万字项目会持续放大章节、对话、校验记录表的访问成本。前几阶段已经收窄了查询范围，本阶段补齐对应数据库索引，避免查询在数据增长后仍退化为表扫描。

## 索引范围

- `chapter_contents(project_id, chapter_index)`：单章读取、生成替换、记忆刷新。
- `chapter_contents(project_id, status)`：章节状态统计与筛选。
- `dialog_messages(dialog_id, message_type, created_at, id)`：对话分页与压缩。
- `dialog_messages(dialog_id, created_at, id) WHERE action_result IS NOT NULL`：运行中动作检测。
- `consistency_checks(project_id, chapter_index)`：按章节查看一致性问题。
- `consistency_checks(project_id, status)`：待处理问题筛选。

## 验收标准

1. 测试数据库通过 `Base.metadata.create_all` 后包含上述索引。
2. Alembic 迁移为持久数据库创建同名索引。
3. 全量测试和构建通过。
