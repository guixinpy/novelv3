# M3 · 自治护栏

## Goal

把上一版 dogfood 换来的护栏在新循环内重建，达到无人值守可信。

## 范围

| 组件 | 描述 | 优先 |
|------|------|------|
| guards.py | 五级循环风险检测 + 熔断 | P0 |
| budget refund | 只读读取不消耗创作迭代额度 | P0 |
| context compression | 75% 阈值预检 + 头尾保护压缩 | P1 |
| check_chapter_quality | 章节长度/与大纲偏离自检工具 | P1 |
| risk→stop→diagnose→recover | 风险触发时输出诊断+恢复建议 | P1 |
| batch mode | follow-up 队列 + 护栏检查点 | P2 |

## 验收标准

- [ ] 五级检测覆盖：generic_repeat / ping_pong / poll_no_progress / unknown_tool_repeat / 全局熔断
- [ ] 只读工具（permission=read）不消耗迭代预算（refund）
- [ ] 人为构造的乒乓场景在 ≤5 个回合内熔断
- [ ] 上下文用量达到 75% 时触发预检事件
- [ ] `check_chapter_quality` 工具注册并返回有意义的质检报告
- [ ] 熔断时产出诊断事件 + follow-up 恢复建议
- [ ] 批量模式（连续 follow-up 写作）在 GPT 级别可验证
- [ ] 现有 75 agent 测试 + 910 后端测试全绿
