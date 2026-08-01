# P0 Harness 系统化优化 · 技术设计

> 父任务级设计决策，供各子任务引用。各子任务在自身 design.md 中细化实现。

## 架构总览

```
app/agent/                内核（无 DB 依赖，CADR-005）
  loop.py                 run_turn 无状态引擎（T1 改动点）
  harness.py              有状态外壳、JSONL 持久化、follow-up/steering（T1/T6 改动点）
  guards.py               五级循环检测（不变）
  compaction.py           压缩（T6 改动点）
  approval.py             审批门（不变）
  tooling.py              工具框架（T2 改动点）
  providers/deepseek.py   流式 provider（不变，已有重试）
app/tools/                工具层（可访问 DB；T2/T3/T4/T5 新增或扩展工具）
  chapters.py             write/read/quality（T4 扩展 check_chapter_quality 或新增工具）
  memory.py               plotline/arc（T2/T3 改动点）
  project.py              get_project_state（T6 参考）
app/core/                 纯函数模块（新校验逻辑放这里，工具层调用，可单测）
  format_checker.py       输出格式校验（T4，纯函数，无 DB）
  structural_similarity.py 结构级重复检测（T5，纯函数或轻量 DB 读取）
scripts/analyze_dogfood.py 实验分析（T7 改动点）
backend/tests/agent/      每项改动先补测试
```

## 全局设计决策

### D1. 新增校验逻辑一律放 `app/core/` 纯函数模块
- T4 格式校验、T5 结构相似度、T3 终局核对逻辑 → `app/core/` 下新模块，工具层薄封装。
- 纯函数（输入确定 → 输出确定），无 DB 依赖的放纯函数，需要 DB 的（终局核对、伏笔期限）依赖
  注入数据而非直接查库，保持可单测。

### D2. 工具新增采用「扩展现有工具 + 新增工具」混合
- T3：`plan_arc` 增加 `action="endgame"`（或 define 增参）+ `check_quality_trend` 增加终局核对
  ——**优先扩展现有工具**，减少工具目录膨胀与模型误用面。
- T4/T5：新增 `check_chapter_format` / `check_structure_repeat` 工具（只读，permission="read"），
  注册进默认 registry 自动出现在未知工具错误清单与工具目录。
- 所有新工具 description 遵循：说明「何时用 / 用什么参数 / 返回什么」。

### D3. 终局/伏笔数据存 LongformMemory.memory_metadata（JSON 列）
- `story_arc` 行 memory_metadata 增加 `endgame` 字段：`{"resolve_before": N, "must_resolve": [...], "banned_new_layers": true}`。
- `plotline` 行利用现有 `start_chapter_index` 计算伏笔年龄（当前章 - 起始章 > N 未闭环 → 提醒）。
- 不新增表结构；metadata JSON 向后兼容（缺失字段按未启用处理）。

### D4. 状态快照注入位置（T6）
- 在 `harness._run_one_turn` 每次用户消息进入时、run_turn 之前，把「项目状态快照」作为
  只读 user 消息追加进 history（**不持久化**——用 steer 后清理或直接不写日志，避免污染真相源）。
- 快照内容：章节数、活跃弧线、最近 3 章标题/字数、开放 plotline 数、当前目标章数（若有）。
- 快照生成函数放 `app/core/project_snapshot.py`，接收 DB + project_id，返回文本块。
- 模型频繁 list_chapters/get_project_state 的无效探索将被快照替代（减少往返）。

### D5. 压缩摘要扩展（T6）
- `compact_history` / `_build_summary_text` 保持纯函数；新增可选参数 `extra_context: str | None`，
  由 harness 从 DB 查询「最近 3 章标题/人物状态/开放线索」后传入，拼入摘要尾部。
- 摘要仍为确定性模板（两级压缩 LLM 版不纳入本次，预算成本考量，列入 P2 候选）。

### D6. 错误恢复注入（T1）
- 扩展 `harness._run_one_turn` 的 follow-up 机制：除 GuardTripped 外，回合内出现工具错误
  （result.is_error）时，turn 结束后注入「错误诊断 + 下一步建议」user 消息。
- 防抖：每回合最多注入 1 条错误恢复消息；错误次数统计防无限循环（错误恢复消息本身再出错
  不重复注入，由 L5 熔断兜底）。

### D7. 情节线规范（T2）
- `track_plotline` open 时校验：title ≤ 40 字符、禁止含「第 N 章/卷」字样（超限返回错误 + 示例）。
- query 时：支持前缀/模糊匹配（现有 LIKE 已具备，补排序与未命中回退：回退最近一条同弧线并告警）。
- 写记忆类工具统一 `get_or_create_longform_memory(db, project_id, memory_type, scope_key)` 封装
  放 `app/core/longform_memory.py`（现有 app/core/longform_memory.py 已存在，检查后并入）。

### D8. 系统提示词强化
- 工具目录注入强化与「只能调用目录内工具」约束写入 harness 使用的系统提示词模板
  （`prompting/` 侧）；T2 落地工具描述避混淆名，T6 落地事实表规范。

## 数据流（回合级）

```
用户消息 → _run_one_turn
  ├─ [T6] 注入项目状态快照（不持久化）
  ├─ 预检上下文用量 → 压缩（[T6] 摘要带写作上下文）
  └─ run_turn
       ├─ provider.stream（已有重试）
       ├─ _execute_one：before_tool_call（[T1] 钩子异常兜底）→ registry.execute（[T2] 校验示例/upsert）
       │    └─ 工具实现（[T3] plan_arc 终局核对 [T4] 格式校验 [T5] 结构重复）
       └─ guards.check（已有）
  └─ [T1] 回合末：工具错误汇总 → 注入恢复消息（follow-up）
```

## 兼容性与回滚

- 所有新增工具/参数为增量：旧会话 JSONL 回放不受影响（新事件/字段可选）。
- `LongformMemory.memory_metadata` 新增键：读侧全部用 `.get()` 默认值，无迁移。
- 每个子任务独立 commit；出问题回滚到上一 commit（Trellis 2.3 rollback）。
- 工具权限：新增工具全部 read（T4/T5）；T2/T3 只改现有工具行为，不改权限。

## 风险与对策

| 风险 | 对策 |
|---|---|
| 错误恢复注入造成消息膨胀/循环 | D6 每回合 1 条上限 + 已有 L5 熔断 |
| 状态快照每回合注入增加 token 成本 | 快照 ≤200 token；替代 list_chapters 往返更划算 |
| 格式校验误报（真实文本含 `**` 语义） | 规则只查明确模式（`**` 成对残留、章题行、备选词 `/`）；报警不拦截，由模型判断重写 |
| 终局约束误伤（正常新线索被禁止） | 只在「接近卷尾（≤5 章）」启用强制回收模式，其余时间仅提醒 |
| 结构相似度误判 | 阈值保守（相似度 >0.7 且同模式第 3 次才告警），只提示不强制 |

## 测试策略（每个子任务共同）

- 每项改动：先在 `backend/tests/agent/` 补测试（新增工具/函数单独测试文件或并入现有），再改内核。
- T1 补 `test_loop.py` 钩子异常用例 + `test_harness.py` 错误恢复注入用例 + 压缩重放矩阵。
- T4/T5 校验函数纯函数单测（构造已知文本/大纲断言检出）。
- 全量：`cd backend && python -m pytest -q`（基线 596 passed）；前端不动但跑一遍 vitest 确认无回归。
