# Phase 4: Memory Provenance Projection

## 背景

本阶段继续把 novelv3 从页面工具集合改造成 Agent-native 写作系统。前 3 个阶段已补齐 run loop contract、工具输入验证和循环风险诊断；下一步需要让 Agent 在召回知识库/长期记忆时知道“信息来自哪里、是否被截断、是否可作为世界真相使用”。

本阶段主要吸收 `openhuman` 的 memory citation / provenance 思路，同时保留 novelv3 的领域边界：知识库保存作者偏好、项目策略、学习规则、参考模式和候选写作经验；Athena/世界模型才保存小说内部事实。

## 范围

本阶段只处理 `inspect_agent_knowledge_base_route` 的只读输出投影：

1. 新增统一 `memory_provenance` 字段。
2. 汇总已返回的来源：`Project.style_config`、`Project`、`PromptRule(rule_type=learned)`、`Project.style_config.knowledge_base_candidates`、`FewShotExampleLibrary`。
3. 暴露窗口限制与截断信息，方便 Agent 判断是否需要更多召回。
4. 明确 world-truth boundary：知识库可影响写作风格和策略，但不能直接当作世界事实。

不在本阶段做：

- 不改数据库结构。
- 不改召回排序。
- 不接入新向量检索。
- 不把知识库和世界模型合并。

## 验证

- T0/T1：新增 `backend/tests/test_writing_agent_knowledge_base_route.py` 用例，先确认缺少 `memory_provenance` 时失败，再实现通过。
- T1：运行知识库 route 相关测试。
- 暂不跑完整前后端验证；本阶段是只读投影小改动。

## 成功标准

- 稀疏项目和配置项目都返回 `memory_provenance`。
- 配置项目能列出实际来源和 item counts。
- 截断 learned rules 时，`memory_provenance.windows` 能暴露 limit、total、returned、has_more。
- `memory_provenance.boundaries.world_truth` 明确知识库不是世界模型事实源。
