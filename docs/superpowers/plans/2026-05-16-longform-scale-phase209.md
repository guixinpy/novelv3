# Phase 209 - 提案冲突检测定向查询

## 目标

世界模型提案详情用于审阅候选事实。旧实现遇到非章节级 truth 候选项时，会构建完整 `current_truth` projection，再从中查找 subject/predicate 是否冲突。长篇项目事实量持续增长后，打开单个提案详情不应触发完整真相投影。

## 变更

- `_detect_item_conflicts()` 不再为非章节 truth 候选项构建完整 projection。
- 新增 `_find_current_truth_claim_value()`，按当前 bundle 的 profile scope、`subject_ref`、`predicate` 定向查询当前候选事实，只投影 `id` 与 `object_ref_or_value`。
- 冲突结果直接使用定向查询返回的 claim id，避免二次全局查找。

## 测试

- RED：`test_proposal_detail_skips_full_projection_for_targeted_truth_conflicts` 先将完整 projection 调用替换为失败函数，旧实现会失败。
- GREEN：定向查询实现后，该测试通过，并仍返回正确 `truth_conflict`。
- 回归：世界模型前端 API、提案服务、世界 profile 测试通过。

## 后续验证

- 已运行：`backend\.venv\Scripts\python.exe -m pytest backend/tests/test_world_frontend_api.py backend/tests/test_world_proposals.py backend/tests/test_world_profiles.py -q`
- 结果：`118 passed`
