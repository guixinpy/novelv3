# P1 弧线规划结构性校验（内容无关重构版）

## Goal

按用户确立的长期判断标准——**harness 只约束「对任何题材成立」的工程不变量，情节内容完全留给模型**——
修正现有 harness 的特化成份，并补强弧线规划的结构性约束（连续性/结构完整性维度）。

## 判断标准（用户采纳，2026-08-01）

一个约束对**所有题材**是否成立？
- 成立 → harness 管（工程不变量：一致性/连续性/结构完整性/节奏/格式/容错）
- 不成立 → 特化，污染创作自由（题材/风格/反派形态/冲突类型/卷部结构/情节走向归模型）

## 工程不变量 vs 内容特化（现有 harness 审视）

| 已做 ✓ 工程不变量 | 特化 ⚠️ 需修正 |
|---|---|
| T1 容错恢复（hook 兜底/错误注入/guard） | T5 主题词指纹：词表（最初/来处/名字…）绑定 200 章题材 |
| T2 工具可靠性（upsert/参数示例/情节线规范） | T3 措辞：「禁止新增更早/更深/更初层级」是特定递推模式表达 |
| T4 格式守门员 | （原提案门 prd 的「抽象词黑名单校验反派」——**从未实现，撤销草稿**） |
| T6 记忆注入/状态快照/事实表 | |
| 实体登记（rule+l2，一致性维度） | |
| T3 核心：伏笔登记-回收闭环、收束章数 | |

## Requirements

### R1. 新卷启动连续性提示（结构性）
- `plan_arc` define 新增可选参数 `relation_to_previous`（与前卷关系：承接的旧线索/人物/事件）
- 接续启动检测：start_chapter ≤ 上一弧线 end_chapter + 2 且未传 relation_to_previous →
  **提示**（不拒绝）：「新卷启动建议声明与前卷的关系，避免读者产生世界重启感」
- 传入则记录进 metadata.arc_relation（progress/快照可查看）

### R2. 弧线收束约束可见性（结构性）
- `plan_arc progress`：活跃弧线 metadata 无 endgame（未设 must_resolve/收束章）→ 提示
  「本卷未设置收束约束（define 可补 must_resolve）」，不阻塞

### R3. T3 措辞泛化（内容无关表达）
- endgame 警告中「禁止新增更早/更深/更初层级」→「接近收束章，请优先回收开放线索，暂缓开新线」
- `tools/memory.py` plan_arc progress 与 `tools/chapters.py` check_quality_trend 两处

### R4. T5 去特化（独立子任务，不在本任务实现）
- `structural_similarity.py` 主题词表改为**内容无关结构特征**（章节结尾句式长度分布/对话占比/标点密度）
  或标注「题材相关需随题材扩充」——方案评估与实验验证另立任务
- 本任务仅记录决策，不改 T5 代码

## Acceptance Criteria

- [ ] define 传 relation_to_previous → metadata 记录，progress/快照可查看（新增用例）
- [ ] 接续启动未传 → define 返回提示（不拒绝，弧线仍创建）（新增用例）
- [ ] 非接续启动（新项目首弧线）不触发提示（新增用例）
- [ ] 活跃弧线无 endgame → progress 提示可补 must_resolve（新增用例）
- [ ] T3 两处措辞无「更早/更深/更初」字样（断言更新）
- [ ] 全文无抽象词黑名单类内容校验（grep 验证无新增）
- [ ] 后端全量 pytest 通过（591 基线只增不减）、前端 vitest 无回归
- [ ] 独立 commit（message 前缀 `harness: arc-structure`）

## Out of Scope

- 情节内容校验（反派形态/冲突类型/主角目标/卷部结构）——模型创作自由
- T5 去特化实现（另立任务，本任务记录决策）
- 新工具提案门（原定位撤销）

## Notes

- 判断标准写入 progress-tracker 供后续 harness 决策引用
- relation_to_previous 是可选参数：不传不阻塞（仅提示），向后兼容
