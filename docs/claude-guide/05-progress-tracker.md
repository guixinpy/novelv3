# 05 · 进度追踪

> 每次 session 开始先读本文档，结束前更新本文档。只追踪活跃工作；完成的里程碑折叠为一行。

## 当前状态

- **阶段**：L1-L3 通过 / M4 部分完成（37/50 章）/ M5 工具集已验证（30 章多弧线），**正式退出标准未关闭**
- **分支**：`claude/agent-refactor`（2026-08-01 已快进合并到 `main`）
- **最近更新**：2026-08-01（实证审计 + 收尾清理）

## 2026-08-01 实证审计

方法：代码静态检查 + 全量测试复跑（pytest / vitest / vue-tsc）+ 真实会话日志核对（`data/agent_sessions/`，25 个会话）。

结论：

- ✅ **真实完成**：Agent 内核（loop/harness/tooling/guards/budget/compaction/approval）、17 个 @tool、provider 层（原生 function calling + 流式）、M2 旧编排层删除（commit `796cb175`，121 文件 / -27,229 行）、L3 10 章验证、M5 工具集 + 30 章多弧线测试（会话日志佐证）、测试数字属实（后端 586 / 前端 576）。
- ⚠️ **文档虚标/未完成**：M2 清理遗留死代码（本次已清理 61 文件 / -19,789 行）；CADR-004「双轨持久化」DB 轨在 v2 从未实现（本次修订为 JSONL 单轨）；v1 旧生成管线（`ai_service` + 8 个 v1 API）仍存活；M4 50 章、M5 200 章退出标准未执行。

## 已完成

- ✅ 2026-06-11 仓库克隆、工作分支建立、旧 codex-guide 归档、claude-guide 编写
- ✅ 2026-06-11 **M0**：Provider 层 + 目录骨架 + 依赖规则
- ✅ 2026-06-11 **M1**：loop/harness/tooling/budget/tools + /api/v2 + 前端（L1 通过）
- ✅ 2026-07-13 **M1 dogfood**：真实 DeepSeek API，Agent 自主调用 ≥2 工具
- ✅ 2026-07-13 **M2**：审批门 + 写入工具 + 旧编排层删除（121 文件 / -27,229 行，`git grep` 零命中）
- ✅ 2026-07-13 **M3**：guards 五级 + budget refund + compaction + recovery（L3 通过）
- ✅ 2026-07-14 **L3 验证**：10 章 / 32K 字，零护栏触发（会话日志在 `data/agent_sessions/`）
- ✅ 2026-07-14 **L4 狗食**：37 章 / 129K 字（会话日志佐证；未达 50 章标准）
- ✅ 2026-07-14 **M5 基本验证**：plan_arc / check_quality_trend / arc_consolidation + 30 章 / 3 弧线测试（30/30，79,899 字）
- ✅ 2026-07-14 **M5 研究**：hermes-agent + openclaw + openhuman 综合
- ✅ 2026-08-01 **审计收尾**：死代码清理（61 文件 / -19,789 行，前端测试 576→485）；`.trellis` agent-refactor 0.6.11 提交；CADR-004 修订；分支快进合并 `main`

## 成熟度核对

1. ✅ L1: 模型驱动循环 + 流式 + 原生 tool call（实测）
2. ✅ L2: 全流程工具 + 旧编排层删除（实测零命中；注：v1 `ai_service` 旧生成管线仍服务 Athena/手稿，属绞杀迁移保留路径，去留待决策）
3. ✅ L3: 10 章无人值守 + 护栏（实测代码 + 会话日志）
4. 🔶 L4: 37/50 章 —— 50 章退出标准未执行；记忆问答与「第 50 章上下文不含前 40 章原文」验证未做
5. 🔶 L5: M5 工具集 + 30 章验证有效；200 章退出标准未执行

## 下一步

1. **M4 50 章 dogfood**（`scripts/l4_dogfood.py`，API key 已配置）—— 当前最高优先
2. **M5 细化**：质量指标阈值 + 200 章实验设计（任务 `08-01-audit-fix-cleanup` 已有方案草稿）
3. 决策 v1 旧生成管线（`ai_service` + 8 个 API）去留：继续保留 or 逐步迁移到 Agent 工具

## 问题清单

### 已修复

1. ~~故事弧线崩塌~~ → M5 plan_arc（30 章多弧线验证通过）
2. ~~check_quality_trend 列名 bug~~（body→content）
3. ~~approval_pending SSE 事件丢失~~
4. ~~队列背压死锁~~（maxsize=1→64）
5. ~~死代码残留~~ → 2026-08-01 删除 61 文件（writingAgent 面板、chapter_compression/expansion、test_support 残留）

### 待处理（2026-08-01 审计确认）

1. M4 50 章验证未执行（当前 37/50）
2. M5 200 章实验未执行
3. v1 旧生成管线（`ai_service` + 8 个 v1 API）仍存活，需决策去留
4. v2 会话 DB 轨迹未实现 → 已修订 CADR-004 为 JSONL 单轨（不再要求双写）

## 测试基线（2026-08-01 实测）

- 后端：586 passed, 0 failed（pytest 实测）
- 前端：62 files / 485 tests, 0 failed（vitest 实测；死代码清理后 576→485）
- 类型检查：`vue-tsc --noEmit` 通过
- 工具：**17** 个 @tool
- 代码量：backend/app 非测试约 34.5K 行（清理后）
- 会话日志：25 个真实 v2 会话（`data/agent_sessions/`）
