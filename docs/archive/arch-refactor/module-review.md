# 归档模块多视角评审结论（2026-08-02）

评审对象：module-inventory.md 的 A-I 九组（arch-refactor 后新架构不包含的模块）。
评审方式：4 视角子代理并行（创作价值 / 读者成品 / 工程维护 / 成本收益，依据六项工程不变量原则）。

## 综合结论

| 组 | 创作 | 读者 | 工程 | 成本收益 | **综合裁决** |
|---|---|---|---|---|---|
| A 世界提案 | 高 | 高 | 中 | 低 | **不恢复官僚层；瘦身事实账本 P2 待定**（事件级一致性缺口实证时） |
| B 自优化 | 低 | 中 | 无 | 负 | **永久放弃**（内容特化教科书样本） |
| C 评审/修订链 | 高 | 高 | 中 | 中 | **连续性检测纯函数重建 P1**（术语配置化）；修订链走方案 B（人工标注） |
| D 上下文装配 | 中-高 | 高 | 中低 | 中 | **接线缺口 P1**（已存在的检索块接入 pipeline）；json_utils/prompt_optimizer 迁入 |
| E athena 辅助 | 中 | 中 | 低 | 中 | **L2 提取通道重建 P1**（一致性#1 空洞）；athena_setup_terms 迁入 |
| F 杂项 | 低-无 | 低 | 无-低 | 低 | **不恢复**（被新 core 逐一替代） |
| G 模型层 | 依附 | 低-中 | 低 | 负 | **不恢复**；versions 章节回滚按需重建（P2 待定） |
| H 记忆辅助 | 中 | 中 | 无 | 中 | **narrative_plan_window 瘦身重挂 P1**（未来大纲窗口） |
| I 脚本 | 无 | 无 | 无-低 | 负 | **清理**：10 个存留旧实验脚本删除/收敛，2 个断链移除 |

## P1 推荐清单（值得做，低风险纯函数/小件）

1. **check_quality_trend 字数趋势检测**（清单外发现）——六不变量「节奏管理#4」唯一缺失对应物，~30 行题材无关，成本极小。可恢复于 `git show 474a8f8c^:backend/app/tools/chapters.py:441`
2. **C 组连续性检测纯函数重建**——时间线/编号/关系锚点冲突检测（不依赖 world 表的部分），**术语必须配置化**（旧实现硬编码本书剧情：林深/顾衍/雾灾）
3. **D 组接线**：`build_chapter_retrieval_context`（domain/retrieval/athena_retrieval.py:470 已存在）接入 pipeline._plan
4. **E 组 L2 提取通道**——LLM 事实提取（l2_extractor 提示词题材无关可直接复用），喂实体/记忆
5. **json_utils.parse_json_safely / prompt_optimizer 迁入**（41+52 行小纯函数）
6. **H 组 narrative_plan_window 瘦身重挂**——未来章节大纲窗口（写作前方规划视野）
7. **athena_setup_terms 迁入**（全组唯一真纯函数模块，引号/非引号术语提取）
8. **I 组脚本清理**——l3/l4/m5 系列 10 个旧脚本（全部指向已删端点）删除或收敛为 1 个网络级回归

## P2 待定（条件触发）

- A 组瘦身事实账本（world_replay/projection 确定性账本内核 ~500 行）——事件级一致性缺口实证时
- C 组无词表 LLM 评审——长程实证需要时
- versions 章节回滚——前端重写需要时按新模型重建
- F 组 dialog/拓扑——前端定盘时

## 永久放弃（不恢复）

- B 组（learned PromptRule）、G 组（16 模型）、F 组（基础设施件）、I 组（旧验证脚本）
- A 组提案官僚层（提案→评审队列→决议）+ GenreProfile 题材档案
- C/D/E 全部特化词表与世界耦合件（雾安局/记忆雾晶/N-07/苏晚晴 等硬编码）
- 修订链原样恢复（走方案 B：人工标注→新 API→pipeline revise）
- TimelineChecker（核心判定是 stub，无物可恢复）

## 关键原则落实

- **六项工程不变量**：只恢复题材无关的工程不变量（连续性检测/节奏趋势/提取通道），词表式/题材档案式实现永久放弃
- **前端重写是总闸门**：A 组、dialog/拓扑、versions 的恢复全部排在前端重写之后
- **已被覆盖的零恢复**：压缩投影（compaction 更优）、event_bus（core/events）、故事线（LongformMemory）、上下文注入（快照+检索工具）

## 各视角报告存档

- 创作视角：teammate review-creation（重点：A 组世界真相账本是最大真缺口，C 组连续性评审纯文本部分可独立重建）
- 读者视角：teammate review-reader（重点：对应网文弃书三大主因——硬伤/世界观崩坏/悬念管理）
- 工程视角：teammate review-engineering（重点：旧代码=DB 服务层形态，恢复需重写接口层；术语配置化是通用化前提）
- 成本收益视角：teammate review-value（重点：P0 无必须恢复项；特化风险专项；清单外发现 check_quality_trend）
