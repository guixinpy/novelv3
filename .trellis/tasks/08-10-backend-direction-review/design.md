# 质量保障特化（质量趋势 + 连续性检测）—— 技术设计

## 1. 设计原则（用户约束）

**工具不越权**：检测器是信息提供者，模型/用户是决策者。
- 输出一律「报告形态」：问题描述 + 证据 + 可能原因（供参考），无指令式文案、不自动修复、不阻塞
- 修正旧实现缺陷：旧 `check_quality_trend` 的 advice 为指令式（"请立即检查：1)…2)…"）→ 改为信息形态
- 两能力均为**确定性纯函数**（零 LLM 成本）：趋势是 SQL 聚合，连续性检测是规则提取 + 集合比对

## 2. R1 质量趋势（快照注入）

### 2.1 数据与判定（domain/writing/quality_trend.py 新模块）

```python
def quality_trend_stats(db, project_id, window=10) -> dict | None
```

- 取最近 ≤window 章（word_count 普通列），不足 3 章 → `{"trend": "insufficient_data"}`
- 前半/后半窗口均值比 → 四级：`severe_decline`(<0.5) / `declining`(<0.75) / `growing`(>1.3) / `stable`
- 输出：trend + 前后均值 + 降幅 + 可能原因列表（**信息形态**，如"可能原因：主线完结/填充内容/场景单薄"，无"请立即"指令）

### 2.2 快照注入（project_snapshot.py）

新段，仅当数据充足且非 stable：
```
质量趋势: 近10章字数 3200→2100（-34%，可能: 主线尾声/填充内容）
```
- stable 不注入（噪声）；长度 ≤约 40 字
- 位置：章节进度段之后（与进度相邻，模型对照弧线判断）

## 3. R2 连续性检测（工具形态）

### 3.1 checker registry（domain/writing/continuity.py 新模块）

```python
def check_continuity(db, project_id, chapter_index=None, *, all_chapters=False) -> dict
```

- 第一版维度：**角色状态**（CharacterStateChecker）
  - 从 setup.characters 读角色名 + character_status（默认 alive）
  - 状态为 dead（昏迷等非活跃状态可后续扩展）的角色名单
  - 用 `mine_entities_from_text(chapter.content)`（entity_miner 复用）提取本章出现的角色
  - 交集 → issue：角色「X」已标记为死亡，却在第 N 章再次出场
  - 空 chapter_index 时默认检查最近一章
- 输出结构（报告形态）：
  ```json
  {"issues": [{"checker": "character_state", "severity": "fatal", "subject": "X",
    "chapter_index": N, "evidence": "出现在第 N 章", "suggestion": "确认角色状态或修改出场安排"}],
   "checked_chapters": 1}
  ```
  - `suggestion` 是给模型的参考，非强制
- checker 接口：`(db, project_id, chapter, setup) -> list[issue]`，注册表扩展后续维度（时间线/编号/关系锚点）

### 3.2 工具（domain/tools/retrieval_tools.py 或新 quality_tools.py）

```
name: check_continuity    permission: read
args: chapter_index: int = 0（0=最近一章）
```
- 放 writing_tools 或独立文件？→ **独立 quality_tools.py**（与写工具/记忆工具并列，避免文件膨胀）
- 模型按需调用：弧线转折、久隔重写、长章节后自查

## 4. 兼容性

- 无 schema 变更（复用 setup.characters 的 name/character_status、chapter_contents.word_count）
- 快照新增一段 ≤40 字：总量预算 400 字内可容
- 工具新增一个 read 工具，无审批拦截变更
- 旧 `check_quality_trend` 在归档代码（474a8f8c^），本实现为新写（非迁移，语义按原则修正）

## 5. 风险

| 风险 | 对策 |
|---|---|
| 角色状态误报（回忆/梦境/同名） | 报告形态不阻塞，模型/用户裁决；severity 用 fatal 但仅信息 |
| 快照膨胀 | 趋势段 ≤40 字 + 仅非 stable 时注入 |
| mine_entities 提取质量（姓氏白名单漏检） | 与 entity_miner 同一通道，promoted 名单补充（后续） |
