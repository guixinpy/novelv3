# P1 实体登记来源扩展 · 技术设计

## 数据流

```
章节正文（write_chapter/revise_chapter）
  ├─ mine_entities_from_text(text) → 候选名（rule 通道）
  │    └─ register_entity_candidates(source="rule") → entity_candidates 表
  └─ _capture_entities（现有）：已知实体 + 转正候选（chapter_count≥2）→ entity_state 记忆 upsert

L2 深查（background_analyzer.deep_check）
  └─ subject/object → register_entity_candidates(source="l2") → entity_candidates（免转正）
       └─ 下次 _capture_entities 时纳入白名单
```

## D1. 模型与表

```python
# app/models/entity_candidate.py
class EntityCandidate(Base):
    __tablename__ = "entity_candidates"
    id: str PK
    project_id: str FK, nullable=False
    name: str, nullable=False
    source: str = "rule"          # rule | l2
    first_chapter: int | None
    last_chapter: int | None
    chapter_count: int = 1        # 出现章数（同章去重）
    created_at / updated_at
    __table_args__ = UniqueConstraint("project_id", "name")
```

## D2. entity_miner 提取规则

- 姓氏白名单：`core/entity_miner.py::_COMMON_SURNAMES`（约 300 常见姓：赵钱孙李周吴郑王…含百家姓主体 + 复姓 欧阳/司马 等 10+）
- 模式：`re.finditer(r"(?:{surnames})[一-鿿]{{1,2}}", text)` 后过滤：
  - 排除尾字为虚词/常用词（的/了/是/在/和/有/不/也/都/很/着/过/就/说/道/看/想/去/来/走/水/光/城/树/年/月 等停止词表）
  - 排除「姓氏+称谓」已在模式内（先生/小姐/女士/警官/局长/老师/老板/医生 等接姓氏后 2 字内——称谓词作为尾字候选排除，只留纯人名）
  - 候选去重保序
- `register_entity_candidates`：查 (project_id, name) → 存在且 last_chapter != 当前章 → chapter_count+1、
  last_chapter 更新；不存在 → 新建。同章重复调用只更新 last_chapter 不增 count。

## D3. 转正规则

- `_capture_entities` 白名单 = WorldCharacter ∪ WorldLocation ∪ Setups.characters ∪
  {c.name for c in entity_candidates where chapter_count ≥ 2} ∪ {l2 来源候选（免转正）}
- rule 来源需跨章；l2 来源直接入白名单（LLM 提取可信）

## D4. 接入点

1. `tools/chapters.py` write_chapter/revise_chapter：正文写入后、_capture_entities 前，
   调 `mine_entities_from_text` + `register_entity_candidates(source="rule")`
2. `tools/chapters.py` `_capture_entities`：已知实体循环前，查询转正候选并入 known_entities
3. `core/background_analyzer.py` deep_check：保存 extracted_facts 循环中，subject/object
   调 `register_entity_candidates(source="l2")`（值过滤：str 且长度 1-8）

## D5. 风险与对策

| 风险 | 对策 |
|---|---|
| 规则误报（非人名被提取） | 停止词表过滤 + 跨章转正门槛；候选不直接进记忆（先入候选表） |
| 转正候选进记忆后仍有误报 | 阈值可调（≥2）；候选表可审计（source 标记） |
| 姓氏表不全（罕见姓漏提） | L2 通道补（LLM 提取无姓氏限制） |
| 性能（每章全文正则） | 正则线性扫描，200 章级文本 <100ms |

## 保留不变

- entity_state 记忆结构与 query_memory 不变；_capture_entities 行为向后兼容
- 新表自动建（Base.metadata.create_all 路径与现有表一致——tests conftest 与 app 启动均建）
