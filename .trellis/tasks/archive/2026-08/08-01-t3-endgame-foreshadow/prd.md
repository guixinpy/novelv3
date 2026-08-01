# T3 终局与伏笔约束：plan_arc 卷终局 + 回收期限

> 父任务：08-01-harness-optimization（design.md D2/D3）。来源：评审 P0-1（必做）、交接方向 3/6。
> 背景：200 章实验最大教训 —— ch160-201 无限「更早/更深/更初」递推、无终局；伏笔铺了不收。

## Goal

给弧线规划加「卷终局约束」，给伏笔加「回收期限」，让模型在接近卷尾时被迫收束而非无限递推。

## Requirements

### R1. plan_arc define 登记终局约束（`tools/memory.py` plan_arc）
- define 新增可选参数 `must_resolve: list[str]`（本卷结束前必须回收的伏笔清单）。
- 收束章号 = `end_chapter`（弧线结束章即收束点）。
- 写入 `LongformMemory.memory_metadata["endgame"]`：`{"resolve_before": end_chapter, "must_resolve": [...]}`；
  **合并写入**，不得覆盖已有 metadata 键（provenance/source）。
- 不传 must_resolve → 不写 endgame 键（现有行为不变，向后兼容）。

### R2. plan_arc progress 输出终局状态
- progress 返回体增加：
  - `endgame_remaining`: 距收束章剩余章节数（当前最新章 vs resolve_before）
  - `must_resolve_open`: must_resolve 中仍未闭环的项（对照开放 plotline 标题，模糊包含匹配）
  - `endgame_warning`: 剩余 ≤5 章且仍有未回收项 → 强制回收模式警告：
    「本卷剩余 N 章，以下伏笔必须在收束前回收：X/Y/Z。禁止新增「更早/更深/更初」层级。」
  - 剩余 ≤0 → 弧线已过期（超收束章未回收）警告

### R3. check_quality_trend 增加终局核对（`tools/chapters.py`）
- 调用时取当前活跃 story_arc 的 endgame 数据：
  - 最新已写章 vs resolve_before，剩余 ≤5 章 → 返回体附 `endgame_mode: true` + 未回收清单 + 强制回收提示
  - 剩余 >5 → `endgame_mode: false`（无打扰）
- 不破坏现有 trend 输出结构（附加字段）。

### R4. 伏笔回收期限（track_plotline query）
- open 的 plotline 计算 `age_chapters`（最新章序号 - start_chapter_index）；
  超过 `_PLOTLINE_STALE_AFTER = 30` 章未闭环 → 该条目附 `stale: true`，返回体附
  `stale_warning`: 「以下伏笔已开放超过 30 章：X(起始于第N章)…。请在本卷收束前回收，或显式闭环。」
- 最新章序号：查 ChapterContent max(chapter_index)。

## Acceptance Criteria

- [ ] define 传 must_resolve → metadata.endgame 写入且不覆盖 provenance（新增用例）
- [ ] define 不传 must_resolve → 无 endgame 键（既有用例保持通过）
- [ ] progress 返回 endgame_remaining/must_resolve_open，剩余 ≤5 且有未回收 → endgame_warning 含「禁止新增」字样
- [ ] check_quality_trend 在卷尾返回 endgame_mode + 未回收清单
- [ ] query 返回 stale 标记与 stale_warning（伏笔 >30 章未闭环）
- [ ] 后端全量 pytest 通过（615 基线只增不减）、前端 vitest 无回归
- [ ] 独立 commit（message 前缀 `harness: T3`）

## 实现要点（已核实代码位置）

- `backend/app/tools/memory.py` — plan_arc define/progress、track_plotline query
- `backend/app/tools/chapters.py:327` — check_quality_trend
- metadata 合并：读 `(m.memory_metadata or {})` → dict.update → 写回
- 最新章序号：`ChapterContent.chapter_index` max 查询（项目内已有类似模式，见 memory_tree）
- 测试：`backend/tests/agent/test_tools_memory.py`、`test_tools_quality.py`

## Notes

- 只读工具；不改变权限与事件契约。
- must_resolve 匹配用「包含匹配」（plotline.title 含清单项即算已回收），容忍标题措辞差异。
