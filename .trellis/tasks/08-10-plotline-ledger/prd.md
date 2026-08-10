# 伏笔/悬念账本（自省自动提取 + 超期钩子）

## Goal

章末自省同一次 LLM 调用顺带提取伏笔状态变化（open/close/postpone），账本记录**预计回收章**与**回收摘要**；快照注入从"开放伏笔计数"升级为"超期/临期具体清单"，驱动模型主动决策（收线或显式延期）。09-per-book-self-optimization.md 定稿的独立后续项。

## Background（读者视角痛点）

弃书第一主因是伏笔悬而不收。现状（track_plotline）已能登记 open/close/query + 30 章 stale 警告，但：
- 快照只注入"N 条开放伏笔"计数——模型不知道**哪条**该收了，计数无行动价值
- 没有"计划回收点"概念——作者（模型）埋线时心里有计划，账本不记录
- 回收（close）只记章号，不记"怎么收的"（payoff），复盘无据可查
- 登记完全依赖模型主动调用 track_plotline，覆盖率不可控

## Requirements

- **R1 自省自动提取**：章末自省（introspect_and_record）同一次 LLM 调用输出 `plotline_updates` 字段，应用 open/close/postpone/none 动作到账本。不自增 LLM 调用次数。
- **R2 账本字段**：`expected_resolve_chapter`（预计回收章）、`payoff`（回收摘要）存入 LongformMemory.memory_metadata，不建新表。
- **R3 快照超期钩子**：项目快照注入从"开放伏笔计数"升级为"数量 + 超期/临期具体清单（≤3 条，超期优先）"，不超快照总预算。
- **R4 工具增强**：track_plotline 手动登记同步可用新字段——open 支持 expected_resolve_chapter，close 支持 payoff；query 返回临期/超期两级标记。

## Constraints

- 不新建表/不新增普通列（SQLite JSON 索引比较不可靠，超期查询走已有 start_chapter_index + status 普通列）
- 向后兼容：旧格式自省输出（无 plotline_updates 字段）照常记账，不产生副作用
- 自省失败/解析失败/匹配失败全部 fail-open：不阻塞写作流程，只记日志
- 幂等：已自省章节（introspect_log 标记）不重复提取
- title 防漂移：更新动作（close/postpone）的 title 必须与开放伏笔清单逐字一致，否则匹配失败记日志
- 快照注入保持"仅供参考"定位：伏笔清单是提醒，不是硬指令

## Acceptance Criteria

- [ ] 自省后账本正确变化：open 新建（含 expected）、close 闭合（含 payoff + 结束章）、postpone 更新 expected
- [ ] 已自省章节重放不重复提取（幂等标记生效）
- [ ] 旧格式自省输出（无 plotline_updates）不影响 experiences 记账，应用层零动作
- [ ] track_plotline open/close/query 新参数工作；query 返回临期（距 expected ≤3 章）/超期（超 expected 或 30 章阈值）标记
- [ ] 快照伏笔段含超期/临期具体清单（≤3 条）且无超期时不虚报
- [ ] 全部现有测试通过 + 新增单测覆盖上述路径
- [ ] ruff 检查通过

## Notes

- 设计决策（2026-08-10 讨论）：登记来源=自省自动提取（直接含第一期）；字段=最小（expected_resolve_chapter + payoff，无 importance/dropped）
- 后续可选（本期不做）：importance 分级、dropped 状态、前端账本视图
