# 2026-04-24 Manuscript Optimization Change Review

## 状态

- 当前分支：`wip/slash-commands-base`
- 基线：`f77cec7f1d88d368e90f779fd1343a4a41d8cad6`
- 工作区混合来源：Claude 既有大批改动 + 本轮 Manuscript/Hermes/Athena 闭环 + 工程收口。
- 禁止事项：不要执行粗暴 `git reset`、`git checkout .`、删除未跟踪文件；这些会破坏 Claude 工作。

## 验证记录

- 后端全量：`cd backend && .venv/bin/python -m pytest -q`
  - 结果：`216 passed in 46.00s`
- 前端全量：`cd frontend && npx vitest run`
  - 结果：`57 passed`
- 前端构建：`cd frontend && npm run build`
  - 结果：成功
- 浏览器冒烟：`agent-browser`
  - 跑通 `Manuscript 批注/修正 -> 提交 -> Hermes 自动重生成 -> Athena 自优化展示`

## 分组 1：Claude 基础/样式/命令/历史改动

这组主要是本轮接手前已存在的改动，需独立审查，避免和 Manuscript 闭环混在一个提交里。

- `.claude/settings.json`
- `.claude/skills/build/SKILL.md`
- `.claude/skills/test/SKILL.md`
- `.claude/skills/verify/SKILL.md`
- `CLAUDE.md`
- `backend/ruff.toml`
- `frontend/eslint.config.js`
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/src/styles/tokens.css`
- `frontend/src/components/base/BaseBadge.vue`
- `frontend/src/components/base/BaseInput.vue`
- `frontend/src/components/base/BaseModal.vue`
- `frontend/src/components/layout/ActivityBar.vue`
- `frontend/src/components/layout/AppShell.vue`
- `frontend/src/components/layout/SubNav.vue`
- `frontend/src/components/layout/TopBar.vue`
- `frontend/src/components/chat/ActionCard.vue`
- `frontend/src/components/chat/ChatSummaryCard.vue`
- `frontend/src/components/shared/ProjectDashboard.vue`
- `docs/manual-test-checklist.md`
- `docs/test-screenshots/*`
- `docs/others/claude 摘要001.txt`

建议提交名：`chore: align frontend shell and tooling`

## 分组 2：后端修订闭环

核心后端能力：修订持久化、批注/修正、重生成、失败状态、幂等、删除清理。

- `backend/alembic/versions/20260424_add_chapter_revisions.py`
- `backend/app/models/chapter_revision.py`
- `backend/app/models/__init__.py`
- `backend/app/schemas/chapter_revision.py`
- `backend/app/schemas/__init__.py`
- `backend/app/api/chapter_revisions.py`
- `backend/app/api/chapters.py`
- `backend/app/api/projects.py`
- `backend/app/main.py`
- `backend/app/core/revision_feedback.py`
- `backend/tests/test_chapter_revisions.py`
- `backend/tests/test_projects.py`

建议提交名：`feat: add chapter revision regeneration backend`

审查重点：
- `ChapterRevision.chapter_id` 外键要求删除项目时先删 revision 子表。
- `regenerate_revision` completed 后幂等返回现有章节，不重复打模型。
- failed 状态允许后续重试。

## 分组 3：自优化后端 + Athena endpoint

从用户反馈中生成 learned prompt rules，提供 Athena 自优化数据。

- `backend/app/core/self_optimization.py`
- `backend/app/api/athena.py`
- `backend/tests/test_self_optimization.py`

建议提交名：`feat: expose learned optimization state in Athena`

审查重点：
- 当前为启发式规则提取，不调用 LLM。
- 单次反馈最多降低一次 `description_density`，防止过激微调。

## 分组 4：Manuscript 前端编辑器

正文编辑器、批注、修正、提交确认、Range offset、内联高亮和 diff。

- `frontend/src/stores/manuscript.ts`
- `frontend/src/stores/manuscript.test.ts`
- `frontend/src/views/ManuscriptView.vue`
- `frontend/src/components/manuscript/AnnotationBubble.vue`
- `frontend/src/components/manuscript/ManuscriptEditor.vue`
- `frontend/src/components/manuscript/ManuscriptEditor.test.ts`
- `frontend/src/components/manuscript/RevisionSubmitModal.vue`
- `frontend/src/components/manuscript/RevisionSummaryPanel.vue`
- `frontend/src/components/manuscript/revisionRender.ts`
- `frontend/src/components/manuscript/revisionRender.test.ts`
- `frontend/src/components/manuscript/selectionOffsets.ts`
- `frontend/src/components/manuscript/selectionOffsets.test.ts`
- `frontend/src/api/client.ts`（revision API 部分）
- `frontend/src/api/types.ts`（revision 类型部分）

建议提交名：`feat: build manuscript revision editor`

审查重点：
- 选区 offset 使用 DOM Range，不再用 `indexOf`。
- contenteditable blur 直接读 DOM 文本，避免 input 事件漏掉导致修正丢失。
- 当前重叠批注保守跳过后者。

## 分组 5：Hermes 修订接力

Manuscript 提交后跳 Hermes，Hermes 消费 `revision_id` 并触发后端重生成。

- `frontend/src/views/HermesView.vue`
- `frontend/src/stores/chat.ts`
- `frontend/src/stores/chat.workspace.test.ts`
- `frontend/src/api/client.ts`（`regenerateRevision` 部分）
- `frontend/src/api/types.ts`（`ChapterContent` 等共享类型）

建议提交名：`feat: hand off manuscript revisions to Hermes`

审查重点：
- Hermes 消费后清除 query，避免刷新重复触发。
- 前端不再伪造修订消息，后端落库后刷新历史。

## 分组 6：Athena 自优化前端

Athena 新增“自优化”section，展示 learned rules、偏好参数、学习日志。

- `frontend/src/components/athena/OptimizationPanel.vue`
- `frontend/src/stores/athena.ts`
- `frontend/src/stores/athena.optimization.test.ts`
- `frontend/src/stores/ui.ts`
- `frontend/src/views/AthenaView.vue`
- `frontend/src/api/client.ts`（`getAthenaOptimization` 部分）
- `frontend/src/api/types.ts`（`AthenaOptimization` 类型）

建议提交名：`feat: show Athena self-optimization results`

## 分组 7：World/API 契约和迁移收口

全量测试暴露的既有契约/迁移问题，已修到当前实现。

- `backend/tests/test_world_frontend_api.py`
- `backend/tests/test_world_profiles.py`
- `backend/alembic/versions/20260424_add_chapter_revisions.py`

建议提交名：`test: align world proposal pagination and migration head`

审查重点：
- `proposal-bundles` 当前返回分页对象 `{ items, total, offset, limit }`，测试已按该契约调整。
- 修订迁移接到 `bfe0f1ff2e2d` 后，避免 Alembic 多 head。

## 分组 8：World model / backend 大量既有改动

这些文件在本轮任务前已处于修改状态或来自 Claude 前序工作；需要独立审查，不能混入 Manuscript 闭环提交。

- `backend/alembic/env.py`
- `backend/alembic/versions/05ffa48c7449_add_versions_table.py`
- `backend/alembic/versions/22b614b45ce0_add_projects_table.py`
- `backend/alembic/versions/29ed587ef7a9_add_phase2_models.py`
- `backend/alembic/versions/3c8245c6f81c_add_setups_and_chapter_contents.py`
- `backend/alembic/versions/acdb7e6de884_add_style_config_to_projects.py`
- `backend/alembic/versions/bdab5f1bbbe7_add_few_shot_examples_and_prompt_rules_.py`
- `backend/alembic/versions/d9f5e6a1c2b3_add_dialog_message_types_and_meta.py`
- `backend/alembic/versions/e3b4d4b5c6a7_add_world_model_stage1_tables.py`
- `backend/alembic/versions/f7c1e2d3a4b5_add_world_proposal_tables.py`
- `backend/app/api/background_tasks_api.py`
- `backend/app/api/config.py`
- `backend/app/api/export.py`
- `backend/app/api/preferences.py`
- `backend/app/api/versions.py`
- `backend/app/api/writing.py`
- `backend/app/core/*`（除本轮新增 `revision_feedback.py`、`self_optimization.py`）
- `backend/app/models/*`（除本轮新增 `chapter_revision.py`）
- `backend/app/schemas/*`（除本轮新增 `chapter_revision.py`）
- `backend/tests/test_background.py`
- `backend/tests/test_checkers.py`
- `backend/tests/test_consistency.py`
- `backend/tests/test_dialogs.py`
- `backend/tests/test_export.py`
- `backend/tests/test_outlines.py`
- `backend/tests/test_setups.py`
- `backend/tests/test_storylines.py`
- `backend/tests/test_world_profiles.py`

建议提交名：按 Claude 原工作主题继续拆，不建议我在不了解历史意图时合成一个提交。

## 建议提交顺序

1. `chore: align frontend shell and tooling`（Claude UI/工具基础）
2. `feat: add chapter revision regeneration backend`
3. `feat: expose learned optimization state in Athena`
4. `feat: build manuscript revision editor`
5. `feat: hand off manuscript revisions to Hermes`
6. `feat: show Athena self-optimization results`
7. `test: align world proposal pagination and migration head`
8. Claude world/backend 既有改动按原主题继续拆分

## 安全检查

- 未发现用户提供的 DeepSeek key 被写入仓库文本文件。
- 本轮没有执行回滚、reset、checkout 删除工作。
- 本轮没有创建 commit。
