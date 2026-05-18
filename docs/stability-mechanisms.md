# 项目长期稳定性机制说明

这份文档解释当前项目靠哪些机制和模块维持长期稳定性。

结论先说清楚：项目不是靠某一个“大模型能力”稳定，而是靠一组可回溯、可审阅、可回滚、可测试的工程机制稳定。大模型负责生成内容，但真正让系统不容易乱掉的是数据契约、世界模型、上下文透明化、提案审批、版本回滚和自动化测试。

## 1. 总体稳定性结构

当前项目的稳定性主要来自七层：

| 层级 | 作用 | 代表模块 |
| --- | --- | --- |
| 数据契约层 | 保证核心数据结构可迁移、可校验 | SQLAlchemy models、Pydantic schemas、Alembic |
| 创作流程层 | 保证项目按设定、故事线、大纲、正文推进 | Hermes、state diagnosis、pending action |
| 世界模型层 | 保证长篇小说里的事实、角色、地点、规则不漂移 | Athena、world-model、proposal bundles |
| 上下文层 | 保证 AI 调用时带入了什么内容可查看、可调试 | model-call-traces、context blocks |
| 检索记忆层 | 保证章节越多后仍能找回前文和事实 | Athena retrieval、embedding service |
| 恢复层 | 保证出错后可回滚、可再生成、可追踪 | versions、chapter revisions、rollback |
| 验证层 | 保证改动后不会轻易破坏已有能力 | pytest、vitest、vue-tsc、vite build、手工 UAT |

## 2. 数据契约层：稳定性的地基

后端使用 FastAPI + SQLAlchemy + Pydantic + Alembic。

关键机制：

- `backend/app/models/` 保存数据库真实结构。
- `backend/app/schemas/` 保存 API 输入输出结构。
- `backend/alembic/versions/` 保存数据库迁移历史。
- `backend/app/main.py` 集中注册所有 API router，避免接口散落。

这层解决的问题：

- 新增字段必须通过模型、schema、迁移一起落地。
- 前后端通过固定 API 合同交互，减少“前端以为有，后端实际没有”的黑盒问题。
- 数据库结构可以随版本演进，而不是靠手工改库。

当前例子：

- `Project.target_chapter_count` 已通过模型、schema、Alembic 迁移和前端创建项目链路打通。
- model call trace、retrieval、world proposal、chapter revision 都有独立模型，不是临时 JSON 堆在一起。

## 3. 创作流程层：Hermes 负责流程稳定

Hermes 的核心价值不是“聊天”，而是维持创作流程秩序。

关键机制：

- `state-diagnosis` 判断项目当前缺什么：设定、故事线、大纲、正文。
- `pending_action` 让 AI 建议的操作必须等待用户确认。
- `ui_hint` 和 `refresh_targets` 告诉前端应该刷新哪个面板。
- 生成任务运行中时，Hermes 会阻止重复触发冲突命令。
- 对话历史会限制长度，并支持压缩，避免聊天上下文无限膨胀。

这层解决的问题：

- 用户不会在没有设定时误生成正文。
- AI 不会绕过用户直接执行高影响动作。
- 前端不会盲目刷新不存在的数据，减少 404 噪音。
- 长会话不会因为上下文无限增长而失控。

## 4. 世界模型层：Athena 负责长篇稳定

Athena 是项目长期稳定产出长篇小说的关键模块。

它解决的不是“写得好不好”这个单点问题，而是“写到第 30 章、第 80 章时，世界规则和人物事实是否还可信”。

### 4.1 Profile Version

世界模型不是一团散乱设定，而是绑定在 `ProjectProfileVersion` 上。

稳定性来自：

- 每个项目有当前世界档案版本。
- 世界事实、事件、提案都绑定 profile version。
- 旧 profile 的数据不会混入当前 profile。
- world-model API 会拒绝操作非当前 profile 的提案。

这能避免一个很危险的问题：用户已经切换了世界设定版本，但系统还在拿旧提案改新世界。

### 4.2 结构化世界实体

Athena 把设定拆成结构化实体：

- 角色：`WorldCharacter`
- 地点：`WorldLocation`
- 势力：`WorldFaction`
- 物品：`WorldArtifact`
- 资源：`WorldResource`
- 规则：`WorldRule`
- 关系：`WorldRelation`
- 时间锚点：`WorldTimelineAnchor`
- 事件：`WorldEvent`
- 事实声明：`WorldFactClaim`
- 证据：`WorldEvidence`

这层的意义是：世界观不只是一段文本，而是一套可以查询、投影、校验和追踪来源的数据。

### 4.3 事件账本与投影

世界模型通过事件和事实生成不同视角：

- 当前真相：世界现在实际发生了什么。
- 角色认知：某个角色知道什么、不知道什么。
- 章节快照：写到某一章时，世界应该是什么状态。

这对长篇很关键。

没有这层时，AI 只会“凭最近上下文记忆”；有这层后，系统可以明确告诉模型：这一章之前已经确认了哪些事实，哪些事实角色还不知道。

### 4.4 提案审批机制

Athena 对世界模型的修改不是直接写入真相层，而是生成提案：

- `WorldProposalBundle`：一次世界变更包。
- `WorldProposalItem`：具体候选事实。
- `WorldProposalReview`：用户或系统的审阅记录。
- `WorldProposalImpactScopeSnapshot`：影响范围快照。

提案可以：

- 通过
- 带修改通过
- 拒绝
- 标记不确定
- 拆分
- 回滚

这层是世界模型最重要的安全阀。它避免 AI 一句话把世界真相改坏。

## 5. 检查器层：提前发现世界矛盾

世界模型有 layered checker：

- L0 Schema Gate：检查事件和事实的基础字段。
- L1 Event Ledger Gate：检查事件账本合法性。
- L2 Deterministic Replay：检查事件能否稳定重放。
- L3 Cross-Entity Rules：检查跨实体关系。
- L4 Profile Rules：检查题材档案规则。
- L5 Semantic Checks：语义检查预留层。
- L6 Governance：治理检查预留层。

已经覆盖的典型问题：

- 重复事件
- 断裂的 supersedes 链
- 非法事件类型
- 角色关系互斥
- 地点连续性
- 所有权链条
- 科幻题材里的技术边界
- 悬疑题材里的证据链和时间窗口
- 角色认知层冲突

注意：L5、L6 目前还是预留层，不要把它们理解成已经成熟的语义审稿系统。

## 6. 上下文透明化层：让 AI 调用可审计

这是最近一轮稳定性增强的重点。

核心模块：

- `AIModelCallTrace`
- `backend/app/core/model_call_trace.py`
- `backend/app/api/model_call_traces.py`
- `frontend/src/components/modelTrace/ModelTraceDrawer.vue`
- `frontend/src/stores/modelTraces.ts`

每次重要 AI 调用会记录：

- trace 类型
- 模型名
- temperature
- max tokens
- prompt tokens / completion tokens
- raw messages
- context blocks
- 上下文来源 sources
- 调用状态 success / failed
- 错误信息
- 响应消息 ID

这层解决的问题：

- 用户能看到 AI 到底吃了什么提示词。
- 用户能看到世界模型哪些节点被塞进上下文。
- 失败调用也能留下记录，方便排查。
- prompt 模板、检索证据、章节上下文、用户反馈都能拆块查看。

安全处理：

- trace 会截断过长内容。
- trace 会脱敏 API key、Bearer token、password、secret 等敏感字段。
- 用户消息不显示上下文按钮，AI 和系统消息有 trace 时才显示。

## 7. 检索记忆层：支撑长篇上下文

长篇小说不能只靠最近几条对话或上一章摘要。

当前检索层包括：

- `RetrievalDocument`
- `RetrievalChunk`
- `RetrievalEmbedding`
- `backend/app/core/athena_retrieval.py`
- `backend/app/core/embedding_service.py`

当前索引来源：

- 已生成章节
- 已确认世界事实

当前检索方式：

- 本地 hash embedding 作为默认方案。
- 可切换 OpenAI-compatible remote embedding。
- 检索分数结合 lexical score 和 vector score。
- 章节生成时只检索目标章节之前的内容，避免未来章节污染当前章节。

这层解决的问题：

- 章节越来越多后，系统仍能找回相关前文。
- 世界事实可以参与检索，不只依赖正文文本。
- 章节 prompt 能带入“检索证据”，减少遗忘和前后矛盾。

限制也要说清：

- 默认本地 hash embedding 是工程可用方案，不是最高质量语义向量。
- 真正生产级长篇质量，后续仍建议接远程 embedding 或更强的向量模型。

## 8. 章节生成稳定机制

正文生成不是裸调用模型。

章节生成上下文包括：

- Setup 世界观
- Setup 角色
- 当前章节大纲
- 场景和出场角色
- 上一章摘要
- Athena 世界上下文
- 检索证据
- 已确认事实
- 未解决一致性问题
- 用户修订反馈
- 风格偏好规则
- few-shot 示例

生成后会自动做几件事：

- 保存或替换章节内容。
- 更新项目总字数。
- 写入 model call trace。
- 运行基础一致性检查。
- 分析章节并生成世界模型候选提案。
- 更新章节检索索引。
- 发出章节生成事件，供后台任务继续处理。

这层的价值是：正文生成完成后，系统不会只留下“一段文本”，还会回流到世界模型、检索系统和一致性检查。

## 9. 版本和修订层：允许犯错，但要能恢复

长期创作一定会改稿，所以稳定性不能靠“不出错”，而要靠“出错后能恢复”。

当前恢复机制：

- `Version` 保存节点版本。
- `rollback_version` 可以把 setup、storyline、outline、chapter 回滚到旧内容。
- `ChapterRevision` 保存正文修订任务。
- 修订有 base version 和 result version。
- 修订反馈会进入自优化逻辑，形成后续 prompt / style 规则。

这层解决的问题：

- 用户可以回滚不满意的内容。
- AI 改坏正文时不会覆盖掉唯一版本。
- 批注、修正、再生成能形成闭环，而不是一次性聊天。

## 10. 一致性检查和后台任务

当前一致性检查分两类：

- L1：同步检查，适合快速发现明确问题。
- L2：后台深度检查，生成 `BackgroundTask` 后异步执行。

已有能力：

- 死亡角色再次出现这类基础矛盾会被标记。
- 深度检查任务有 pending、running、completed、failed 状态。
- 用户可以查询后台任务结果。

限制：

- 后台任务目前是进程内异步任务，不是生产级队列。
- 如果未来要多用户、长任务、高并发，应该升级为 Celery、RQ、Arq 或类似队列。

## 11. 前端状态稳定机制

前端稳定性主要靠 Pinia store 里的请求隔离。

关键机制：

- world model store 使用 request lane：overview、bundles、detail。
- 每次请求都有 requestId 和 project scope version。
- 迟到的旧请求不会覆盖新项目数据。
- 提案审阅使用 item 级 pending counter，不会因为一个按钮 loading 锁死整个面板。
- model trace store 同样隔离 list 和 detail 请求。
- 项目初始化 hydration 只请求 diagnosis 已完成的资源，避免新项目刷新时无意义 404。

这层解决的问题：

- 快速切项目时，不会把 A 项目的世界模型显示到 B 项目。
- 用户连续审阅提案时，局部状态更准确。
- 上下文抽屉关闭后，迟到的 trace 详情不会重新写回页面。

## 12. 自动化验证层

当前项目靠自动化测试守住已有行为。

后端：

- `pytest`
- 覆盖 projects、dialogs、setups、storylines、outlines、chapters、Athena、retrieval、world model、proposal、model traces、revisions、versions、export、preferences 等。

前端：

- `vitest run`
- 覆盖 chat、Athena 面板、worldModel store、modelTraces store、Manuscript 编辑器、ProjectList、Hydration、API client 等。

构建：

- `npm run build`
- 内含 `vue-tsc --noEmit` 和 `vite build`。

长篇规模 smoke：

- `backend\.venv\Scripts\python.exe scripts\longform_scale_smoke.py`
- 合成千章/百万字项目，验证长篇记忆、检索索引、上下文构建、叙事规划窗口、连续写作 worker、生成后维护和后台任务进度。
- CLI 可以用 `--max-elapsed-ms` 和 `--max-stage-ms STAGE=MS` 做性能门禁。
- CLI 也可以用 `--max-writing-under-target`、`--max-writing-over-target`、`--max-writing-warnings` 做写作质量风险门禁。
- smoke 报告会输出 `writing_worker.generation_diagnostics`，用于检查本轮连续写作是否出现偏短、偏长或维护警告。

数据库：

- Alembic migration 管理 schema 变更。

这层解决的问题：

- 每次修功能后能快速知道有没有破坏核心链路。
- prompt 模板变量替换、上下文按钮、trace 抽屉、世界模型提案刷新这类细节有回归测试保护。

## 13. 当前仍然不够稳定的地方

这些地方不要自欺欺人：

1. 后台任务还不是生产级队列。
2. 默认 embedding 质量有限，只是稳定可用，不是高质量语义检索上限。
3. Athena 的章节事实抽取和世界提案仍然需要更多真实长篇压测。
4. L5 / L6 checker 还是预留层，不能当作成熟语义审稿。
5. 当前没有完整的多用户权限、安全隔离和审计体系。
6. 合成 longform smoke 能证明规模链路稳定，但仍不能替代真实网络小说长周期 dogfood。

## 14. 维护原则

后续维护这个项目，最重要的是守住几条规则：

1. 不允许 AI 直接修改世界真相，必须走提案和审阅。
2. 新增 AI 调用必须接入 model call trace。
3. 新增影响长篇连续性的上下文，必须能在上下文抽屉里看到。
4. 新增数据库字段必须同时改 model、schema、migration、前端调用和测试。
5. 新增生成链路必须考虑失败 trace、用户可见错误和恢复路径。
6. 修改前端异步加载必须考虑 project scope 和迟到请求。
7. 修改世界模型必须考虑 profile version 和 contract version。
8. 大功能合并前至少跑后端测试、前端单测、前端构建。

## 15. 一句话总结

项目长期稳定性靠的不是“AI 更聪明”，而是：

- Hermes 管流程。
- Athena 管世界模型。
- retrieval 管长篇记忆。
- trace 管上下文透明。
- proposal 管世界变更审批。
- version / revision 管恢复。
- tests / build / migration 管回归。

只要这几层不被绕开，项目就有继续扩展成长篇小说生产系统的基础。
