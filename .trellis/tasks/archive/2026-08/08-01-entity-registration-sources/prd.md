# P1 实体登记来源扩展（规则提取 + L2 注入）

## Goal

解决实体登记白名单太薄的问题（200 章项目 Setup 仅 1 角色 → 全书 30+ 角色、entity_state 记忆仅 2 条，
导致人物状态记忆空白、长程人物关系断裂）。双通道扩展实体来源：
A. 正文规则提取（纯 Python 姓氏白名单 + 频率过滤，随写作增量）
B. L2 一致性深查的事实实体注入（extracted_facts 的 subject/object）
用户 2026-08-01 决策：C 方案（A+B 组合）。

## 现状（调研确认）

- `_capture_entities`（tools/chapters.py）：从 WorldCharacter/WorldLocation/Setups.characters 读已知实体，
  正文包含则 upsert entity_state 记忆——**白名单式，来源太薄**
- 200 章项目实测：Setups 1 角色（程景洲）、WorldCharacter/Location 空、entity_state 仅 2 条
- `extracted_facts` 表存在（L2 深查写入，background_analyzer.deep_check），data JSON 含 subject/predicate/object，
  200 章项目 0 条（未跑深查）；source 区分 l2_llm / l1_rule
- `text_mentions.count_non_overlapping_mentions` 可复用（L1 提取器在用）

## Requirements

### R1. 候选实体表 + 模型
- 新表 `entity_candidates`（模型 `EntityCandidate`）：project_id, name, source（rule/l2）, first_chapter,
  last_chapter, chapter_count（出现章数）, created_at；唯一约束 (project_id, name)
- 迁移方式：建表 + 现有 DB 自动建表（app.db Base.metadata；检查项目迁移机制后定）

### R2. 正文规则提取 `core/entity_miner.py`
- `mine_entities_from_text(text) -> list[str]`：
  - 中文姓氏白名单（~300 常见姓，硬编码集合）+ 后接 1-2 个汉字的「姓+名」模式
  - 排除常见误报（接「先生/小姐/警官/警官/局长」等称谓词也算人名？——接称谓词算；接「的/了/是/在」等虚词不算）
  - 2-4 字候选（含姓）
- `register_entity_candidates(db, project_id, chapter_index, names, source)`：upsert 候选，
  新章则 chapter_count+1、first/last_chapter 更新
- **转正规则**：chapter_count ≥2（跨 ≥2 章出现）的候选进入实体登记白名单

### R3. _capture_entities 接入候选源
- 已知实体源（WorldCharacter/WorldLocation/Setups）合并「转正候选」（chapter_count ≥2 的 entity_candidates）
- 每次写入章节时：先 `mine_entities_from_text` → register（source=rule）→ 再走原 _capture_entities 流程

### R4. L2 事实实体注入
- `background_analyzer.deep_check` 保存 extracted_facts 时，把 fact 的 subject/object 调
  `register_entity_candidates(..., source="l2")`（l2 来源不设转正门槛——LLM 提取准确）
- subject/object 提取：fact.get("subject")/fact.get("object") 或 data 内字段（以实际 L2 输出结构为准）

### R5. 200 章数据验证（可测性关键）
- 用 `data/exports/M5-200章-201章.md` 抽样章节跑 `mine_entities_from_text`，
  验证能发现 程砚秋/苏晚晴/顾沉舟 等主要角色（≥2 章出现的角色应被提取）

## Acceptance Criteria

- [ ] `entity_candidates` 表可建（测试用 SQLite 建表通过）
- [ ] `mine_entities_from_text`：200 章抽样正文提取出主要角色名（≥80% 主要角色命中）；常见虚词不误报
- [ ] 候选 upsert：跨章计数正确、同章去重（新增用例）
- [ ] `_capture_entities`：转正候选进入白名单（写 2 章含新角色 → entity_state 出现该角色）（新增用例）
- [ ] L2 注入：deep_check 后 subject/object 进入候选表（source=l2）（新增用例）
- [ ] 后端全量 pytest 通过（583 基线只增不减）、前端 vitest 无回归
- [ ] 独立 commit（message 前缀 `harness: T?` → 本任务用 `refactor: entity`）

## Notes

- 不引入 NLP 依赖；姓氏白名单硬编码（可后续扩充）。
- 转正阈值（≥2 章）保守可调；rule 来源需转正、l2 来源免转正（来源可信度差异）。
