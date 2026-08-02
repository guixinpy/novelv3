# T6 上下文注入工程：状态快照 + 摘要倾斜 + 事实表 + 人物卡

> 父任务：08-01-harness-optimization（design.md D4/D5）。来源：清单 §二.2、交接方向 5/9、评审 P1-4/6。
> 背景：200 章实测模型频繁 list_chapters/get_project_state 探索（无效往返）；
> 压缩后只剩抽象主题、丢人物关系（ch100 完结与 ch101 重启之间角色动机断裂）；
> ch98「廖城」/ch100「花城」城市名错误、全角引号 ch31 起消失（格式规范未跨章锁定）；
> 第二部「最初的名字」203 次（主题记忆过度注入）。

## Goal

让模型每回合自带「可行动的写作上下文」，减少工具探索往返、压缩后保住人物/关系/规范。

## Requirements

### R1. 回合级项目状态快照（新模块 `app/core/project_snapshot.py`）
- `build_project_snapshot(db, project_id) -> str | None`（无 db/无 project 返回 None）：
  - 章节总数、最近 3 章标题/字数
  - 活跃弧线（标题/跨度/距收束章剩余）
  - 开放 plotline 数（含 stale 数）
  - 目标章数（若有 endgame resolve_before）
  - **全书事实表**：Setups 角色名/地点名清单 + 格式规范（全角引号、无 markdown 残留等——来自 T4 规则说明）
- 文本块 ≤200 token（约 400 字内）。
- **注入位置**：`harness._run_one_turn` 临时拼进 system prompt（`history[0]["content"]` 追加快照段），
  **不持久化**（system 消息本就不落盘；压缩重放同样被 [1:] 切掉）。

### R2. 压缩摘要倾斜（compaction.py）
- `compact_history(..., extra_context: str | None = None)` 与 `_build_summary_text(..., extra_context)`：
  摘要尾部追加「最近写作上下文：」段（快照文本）。
- harness 压缩调用处传快照（与 R1 同一来源）。

### R3. query_memory 人物卡优先级
- 返回排序改为：**author_explicit 优先 → 最近更新优先**（内存排序，结果 ≤10 条）；
  主题金句类（agent_inferred 抽象句）自然靠后，人物状态/关系卡靠前。
- 不改变返回结构。

## Acceptance Criteria

- [ ] `build_project_snapshot`：含章节数/最近 3 章/活跃弧线/开放线索/事实表角色名（新增 ≥2 用例）
- [ ] harness 注入快照：provider 首个调用 system 含「项目状态快照」；jsonl 无快照内容（不持久化）
- [ ] 无 db（现有 harness 测试场景）→ 快照跳过，行为不变（既有测试全绿）
- [ ] compact 带 extra_context → 摘要含「最近写作上下文」（新增用例）
- [ ] query_memory author_explicit 条目排在 agent_inferred 前（新增用例）
- [ ] 后端全量 pytest 通过（641 基线只增不减）、前端 vitest 无回归
- [ ] 独立 commit（message 前缀 `harness: T6`）

## 实现要点（已核实代码位置）

- 新文件 `backend/app/core/project_snapshot.py`
- `backend/app/agent/harness.py:186` — `_run_one_turn` system 构造处
- `backend/app/agent/compaction.py:65-135` — compact_history、`:138` _build_summary_text
- `backend/app/tools/memory.py:170-240` — query_memory 排序
- 事实表数据源：`app.models.Setup`（characters/locations JSON）+ Project
- 测试：`test_harness.py`（注入）、`test_compaction.py`（extra）、`test_tools_memory.py`（排序）、
  新 `test_project_snapshot.py`

## Notes

- 快照只读；不改变事件契约；无 db 时静默跳过（向后兼容）。
- 快照内容不写进 JSONL 日志（真相源不受污染）。
