# Implement Plan: Spec Bootstrap

## Phase 1: Backend (5 files)

Use `trellis-implement` sub-agent for each batch.

### Batch B1: directory-structure.md + database-guidelines.md
- directory: backend `app/` 包结构, 所有子包说明, snake_case 命名
- database: SQLAlchemy ORM 基类, 表名, UUID PK, timestamp 模式, Alembic 迁移模式

### Batch B2: error-handling.md + logging-guidelines.md
- error: AppError 定义, with_retry 模式, API HTTPException, 诊断中间件
- logging: log_event 函数, 请求 ID, 结构化字段

### Batch B3: quality-guidelines.md
- Ruff 配置, pytest conftest 模式, test_support 工具, 测试约定

## Phase 2: Frontend (6 files)

### Batch F1: directory-structure.md + component-guidelines.md
- directory: src/ 完整结构, PascalCase/camelCase 约定
- component: `<script setup>`, defineProps, emit, 插槽, BEM + Tailwind CSS

### Batch F2: state-management.md + hook-guidelines.md
- state: Pinia 组合式 API store, requestCache, 分页, 快照
- hooks: 组合式函数, store action 模式

### Batch F3: quality-guidelines.md + type-safety.md
- quality: TypeScript strict, ESLint, Vitest, Playwright
- type-safety: types.ts, defineProps 泛型, Pydantic 后端正交验证

## Phase 3: Finalize

- 更新 `backend/index.md` 和 `frontend/index.md` 的 Status 列
- 验证所有文件无占位符
- 验证交叉引用一致性

## Validation

```bash
# Check no placeholder text remains
grep -r "To be filled\|To be written\|fill in\|FIXME\|TODO" .trellis/spec/
```
