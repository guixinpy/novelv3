# Longform Scale Phase 28: 运行中动作检测去全量消息扫描

## 目标

命令进入运行中保护逻辑时，只需要判断最近是否存在未完成的动作结果。当前 `_latest_unfinished_action_type` 会读取整个对话消息历史；长期创作对话增长后，这会让一次命令检查跟历史长度绑定。

## 验收标准

1. 未完成动作检测仍能返回最近运行中的动作类型。
2. 查询只扫描带 `action_result` 的消息，不读取全部普通消息。
3. 对话 API 测试通过。

## 实施步骤

1. 新增 SQL 捕获测试，复现全量消息读取。
2. 为 `_latest_unfinished_action_type` 增加 `action_result IS NOT NULL` 过滤。
3. 跑聚焦测试、对话测试和全量验证。
