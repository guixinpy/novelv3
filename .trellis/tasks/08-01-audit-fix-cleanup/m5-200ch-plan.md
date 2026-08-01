# M5 细化方案 · 200 章长程实验

> 前置：M4 50 章 dogfood 通过（`3064415b` 项目，2026-08-01 运行中）。

## 1. 目标与验收口径

对应 `03-roadmap.md` M5 退出标准：

> ≥200 章连续生成，质量趋势指标（长度方差、重复度、一致性违规数）不出现持续恶化斜率。

验收数据源：
- 章节表 `chapter_contents`（字数、状态）
- `longform_memories`（弧线摘要、plotline 闭环）
- `world_*` 表（实体一致性）
- 会话 JSONL（`turn_ended.prompt_tokens`、guard 触发）
- `check_quality_trend` 工具输出（每章后模型自检记录）

## 2. 指标与阈值（建议初值，实验开始前确认）

| 指标 | 计算 | 恶化阈值 |
|---|---|---|
| 章节字数中位数 | 每 10 章窗口 | 连续 3 个窗口下滑 >20% |
| 字数方差 | 每 10 章窗口 | 变异系数 >0.5 持续 2 窗口 |
| 重复度 | 相邻章节 n-gram 重合（离线脚本） | 窗口重合率上升 >50% |
| 一致性违规 | world_checker 抽查 + 人工评审（每 20 章） | 单窗口硬性漂移 ≥1 起 |
| 情节线滞留 | `track_plotline` 开放时间 | 弧线结束 5 章后仍未闭环 >3 条 |
| 护栏触发 | 会话 JSONL | 任意 guard_tripped |

止损规则：任一指标连续 2 个窗口越过阈值 → 停止实验，输出诊断报告（定位是记忆召回、弧线规划还是质量自检失效），修复后从上一个 checkpoint 续跑。

## 3. 实验设计

方式：**既有长篇续写**（非新建项目），模拟真实创作场景。

- 项目：1 个，目标 200+ 章；或 2 个项目各 100+ 章（建议先 1 个，控制成本）。
- 结构：5-6 卷（每卷 30-40 章），每卷开头 `plan_arc define` 新弧线。
- 每章流程（复用 `l4_dogfood.py` 消息模板）：
  1. 写前 `query_memory` 回顾人物/位置 + `track_plotline query`
  2. `write_chapter`
  3. `check_chapter_quality` 自检 + `track_plotline` 推进
  4. 每 10 章 `check_quality_trend` + `memory_tree overview`
- 每卷 checkpoint：导出会话 JSONL + 质量指标快照到 `C:\tmp\m5_200ch\`。

## 4. 运行与成本估算

- 工具：`scripts/m5_200ch_test.py`（新建，模式同 `m5_30ch_test.py`，含 plan_arc 卷规划）。
- 预计每章 8-15K 输入 tokens + 2-4K 输出（50 章实测约 15K 字/10 章 → 每章 ~1.5K 字）。
- 200 章估算：输入 ~2-3M tokens、输出 ~0.5M tokens；DeepSeek 按当前价约 ¥10-40（以实际模型计价为准）。
- 时长：按本轮实测 ~1.5 分钟/章，约 5-6 小时（可分段跑，`--start-chapter` 续跑）。

## 5. 前置代码要求（M4 暴露的缺口，已修复或待确认）

已修复（commit `4db43cf0` / `005a363a` / `30ca96a0`）：
- 工具执行 db rollback（IntegrityError 不再毒化请求）
- `plan_arc` upsert（重复 define 不冲突）
- `write_chapter` 推进项目状态（draft→writing）
- `query_world` 回退 `update_setup` 数据（设定可见）
- dogfood 脚本 SSE 字段兼容 + recall 严格判定

实验前仍需验证：
- 压缩接线（`f3739a53`）在真实 50 章单会话中的触发记录（检查 JSONL `compaction` 条目）
- 第 50 章请求上下文是否真的不含前 40 章原文（从 compaction 快照 + token 用量推断；如需强证据，可在 harness 增加请求快照日志）

## 6. 产出

- `m5_200ch_report.md`：每卷指标表、触发止损的原因与修复、最终 PASS/FAIL 判定。
- 实验数据目录 `C:\tmp\m5_200ch\`（JSONL 快照 + 指标 CSV）。
