# Phase18: Hermes 推荐后继预览入口

## 背景

Phase12-17 已把推荐后继工具链从 Agent run、后端结果视图、聊天投影和 Drawer 投影打通，但 Hermes 对话入口目前只会在低细节“继续”文本下优先处理可恢复阻塞运行。若上一轮运行成功并产出 `recommended_followups`，用户仍需要理解内部 run id 或进入开发化入口才能继续，这不符合“对话驱动的写作 Agent”目标。

## 参考项目取舍原则

openclaw、hermes-agent、openhuman 中相似能力不做机械照搬。每个模式按以下标准甄别：

1. 是否强化长期写作 Agent 的自主编排，而不是只增加通用 Agent 复杂度。
2. 是否能映射为 novelv3 已有模块的工具化能力，并保留可审计的 run、step、action_result。
3. 是否能用小范围行为测试验证，避免不可控的大重构。
4. 相同能力优先选择更清晰、更可维护、更适合百万字长篇连续性的方案；必要时吸收后再调整。

## 目标

当用户在 Hermes 中输入“继续/继续吧/下一步”等低细节文本时：

1. 若存在可恢复的阻塞/失败 Agent run，继续保持现有恢复预览优先级。
2. 若不存在可恢复运行，但最近的成功 Agent run 产出推荐后继，创建 `dialog_auto_plan` run，预览 `plan_recommended_followups`。
3. assistant 消息保存 `action_result.type = plan_recommended_followups`，前端可复用 Phase16/17 的投影。
4. 不自动执行推荐后继工具；写入型或确认型后继仍遵守现有 confirmation/plan_hash 策略。

## 实施步骤

1. RED：在 `backend/tests/test_dialogs.py` 增加低细节继续触发推荐后继预览的失败测试。
2. GREEN：补一个最新推荐后继 run 选择函数，并在 `backend/app/api/dialogs.py` 增加 `_handle_dialog_recommended_followup_preview`。
3. 验证：先跑目标测试，再跑 dialog 相关 action result/recovery 小集合。

## 非目标

- 不修改推荐后继 planner 的执行确认策略。
- 不新增前端 UI；前端投影已在 Phase16/17 覆盖。
- 不在本阶段改造完整 Agent run routing 架构。
