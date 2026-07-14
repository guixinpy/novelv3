# Design · 推进 Agent 化

## 架构边界

```
新内核 (保留)              旧编排层 (删除目标)         API 层
─────────────────────    ─────────────────────    ──────────
agent/loop.py            services/writing_agent/   api/dialogs.py ← 删除
agent/harness.py         ├─ run_service.py         api/chapters.py ← 迁移到 v2
agent/tooling.py         ├─ planner.py             api/outlines.py ← 迁移到 v2
agent/budget.py          ├─ batch_*.py             ...
agent/guards.py          ├─ agent_*.py
agent/compaction.py      ├─ tool_*.py
agent/approval.py        └─ ... (58 files)
agent/events.py
agent/providers/
tools/ (12 @tool)
```

## 删除策略

三阶段绞杀：

1. **标记死代码**：从 API 入口向内追溯依赖链，标记「新架构已覆盖」vs「需迁移」vs「死代码」
2. **切断引用链**：`api/dialogs.py` → 删除；`api/chapters.py` 等 → 改为调用新 tools
3. **批量删除**：移除 `services/writing_agent/` 整个目录

## 风险评估

| 风险 | 影响 | 缓解 |
|------|------|------|
| 删除仍在用的代码 | 功能破损 | 每步运行 `pytest tests/ -q` |
| v1 端点有前端调用 | 前端报错 | 搜索前端 import 确认无引用 |
| 测试依赖旧模块 | 测试失败 | 删除旧测试时同步确认 |

## 回滚方式

每步一个 commit，出错 `git revert` 即可。
