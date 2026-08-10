# 伏笔/悬念账本 —— 执行计划

## 有序清单

1. **memory_service.py：plotline_apply_updates + track_plotline 增强**
   - 新函数 `plotline_apply_updates(db, project_id, updates, *, commit=True)`：open/close/postpone/none 动作映射，匹配失败 fail-open，校验违规跳过
   - `track_plotline`：open 加 `expected_resolve_chapter`，close 加 `payoff`；query 返回项加两字段 + overdue/due_soon 两级标记（保留 stale 兼容）
   - verify：新增单测（apply 各动作/匹配失败/校验违规；query 标记）
2. **writing_experience.py：prompt + 解析 + 接线**
   - system prompt 追加 plotline_updates 输出规格与纪律
   - `_build_introspect_user_prompt` 加 `open_plotlines` 参数
   - `_parse_introspect_output` 返回 `{"experiences", "plotline_updates"}`（旧格式兼容 → 空列表）
   - `introspect_and_record`：查开放伏笔清单 → 传 prompt → 解析双段 → 同一事务应用（commit=False 并入）
   - verify：新增单测（旧格式兼容、双段解析、原子性、幂等）
3. **project_snapshot.py：快照伏笔段升级**
   - 计数 → 数量 + 超期/临期清单（≤3 条，超期优先）
   - verify：快照单测更新
4. **memory_tools.py：工具描述/参数同步**
   - track_plotline description + handler 参数
   - verify：工具参数单测
5. **全量验证**
   - `pytest backend/tests` 全量通过
   - `ruff check backend` 通过
   - verify：如上

## 验证命令

```bash
cd backend && python -m pytest tests/ -x -q      # 全量
cd backend && python -m ruff check .            # lint
```

## 评审门

- 单测覆盖：apply 全动作 + 匹配失败 + 旧格式兼容 + 快照清单 + 幂等
- 行为不变式：自省失败 fail-open；已自省章不重复；无 plotline_updates 输出时 experiences 记账不受影响
- 提交前跑 `task.py validate`

## 回滚点

- 每步独立提交（1→2→3→4），任一步出问题 `git revert` 该步即可
- 自省 prompt 变更风险最高（影响既有 experiences 质量）——步骤 2 提交前先跑存量自省单测
