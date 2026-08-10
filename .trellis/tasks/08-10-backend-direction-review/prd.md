# 后端方向评估：基础能力 vs 网文特化

## Goal

讨论现有后端架构的成熟度，评估两个方向：
1. 是否继续打磨 agent 基础能力（通用内核）与工具
2. 如何进一步特化为「专精于长篇网络小说创作的 agent」

产出：方向判断 + 下一步打磨优先级（可能含实施计划）。

## Background（已确认事实，2026-08-10 盘点）

**架构现状**：
- 三层架构（core 领域无关内核 / domain 网文领域层 / app 数据+API），依赖单向
- 154 passed / ruff 全过 / 三轮 code-review + simplify 打磨
- 通用内核成熟：事件流、无状态回合、审批门（线程安全）、压缩、护栏、幂等、ephemeral、部分流恢复

**已特化**（网文侧）：
- per-book 自优化（09）：章末自省 → 写作经验记忆 → 快照注入
- 伏笔账本（11）：自省自动提取 open/close/postpone → 到期清单注入
- 弧线规划/聚合、格式守门员、实体挖掘/共现、项目快照（章节进度/最近章/到期伏笔/事实表）

**未做的基础能力候选**（archived-modules-review P1 八项待办，2026-08-02 四视角评审结论）：
- ① check_quality_trend 字数趋势（节奏管理唯一缺失）
- ② 连续性检测纯函数重建（时间线/编号/关系锚点，术语配置化）
- ③ build_chapter_retrieval_context 接入（函数已存在 athena_retrieval.py:470）
- ④ L2 提取通道 ⑤ json_utils.parse_json_safely/prompt_optimizer 迁入
- ⑥ narrative_plan_window 瘦身重挂 ⑦ athena_setup_terms 迁入
- ⑧ 旧实验脚本清理（l3/l4/m5 系列指向已删端点）

**B 类剩余吸收**（08 文档）：B1 afterToolCall 钩子位（无消费方）、B2/B9/B10 条件触发（断点恢复/压缩链/外部探测）

**关键缺口**：50 章/200 章长程实验未跑——单测证明逻辑正确，不证明 prompt 驱动模型行为有效（09/11 效果未验证）

## Requirements

- **R1 质量趋势监控**（P1①，旧 check_quality_trend）：字数窗口趋势量化（四级判定 + 参考信息），作为长程实验的观测尺子
- **R2 连续性检测**（P1②，旧 L1 提取 + 设定卡比对）：第一版角色状态维度（设定卡标记死亡/昏迷的角色再次出场），checker 接口可扩展；术语从设定卡读取（题材无关）

## Acceptance Criteria

- [ ] R1：快照注入字数趋势段（≤约 30 字，信息形态非指令）
- [ ] R2：check_continuity 工具返回 issue 清单（角色状态维度），issue 为报告形态（含证据/建议参考，不自动修复不阻塞）
- [ ] 两能力均为确定性纯函数（零 LLM 成本）
- [ ] 新增单测覆盖；全量 154+ passed；ruff 全过

## Constraints（用户原则，2026-08-10）

**工具不越权**：所有工具/检测器是模型与用户的「信息提供者」；模型和用户是最终决策者。
- 检测器发现 issue 只是报告：不自动修复、不阻塞流程、不指令式命令
- 建议文案用「信息 + 可能原因 + 供参考」形态，不用「请立即…必须…」
- 质量趋势 advice 修正旧实现的指令式文案（原则修正点）

## Key Decisions

- **方向决策（2026-08-10）**：下一步 = 质量保障特化（质量趋势 + 连续性检测），不做基础补漏全覆盖、不先跑实验
- **接入形态**：混合——质量趋势 → 快照注入（每回合可见，轻量 SQL）；连续性检测 → 工具（模型按需深查）。两者均为确定性纯函数零 LLM 成本
- **维度范围（设计推荐）**：第一版只做角色状态（复用 entity_miner 提取），checker registry 扩展点；时间线/编号/关系锚点后续维度

## Out of Scope

- 前端重写（总闸门，另行规划）

## Notes

- 证据：docs/claude-guide/00-backend-architecture.md（架构总览）、08（吸收清单）、
  docs/archive/claude-guide-legacy/05-progress-tracker.md（重构期进度）、
  docs/archive/arch-refactor/module-review.md（P1 八项待办出处）
