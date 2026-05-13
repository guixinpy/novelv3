# Longform Scale Phase 27: 对话压缩消息选择器去全量加载

## 目标

Hermes `/compact` 只需要压缩最后一条 summary 之后的 plain 消息。当前选择器先加载整个对话历史，再在 Python 中寻找最后 summary；对百万字项目的长期对话会产生不必要的内存与查询成本。

## 验收标准

1. 仍然只压缩最后 summary 之后的 plain 消息。
2. 选择器不再发出无 `message_type` 约束的全量 `dialog_messages` 查询。
3. 原有对话压缩测试通过。

## 实施步骤

1. 新增 SQL 捕获回归测试，先证明当前实现会全量加载对话消息。
2. 改为先查询最后一条 summary 的排序边界，再只查询边界之后的 plain 消息。
3. 跑聚焦测试和全量验证。
