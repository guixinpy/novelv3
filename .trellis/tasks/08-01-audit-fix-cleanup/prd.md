# PRD · 审计修正收尾：死代码清理 + ADR 修订 + 验证推进

## 背景

2026-08-01 对 `claude/agent-refactor` 分支做了实证审计（代码检查 + 全量测试 + 会话日志核对），发现文档声明与代码状态存在以下偏差：

1. 前端 `frontend/src/components/writingAgent/` 下 58 个 AgentRun* 面板及测试**无任何引用**（v1 轨迹可视化，v2 无数据源）。
2. 后端 `chapter_compression.py` / `chapter_expansion.py` **无任何引用**（含测试）。
3. `backend/test_support/writing_agent_run_helpers.py` 引用已不存在的 `app.services.writing_agent`，且无测试使用。
4. CADR-004「双轨持久化」只实现一半：v2 会话仅写 JSONL，未写 `WritingAgentRun/Step` DB 表。
5. `.trellis/` 有 18 个未提交改动（agent-refactor，0.6.7→0.6.11），无任务记录、无验证记录。
6. `05-progress-tracker.md` 停留在 2026-07-14，未反映以上事实与 8 月工作。
7. M4（50 章）与 M5（200 章）正式退出标准未执行；`scripts/l4_dogfood.py` 已具备 50 章能力，`.env` 已配置 API key。

## 目标

1. 删除全部证据确认无引用的死代码。
2. 对 v2 轨迹持久化做出明确决策并落地文档（废弃 CADR-004 的 DB 轨要求，保留 athena v1 兼容路径）。
3. 收尾 `.trellis` agent-refactor 未提交改动（冒烟验证 + 独立 commit）。
4. 按实测校准 `05-progress-tracker.md`。
5. 将 `claude/agent-refactor` 快进合并到 `main`。
6. 推进 M4 50 章验证：运行或交付可复现运行方案，并记录结果。
7. 输出 M5 细化方案（200 章实验的设计要点与前置条件）。

## 约束

- 不改变 Agent 内核（loop/harness/tooling/guards/budget/compaction/approval）行为。
- 删除仅限审计证据确认无引用的文件；不顺手清理未验证的疑似死代码。
- 后端 pytest、前端 vitest 在每一步保持全绿（死代码删除导致的数量下降需在 commit message 与 tracker 中说明）。
- 不引入新依赖；不修改数据库 schema；不触碰 `docs/archive/`。
- `WritingAgentRun/Step` 模型、`dialog_utils.py` 保留（athena v1 对话仍在使用）。

## 验收标准

1. `rg "writingAgent|chapter_compression|chapter_expansion|writing_agent_run_helpers"` 在 `backend`、`frontend/src`、`scripts` 中零命中（归档与 git 历史除外）。
2. `pytest -q` 全绿；`vitest run` 全绿（删除的测试用例数有记录）。
3. `06-decisions.md` 含 CADR-004 修订条目（日期、决策、理由、保留范围）。
4. `05-progress-tracker.md` 按实测重写：M2/M4/M5 状态与问题清单与代码一致。
5. `git rev-list --count main..claude/agent-refactor` 为 0（ff-only 合并完成）。
6. M4 验证：`scripts/l4_dogfood.py` 可运行且结果（50 章通过或阻塞原因）已记录；记忆问答与「第 50 章上下文不含前 40 章原文」检查有明确执行方案。
7. M5 细化方案文档产出（放入任务目录）。
