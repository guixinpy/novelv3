# 05 · 进度追踪

> 每次 session 开始先读本文档，结束前更新本文档。只追踪活跃工作；完成的里程碑折叠为一行。

## 当前状态

- **阶段**：M4 基础完成（工具就绪，嵌入 fallback 已接入）
- **分支**：`claude/agent-refactor`
- **最近更新**：2026-07-14

## 已完成

- ✅ 2026-06-11 仓库克隆、工作分支建立、旧 codex-guide 归档、claude-guide 编写
- ✅ 2026-06-11 **M0 完成**：Provider 层 + 目录骨架 + 依赖规则
- ✅ 2026-06-11 **M1 代码完成**：loop/harness/tooling/budget/tools + /api/v2 + 前端
- ✅ 2026-07-13 **M1 dogfood 验证通过**：真实 DeepSeek API，Agent 自主调用 ≥2 工具
- ✅ 2026-07-13 **M2 Phase A**：审批门 + 5 写入工具 + 前端审批 UI
- ✅ 2026-07-13 **M2 Phase B**：删除 adapter-descriptor 层 (-12K LOC)
- ✅ 2026-07-13 **M2 测试清理**：删除 45+ 旧测试文件
- ✅ 2026-07-13 **M3 guards**：guards.py (5 级风险检测) + 预算 refund + 上下文压缩
- ✅ 2026-07-13 **M3 remainder**：check_chapter_quality 工具 + 风险→恢复注入
- ✅ 2026-07-14 **M4 memory**：track_plotline / query_memory 工具 + 实体自动捕获
- ✅ 2026-07-14 **v1 清理**：删除 dialogs 路由注册, intent_router.py, writing_agent_runs
- ✅ 2026-07-14 **前端重构**：AgentV2View 升级为主页, 设计系统统一, 死代码清理
- ✅ 2026-07-14 **综合审计**：10 轮自检, 修复 15+ 关键问题

## M1-M3 退出标准核对

1. ✅ 真实对话 ≥2 工具调用（M1 dogfood）
2. ✅ 中断/恢复：JSONL 重建会话
3. ✅ 内核单测全绿
4. ✅ 全流程「新建项目→设定→大纲→第1章→修订」
5. 🔶 L3 无人值守 10 章验证（脚本就绪，未完整运行）

## 下一步

1. L3 无人值守 10 章验证（运行 `.trellis/tasks/archive/.../l3_unattended.py`）
2. 剩余 writing_agent/ 死文件清理（~15 个文件）
3. M5 百万字专业化规划

## 问题清单

（空）

## 测试基线

- 后端：730 passed, 0 failed
- 前端：91 suites, 576 tests, 0 failed
- 工具：12 个 @tool 全部注册可用
