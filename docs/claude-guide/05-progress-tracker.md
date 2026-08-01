# 05 · 进度追踪

> 每次 session 开始先读本文档，结束前更新本文档。只追踪活跃工作；完成的里程碑折叠为一行。

## 当前状态

- **阶段**：**L1-L5 全部通过**（M5 200 章实验 PASS）
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
- ✅ 2026-08-01 **M4 50 章验证通过**：项目 `3064415b`（悬疑/50 章/70K 字），零护栏触发、零一致性错误、65 条情节线、记忆召回 3/3 PASS（`scripts/l4_dogfood.py`，含 4 次续跑与 6 个真实 bug 修复，见问题清单）
- ✅ 2026-08-01 **M5 200 章实验通过**：项目 `5e2eccbe`（悬疑/201 章/284.6K 字），零护栏触发、零一致性错误、137 条情节线、30 次上下文压缩、字数趋势无持续恶化（窗口均值 1081-2174，无连续 3 窗口下滑）、记忆召回 PASS、tokens 输入 82.6M/输出 0.79M

## 成熟度核对

1. ✅ L1: 模型驱动循环 + 流式 + 原生 tool call（实测）
2. ✅ L2: 全流程工具 + 旧编排层删除（实测零命中；注：v1 `ai_service` 旧生成管线仍服务 Athena/手稿，属绞杀迁移保留路径，去留待决策）
3. ✅ L3: 10 章无人值守 + 护栏（实测代码 + 会话日志）
4. ✅ L4: 50 章 dogfood + 记忆召回 3/3；上下文排除通过多会话续跑 + 压缩快照实现（单会话 268→43 条压缩记录）
5. ✅ L5: 200 章长程实验通过（故事第 100 章自然完结后以「第二部」模式续写至 200 章，模型拒绝注水的规范行为被证实有效）

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

### 2026-08-01 M4 验证中修复的真实 bug

1. ~~compaction 未接线~~ → harness 75% 阈值自动压缩 + 日志检查点 + 断点重放（`f3739a53`）
2. ~~工具异常毒化请求~~ → 工具执行失败自动 rollback session（`4db43cf0`）
3. ~~plan_arc 重复 define 唯一约束冲突~~ → upsert（`4db43cf0`）
4. ~~项目状态卡在 draft~~ → write_chapter 推进 writing/content（`30ca96a0`）
5. ~~query_world 看不到 update_setup 设定~~ → 回退 Setups 表（`005a363a`）
6. ~~压缩拆散 tool 消息配对 → DeepSeek 400~~ → 压缩后清洗孤立 tool 消息（`bf8f5929`）
7. ~~entity_state 记忆永远为空~~ → _capture_entities 纳入 Setups 角色 + 50 章回填（`ec23184a`）

### 待处理（2026-08-01 审计确认）

1. ~~M4 50 章验证未执行~~ → 2026-08-01 通过
2. ~~M5 200 章实验未执行~~ → 2026-08-01 通过（报告：`C:\tmp\dogfood_reports\5e2eccbe-*`）
3. v1 旧生成管线（`ai_service` + 8 个 v1 API）仍存活，需决策去留
4. v2 会话 DB 轨迹未实现 → 已修订 CADR-004 为 JSONL 单轨（不再要求双写）
5. Setups.characters 实体登记不完整（50 章项目仅 1 个角色入档）→ 实体来源需扩展（track_plotline/正文提取）

### 2026-08-01 M5 200 章实验中新增修复

1. ~~审批门未知工具 KeyError 崩掉 SSE~~ → 返回友好错误 + 可用工具清单（`c696bf27`）
2. ~~压缩摘要嵌套旧摘要/丢失写作信息~~ → 跳过旧摘要 + 纳入最近写入/质量（`3da0f933`）
3. ~~track_plotline 闭环后重开唯一约束冲突~~ → 复用行 reopen（`0e7bb3de`）
4. ~~200 章目标与故事自然完结冲突~~ → 「第二部」实验模式（`ac598c93`）

## 下一步（2026-08-01 更新）

1. **harness 系统化优化**（任务 `08-01-audit-fix-cleanup` 的 `harness-engineering-list.md`）：
   参考已更新的 hermes-agent / openclaw / openhuman 最新源码（`docs/references/`），
   优先：容错兜底、幻觉治理、上下文状态快照、恢复闭环、可观测性
2. 决策 v1 旧生成管线（`ai_service` + 8 个 API）去留
3. 扩展实体登记来源（Setups 角色不完整 → 正文/情节线提取）

## 测试基线（2026-08-01 实测）

- 后端：586 passed, 0 failed（pytest 实测）
- 前端：62 files / 485 tests, 0 failed（vitest 实测；死代码清理后 576→485）
- 类型检查：`vue-tsc --noEmit` 通过
- 工具：**17** 个 @tool
- 代码量：backend/app 非测试约 34.5K 行（清理后）
- 会话日志：25 个真实 v2 会话（`data/agent_sessions/`）
