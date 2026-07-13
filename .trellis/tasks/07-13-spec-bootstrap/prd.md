# PRD: Trellis Spec Bootstrap

## Goal

Refresh `.trellis/spec/` guidelines from the real codebase: replace every "To be filled by the team" placeholder with concrete project-specific patterns, file paths, examples, and anti-patterns derived from the actual Mozhou AI Writer codebase.

## Requirements

1. **backend/ (5 files)** — Fill with FastAPI + SQLAlchemy patterns found in `backend/app/`

   | File | Must include |
   |------|-------------|
   | `directory-structure.md` | `app/` 包结构 (api/core/models/services/agent), 模块组织, snake_case 命名 |
   | `database-guidelines.md` | SQLAlchemy ORM 模式, SQLite + WAL, Alembic 迁移, UUID PK, JSON 字段 |
   | `error-handling.md` | AppError 异常类, with_retry 重试机制, HTTPException, 诊断中间件 |
   | `quality-guidelines.md` | Ruff 配置 (py311, line-length 120), pytest 模式, conftest fixture |
   | `logging-guidelines.md` | log_event 函数, 请求追踪中间件, 结构化日志 |

2. **frontend/ (6 files)** — Fill with Vue 3 + TypeScript patterns found in `frontend/src/`

   | File | Must include |
   |------|-------------|
   | `directory-structure.md` | src/ 目录 (components/stores/views/api), PascalCase Vue, camelCase TS |
   | `component-guidelines.md` | `<script setup lang="ts">`, defineProps/defineEmits, BEM CSS, Tailwind |
   | `hook-guidelines.md` | 组合式函数模式, Pinia useXxxStore 命名, 数据流 |
   | `state-management.md` | Pinia 组合式 API, requestCache, 快照防旧, 分页 |
   | `quality-guidelines.md` | TypeScript strict, ESLint 配置, Vitest, Playwright E2E |
   | `type-safety.md` | TypeScript 5.6 类型模式, API types.ts, 互补 Pydantic 后端类型 |

3. **guides/ (unchanged)** — 保持现有内容

## Non-goals

- 不修改 `guides/` 下的思维指南
- 不新增或删除 spec 文件
- 不改动 `.trellis/spec/index.md` 顶层索引
- 不修改代码

## Acceptance Criteria

- [ ] 每个 backend/ 和 frontend/ spec 文件包含真实代码路径和示例
- [ ] 所有 "To be filled" / "To be written" / 注释模板被移除
- [ ] 没有空标题、占位符或复制的样板文本
- [ ] backend/index.md 和 frontend/index.md 的 Status 列从 "To fill" 改为 "Done"
- [ ] 文件中引用真实存在的文件路径
- [ ] 每个文件至少包含 2 个项目特有的代码示例或反模式
