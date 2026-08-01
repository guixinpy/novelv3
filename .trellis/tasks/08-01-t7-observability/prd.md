# T7 可观测性：analyze 补幻觉/未知工具/质量维度

> 父任务：08-01-harness-optimization（最后一个子任务）。来源：清单 §二.5、交接方向 10。
> 背景：200 章实验报告缺「幻觉工具名」「未知工具频率」「每章质量自检」维度，无法量化 harness 改进效果。

## Goal

`scripts/analyze_dogfood.py` 补四个观测维度，让后续实验报告能量化幻觉治理与质量守门效果。

## Requirements

### R1. 幻觉工具名统计
- 从 tool 错误消息解析「工具 X 不存在」模式（`工具\s*(\S+?)\s*不存在`）→ Counter 幻觉工具名。
- 报告新增 `hallucinated_tools: [{name, count}]`（按次数降序）。

### R2. 未知工具频率
- 未知工具调用次数 / 全部 tool 消息数 → `unknown_tool_rate`（百分比，保留 2 位）。
- 数据源：`hallucinated_tools` 总数 + tool 消息计数（session 解析时统计）。

### R3. 每章质量自检结果
- 解析 tool 消息中 quality 结果（check_chapter_quality/check_chapter_format 的返回
  `"quality": "pass|needs_review|fail"` 与 chapter_index）→ 按章汇总。
- 报告新增 `chapter_quality: [{chapter_index, quality}]`（按章号升序，一 章多检取最新）。
- 补充：format 检查的 issue 类型频率（markdown_bold/slash_alternative 等，新工具 T4 产出）。

### R4. 压缩事件质量
- compaction 记录追加评估：`summary_has_writing_context`（summary 含「最近写入章节」「质量自检」「最近写作上下文」之一）、
  节省比例 `saving_ratio`（1 - after/before）。
- 报告新增 `compaction_quality`: {count, with_writing_context, avg_saving_ratio}。

### R5. 报告 md 输出
- 新增章节：「幻觉工具调用」「每章质量自检」「压缩摘要质量」；`main()` 打印摘要行补幻觉/质量统计。

## Acceptance Criteria

- [ ] 对现有 200 章项目（`5e2eccbe`）运行 analyze 不报错，报告包含全部新维度
- [ ] 幻觉工具统计与未知工具频率数值一致（幻觉总数 = unknown 次数，rate = count/tool_msgs）
- [ ] 章节质量表按章升序、最新检查优先
- [ ] 压缩摘要质量统计输出（含写作上下文的压缩数、平均节省比例）
- [ ] 既有字段（turns/compactions/errors/chapters）不变
- [ ] 独立 commit（message 前缀 `harness: T7`）

## 实现要点（已核实代码位置）

- `scripts/analyze_dogfood.py`：session 解析循环（`:86-90` 错误收集处扩展统计）、
  report 构造（`:95-125`）、md 输出（`:138-176`）、main 打印（`:187-191`）
- 测试方式：脚本无 pytest；验收 = 对 `5e2eccbe` 运行 + 断言报告字段（手写验证脚本或直接运行查看）
- DB：`data/mozhou.db`（sqlite，gitignore，200 章实验数据在）

## Notes

- 不改会话日志格式（只读分析）。
- 正则解析容忍「工具 read_chapter 不存在」「工具 foo 不存在。可用工具…」两种句式。
