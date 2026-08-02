# P1 弧线规划结构性校验 · 技术设计

## 改动点（3 处，全部结构性、向后兼容）

### D1. plan_arc define：relation_to_previous（tools/memory.py）

- 签名加 `relation_to_previous: str = ""`（可选）；schema 同步
- 接续检测：查询上一弧线（story_arc 按 start_chapter 排序，取 end_chapter 小于当前 start 的最近一条）：
  `is_continuation = prev_arc is not None and start_chapter <= prev_arc.end_chapter + 2`
- is_continuation 且未传 → 返回体附 `continuation_hint` 提示（**不拒绝**，弧线照常创建）
- 传入 → metadata.arc_relation = relation_to_previous（合并写入，不动 endgame/provenance）

### D2. plan_arc progress：收束约束可见性（tools/memory.py）

- progress 返回体：active arc metadata 无 endgame 键 → 附
  `endgame_hint: "本卷未设置收束约束（define 可补 must_resolve 与收束章），长卷易出现开线不收束"`

### D3. T3 措辞泛化（tools/memory.py + tools/chapters.py）

- memory.py progress 的 endgame_warning：`禁止新增「更早/更深/更初」层级` →
  `接近收束章，请优先回收开放线索，暂缓开新线`
- chapters.py check_quality_trend 的 endgame_advice：同措辞替换

## 兼容性

- relation_to_previous 可选：不传行为不变（仅接续时多一条提示文本）
- endgame_hint 是新增字段：不影响既有断言（除 T3 措辞断言需更新）
- 无 schema/表变更

## 测试

- test_tools_memory.py：relation 记录/接续提示/非接续不提示/无 endgame 提示
- test_tools_quality.py：措辞断言更新
- 既有 plan_arc 测试全绿（不传新参数）
