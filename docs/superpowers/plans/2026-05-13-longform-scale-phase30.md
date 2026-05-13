# Longform Scale Phase 30: 对话消息复合游标分页

## 目标

对话消息轮询使用 `after_id` 获取增量。当前服务只用 `created_at > cursor.created_at` 判断新消息；如果多条消息拥有相同时间戳，会漏掉同时间但排序更靠后的消息。

## 验收标准

1. `after_id` 使用 `(created_at, id)` 复合游标。
2. 默认最新页和 limit 页仍按时间升序返回。
3. 对话消息分页测试和全量验证通过。
