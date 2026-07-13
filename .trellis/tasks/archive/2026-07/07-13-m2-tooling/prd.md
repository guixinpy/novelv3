# M2 · 全能力工具化 + 旧编排层删除

## Goal

将 novelv3 从「确定性工作流编排」翻转为「模型驱动的工具调用 Agent」——新增写入类工具、接入审批门，然后删除整个旧编排层（~10K LOC）。

## 新增内容

1. **写入类工具**（app/tools/，@tool 模式）：
   - 「write_chapter」— 创建/更新章节正文
   - 「revise_chapter」— 按修订指令修改章节
   - 「propose_world_change」— 提出世界观变更
   - 「update_outline」— 更新大纲
   - 「update_setup」— 更新作品设定

2. **审批门**（agent/approval.py）：
   - write/permission=write 的工具在模型侧请求后，先进入 pending 状态
   - 通过 SSE 事件 `approval_pending` 通知前端
   - 用户审批通过后继续执行；拒绝则返回模型重做

3. **前端审批 UI**：
   - 在 v2 对话流中展示 pending approval 卡片
   - 审批/拒绝按钮，结果回传后端

## 删除内容（按依赖顺序）

| 批次 | 目标 | LOC | 条件 |
|------|------|-----|------|
| A | 描述符-适配器层（27 文件） | ~8,396 | 写入类工具上线后，无外部消费者 |
| B | 生成执行管线（4 文件） | ~1,005 | 功能已被写入工具覆盖 |
| C | slash_command_route | ~890 | 适配器层删除后自动脱离 |
| D | 关联测试文件 | ~2,000+ | 对应生产代码删除后 |

**独立保留**（需 v1 API 完全下线后才删除）：
- intent_router（2,400 行）— 被 dialogs.py API 直接依赖
- planner（6 文件，2,643 行）— 同上
- run_service（2,015 行）— 同上
- dialogs.py（1,912 行）— v1 对话 API 端点

## 验收标准

- [ ] 对话完成全流程：「新建项目→生成设定→生成大纲→写第 1 章→按我的意见修订」，全程无旧编排层参与
- [ ] `git grep -E "intent_router|run_service|tool_descriptors" — backend/app/` 零命中（仅保留 `intent_router` 在删除前）
- [ ] 后端 LOC 较重构前下降 ≥15%（预期 27K → ≤23K，第一阶段删除 4K+）
- [ ] 写入工具单测覆盖：成功写入、参数验证、错误回填
- [ ] 审批门单测：pending → approve → execute / pending → reject → notify
- [ ] 前端 build + 单测全绿
- [ ] 现有只读工具回归测试全绿
