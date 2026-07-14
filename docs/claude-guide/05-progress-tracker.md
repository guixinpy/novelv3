# 05 · 进度追踪

> 每次 session 开始先读本文档，结束前更新本文档。只追踪活跃工作；完成的里程碑折叠为一行。

## 当前状态

- **阶段**：L3 通过 / L4 部分完成 / M5 基本验证（弧线系统消除崩塌）
- **分支**：`claude/agent-refactor`
- **最近更新**：2026-07-14

## 已完成

- ✅ 2026-06-11 仓库克隆、工作分支建立、旧 codex-guide 归档、claude-guide 编写
- ✅ 2026-06-11 **M0**：Provider 层 + 目录骨架 + 依赖规则
- ✅ 2026-06-11 **M1 代码**：loop/harness/tooling/budget/tools + /api/v2 + 前端
- ✅ 2026-07-13 **M1 dogfood**：真实 DeepSeek API，Agent 自主调用 ≥2 工具
- ✅ 2026-07-13 **M2**：审批门 + 写入工具 + 旧层删除 + 测试清理
- ✅ 2026-07-13 **M3**：guards.py + budget refund + compaction + recovery injection
- ✅ 2026-07-14 **M2 完全关闭**：删除 writing_agent/ 58 files/21K LOC，LOC -60.3%
- ✅ 2026-07-14 **L3 验证通过**：10章/32K字，零护栏触发，零人工干预
- ✅ 2026-07-14 **L4 狗食**：37章/129K字，发现弧线崩塌问题（→M5）
- ✅ 2026-07-14 **M5 基本验证**：plan_arc + check_quality_trend + 弧线记忆巩固 → 10章质量稳定，零填充
- ✅ 2026-07-14 **M5 研究**：hermes-agent (Frozen Snapshot/Compaction) + openclaw (Dreaming System)

## 成熟度核对

1. ✅ L1: 模型驱动循环 + 流式 + 原生 tool call
2. ✅ L2: 全流程工具 + 旧编排层删除 + `git grep` 零命中
3. ✅ L3: 10章无人值守 + 护栏验证通过
4. 🔶 L4: 37章/129K字完成，弧线崩塌问题已识别（→M5修复）
5. 🔶 L5: M5 工具集（plan_arc/quality_trend/arc_consolidation）已验证有效，需更大规模测试

## 下一步

1. 更大规模 M5 测试（30+ 章，多弧线过渡）
2. 前端适配新工具（plan_arc/check_quality_trend 可视化）
3. openhuman 参考项目分析（agents 仍在运行）

## 问题清单

### L4 狗食发现（→M5 已验证修复）
1. ~~故事弧线崩塌~~ → M5 plan_arc 消除此问题
2. ~~缺乏卷级规划~~ → M5 plan_arc + 系统提示词解决
3. ~~质量趋势不可见~~ → M5 check_quality_trend 解决
4. ~~记忆系统基本可用~~ → M5 弧线记忆巩固增强

### 新发现（M5 测试）
1. check_quality_trend 列名 bug 已修复（body→content）
2. approval_pending SSE 事件丢失 bug 已修复
3. 队列背压死锁 bug 已修复（maxsize=1→64）

## 测试基线

- 后端：586 passed, 0 failed
- 前端：未变
- 工具：**15** 个 @tool（+ plan_arc, check_quality_trend, arc_consolidation）
- 代码量：33,649 LOC (-60.3% vs 重构前)
- 修复的关键 Bug：3 个（approval_pending 事件 + 队列死锁 + 列名错误）
