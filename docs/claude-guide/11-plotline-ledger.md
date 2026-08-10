# 11 · 伏笔/悬念账本（plotline ledger）

> 状态：**已实现**（2026-08-10）｜09 定稿"独立后续项"落定

## 一、问题定义

读者弃书第一主因是伏笔悬而不收。track_plotline 原有能力：登记 open/close/query + 30 章 stale 警告。缺口：

1. **无计划回收点**：作者（模型）埋线时心里有计划，账本不记录
2. **回收无据**：close 只记章号，不记"怎么收的"（payoff），复盘无据可查
3. **注入无行动价值**：快照只报"N 条开放伏笔"计数，模型不知道哪条该收了

## 二、设计决策（2026-08-10 讨论）

| 决策 | 结论 | 理由 |
|---|---|---|
| 登记来源 | **自省自动提取**（同一次 LLM 调用顺带输出 plotline_updates） | 不自增调用成本；覆盖率可控 |
| 字段范围 | **最小**：expected_resolve_chapter + payoff | 直击缺口，不加 importance/dropped |
| 存储 | LongformMemory.memory_metadata JSON，不建表 | 超期判定走普通列（SQLite JSON 索引不可靠教训） |

## 三、实现要点

### 自省接线（writing_experience.py）
- system prompt 输出规格扩为双键：`{"experiences": [...], "plotline_updates": [...]}`，向后兼容（旧格式 → 伏笔段零动作）
- user prompt 注入「当前开放伏笔」清单（≤20 条，含 overdue 标记）——模型才能对已有伏笔 close/postpone
- 纪律：更新动作 title 必须与清单逐字一致（防漂移）；无变化输出空数组
- 解析复用大括号配对健壮解析；应用与经验记账同事务（commit=False 原子提交 + 幂等标记）

### 应用层（memory_service.py）
- `plotline_apply_updates(db, project_id, chapter_index, updates)`：open（新建/补 expected/reopen）/ close（payoff + 结束章）/ postpone（更新 expected）/ none
- fail-open：title 校验违规、匹配失败（漂移）、未知动作 → 记日志跳过
- `_find_open_plotline` 查询前 `db.flush()`：autoflush=False 环境下同事务先改后查必见（reopen → postpone 同 batch 场景）
- `plotline_due_items(db, project_id, limit=3)`：到期条目（超期优先 → 临期），快照钩子用

### 到期判定（_plotline_due_state，query 与快照共用防漂移）
- 有 expected：`latest > expected` → **超期**（overdue_by）；`latest ≥ expected-3` → **临期**（resolves_in）
- 无 expected：沿用 30 章阈值（age_chapters）

### 快照钩子（project_snapshot.py）
```
开放伏笔 3 条；到期伏笔: 「林舟身世之谜」(已超预计 10 章)；「黑市线」(预计 Ch62 收)
```
数量 + 具体清单（≤3 条，超期优先），无到期不虚报——驱动模型主动决策（收线或显式延期）。

### 工具增强（track_plotline）
- open 加 `expected_resolve_chapter`（可选）；close 加 `payoff`（可选）
- query 返回 expected_resolve_chapter/payoff；item 级标记 overdue/due_soon；stale_warning 键保留（合并文案，兼容旧消费方）

## 四、验收

- 145 passed（新增 10：账本应用三动作/skipped 容错/expected 校验/query 两级标记/自省接线 open+close/旧格式兼容/漂移跳过/快照清单/不虚报）
- ruff 全过

## 五、后续可选（本期不做）

- importance 分级（注入优先级）
- dropped 状态（主动放弃，区别于 close）
- track_plotline 工具支持 postpone 动作（当前仅自省输出可延期）
- 前端账本视图（契约 10 表结构不变，metadata JSON 扩展）
