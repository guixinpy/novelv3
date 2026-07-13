# M3 执行计划

## Phase A: 核心护栏（P0）

### A1: guards.py + 五级检测
- `agent/guards.py` — GuardSystem 类（记录 + 五级 check）
- `agent/events.py` — GuardTripped 事件
- `agent/loop.py` — 集成 guards.check() 到工具执行后
- 测试: 每级至少 1 个场景测试（触发/不触发）

### A2: 预算 refund
- `agent/loop.py` — `_execute_one` 内对 permission=read 调用 budget.refund()
- 需要将 IterationBudget 传入 _execute_one
- 测试: read 工具 refund 后 budget.remaining 不变

## Phase B: 上下文管理（P1）

### B1: compaction.py
- `agent/compaction.py` — check_context_usage + compact_history
- `agent/events.py` — ContextWarning 事件
- harness 集成：每次 _run_one_turn 前检查

### B2: check_chapter_quality 工具
- `tools/chapters.py` — 追加 check_chapter_quality
- permission=read，做字数/标题/内容形式检查

## Phase C: 批量模式（P2）

### C1: risk→recover 闭环
- GuardTripped 事件 → 诊断 → follow-up 恢复建议注入
- 测试: guard 触发后收到诊断事件

### C2: 批量 follow-up 写作
- harness.follow_up 队列 + guards 检查点
- 验证: 连续写 N 章，每章间有 guard 检查

## 验证

```bash
cd backend && python -m pytest tests/agent/ -q
cd frontend && npx vitest run
```
