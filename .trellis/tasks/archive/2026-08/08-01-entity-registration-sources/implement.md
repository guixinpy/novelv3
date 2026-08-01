# P1 实体登记来源扩展 · 执行计划

## 阶段 1：模型 + entity_miner 核心

- [ ] `app/models/entity_candidate.py`（EntityCandidate + 唯一约束）+ models/__init__ 注册
- [ ] `core/entity_miner.py`：`_COMMON_SURNAMES`（~300）+ `mine_entities_from_text` + 停止词过滤
      + `register_entity_candidates(db, project_id, chapter_index, names, source)`
- [ ] 测试 `test_entity_miner.py`：
      - 提取：含 程砚秋/苏晚晴/顾沉舟 的文本提取出这三名
      - 停止词过滤：「我觉得」「王顾左右」类不误报
      - upsert：跨章 count+1、同章不重复、source 标记
- [ ] 验证门：`python -m pytest tests/test_entity_miner.py -q`

## 阶段 2：接入 _capture_entities（rule 通道）

- [ ] `tools/chapters.py` write_chapter/revise_chapter：正文后调用 mine+register(source="rule")
- [ ] `_capture_entities`：白名单合并转正候选（chapter_count≥2）
- [ ] 测试：写 2 章含新角色「欧阳雪」→ entity_state 出现欧阳雪（新增用例，test_tools_write.py）

## 阶段 3：L2 注入

- [ ] `background_analyzer.deep_check`：extracted_facts 循环中 subject/object → register(source="l2")
- [ ] 测试：deep_check（mock LLM）后候选表含 subject/object 且 source=l2

## 阶段 4：200 章数据验证 + 收尾

- [ ] 用 `data/exports/M5-200章-201章.md` 抽样（ch1-10/ch31-40/ch101-110）跑 mine_entities_from_text，
      统计主要角色命中率（程砚秋/苏晚晴/顾沉舟/姚先生/陆四海/程叔夜/婆婆/蓑衣老汉…）
- [ ] 后端全量 pytest + 前端 vitest 无回归
- [ ] progress-tracker 记录；独立 commit ×2-3

## 回滚点

- 阶段 1 完成即安全点（新表 + 新模块，无行为变化）
- 阶段 2/3 接入后全量测试绿才继续
