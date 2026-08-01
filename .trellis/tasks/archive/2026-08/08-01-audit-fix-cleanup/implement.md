# Implement · 审计修正收尾

按序执行，每步完成后跑对应验证。

## Step 1 · .trellis agent-refactor 冒烟验证并提交

```powershell
python .trellis/scripts/get_context.py
python .trellis/scripts/get_context.py --mode phase
python .trellis/scripts/task.py list
python .trellis/scripts/task.py current --json
git add .trellis .gitattributes
git commit -m "chore(trellis): agent-refactor 0.6.11 — dispatch auto + context injection + json outputs"
```

验证：4 个命令全部正常退出且输出合理。

## Step 2 · 删除死代码

```powershell
# 删除前再次确认引用零命中
rg -n "writingAgent" frontend/src --glob "!components/writingAgent/**" --glob "!**/*.test.ts"
rg -n "chapter_compression|chapter_expansion" backend scripts
rg -n "writing_agent_run_helpers" backend
# 删除（apply_patch Delete File，61 个文件）
git add -A
```

验证：`pytest -q` 全绿；`frontend/node_modules/.bin/vitest.cmd run --reporter=dot` 全绿（记录删除的 test 数量）；`vue-tsc --noEmit` 通过。

## Step 3 · CADR-004 修订 + tracker 校准

- `docs/claude-guide/06-decisions.md`：CADR-004 追加修订条目（日期 2026-08-01）。
- `docs/claude-guide/05-progress-tracker.md`：按审计结果重写。

验证：两份文档内容与代码事实一致（对照本任务 prd 验收 3/4）。

## Step 4 · 提交清理与文档

```powershell
git add -A
git commit -m "chore: remove dead code (writingAgent panels, chapter compression/expansion, stale test_support) + CADR-004 revision + tracker calibration"
```

## Step 5 · 合并 main

```powershell
git rev-list --left-right --count main...HEAD   # 期望 0 N
git checkout main
git merge --ff-only claude/agent-refactor
git checkout claude/agent-refactor
```

验证：`git rev-list --count main..claude/agent-refactor` = 0；`git log main -1` 指向最新提交。

## Step 6 · M4 50 章验证

```powershell
# 启动后端（后台）
Start-Process -WindowStyle Hidden -FilePath python -ArgumentList "backend/mozhou.py"
# 检查 l4_dogfood.py 是否支持记忆问答/上下文排除；必要时补能力
python scripts/l4_dogfood.py --chapters 50
```

验证：结果记录（通过 / 失败 / 阻塞原因）；日志落盘。

## Step 7 · M5 细化方案

输出 `m5-200ch-plan.md`（任务目录），包含指标阈值、实验设计、成本估算、止损规则。
