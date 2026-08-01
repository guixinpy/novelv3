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

## 2026-08-01 harness 系统化优化（任务 `08-01-harness-optimization`，T1-T7 全部完成）

对 200 章实验暴露问题做系统化治理，7 个子任务独立 commit（`40a71a8a`→`7567e7af`）：

| 子任务 | 内容 | 验证 |
|---|---|---|
| T1 内核健壮性 | before_tool_call 钩子异常 fail-closed 兜底；回合内工具错误自动注入「错误诊断+建议」；guard 触发立即结束回合（修复只 break 工具批的缺陷）；压缩重放测试矩阵 | 8 测试 |
| T2 工具可靠性 | 参数校验错误附「参数示例」few-shot；`get_or_create_longform_memory` 统一 upsert（5 处接入）；plotline 标题规范（>40 字/含章号拒绝 + 命名模板）；query 前缀/模糊匹配 + 未命中回退最近开放线 | 11 测试 |
| T3 终局与伏笔约束 | plan_arc define `must_resolve` 终局约束（metadata.endgame）；progress/check_quality_trend 卷尾 ≤5 章强制回收模式（禁止新增「更早/更深/更初」层级）；plotline 开放 >30 章 stale 提醒 | 7 测试 |
| T4 输出格式守门员 | `check_chapter_format`：markdown `**` 残留/中文斜杠备选词/正文章题行/全角引号成对/半角标点 + 章末卡点（无钩子句式）；quality fail→重写 | 13 测试 |
| T5 结构级重复检测 | `check_structure_repeat`：标题重复 + 结尾主题词指纹成团 ≥3 章 → 模板循环告警（换名城检测） | 6 测试 |
| T6 上下文注入工程 | 回合级项目状态快照（章节/最近3章/活跃弧线/开放伏笔/事实表角色地点/格式规范，回调注入不持久化，CADR-005 合规）；压缩摘要追加「最近写作上下文」；query_memory 人物卡 author_explicit 优先 | 6 测试 |
| T7 可观测性 | analyze_dogfood.py 补：幻觉工具名统计/未知工具频率/每章质量自检/压缩摘要质量（200 章实测：201 章质量覆盖、30 次压缩中 24 次保留写作上下文、平均节省 74.5%） | 实测 |

测试基线（2026-08-01 harness 优化完成后实测）：
- 后端：**647** passed（596 → 647，+51 新增测试）
- 前端：62 files / 485 tests, 0 failed（vitest 实测）
- 类型检查：`vue-tsc --noEmit` 通过
- 架构规则：test_dependency_rules 通过（内核无领域依赖）
- 工具：**19** 个 @tool（+check_chapter_format / check_structure_repeat）
- 会话回放：20 个 200 章会话 JSONL 在改造后内核下加载全部成功

遗留（未纳入本次范围）：
- 两级压缩 LLM 摘要版（预算允许时，hermes Frozen Snapshot 模式）→ P2 候选
- 结构相似度主题词表需随新实验补充
- 实体登记来源、第二部结构策略 → P1 待决策（v1 管线去留已决：全面绞杀完成）

## 2026-08-01 v1 生成管线全面绞杀（任务 `08-01-v1-pipeline-removal`，用户选 C 方案）

统一 LLM 调用路径到 v2 provider，删除 v1 旧管线（阶段 1 迁移 → 阶段 2 删除 → 阶段 3 清理）：

- **统一路径**：`Provider.complete()`（base.py 已有）+ `app/agent/providers/__init__.py::build_provider` 工厂；
  athena 聊天（dialog_utils）、一致性 L2（l2_extractor，提示词内联）、章节修订/v2 动作
  （chapters.create_or_replace_chapter）全部迁移，token 统计改用 `ProviderResponse.usage` 契约
- **删除**（-2,399 行）：`core/ai_service.py`、`core/deepseek_adapter.py`、`core/chat_compaction.py`；
  4 个死生成端点（outlines generate/expand-window、setups generate、storylines generate）；
  `prompting/providers/{outline,setup,storyline,project}.py`（活跃符号迁 core：
  SetupContextSnapshot/TRUNCATED_SETUP_CONTEXT_MARKER → `core/setup_context`、
  parse_json_safely/normalise_json_text → `core/json_utils`、
  project_chapter_word_range → `core/chapter_utils`、build_command_args_block → assembler）
- **保留**：prompting 装配核心（assembler/registry/renderer/budgeter）+ dialog/chapter 生成链
  （活跃功能依赖，删双套 HTTP 客户端即达目的）；chapters.generate 端点（已走 v2 agent tool）；全部 CRUD
- **测试**：+1（provider.complete）；-29（生成端点/迁移历史/adapter 清理用例）；CRUD 用例保留
- 测试基线（v1 绞杀后实测）：后端 **620 passed**、前端 485 tests、vue-tsc 通过、
  会话回放 20/20 成功、依赖规则测试通过
