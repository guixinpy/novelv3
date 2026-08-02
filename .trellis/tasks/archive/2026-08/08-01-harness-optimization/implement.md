# P0 Harness 系统化优化 · 执行计划

> 父任务级执行计划：子任务的创建/启动顺序、全局验证门、回滚点。
> 每个子任务内部按自身 prd/design/implement 执行（先测试后内核、独立 commit）。

## 执行顺序（推荐顺序 = 依赖 + 风险 + 评审 P0 优先级）

1. **T1 内核健壮性**（打底：钩子兜底 + 错误恢复注入 + 压缩重放测试）
2. **T2 工具可靠性**（工具层：参数示例 + upsert 封装 + 情节线规范 ← 评审 P0-3）
3. **T3 终局与伏笔约束**（← 评审 P0-1，最重要写作约束）
4. **T4 输出格式守门员**（← 评审 P0-2）
5. **T5 结构级重复检测**
6. **T6 上下文注入工程**（跨模块，最后做）
7. **T7 可观测性**（汇总维度）

T3 与 T4 相互独立可交换；T6 依赖 T1/T2 的内核与工具层稳定（避免同时改动难定位回归）。

## 每个子任务的固定流程

```
1. 创建子任务（已创建，planning）
2. 写子任务 prd.md（需求 → 验收标准；可继承父 design 决策，无需重复）
   - 简单子任务 PRD-only；T1/T6 建议补自身 design 要点
3. task.py start → in_progress
4. 先在 backend/tests/agent/ 补测试（红）→ 改内核/工具（绿）
5. 跑后端全量 pytest + 前端 vitest（无回归）
6. 独立 commit（message 标注方向，如 "harness: T4 输出格式守门员"）
7. task.py finish → 归档（archive）
```

## 全局验证门（每步必须过）

| 门 | 命令 | 通过标准 |
|---|---|---|
| 后端测试 | `cd backend && python -m pytest -q` | 596 passed 且只增不减 |
| 前端测试 | `cd frontend && .\node_modules\.bin\vitest.cmd run --reporter=dot` | 485 tests 通过 |
| 类型检查 | `cd frontend && .\node_modules\.bin\vue-tsc.cmd --noEmit` | 通过 |
| 会话回放 | 200 章 JSONL（`data/agent_sessions/`）加载到改造后 harness 不抛错 | 兼容 |
| 无死代码 | 变更 diff 无孤儿 import/函数 | 审查 |

注意：`npm` 命令在当前机器损坏，一律用 `node_modules\.bin\` 直接入口。

## 子任务依赖与交接

- T2 的 upsert 封装（D7 `get_or_create_longform_memory`）是 T3 前置（T3 写终局数据复用）；
  T2 先于 T3 启动。
- T6 的项目状态快照读取「开放 plotline 数」依赖 T3 的 endgame 数据（可选字段，无 T3 也自洽）。
- T7 的分析维度依赖 T1（错误恢复事件）与 T4（格式校验结果）产生的日志/数据；
  最后执行，从 JSONL 会话日志解析。

## 评审门（父子任务）

- 父任务 prd/design/implement 完成后：用户评审通过 → 启动 T1。
- 每个子任务实现完成后：trellis-check 检查 → 用户可见结果 → 下一子任务。
- 全部 7 个子任务完成后：父任务验收（跨子任务验收标准）→ 父任务归档。

## 回滚点

- 每个子任务 commit 独立；单子任务失败 → 回滚该 commit（Trellis 2.3）。
- T6 状态快照注入若导致模型行为异常 → 先停快照注入（一行开关），再排查。
- 任何一步后端全量 pytest 不通过 → 停止推进，先修到绿。

## 里程碑

- M1: T1+T2 完成（内核与工具层健壮）→ 可作为一次安全提交点
- M2: T3+T4 完成（评审 P0 三项必做全部落地）
- M3: T5+T6 完成
- M4: T7 完成 → 父任务验收 → 归档
