# Longform Scale Phase 40: 热表索引迁移覆盖真实数据库

## 目标

Phase 39 在 ORM 模型上补充了 `versions` 和 `background_tasks` 热表索引，但真实 SQLite 数据库需要 Alembic 迁移才能获得这些索引。本阶段补充迁移测试，并更新既有长篇热表索引迁移，确保新装或升级数据库都具备同样索引。

## 验收标准

1. Alembic `upgrade head` 后存在版本历史索引。
2. Alembic `upgrade head` 后存在后台任务索引。
3. ORM `create_all` 热表索引测试仍通过。
4. 迁移测试和完整验证通过。
