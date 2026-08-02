# P1 弧线规划结构性校验 · 执行计划

## 阶段 1：relation_to_previous（D1）

- [ ] plan_arc define 加参数 + schema + 接续检测 + continuation_hint + metadata.arc_relation
- [ ] 测试（test_tools_memory.py）：relation 记录 / 接续未传提示（弧线仍创建）/ 非接续不提示

## 阶段 2：收束约束可见性（D2）

- [ ] progress 无 endgame → endgame_hint
- [ ] 测试（test_tools_memory.py）

## 阶段 3：T3 措辞泛化（D3）

- [ ] memory.py + chapters.py 措辞替换
- [ ] 断言更新（test_tools_memory/test_tools_quality）

## 阶段 4：验证收尾

- [ ] `grep -rn "更早\|更深\|更初" backend/app` 归零（T3 措辞）
- [ ] 后端全量 pytest + 前端 vitest 无回归
- [ ] progress-tracker 记录判断标准 + 本任务；独立 commit（`harness: arc-structure`）
- [ ] T5 去特化：记录为独立子任务（Out of Scope），后续另立

## 回滚点

- 全部为提示/可选参数：无行为变更风险；单 commit 可整体回滚
