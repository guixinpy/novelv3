# 03 · 路线图（M0–M5）

总策略：**绞杀式迁移（Strangler Fig）**——新内核先与旧系统并存，能力逐个迁到新循环，验证后删除旧路径。任何时刻 `main` 分支可用；禁止「大爆炸式重写后长期不可用」。

每个里程碑有明确**退出标准**：全部满足才进入下一阶段。退出标准必须可由命令或可复现实验验证（见 `04-development-rules.md`）。

---

## M0 · 地基与瘦身准备（预计 1-2 个 session）

**目标**：为新内核腾出干净地基，不改行为。

- [ ] Provider 层重写：`agent/providers/`，DeepSeek 原生 function calling + 流式 + 重试归一化；旧 `deepseek_adapter.py` 标记待删
- [ ] 确认保留清单模块的测试独立可跑（world_checker / retrieval / proposal / models）
- [ ] 建立 `app/agent/`、`app/tools/`、`app/domain/` 空骨架与依赖规则（api → agent → tools → domain → models，禁止反向）
- [ ] 在 CI/验证脚本中固化「保留模块回归」命令

**退出标准**：
1. `pytest tests/ -q` 全绿（行为未变）
2. 新 provider 单测覆盖：流式分片重组、tool_call 解析、错误重试、用量统计

---

## M1 · 最小可用 Agent 内核（L1）

**目标**：模型驱动循环端到端跑通，与旧系统并存。

- [ ] `loop.py`：无状态回合引擎（组装→流式调用→工具执行→观察回填→终止判定），事件 sink
- [ ] `harness.py`：会话状态、JSONL 日志、steering/follow-up 队列、钩子
- [ ] `registry.py` + `@tool` 装饰器 + 权限三级
- [ ] 首批只读工具：`read_chapter` / `list_chapters` / `query_world` / `search_text` / `get_project_state`
- [ ] `budget.py`（迭代+令牌预算）与基础停止条件
- [ ] `/api/v2/sessions` 最小实现（创建、发消息、SSE 流）
- [ ] 前端最小接入：对话面板走 v2 SSE（可先开发者开关隐藏）

**退出标准**：
1. 通过对话「帮我看看第 3 章和林思的设定有没有矛盾」，Agent 自主调用 ≥2 个工具并给出有据回答
2. 中断/恢复：kill 进程后会话可从 JSONL 恢复继续
3. 内核单测：循环终止、预算耗尽、工具错误回填、流式事件序列

---

## M2 · 全能力工具化 + 旧编排层删除（L2）

**目标**：写作能力全部变成工具，删除模拟层。**这是减法最大的阶段。**

- [x] 写入类工具上线：`write_chapter` / `revise_chapter` / `propose_world_change` / `update_outline` / `update_setup`，接入审批门（`approval.py`）
- [x] 前端审批 UI 迁移到 v2（pending approval 卡片）
- [x] 删除：intent_router / descriptor-adapter 层（~8K LOC）/ 旧测试（45+ files）
- [x] 删除对应 v1 端点与前端调用（dialogs router 注销，HermesView 删除）
- [x] 同步删除只为旧机器兜底的测试
- [ ] `WritingAgentRun/Step` 写入逻辑接到新循环（前端轨迹可视化待完成）

**退出标准**：
1. 对话完成全流程：「新建项目→生成设定→生成大纲→写第 1 章→按我的意见修订」，全程无旧编排层参与
2. `git grep intent_router|run_service|tool_descriptors` 零命中
3. 后端 LOC 较重构前下降 ≥30%（预期 27K → ≤19K），测试全绿
4. 前端 build + 单测全绿，v1 编排端点调用清零

---

## M3 · 自治护栏（L3）

**目标**：把上一版 dogfood 换来的护栏在新循环内重建，达到无人值守可信。

- [ ] `guards.py`：移植五级循环风险检测（generic_repeat / ping_pong / poll_no_progress / unknown_tool_repeat / 全局熔断）
- [ ] 预算 refund：程序性只读调用不消耗创作迭代额度
- [ ] `compaction.py`：上下文用量预检（75% 阈值）+ 头尾保护压缩 + 压缩记录入会话日志
- [ ] 章节长度/质量自检工具：`check_chapter_quality`（长度超标、与大纲偏离）供模型自查
- [ ] 风险触发 → 停止 → 诊断报告 → 恢复建议的闭环（恢复建议作为 follow-up 消息注入）
- [ ] 批量模式：「连续写 N 章」= follow-up 队列驱动，每章之间过护栏检查点

**退出标准**：
1. 无人值守连续生成 10 章（真实模型、真实项目),全程零人工干预或在异常时自动停止并给出可执行诊断
2. 人为构造乒乓场景（互相矛盾的世界观提案），熔断在 ≤5 个回合内触发
3. 构造超窗场景，压缩自动发生且后续生成不破坏连贯性

---

## M4 · 长期记忆（L4）

**目标**：跨章一致性从「靠上下文」升级为「靠记忆系统」。

- [ ] `domain/memory/` 整合五条旧码路：append（确定性 chunk ID）/ cascade（层级摘要级联）/ recall（多通道）
- [ ] 实体索引：章节归档时抽取实体 → 实体状态卡（当前位置/关系/状态）+ 共现图
- [ ] 情节线通道：伏笔/线索登记与闭环状态查询工具（`list_open_threads`）
- [ ] 记忆注入接到 `context.py` 易变层：每回合按当前任务多通道召回
- [ ] 远程向量嵌入评估：如本地 hash 嵌入召回不足，接入嵌入 API（继承旧 ADR-004 的「先本地后远程」判定）
- [ ] 记忆质量审计：用真实模型验证摘要质量（上一版止步于 fake model 的遗留问题）

**退出标准**：
1. 50 章 dogfood：人物名称/属性/关系零硬性漂移（world checker + 人工抽查）
2. 「林思现在在哪、和谁在一起、身上带着什么」类问题，Agent 通过记忆工具正确回答（不靠全文重读）
3. 第 50 章生成时上下文中不含第 1-40 章原文,仅含记忆召回结果，连贯性人工评审通过

---

## M5 · 百万字专业化（L5）

**目标**：长程质量不下滑。此阶段开始前重新细化（依赖 M4 的 dogfood 发现）。

方向性条目（届时修订）：
- [ ] 质量趋势作为记忆：「最近 3 章节奏偏慢」成为可召回事实，影响后续生成
- [ ] 弧线/卷级规划工具：Agent 在卷边界自主回顾与规划
- [ ] 伏笔闭环强制：长期未闭环线索在卷末触发提醒
- [ ] 文风一致性采样审计
- [ ] 续写既有长篇 ≥200 章实验

**退出标准**：≥200 章连续生成，质量趋势指标（长度方差、重复度、一致性违规数）不出现持续恶化斜率；具体阈值在 M4 完成后定义。

---

## 里程碑外的持续事项

- 每个 M 完成时：更新 `05-progress-tracker.md`、给 main 提 PR（经用户批准后合并）、打 tag
- dogfood 发现的问题先记录进 progress-tracker 的「问题清单」，修复优先于新功能（继承旧版教训：不在失败的 dogfood 上叠新功能）
