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
- 两级压缩 LLM 摘要版：多视角评审（创作/工程/成本收益）结论为**现阶段不做**——T6 状态快照/
  事实表/人物卡已外置覆盖「压缩丢人物关系」，LLM 摘要纯增量且违反「压缩路径无失败点」；
  未来若实测出现 T6 覆盖不到的动态缺口，以「补充段 + 失败静默降级」条件性引入

## 2026-08-02 T5 弱化 + 两级压缩评审（多视角机制第二次应用）

- **T5 弱化**（`70a13148`）：主题词指纹是 200 章单本书补丁（题材特化）；「结构重复」本身非普适
  （单元剧/日常文允许）；A 方案（内容无关结构特征）被工程视角证伪（换名城是语义节拍重复非句法异常）。
  移除指纹检测（-30 行），仅保留标题重复检测（唯一普适不变量）
- **两级压缩**：3 视角（创作条件性/工程条件性/成本收益不值得）→ 不做，理由见上
- 验证：后端 590 passed

## 2026-08-02 stub 生成端点体系清理（任务 `08-02-stub-generation-removal`，四视角评审一致推荐 C）

多视角评审机制首用：创作/产品体验/工程维护/成本收益 4 个子代理并行评估 → 一致推荐删除（stub 硬编码
success 无审计价值、前端组件零调用、B 方案与审批门/SSE 架构根本矛盾）→ 用户拍板执行：

- **删除**：`execute_agent_api_tool` + 4 个生成端点（chapters.generate / athena ontology/evolution）+ 假错误管道
  （_raise_if_agent_generation_failed/_with_agent_metadata/LEGACY_GENERATION_400_ERRORS）+ action 3 个 stub 动作
  + 前端 3 个假生成方法（注释引导 v2 会话）
- **修复评审盲区**：continuous writing/retry 后台任务此前调 stub 从不真生成 → 改接真路径
  `create_or_replace_chapter`（trace 关联改 DB 查询）
- **保留**：WritingAgentRun 表/模型（历史审计）、generate_chapter 动作、GET 查询端点
- 生成入口收敛为唯一真路径：v2 agent 会话（AgentV2View）
- 代码量：-443 行；后端 591 passed、前端 485 + vue-tsc 通过

## 2026-08-01 能力框架确立：六项工程不变量（用户拍板，长期判断标准）

harness 只约束**对任何题材成立**的写作工程不变量，情节内容（题材/风格/反派形态/冲突类型/卷部结构/
情节走向）完全留给模型——内容特化会污染创作自由、导致产出同一化：

1. **一致性**：人物/地点/事件/设定跨章不矛盾（实体登记、query_memory、事实表）
2. **连续性**：章间衔接、因果不断裂（状态快照、relation_to_previous）
3. **结构完整性**：伏笔登记-回收闭环、收束（endgame/must_resolve）
4. **节奏管理**：篇幅/信息密度/不注水（check_quality_trend）
5. **格式语言**：标点/排版/语言规范（check_chapter_format）
6. **容错恢复**：幻觉/走偏纠偏（hook 兜底/错误注入/guard）

判断标准：约束对**所有题材**是否成立——成立则 harness 管，否则是特化。

### 弧线规划结构性校验（任务 `08-01-new-part-proposal-gate`，内容无关重构）
- `plan_arc` define 可选 `relation_to_previous`：接续启动未声明 → 提示（不拒绝）；记录 metadata.arc_relation
- `progress`：无收束约束 → endgame_hint 提示补 must_resolve（不阻塞）
- T3 措辞泛化：「禁止新增更早/更深/更初层级」→「优先回收开放线索，暂缓开新线」
- 原「抽象词黑名单校验反派」草稿撤销（情节内容归模型）
- 测试：+4；后端 595 passed、前端 485 无回归

## 2026-08-01 实体登记来源扩展（任务 `08-01-entity-registration-sources`，用户选 C 方案）

解决实体登记白名单太薄（200 章项目 Setup 仅 1 角色 → entity_state 记忆仅 2 条）：

- **新表 `entity_candidates`**（唯一约束 project+name，source 区分 rule/l2）
- **rule 通道** `core/entity_miner.py`：中文姓氏白名单（~300 姓，移除虚词性那/和/从）+ 停止词尾过滤
  + 汉字尾字校验；write_chapter/revise_chapter 正文后自动挖掘注册；**跨 ≥2 章转正**进 _capture_entities 白名单
- **l2 通道**：background_analyzer deep_check 保存 extracted_facts 时 subject/object 注入（LLM 提取免转正）
- **200 章数据验证**（30 章抽样）：程砚秋 29/苏晚晴 18/顾沉舟 6/林舟 8 章命中转正；
  虚词误报（那/和/从 系）清零；称谓式角色（姚先生/婆婆/周伯）规则无法提取 → 由 L2 通道补充
- 测试：+8；后端 591 passed、前端 485 无回归

## 2026-08-01 生成模式统一到 v2 + prompting 全链淘汰（任务 `08-01-generation-unify-v2`，用户选 B 方案）

一次性消除 v1 遗留的提示词子系统，生成统一为「内联提示词 + provider.complete」v2 风格：

- **迁移**（`6a748f22`）：`core/prompt_budget.py`（预算截断纯函数，priority+头尾截断行为不变）、
  `core/generation/`（chapter.py + blocks_* 6 模块 + errors + render.py 模板渲染/trace 元数据内联）、
  `core/dialog_prompts.py`（624 行 dialog 装配去 PromptAssembler）；`chapters._build_chapter_call_payload`
  改用 render_prompt + apply_context_budget；模板保留 5 个活跃文件（backend/prompts/*.txt 由 core 直接读）
- **修复**（`3c294006`）：action_execution_service 的 generate_setup/storyline/outline 3 动作改走
  athena control-plane 记录（v1 绞杀阶段 2 遗漏的死引用），补 4 个测试
- **淘汰**（`9ca22e0a`）：`app/prompting/` 全包删除（-979 行）、5 个死亡模板、2 个测试文件
- 测试基线（生成统一后实测）：后端 **583 passed**、前端 485 tests、vue-tsc 通过、
  会话回放 20/20、依赖规则通过；代码量累计 -3,378 行（v1 绞杀 + 生成统一）

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

## 2026-08-02 agent 架构重构（任务 `08-02-agent-arch-refactor`，设计先行+骨架新建）

多轮重构遗留问题 + 参考三个开源 agent（hermes-agent/openclaw/openhuman，各出研究报告中吸收点），
从基础重构为「agent 为核心」三层架构。前端不参与（后续重写）。

**规划**：prd/design/implement 三件套 + 三份研究报告（research/）；用户决策：
设计先行+骨架新建 / API 完全自由 / 测试重写为主纯函数移植 / 核心链保留扩展归档。

**阶段 0 归档**（`65bf2991`）：self_optimization 实验链（learned PromptRule）4 文件归档。
world_* 深度嵌入核心链，延迟到阶段 4 随旧后端整体清理（执行中兑现）。

**阶段 1 内核骨架**（`af2d63ef`）：`backend/core/` 全新内核（领域无关，零业务依赖）：
- 事件模型（agent_start→turn_end→agent_end 稳定协议）+ TurnState 对象化（hermes）
- loop：无状态回合 + wall-clock + 优雅暂停（部分结果可续写）+ 失败分类进事件
- 护栏：五级（L4 改 error_code 判断，修字符串耦合）+ 压缩后循环守卫 PC
- 上下文：CJK 估算（中文1字≈1.5token，修 len//2）+ 指纹缓存 + CompactionState 实例化
  （修多会话污染）+ 失败冷却/无效计数 + 状态重注入
- 工具：pydantic schema 生成（修手写漂移）+ 失败分类学 + 结果归一化 + artifact 落盘 fail-closed
- 会话：append-only 转录 + 压缩检查点 + 幂等键 + sidecar + 前向兼容
- harness：steer/followUp 双队列（one-at-a-time）+ 写锁 + KV-cache 契约
- workflow：plan→execute⇄review→finalize 图机制（worker 注入可测）
- 测试：scripted mock provider（黄金模式）覆盖重试/护栏/压缩/双队列/优雅暂停

**阶段 2 最小闭环**（`c996dad3`）：domain/writing 纯函数迁入 + chapter_gen 精简生成 +
domain/tools（write_chapter 落库+artifact/check_format）+ api/v2（会话中心 SSE 事件流）；
真实生成验证 Ch1《夜色下的信》1079 字。

**阶段 3 领域迁入**（`7da3cdb2`）：domain/memory（snapshot/outline_lookup/longform_memory
摘 WorldProposalItem 依赖等 7 模块）+ domain/retrieval（entity_miner/athena_retrieval 等 5 模块）；
工具补齐：track_plotline/query_memory/plan_arc/memory_tree/get_entities/retrieve。
200 章实验数据可读验证（201 章/28.4 万字/248 条记忆）。

**阶段 4 整链退役**（`474a8f8c`，-18,728 行）：world 全套 42 文件归档兑现；
旧 agent/tools/api/core/services/schemas 全部删除；main.py 仅挂 v2 路由；
memory_tools 解除旧包装（业务提取为 domain/memory/memory_service.py）；
athena_retrieval 摘 WorldFactClaim；旧测试归档 tests-legacy（550+）。

**阶段 5 dogfood**（`80e685bb`）：8 章连续写作全通过（49 工具调用 0 错误、0 护栏触发、
852-1124 字稳定、章节连贯）。实测修复 2 bug：agent_turn_ended 误入 messages 导致 400、
database_url PROJECT_ROOT 路径多跳一层（旧 bug）。

**新架构形态**：
```
backend/
├── core/      内核（loop/harness/context/guards/tools/session/workflow/providers）~2,700 行
├── domain/    领域（writing/memory/retrieval + memory_service + 8 个工具）
├── api/v2/    新 API（5 端点：sessions/messages/steer/followup/events）
├── app/       models/db/config/main（数据层）
└── tests/     79 passed（mock provider 全确定性测试）
```
测试基线：新架构 79 passed + dogfood 8 章真实生成验证。代码量累计 -20k+ 行（重构+绞杀）。

## 待办（2026-08-02 记录）

### 人工章节标注功能恢复（方案 B：前端重写时一并设计）

旧版「章节批注/修正」功能（RevisionAnnotation/RevisionCorrection + chapter_revisions API +
revision_feedback.py）已随整链退役归档（docs/archive/arch-refactor/legacy/）。

**决策**：不在旧架构恢复，**纳入前端重写时设计**（用户 2026-08-02 确认）：
- 新交互：用户在章节文本上画线/选中批注 + 修正（原文→改文）
- 新 API：如 POST /api/v2/agent/sessions/{id}/annotations（待前端重写时定稿）
- agent 修订：复用 pipeline.py 的 revise 机制，批注作为修订理由
  （pipeline 的 extra_feedback 参数即为此预留入口）

**架构现状**：工具审批（ApprovalGate）已恢复可用；人工标注是唯一的用户→agent
文本反馈缺口。归档参考：legacy/models/chapter_revision.py、tests-legacy/、
旧 core 的 revision_feedback.py。

### 归档模块多视角评审（2026-08-02，四视角子代理）

归档模块 A-I 九组经 4 视角评审（创作/读者/工程/成本收益），完整结论见
docs/archive/arch-refactor/module-review.md。

**P1 待办（低风险纯函数）**：① check_quality_trend 字数趋势（节奏管理#4 唯一缺失，~30 行）
② 连续性检测纯函数重建（术语配置化）③ build_chapter_retrieval_context 接入 pipeline
④ L2 提取通道 ⑤ json_utils/prompt_optimizer 迁入 ⑥ narrative_plan_window 瘦身重挂
⑦ athena_setup_terms 迁入 ⑧ 旧实验脚本清理（l3/l4/m5 系列）

**P2 待定**：世界事实账本瘦身（实证缺口时）/ 无词表 LLM 评审 / versions 回滚 / dialog 拓扑（前端定盘时）

**永久放弃**：B 自优化、G 模型层、F 杂项、I 旧脚本；全部特化词表与世界耦合件（六项不变量原则）。
