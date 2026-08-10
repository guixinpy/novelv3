# 质量保障特化 —— 执行计划

## 有序清单

1. **domain/writing/quality_trend.py**：`quality_trend_stats(db, project_id, window=10)` 纯函数
   - verify：新增单测（四级判定/不足 3 章/无数据）
2. **project_snapshot.py**：趋势段注入（非 stable 才注入，≤40 字，信息形态）
   - verify：快照单测更新/新增
3. **domain/writing/continuity.py**：`check_continuity` + CharacterStateChecker（复用 mine_entities_from_text）
   - verify：新增单测（死亡角色出场/正常角色不出 issue/无设定卡）
4. **domain/tools/quality_tools.py**：`check_continuity` 工具注册（read 权限）
   - verify：工具参数单测
5. **全量验证**：`pytest tests/ -q` + `ruff check .`

## 验证命令

```bash
cd backend && python -m pytest tests/ -q
cd backend && python -m ruff check .
```

## 评审门

- 原则审查：所有输出为报告形态（无指令式文案、不自动修复、不阻塞）——README 检查
- 复用审查：角色提取走 entity_miner（不新造提取器）；趋势走 word_count 普通列
- 快照预算：新增段 ≤40 字

## 回滚点

- 每步独立提交（1→2→3→4）；步骤 2（快照）风险最高（每回合可见）——提交前先过存量快照测试
