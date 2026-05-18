# Longform Scale Phase 26: 世界模型仪表盘聚合计数

## 目标

世界模型仪表盘只需要展示运营性指标与下一步动作，不应为了几个计数构建完整真相投影。千章项目中，这会把一次仪表盘访问变成全量 anchors/events/facts/catalog 读取。

## 验收标准

1. `/world-model/dashboard` 在已有 profile 时仍返回原有结构。
2. `fact_count` 能通过聚合查询得到当前真相事实数量。
3. 仪表盘请求不再触发对 `world_fact_claims` 的全行投影读取。
4. 原有世界模型 API 测试通过。

## 实施步骤

1. 新增 SQL 捕获测试，先复现 dashboard 加载完整事实行的问题。
2. 将 dashboard 计数改成数据库聚合与轻量计数查询。
3. 跑聚焦测试，再跑全量后端、前端、类型、构建验证。
