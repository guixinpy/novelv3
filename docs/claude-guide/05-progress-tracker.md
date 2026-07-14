# 05 · 进度追踪

> 每次 session 开始先读本文档，结束前更新本文档。只追踪活跃工作；完成的里程碑折叠为一行。

## 当前状态

- **阶段**：M2 完全关闭 — L3/L4 验证脚本就绪 — M5 蓝图完成
- **分支**：`claude/agent-refactor`
- **最近更新**：2026-07-14

## 已完成

- ✅ 2026-06-11 仓库克隆、工作分支建立、旧 codex-guide 归档、claude-guide 编写
- ✅ 2026-06-11 **M0 完成**：Provider 层 + 目录骨架 + 依赖规则
- ✅ 2026-06-11 **M1 代码完成**：loop/harness/tooling/budget/tools + /api/v2 + 前端
- ✅ 2026-07-13 **M1 dogfood 验证通过**：真实 DeepSeek API，Agent 自主调用 ≥2 工具
- ✅ 2026-07-13 **M2 Phase A**：审批门 + 5 写入工具 + 前端审批 UI
- ✅ 2026-07-13 **M2 Phase B**：删除 adapter-descriptor 层
- ✅ 2026-07-13 **M2 测试清理**：删除 45+ 旧测试文件
- ✅ 2026-07-13 **M3 guards**：guards.py (5 级风险检测) + 预算 refund + 上下文压缩
- ✅ 2026-07-13 **M3 remainder**：check_chapter_quality + 风险→恢复注入
- ✅ 2026-07-14 **M4 memory**：track_plotline / query_memory + 实体自动捕获
- ✅ 2026-07-14 **M2 完全关闭**：删除 services/writing_agent/ (58 files / 21,702 LOC)，LOC 84,664→33,649 (-60.3%)，git grep 零命中
- ✅ 2026-07-14 **L3 验证脚本**：scripts/l3_verify.py（无人值守 10 章 + 熔断测试）
- ✅ 2026-07-14 **L4 验证脚本**：scripts/l4_dogfood.py（50 章一致性 + 记忆召回测试）
- ✅ 2026-07-14 **M5 蓝图**：百万字专业化方向性规划

## M1-M4 退出标准核对

1. ✅ 真实对话 ≥2 工具调用（M1）
2. ✅ 中断/恢复：JSONL 重建会话（M1）
3. ✅ 内核单测全绿（M1）
4. ✅ 全流程「设定→大纲→第1章→修订」（M2）
5. ✅ `git grep intent_router|run_service|tool_descriptor` 零命中（M2）
6. ✅ L3 无人值守 10 章（2026-07-14 验证通过：10章/32,421字，零护栏触发）
7. 🔶 L4 50 章一致性（37章/129,809字完成，但Ch18后故事弧线崩塌→填充内容，这是M5要解决的核心问题）

## 下一步

1. 启动后端，运行 `python scripts/l3_verify.py --project-id <ID>`（L3 验证）
2. 运行 `python scripts/l4_dogfood.py --project-id <ID>`（L4 验证）
3. 基于 L4 狗食发现细化 M5 蓝图，启动实现

## 问题清单

### L4 狗食发现（2026-07-14）
1. **故事弧线崩塌**：Ch1-18 质量稳定（1,341→5,808字），Ch19 起变为尾声+番外填充（逐章缩至 205 字）
2. **缺乏卷级规划**：Agent 不知有 50 章目标，主线自然完结后无法开启下一弧线
3. **质量趋势不可见**：Agent 不自知章节在缩水，无自我纠正机制
4. **记忆系统基本可用**：每章正常调用 query_memory + track_plotline，无人物硬性漂移

## 测试基线

- 后端：586 passed, 0 failed
- 前端：91 suites, 576 tests, 0 failed
- 工具：12 个 @tool 全部注册可用
- 代码量：33,649 LOC (-60.3% vs 重构前)
