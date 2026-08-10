# 伏笔/悬念账本 —— 技术设计

## 1. 数据模型（不迁移）

复用 `LongformMemory`（memory_type="plotline"），新字段全部走 `memory_metadata` JSON：

| 字段 | 存处 | 语义 |
|---|---|---|
| `expected_resolve_chapter` | memory_metadata | 预计回收章（int，可空） |
| `payoff` | memory_metadata | 回收摘要（close 时记录，可空） |

**查询策略**：超期/临期判定全走普通列 `start_chapter_index`、`status`（SQLite JSON 索引比较不可靠——既有教训），expected 仅作二级判断（读到行后内存比较）。

## 2. 自省接线（核心）

### 2.1 system prompt（`writing_experience.py::_INTROSPECT_SYSTEM_PROMPT`）

输出规格从单键扩为双键，**追加**伏笔段，不改动 experiences 语义：

```json
{"experiences": [...],
 "plotline_updates": [
   {"action": "open", "title": "…", "summary": "…", "expected_resolve_chapter": 80},
   {"action": "close", "title": "…", "payoff": "…"},
   {"action": "postpone", "title": "…", "expected_resolve_chapter": 120},
   {"action": "none"}
 ]}
```

纪律条文（追加到 system prompt）：
- 更新动作（close/postpone）的 title 必须与下方"当前开放伏笔"清单**逐字一致**，不得自创标题；不确定时输出 none
- open 仅登记本章**新埋设**的伏笔；expected_resolve_chapter 由作者心证（何时该收），可空
- close 须给出 payoff（如何回收）
- 本章无任何伏笔变化 → `"plotline_updates": []` 或 `[{"action": "none"}]`

### 2.2 user prompt（`_build_introspect_user_prompt`）

新增参数 `open_plotlines: list[dict]`（title/start_chapter_index/expected/是否超期），拼入一行：
`当前开放伏笔：{title}(埋于 Ch{n}, 预计 Ch{m} 收[, 已超期])、…`

调用方 `introspect_and_record` 在构建 prompt 前查询开放伏笔（复用 memory_service 的查询，≤20 条，防 prompt 膨胀）。

### 2.3 解析（`_parse_introspect_output`）

返回结构从 `list[dict]` 改为 `{"experiences": list, "plotline_updates": list}`（或保持返回 list、另取字段——实现选型：**改返回 dict**，两个消费方同步改，单测覆盖旧格式返回 `plotline_updates=[]`）。复用既有大括号配对健壮解析；解析失败仍记日志，两段均空。

### 2.4 应用（`memory_service.py` 新函数）

```python
def plotline_apply_updates(db, project_id, updates: list[dict]) -> dict
```

| 动作 | 行为 | 匹配 |
|---|---|---|
| open | get_or_create_longform_memory 复用（重复 open → already_exists），写入 expected | scope_key（title） |
| close | status open → closed + end_chapter_index + payoff | scope_key == title 精确 |
| postpone | 更新 expected_resolve_chapter | scope_key == title 精确 |
| none / 缺 action | 跳过 | — |

- 匹配失败（close/postpone 找不到开放伏笔）→ 记日志 fail-open，计数 returned
- 与 `apply_experiences` 同批在 `introspect_and_record` 的原子事务内（commit=False 风格：apply_experiences 已用 commit=False + 调用方统一 commit——plotline_apply_updates 同样接受 commit=False 并入该事务，保证自省标记与伏笔更新原子）
- 校验：expected_resolve_chapter 须为 int ≥ 1，title 长度复用 `_PLOTLINE_TITLE_MAX`，违规项跳过记日志

### 2.5 幂等

`introspect_and_record` 已有 introspect_log 标记（普通列 scope_key="chapter:{n}"），已自省章节整体跳过——伏笔提取随自省同批，天然幂等，无需额外标记。

## 3. 快照注入（`project_snapshot.py`）

伏笔段从计数改为：

```
开放伏笔 3 条；超期: 「林舟身世之谜」(埋于 Ch12，34 章未收)；临期: 「黑市线」(预计 Ch80 收)
```

规则：
- 超期判定：有 expected → chapter_index > expected；无 expected → 沿用 `_PLOTLINE_STALE_AFTER=30` 阈值（与 track_plotline 一致）
- 临期：有 expected 且 current 在 `[expected-3, expected]` 区间
- 排序：超期优先 → 临期 → 其余；注入 ≤3 条
- 无超期/临期时保持计数（`开放伏笔 N 条`），不虚报

## 4. 工具增强（`memory_tools.py` + `memory_service.py::track_plotline`）

- `track_plotline`：open 加 `expected_resolve_chapter: int = 0`（0→不存），close 加 `payoff: str = ""`（写入 memory_metadata["payoff"]）
- query 返回项加 `expected_resolve_chapter`、`payoff`；标记逻辑：`stale`（沿用现有）拆为 `overdue`（超期）+ `due_soon`（临期），stale_warning 文案同步区分两级
- 工具 description 同步更新（含 expected/payoff 参数说明）

## 5. 风险与对策

| 风险 | 对策 |
|---|---|
| title 漂移 → close/postpone 静默失效 | prompt 强制逐字复用 + 匹配失败记日志（fail-open） |
| 自动 open 误报（普通情节当伏笔） | provenance=agent_inferred 标记已有；手动登记仍权威；误报可由 close 纠正 |
| 自省 JSON 解析失败连带丢伏笔段 | 复用大括号配对解析；失败只丢两段，不炸流程 |
| prompt 膨胀（开放伏笔过多） | 注入清单上限 20 条 |
| 快照超预算 | 清单 ≤3 条 + 每条 ≤30 字 |

## 6. 改动面

| 文件 | 改动 |
|---|---|
| `backend/domain/memory/writing_experience.py` | system prompt、user prompt 参数、_parse_introspect_output 返回结构、introspect_and_record 接线 |
| `backend/domain/memory/memory_service.py` | 新函数 plotline_apply_updates、track_plotline 参数与 query 标记 |
| `backend/domain/memory/project_snapshot.py` | 伏笔段注入升级 |
| `backend/domain/tools/memory_tools.py` | track_plotline 描述/参数 |
| `backend/tests/` | 新单测（apply/解析/快照/工具）+ 存量测试适配 |
