# Research: OpenClaw agent 架构研究报告

- **Query**: 研究 docs/references/agent-projects/openclaw/（TypeScript 开源 agent 框架），聚焦后端/核心运行时，为 FastAPI + Python 写小说 agent 重构吸收设计
- **Scope**: internal（本地代码研读）
- **Date**: 2026-08-02
- **项目定位**: OpenClaw 是个人 AI 助手（MIT，单用户，多 channel 消息接入），Gateway 是控制面。核心运行时为自研（`src/agents/`），不依赖 LangChain 等外部 agent 框架。版本 2026.7.2，schema: state v6 / agent v16。

## 0. 代码地图（怎么找东西）

| 路径 | 职责 |
|---|---|
| `packages/agent-core/` | **可复用 agent 核心**：agent loop、Agent 类、消息类型、compaction 助手、测试 harness |
| `src/agents/embedded-agent-runner/` | OpenClaw 内置 attempt loop（run-loop、attempt、compaction、工具策略、model fallback） |
| `src/agents/sessions/` | 会话持久化（session-manager）、资源发现、prompt 模板 |
| `src/agents/harness/` | harness 注册/选择/生命周期（内置 `openclaw` + 插件 harness 如 `codex`） |
| `src/agents/agent-tools*.ts` | 内置工具定义、参数 schema、工具策略、before/after tool-call 适配器 |
| `src/llm/` + `packages/llm-core/` + `packages/ai/` | 模型/provider 注册、传输层、provider 实现 |
| `src/context-engine/` | 插件化上下文管理生命周期（assemble/compact/maintain） |
| `src/tasks/` | 任务注册表（SQLite 状态机）+ task flow（多任务编排） |
| `src/trajectory/` | 运行轨迹记录（SQLite） |
| `src/config/` | openclaw.json 配置系统 |
| `packages/retry/` | 独立重试库 |
| `packages/tool-call-repair/` | 纯文本 tool call 解析/修复 |
| `qa/scenarios/` | YAML 化端到端场景测试 |
| `extensions/` | 插件（providers/channels/diagnostics-otel 等，未深入） |

架构文档：`docs/agent-runtime-architecture.md`（代码布局/边界/manifest）与 `docs/openclaw-agent-runtime.md`（开发者工作流）。

---

## 1. 整体架构与模块分层

**怎么做：**

- pnpm monorepo：`src/`（核心运行时）、`packages/`（可复用库）、`extensions/`（插件）、`apps/`（macOS/iOS/Android 等前端，跳过）、`skills/`、`qa/`。
- 分层边界明确（docs/agent-runtime-architecture.md:21-25）：核心调用内置运行时走模块，**插件只能通过 `openclaw/plugin-sdk/*` barrel 导入，禁止 import `src/**` 内部**。
- 资源包用 package.json 的 `openclaw` manifest 声明（docs/agent-runtime-architecture.md:29-42）：
  ```json
  { "openclaw": { "extensions": ["extensions/index.ts"], "skills": ["skills/*.md"], "prompts": ["prompts/*.md"], "themes": ["themes/*.json"] } }
  ```
- runtime 选择（docs/agent-runtime-architecture.md:44-50）：`agentRuntime.id` 配置（model 条目优先于 provider 条目），`auto` 时先选支持该 provider 的插件 harness，否则内置 `openclaw` runtime。
- 关键抽象：**prepared model runtime generation**（docs/agent-runtime-architecture.md:52-56）——gateway 启动时按 agent 构建一份原子快照（auth 模板 + model registry + 投影 catalog），运行期 fork 出可变副本；防半新半旧配置混用。`src/agents/prepared-model-runtime.ts` + `src/agents/embedded-agent-runner/run-loop.ts:263-274`（context-engine 只解析一次复用）。

**值得吸收：**

- 最小可复用核心（`packages/agent-core`）与宿主集成层（`src/agents/embedded-agent-runner`）分离——loop 本身与 OpenClaw 特有逻辑（会话、hook、auth）解耦，agent-core 可独立测试（`packages/agent-core/src/agent-loop.test.ts`）。
- plugin-sdk barrel 边界：对外的类型/运行时接口集中导出，内部实现可自由重构。
- 「一次准备、全程复用」的原子运行时快照（避免每次 turn 重新发现模型/认证）。
- 状态 schema 显式版本化（`openclaw.schemaVersions`，package.json:5-8），迁移有纪律。

**不适合我们：**

- 插件系统（extensions + plugin-sdk + harness 注册）重量级，写小说 agent 规模不需要；但「barrel 边界」思想适用。
- 多 channel 消息接入（WhatsApp/Telegram/…）与本项目无关。

---

## 2. agent 循环模型

**怎么做：**

核心在 `packages/agent-core/src/agent-loop.ts`，双层循环（agent-loop.ts:318-457）：

- **内层** `while (hasMoreToolCalls || pendingMessages.length > 0)`：注入 steering 消息 → stream 一次 assistant 响应 → 执行工具批 → 若 `stopReason === "toolUse"` 且存在 toolCall 则继续；
- **外层** `while(true)`：内层退出（无工具、无 steering）后轮询 follow-up 队列，有则继续，无则 `agent_end` 退出。

`Agent` 类（`packages/agent-core/src/agent.ts:213-643`）是有状态包装器：

- API：`prompt()`（新对话）、`continue()`（从 transcript 续跑，agent.ts:409-438）、`steer()` / `followUp()`（见第 7 节）、`abort()` / `reset()` / `waitForIdle()`。
- 事件订阅：`subscribe(listener)`（agent.ts:297-302），listener 的 promise 被 await，`agent_end` 事件后仍算 run 的一部分（等 listener 收尾才 idle）。

**事件协议**（`packages/agent-core/src/types.ts:548-587`）：`agent_start / turn_start / message_start / message_update / message_end / tool_execution_start / tool_execution_update / tool_execution_end / turn_end / agent_end`。turn = 一次 assistant 响应 + 其工具调用。

**终止条件**（多路）：

- `shouldStopAfterTurn` hook（types.ts:244-244，agent-loop.ts:429-439）：turn 完整结束后优雅停，比如「上下文快满了」。
- 工具结果 `terminate: true` 批量终止（agent-loop.ts:910-915）：**只有当批内所有 finalize 结果都 terminate 才停**。
- abort signal：任何环节可中止，中止时持久化一个 aborted assistant 消息（agent-loop.ts:287-315），保证 transcript 配对完整。
- 失败编码为消息而非异常：`createFailureMessage` 生成 stopReason="error" 的 assistant 消息走正常事件流（agent.ts:563-573）。

**重试/预算**（`src/agents/embedded-agent-runner/run-loop.ts`）：

- 顶层 attempt 重试循环：`MAX_RUN_LOOP_ITERATIONS`（run-loop.ts:177, 290-324），超限后按 failover 决策终止。
- failover 控制器：auth profile 轮换（rate-limit/overload 分类）、model fallback 链、`emptyErrorRetries`（stopReason=error + 0 token 时重发）、`idle-timeout-breaker`（成本失控熔断，run-loop.ts:188-194）、`post-compaction-loop-guard`（压缩后死循环检测，run-loop.ts:195-204）。
- 独立 `packages/retry/`：`retryAsync`（尊重服务器 Retry-After 头、正/对称 jitter、`shouldRetry` 谓词，retry/src/index.ts:253-349）；`RetrySupervisor`（可 cancel 的退避调度器，retry/src/index.ts:67-112）；`sleepWithAbort`（abort 可中断的 sleep，retry/src/index.ts:21-65）。
- token 预算：`contextTokenBudget`（模型上下文窗口）+ `maxOutputTokens`，溢出触发前置压缩（见第 4 节）。
- 工具批处理模式：`toolExecution: "parallel"（默认）| "sequential"`（types.ts:35），单工具可用 `executionMode: "sequential"` 强制整批降级（agent-loop.ts:586-624）。parallel 是「预检（prepare）顺序做，执行并发做，`tool_execution_end` 按完成序发、toolResult 消息按 source 序发」（agent-loop.ts:839-847）。

**值得吸收：**

- **双层循环 + 队列注入**的设计：steering 注入点和 follow-up 注入点是循环天然的两个「检查点」，我们写小说时「生成中改方向」与「生成完追加要求」正好对应。
- 工具批 `terminate` 全票终止语义：避免「一个工具要停、另一个要继续」的竞态。
- 失败走消息而非异常：UI/持久化/恢复统一走一条路径。
- 事件协议粒度（start/update/end + turn 边界）直接可映射到我们的流式推送。
- 重试库的 Retry-After 尊重 + jitter + abortable sleep 是通用能力，Python 侧可直接复刻。

**不适合我们：**

- auth profile 轮换（OAuth/API key 多 profile 故障转移）与多 provider 商用生态绑定，我们单/双 provider 不需要。
- harness 多 runtime 注册（codex 等外部 harness 接入）不需要。

---

## 3. 工具/技能系统

**怎么做：**

工具接口 `AgentTool`（`packages/agent-core/src/types.ts:497-529`）：

```ts
interface AgentTool<TParameters extends TSchema> extends Tool<TParameters> {
  label: string;
  outputSchema?: TSchema;              // 结构化 details 的 schema
  hideFromChannelProgress?: boolean;
  resultContentSource?: "network";     // 结果含外部网络内容 → 污染标记
  prepareArguments?: (args) => TParameters;  // 模型参数 → schema 兼容参数的 shim
  executionMode?: "sequential" | "parallel";
  execute: (toolCallId, params, signal?, onUpdate?) => Promise<AgentToolResult<TDetails>>;
}
```

- **schema 用 TypeBox**（不是 zod）：`import type { Static, TSchema } from "typebox"`（types.ts:14），JSON-schema 兼容。
- **工具调用生命周期管线**（agent-loop.ts:975-1263）：
  1. `resolveToolCallTool`：在 context.tools 中找，找不到走 `resolveDeferredTool` hook（**deferred 工具**：已授权但不在 provider 可见集里，运行时按需水合，agent-loop.ts:931-973）；
  2. `prepareToolCall`：`prepareArguments` → `validateToolArguments`（TypeBox 校验，失败产生 errorKind="argument-validation" 的立即失败）→ `beforeToolCall` hook（可 `{ block: true, reason }` 阻止执行，types.ts:54-57）；
  3. `executePreparedToolCall`：`tool.execute(callId, params, signal, onUpdate)`，onUpdate 流式 partial 更新 → `tool_execution_update` 事件（agent-loop.ts:1110-1135）；
  4. `finalizeToolCallOutcome`：`afterToolCall`（仅执行过的）→ `afterToolOutcome`（**所有**结果，含未执行失败的，types.ts:119-143），可覆写 content/details/isError/terminate。
- **权限策略**（`src/agents/agent-tools.policy.ts` + agent-tools.before-tool-call.*）：
  - allow/deny 列表 + 工具名归一化（`tool-policy-match.ts`）；
  - 子代理分层 deny：`SUBAGENT_TOOL_DENY_ALWAYS`（gateway/agents_list/sessions_send 等）+ leaf 子代理再禁 spawn 类（agent-tools.policy.ts:52-73）；
  - 显式 allow 覆盖 deny（agent-tools.policy.ts:108-116）；
  - exec approvals：companion 主机护栏（docs/tools/exec-approvals.md），模式 deny/allowlist/ask/auto/full，**approvals 只能收紧不能放松**。
- **子代理/多 agent**（docs/tools/subagents.md）：`sessions_spawn` 工具非阻塞（立即返回 run id），**完成是 push 式**（禁止轮询等待）；每个子代理独立 session `agent:<agentId>:subagent:<uuid>`，`context: "fork"` 继承父上下文，thread-bound 或 ACP runtime（Claude Code 等外部 CLI）可选；父结果通过 announce 链回传（subagent-announce-*.ts）。
- **技能**：`skills/<name>/SKILL.md`（frontmatter：name/description/metadata.openclaw 含 requires（需要哪些 bin）、config、install 引导），经 manifest/目录约定发现，运行时注入上下文（`src/agents/embedded-agent-runner/run/attempt-startup.ts` 的 prepareEmbeddedAttemptSkills）。技能本体是「提示词 + 脚本」而非代码。
- **tool-call 修复**（`packages/tool-call-repair/`）：解析模型输出的**纯文本工具调用块**（payload.ts）、流事件归一化（stream-normalizer.ts）、升级为结构化 toolCall（promote.ts）——不依赖 provider 原生 tool call 时的兜底。

**值得吸收：**

- 工具生命周期六阶段管线 + deferred 水合：安全（before block）、兼容（prepareArguments）、观测（update 流）全在一个地方。
- **`resultContentSource: "network"` 污染标记**（turn taint，agent-loop.ts:1344-1394）：网络/外部内容进入 turn 后标记后续模型输出，可作「外部内容不可信」策略基础——对应我们写小说时「外部检索内容 vs 模型原创内容」的区分。
- 子代理「spawn 非阻塞 + push 完成 + 独立 session + context fork」模型比同步编排更抗长任务。
- 技能 = 提示词 + frontmatter 元数据 + 脚本，比代码插件轻得多，适合我们的小说写作技能包。
- TypeBox/JSON-schema 做参数校验（Python 侧 pydantic 同理，理念一致：schema 即校验 + 即文档 + 即 provider 投影）。

**不适合我们：**

- 多通道权限矩阵（channel 级 policy）不需要。
- ACP/外部 CLI harness 接入（Claude Code 等）与我们无关。

---

## 4. 上下文管理

**怎么做：**

- **token 计量：无 tiktoken！字符启发式**（`packages/normalization-core/src/cjk-chars.ts`）：
  - 基础：`estimateTokensFromChars = ceil(chars / 4)`（cjk-chars.ts:10, 50-52）；
  - **CJK-aware 加权**：常见 CJK 1 字符 ≈ 4 token（`text.length + commonCjkCount * 3`），生僻 BMP 3x、宽兼容 2x、补充平面 4x（cjk-chars.ts:28-48）——注释明说是「provider 无关的预算启发式，非精确 tokenizer」；
  - 按消息角色统计（`packages/agent-core/src/harness/compaction/compaction.ts:283-336`）：user/assistant（text+thinking+toolCall）/toolResult/custom/bashExecution/compactionSummary 各算各的。
- **压缩（compaction）**：完整流水线（`src/agents/embedded-agent-runner/`）：
  - 触发：溢出预检（preemptive-compaction.ts）、auto-compaction 配置（agent-settings.ts）、手动 /compact；
  - 执行链：`compact.ts`（facade + model fallback 协调）→ `direct-compaction.ts` → `compaction-session-execution.ts`（**持有会话写锁**、capture checkpoint、运行 before/after hooks、safety timeout、可旋转 successor transcript）；
  - 护栏：`agent-hooks/compaction-safeguard.ts`（压缩质量保障）、`compaction-hooks.ts`（before/after/副作用）、`estimateTokensAfterCompaction` 合理性检查（压缩后比压缩前还大 → 拒绝，compaction-hooks.ts:279-298）；
  - 压缩摘要消息 `role: "compactionSummary"`（types.ts:395-410，含 tokensBefore/tokensAfter/firstKeptEntryId）。
- **transformContext hook**（agent 循环层，types.ts:222）：provider 请求前改写 AgentMessage 上下文（修剪/注入），纯 core 层能力。
- **tool 结果治理**：`tool-result-truncation.ts`（1493 行：结果截断、fullOutputPath 落盘）、`tool-result-context-guard.ts`、`history.ts`（limitHistoryTurns 轮数上限）。
- **context-engine 插件化**（`src/context-engine/types.ts`）：可插拔的上下文管理生命周期——`assemble`（窗口化组装，返回 messages + estimatedTokens + systemPromptAddition）、`compact`、`maintain`、`thread_bootstrap` 投影（持久后端线程 epoch 复用）；引擎能力协商（`ContextEngineHostCapability`，types.ts:64-71）；legacy 为默认引擎。
- 记忆：`src/memory/` + `packages/memory-host-sdk/`（记忆宿主，未深入——本报告不展开）。

**值得吸收：**

- **CJK-aware 字符估算对中文小说场景是重大命中**：零依赖、快、对中文加权合理（中文 1 字 ≈ 1 token 到 4 token 视 tokenizer），比调 tiktoken-js 简单可靠；Python 侧实现同一套正则即可。
- 压缩护栏设计：写锁 + checkpoint + before/after hooks + 结果合理性校验 + safety timeout——我们长篇小说生成（超长上下文）必须防「压缩失败打坏会话」。
- compactionSummary 消息类型（把「被压缩掉的内容摘要」作为消息角色保留在 transcript 里，模型可见摘要、人可见原文）。
- 溢出前置预检 + 压缩后循环守卫（压缩后立刻死循环的检测）值得抄。

**不适合我们：**

- context-engine 插件协议（能力协商、thread_bootstrap）对我们是过度设计；保留「引擎接口」但只实现内置一个。
- memory-host-sdk 未验证，暂不评价。

---

## 5. 会话状态与持久化

**怎么做：**

- 存储：SQLite 为主（`~/.openclaw/state/openclaw.sqlite` 共享状态 + `agents/<id>/agent/openclaw-agent.sqlite` 每 agent auth/runtime 状态 + transcript 行），docs/openclaw-agent-runtime.md:47-68。
- **SessionManager 是树形 transcript**（`src/agents/sessions/session-manager-*.ts`）：
  - 条目带 `id/parentId`（父子链），支持**分支**（side-append、leaf control 标记，session-manager-core.ts:39-44）、fork/rebase（session-manager-branching.ts）、label 标记；
  - 版本化迁移：`CURRENT_SESSION_VERSION`，旧版本禁止运行时直接打开（session-manager-core.ts:86-90），走 doctor/import 迁移；
  - 持久化逐条同步写入（appendTranscriptMessageSync），**幂等键**（user 消息 idempotencyKey，session-manager-persistence.ts:193-221），重复投递安全；
  - prompt-released 侧分支合并（mergePromptReleasedSessionEntries，session-manager-persistence.ts:224-324）。
- 并发：会话写锁（`session-write-lock.ts`）、transcript 写上下文锁（compaction 持锁执行，compaction-session-execution.ts:119-133）。
- 轨迹：`src/trajectory/runtime.ts`（SQLite 事件记录，有大小上限/脱敏/超限丢弃策略，trajectory/runtime.ts:48-62）。
- 目录：`src/config/sessions/`（session-accessor、transcript-tree、version）。

**值得吸收：**

- **树形 transcript（parentId + 分支 + leaf 控制）**：写小说「多方案分叉对比」直接受益——不同章节走向并行分支、可回滚合并。
- 幂等键 + 写锁：我们 FastAPI 并发请求（用户连点、重试）下防重复写入。
- 每消息持久化 + 版本化迁移纪律。

**不适合我们：**

- SQLite 与 legacy 双轨迁移（旧 sessions/ 目录兼容）不需要。

---

## 6. 事件与可观测性

**怎么做：**

- **agent 层事件流**：`AgentEvent` 协议（见第 2 节），`Agent.subscribe()` 订阅，listener 按序 await（agent.ts:639-642）。
- **进程内 EventBus**：`src/agents/sessions/event-bus.ts`（pub/sub，**handler 异常隔离**——一个 subscriber 崩不影响后续，event-bus.ts:27-35）。
- **轨迹记录**：`src/trajectory/runtime.ts`——每次 run 的模型调用/工具/阶段事件入 SQLite，带大小预算（event ≤ 上限、先丢 messagesSnapshot 保 usage/promptCache，trajectory/runtime.ts:57-62, 78-105）、密钥脱敏（redactSecrets）、payload 消毒（sanitizeDiagnosticPayload）。
- **OpenTelemetry 扩展**（extensions/diagnostics-otel/README.md）：traces/metrics/logs → OTLP collector（Grafana/Datadog 等），也可 stdout JSONL。可选插件而非内置。
- 其他：usage 累加器（usage-accumulator.ts）、prompt-cache 可观测（prompt-cache-observability.ts）、status 消息系统（src/status/）、阶段计时（run/attempt-stage-timing.ts，启动各阶段打点）、诊断模型调用事件（attempt.model-diagnostic-events.ts）。

**值得吸收：**

- 事件协议作为「唯一事实流」：UI 渲染、持久化、观测全部消费同一事件流（我们的 SSE 推送直接映射）。
- handler 异常隔离的 EventBus 模式（Python 端 event bus 也常见，但「隔离失败」要显式做）。
- 轨迹事件大小预算 + 降级策略（先丢大字段保关键字段）——防观测本身拖垮系统。
- OTEL 做成可选插件而非核心。

---

## 7. steering / 人机协作（本项目最关心）

**怎么做：**

核心机制在 `packages/agent-core`，三层：

1. **注入队列（steering / follow-up 双队列）**：
   - `Agent.steer(msg)`：排队消息，**在当前 assistant turn 的工具执行完成后、下一次 LLM 调用前注入**（agent.ts:332-334；getSteeringMessages 在 loop 内轮询，agent-loop.ts:286, 441）；
   - `Agent.followUp(msg)`：**只在 agent 本要停止（无工具、无 steering）后**注入再续跑一轮（agent.ts:337-339；外层循环 agent-loop.ts:447-453）；
   - 队列 drain 模式：`QueueMode = "all" | "one-at-a-time"`（types.ts:43）——one-at-a-time 保证每条 steering 消息都独占一次「注入+LLM 响应」机会（PendingMessageQueue.drain，agent.ts:180-194）；
   - 语义注释（types.ts:262-279）：steering = 用户在中途打字注入方向（"Use this for steering the agent while it's working"）；followUp = 等 agent 干完再追加。
2. **agent 主动提问（反向 steering）**：`askUser` / gateway-question（src/agents/harness/user-input-bridge.ts:4-17 的 AgentHarnessUserInputQuestion：header/question/options/multiSelect/isSecret/isOther）——agent 运行中需要输入时把问题投到 channel，用户异步回答后回到 agent。
3. **交互消息载体**（`src/interactive/payload.ts`）：MessagePresentation（tone/按钮样式）+ 类型化动作（command / callback / approval / **question** / url / model-picker，payload.ts:70-98）——跨通道可移植的交互 UI。
4. **审批流**：exec approvals（见第 3 节）——高风险工具的用户确认。
5. **session yield**：`sessions_yield` 中断当前 run（SESSIONS_YIELD_ABORT_REASON，run/attempt.sessions-yield.ts）——子代理让出控制权回父。

另外 `prepareNextTurn` hook（types.ts:251-253）可在 turn 间替换 model/context——「换模型继续写」的机制。

**值得吸收（对写小说场景）：**

- **steer/followUp 双队列就是我们需要的「生成中干预」与「完成后追加」**：用户读一段生成结果 → steer 改大纲方向；整章写完 → followUp 追加下一章要求。one-at-a-time 模式防「多条指令挤一次 prompt」。
- 队列轮询点放在循环的自然检查点（turn 结束后、下一 LLM 调用前），实现简单且语义清晰。
- agent 主动提问（askUser 多选/secret）可用于「写不下去时问作者选 A/B/C 走向」。
- approval 流（危险操作确认）对应我们「覆盖已有章节」「删除分支」等破坏性操作。

**不适合我们：**

- 跨 messaging channel 的交互载体（按钮/回调走 WhatsApp 等）不需要，但动作类型枚举（approval/question/callback）的建模思路可借鉴到 API 响应里。

---

## 8. 任务/规划系统

**怎么做：**

- **没有显式 planner/任务分解器**。编排由三件套组成：
  1. **goal 系统**（docs/tools/goal.md）：**会话级持久目标**——一个目标挂在 session key 上，跨重启存活，`/goal start/edit/pause/resume/complete`，模型侧有 `get_goal/create_goal/update_goal` 工具，TUI footer 常驻显示，有 token 预算。文档明确区分：「goal 不是任务队列」，不调度、不后台、不 cron。
  2. **task registry**（`src/tasks/`）：SQLite 持久任务记录，状态机 queued → running → succeeded/failed（task-registry.types.ts），带 deliveryStatus（投递状态）、取消（task-cancellation-state.ts）、保留期（task-retention.ts）、审计。任务运行时多样：detached（后台）、subagent、ACP（task-executor.ts:51-59）。
  3. **task flow**（task-flow-registry.ts）：多任务编排流——flow 关联多个 task，支持取消级联、owner 权限校验（task-owner-access.ts）。
- 子代理 fanout（第 3 节）是主要「分解」手段：父 agent 用 sessions_spawn 拆任务，结果 push 回来。

**值得吸收：**

- **goal = 轻量持久目标而非任务队列**：写小说「本次会话要完成第 X 章并保持人物一致性」——一个常驻可见的目标 + 3 个模型工具，比复杂 planner 划算得多。
- task registry 状态机 + 投递状态 + 取消 + 保留期：我们后台生成任务（长章生成）可直接用（Python 侧 SQLite/DB 模型）。
- 子代理 fanout + push 完成模型（非阻塞、不轮询）——多角色写作（大纲 agent / 正文 agent / 校对 agent）的协作模式。

**不适合我们：**

- ACP/外部 harness 任务运行时不需要。

---

## 9. provider 接入层

**怎么做：**

- **归一化契约**（`packages/llm-core/src/types.ts`）：
  - 消息模型：`UserMessage / AssistantMessage / ToolResultMessage`（types.ts:300-347），AssistantMessage 含 `usage`（cacheRead/cacheWrite 拆分 + 成本，types.ts:271-294）、`stopReason: "stop"|"length"|"toolUse"|"error"|"aborted"`（types.ts:297）、`responseId/turnId`（turn 身份，供回放/续跑）、`diagnostics`（脱敏错误诊断）；
  - thinking 归一化：`ThinkingLevel: off|minimal|low|medium|high|xhigh|max` + 每级别 token 预算（types.ts:36-49）+ provider 特定值映射（ThinkingLevelMap）；
  - transport：`"sse"|"websocket"|"websocket-cached"|"auto"`（types.ts:55）；cacheRetention（none/short/long）、sessionId（缓存感知）、promptCacheKey（types.ts:97-108）。
  - 已知 API 族：openai-completions / openai-responses / anthropic-messages / google-generative-ai / mistral-conversations / bedrock-converse-stream / google-vertex 等（types.ts:6-15）。
- **StreamFunction 契约（关键）**（types.ts:203-218）：**错误必须编码进流，不得 throw**——终止时产出 stopReason="error"/"aborted" 的 AssistantMessage + errorMessage；流事件协议 start → text/thinking/toolcall delta → done/error（types.ts:399+）。
- 实现层 `packages/ai/src/`：
  - providers/：每 API 族一个适配器（anthropic.ts、openai-completions.ts、openai-responses.ts、google.ts、mistral.ts…），各有 tool projection（openai-tool-projection.ts、anthropic-tool-projection.ts——把 TypeBox schema 投影成各 provider 的 tool 格式）、schema keyword 剥离（schema-keyword-strip.ts，provider 不认识的 JSON-schema 关键字）、prompt cache 处理、usage 解析（anthropic-usage.ts、openai-responses-terminal-usage.ts）；
  - transports/：SSE/WS 传输层（openai-responses-transport.ts、anthropic-transport-stream.ts）、payload 策略（anthropic-payload-policy.ts）、reasoning 兼容（openai-reasoning-compat.ts）；
  - tool call 解析/修复：`tool-call-repair` 包 + openai-completions-tool-calls.ts + openai-responses-tool-call-tracker.ts（流式跟踪 toolcall delta 拼装）。
- 认证：auth profile（API key + OAuth 登录流），`getApiKey` 动态解析（agent.ts:117，防长任务中 token 过期，types.ts:229-232）；provider-runtime 目录（src/provider-runtime/）。
- 模型目录/选择：model-catalog、model-picker（用户换模型 UI）、configured-fallback（模型 fallback 配置）。

**值得吸收：**

- **归一化消息 + 归一化 stopReason + usage 归一化**：我们 Python 侧接多个 provider（Claude/DeepSeek/本地）时，这是接入层必须的第一件事。
- **错误编码进流的契约**：调用方只处理一种「流结束态」，比异常/超时各自为政好。
- TypeBox schema → provider tool 投影 + 关键字剥离：Python 对应 pydantic model → provider JSON-schema 的转换层，注意各 provider 对 JSON-schema 方言的接受度。
- turn 身份（responseId/turnId）+ 回放（replay-state）支持「续跑/重试同一 turn」。

**不适合我们：**

- 十几种 provider 适配器 + OAuth 订阅登录（Copilot/Codex）不需要，留 1-3 个即可。
- websocket transport 对我们是可选优化。

---

## 10. agent 测试设施

**怎么做：**

- **core 层单元测试**（`packages/agent-core/src/agent-loop.test.ts`）：vitest，**注入 fake streamFn**（`failingStreamFn`，test:56-58）+ 直接断言事件序列（collectEvents + expectTerminalFailure，test:60-76）——不需要真实 LLM，测试的就是循环行为（失败终止、中断恢复、steering 注入顺序）。
- **harness 测试帮助**：packages/agent-core/src/harness/（messages.ts、prompt-templates.ts、session/uuid.ts、compaction/）。
- **QA 场景系统**（qa/README.md + qa/scenarios/*.yaml）：YAML 定义可执行端到端场景——objective / successCriteria / execution flow 步骤（waitForGatewayHealthy、startAgentRun、waitForAgentHistoryReply、waitForCondition、assert、forEach 重试）。
  - 亮点：**mock provider（mock-openai）与真实 provider 双跑**（同一场景两套执行路径，scenarios/agents/subagent-fanout-synthesis.yaml:57-59）；
  - **工具调用 ground truth 断言**：mock 的 `/debug/requests` 记录 plannedToolName/plannedToolArgs，断言模型「真的调用了 sessions_spawn 两次且 label 不同」而不是文本编故事（该 yaml:136-157 的注释讲得很清楚）。
- 契约测试：plugin-sdk 的 agent-runtime-test-contracts.ts / channel-contract-testing.js（对外契约锁定）。
- live 测试：`OPENCLAW_TEST_LIVE=1` + 真实凭据（docs/openclaw-agent-runtime.md:30-36）。

**值得吸收：**

- **「注入假 LLM 流 + 断言事件序列」的 core 测试模式**：我们 agent 循环的单元测试就该这样——确定性、无网络、测控制流。
- QA 场景 YAML 化 + mock/真实双跑 + 工具调用 ground truth 断言：端到端回归「agent 真的用了工具 X」而不是「文本提到工具 X」——写小说场景可断言「真的调用了 outline 工具、真的写入了章节文件」。

---

## 总结：最值得吸收的 10 条设计

1. **steer/followUp 双注入队列 + one-at-a-time drain 模式**（agent.ts:332-339, types.ts:262-279）——用户生成中改方向 / 完成后追加，直接命中写小说交互。
2. **归一化消息 + 事件流协议（agent_start…agent_end）+ 错误编码进流**（llm-core/types.ts:203-218, agent-core/types.ts:548-587）——层间契约的唯一事实流，UI/持久化/观测共用。
3. **工具生命周期六阶段管线**（resolve→prepare→validate→before(block)→execute(流式 update)→after/outcome，agent-loop.ts:975-1263）+ terminate 全票终止 + deferred 水合。
4. **CJK-aware 字符 token 估算**（normalization-core/cjk-chars.ts）——零依赖、中文加权合理，比 tiktoken 更适合小说场景预算管理。
5. **compaction 护栏全套**：写锁 + checkpoint + before/after hooks + 结果合理性校验 + safety timeout + 压缩后循环守卫（compaction-session-execution.ts, compaction-hooks.ts:279-298）。
6. **树形 transcript（parentId 分支 + leaf 控制 + 幂等键）**（session-manager-core.ts）——章节多方案分叉/回滚/合并的持久化基础。
7. **工具结果 network 污染标记（turn taint）**（agent-loop.ts:1344-1394）——区分外部检索内容与模型原创内容的信任边界。
8. **goal 轻量持久目标系统**（docs/tools/goal.md）——会话级常驻目标 + 3 个模型工具，不做重 planner。
9. **子代理 spawn 非阻塞 + push 完成 + 独立 session + context fork**（docs/tools/subagents.md, sessions_spawn）——多角色写作编排（大纲/正文/校对）的协作模型。
10. **测试双轨**：core 注入假 LLM 流断言事件序列（agent-loop.test.ts）+ 端到端 YAML 场景 mock/真实双跑与工具调用 ground truth 断言（qa/scenarios/）。

**对重构的粗粒度提示**（仅为参考，不构成修改建议）：openclaw 的核心洞察是「循环是薄的、协议是显式的、干预是排队式的」——agent 循环本身只有 ~460 行（agent-loop.ts），大量复杂度在宿主集成层（会话/认证/hook），我们重构时保持 core loop 薄、把小说领域逻辑放宿主层，与 openclaw 的分层一致。
