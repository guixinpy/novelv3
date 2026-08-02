# Research: openhuman（Rust 开源 agent 框架）架构研究报告

- **Query**: 研究 docs/references/agent-projects/openhuman/ 的后端/核心运行时架构，为我们的写小说 agent（FastAPI + Python）重构吸收优秀设计
- **Scope**: internal（本地代码库深读）
- **Date**: 2026-08-02
- **项目路径**: `docs/references/agent-projects/openhuman/`（以下相对路径均基于该目录）

---

## 0. 项目定位速览

OpenHuman 是"个人 AI 超级智能"桌面应用（Tauri + React 前端，Rust 核心单 crate `openhuman-core`），定位为 **orchestrator 而非 chatbot**：一个「会记忆一切的脑」（Memory Tree + Obsidian vault）、一个「在持久图上跑 agent 舰队的编排器」、一个「深度研究员」（SuperContext 预扫 + 100+ OAuth 集成 / 5000+ MCP / 90000+ Skills）。

**最重要的架构事实（决定整个代码形态）**：agent 执行引擎**不自研**，而是委托给发布版 crate [tinyagents](https://crates.io/crates/tinyagents)（LangGraph/LangChain 风格的持久化状态图 + agent 循环 harness + 模型/工具注册表 + middleware/retry/limits），openhuman 通过 `src/openhuman/tinyagents/` 适配层接入，自己保留「产品策略层」（凭证、OAuth、接入门、端点选择、计费、错误分类、子代理构建流水线、会话外壳）。记忆引擎同理委托给 tinycortex（内存树），工具输出压缩委托给 tinyjuice（TokenJuice）。三者均为 git submodule vendor 进来并可先行在库内测试。

架构文档入口：
- `gitbooks/developing/architecture/agent-harness.md` — agent turn 生命周期权威文档（本报告大量引用）
- `src/openhuman/agent/README.md`、`src/openhuman/context/README.md`、`src/openhuman/mcp_client/README.md` 等 — 每个域自带 README，统一含 Public surface / RPC / Events / Persistence / Dependencies / Used by / Notes gotchas 小节（**域文档化模板极佳**）

---

## 1. 整体架构与模块分层

### 该项目怎么做

**单 crate + 域模块**（不是多 crate workspace）：root crate `openhuman_core`（`Cargo.toml`），业务域全部在 `src/openhuman/*`（约 40+ 域：agent、agent_orchestration、context、memory_*、inference、tools、mcp_client、mcp_registry、config、orchestration、subconscious、learning、approval、cost、triage 等），传输层在 `src/core/`（jsonrpc、event_bus、logging、shutdown）。前端 Tauri 是**独立 Cargo world**（两个 Cargo.lock），与核心通过 JSON-RPC + bearer 通信。

核心分层决策（`src/openhuman/agent/README.md:3`）：
- **agent 域**：拥有 LLM tool-calling 循环、子代理派发、会话转录、triage 管线、prompt 资产。**不**拥有 provider HTTP 传输（inference/）、工具实现（tools/）、prompt 组装（context/）、记忆存储（memory/）。
- **agent_orchestration 域**（`src/openhuman/agent_orchestration/README.md:3-7`）：高层**控制面**（parent/child lineage、生命周期状态、wait/close/follow-up、UI 事件）；**agent::harness 是执行引擎**（prompt 构建、策略过滤工具、模型选择、子代理循环）。控制面与数据面分离。
- **context 域**（`src/openhuman/context/README.md`）：纯逻辑/状态追踪域，无 RPC、无事件、无持久化。
- **每个域有固定文档模板**：README 里统一列 Public surface / RPC / Events / Persistence / Dependencies / Used by / Notes & gotchas — 新工程师几分钟内可定位任何东西。

**运行时分层**：inbound（用户消息/频道/webhook/cron/composio）→ 外部触发器先过 **triage**（小模型分类）→ `Agent::turn`（resume 转录 → 构建 system prompt【仅第一轮】→ 注入记忆 → 进工具循环 → 上下文守卫/压缩 → stop-hook 检查 → 终答）→ 后台 post-turn hooks（archivist / learning / 成本日志 / 情景记忆索引）。

### 值得吸收的点

1. **域模块化 + 每域 README 文档模板**（Public surface/RPC/Events/Persistence/Dependencies/Used by）。我们 Python 端同样可以用 `src/<domain>/README.md` 固定模板约束文档。
2. **控制面/数据面分离**：agent_orchestration（编排语义）与 harness（执行）分离，编排层明确"不得加宽子代理工具可见性"（`agent_orchestration/README.md:41`）。
3. **「自研循环交给发布版框架 + 适配层」**：不重复造轮子；把自己的差异化价值放在适配层（凭证/策略/记忆/产品语义）。对 Python 生态的对应物是直接用成熟 agent 框架（如 langgraph）而非自研 while 循环——但注意本项目此前已自研了循环，吸收点是"循环本身不追求通用化，策略层才是产品"。
4. **域之间通过文档化的依赖方向强制解耦**（agent 不 import provider HTTP，只通过 trait/适配层）。

### 不适合我们的原因（若有）

- 单 crate + 40 域对小说项目过重；我们应保持轻量包结构，只借鉴"域 README 模板"与"控制面/数据面分离"两个点。
- 委托发布版 crate 的前提是有维护 vendor 的预算；我们若自研循环，重点是照抄其**循环外策略层**设计而非图引擎。

---

## 2. agent 循环模型（turn/step、终止、预算、重试、guard）

### 该项目怎么做

**统一入口**：三个调用路径（chat 会话、频道/CLI bus、run_subagent）全部驱动同一个 tinyagents `AgentHarness`（`run_turn_via_tinyagents_shared`，`src/openhuman/tinyagents/mod.rs:525`），"因为三个入口组装同一个 harness，所以它们不会漂移"（`agent-harness.md:154`）。

**RunPolicy 配置**（`src/openhuman/tinyagents/mod.rs:186-247`）：
- `max_model_calls = max_iterations`（默认 10 轮）；`max_tool_calls = max_iterations × 8`；`max_depth = MAX_SPAWN_DEPTH(3)`；`max_wall_clock_ms`（默认 600s，env `OPENHUMAN_AGENT_TURN_TIMEOUT_SECS` 可改，0=无上限）——注意 wall-clock 上限会同时包装**每个** model/tool 调用（`tokio::time::timeout`），这是修"turn 空回复"（模型流挂死）的关键。
- **重试**：`RetryPolicy { max_attempts: 3, initial_backoff_ms: 500, max_backoff_ms: 30000, multiplier: 2.0, backoff_sleep: true }`（`mod.rs:209-216`）；**可重试性由 crate 判定**——永久性错误（config/auth/quota/context）映射为不可重试 Validation 错误，瞬时故障（429/5xx）映射为可重试 Model 错误。
- **未知工具**：`UnknownToolPolicy::ReturnToolError`——注入一条可恢复的 `unknown tool <name>; valid tools: [...]` 工具结果，模型自行纠正，而不是 abort run（`mod.rs:231`）。**非法参数同理**：`InvalidArgsPolicy::ReturnToolError`（`mod.rs:237`）。
- **响应缓存**：仅对确定性内部 run 启用，交互式聊天永不使用缓存响应（双保险，`mod.rs:243-247`）。

**循环内每轮**（`agent-harness.md:137-152`）：context guard（过大则 microcompact/autocompact）→ stop-hook 检查 → provider 调用（流式）→ 解析 assistant 文本/工具调用 → 无工具调用则返回最终文本 → 执行工具 → 超大结果过 summarizer → 追加结果 → 回到循环。

**终止/预算护栏家族**（全部实现为 middleware，注册顺序见 `mod.rs:1857-2304`）：
- **Stop hooks**（`tinyagents/stop_hooks.rs` + `agent/stop_hooks.rs`）：预算上限、线程目标预算、迭代上限等**策略**类终止，每轮后触发，首个 stop 票即 pause 整个 run。
- **CostBudgetMiddleware**（`middleware.rs:1904`）：日/月 USD 成本预算前置检查，超了在 model 调用前 fail。
- **RepeatedToolFailureMiddleware**（`middleware.rs:2074`）：3 次**连续相同失败**（指纹 = 工具名+参数）→ Nudge（注入"自 step X 无进展"纠正消息）→ Halt（记录 root-cause 摘要 + pause）。可恢复性失败（timeout/连接重置/429/5xx）给更宽裕的阶梯。
- **RepeatProgressMiddleware**（`middleware.rs:2688`）：对称地防**成功但空转**——模型重复发相同的成功 no-op 调用也 halt。
- **CapPauser**（`mod.rs:776-780`）：达到模型调用上限时**优雅暂停**并返回部分转录，调用者可 summarize 成 checkpoint 而非报错。
- **wall-clock 上限**（见上）。

**循环外：interrupt（用户驱动）与 stop hook（策略驱动）分开**（`agent-harness.md:390-398`）：两者都进入同一个 harness pause/stop 管道，但来自不同侧。中断走 tinyagents steering channel，在每个工具执行前/子代理 spawn 前/provider 调用前检查；中断后 archivist 仍会用部分上下文收尾。

**失败分类学**：每个失败工具调用分类为 `ClassifiedFailure { class, category, cause_plain, next_action, recoverable }`（`tool_status/`），类别如 MissingPermission / MissingApp / ServiceUnavailable / BadCredentials / BlockedByPolicy / ModelConnection / Timeout / Denied / ApprovalExpired；类别 1:1 映射 UI 状态：可自动重试 / 改设置 / 需用户确认 / 用户拒绝（永不自动重试）。

### 值得吸收的点

1. **护栏家族而非单一 try/except**：迭代上限、USD 预算、wall-clock（含每调用 timeout）、无进展断路器（失败型）、空转断路器（成功型）、未知工具/非法参数"降级为可恢复错误"——这套组合拳正是我们小说生成 agent（长链工具调用、模型反复出错）最需要的。
2. **优雅暂停优于硬失败**：到预算先 pause + 返回部分转录 + 事后可恢复（对应我们"写了一半的长章节"场景——应当能 checkpoint 续写而非丢）。
3. **未知工具/坏参数 = 可恢复错误注入**，让模型自我纠正，而不是 abort 整个 run。
4. **失败分类带 next_action 与 recoverable 标志**，上层（UI/重试策略）据此决策。
5. **stop hooks 与 interrupts 双入口设计**：策略终止与用户终止走同一管道不同来源。
6. **统一 harness、三个入口**：chat/后台/子代理共用一条路径，防止行为漂移。

### 不适合我们的原因（若有）

- 10 轮默认迭代上限对写小说 agent 太紧（长章节需要 Extended 策略——openhuman 本身提供 `IterationPolicy::Extended` 到 50 轮，`definition.rs:35`），我们应默认宽松。
- 30000ms 回退对对话场景合理，对我们内部批处理可更长。

---

## 3. 工具/技能系统

### 该项目怎么做

**Tool trait**（`src/openhuman/tools/traits.rs:257`）：`name()` + `permission_level()`（+ `permission_level_with_args`）+ `spec()`；`PermissionLevel` 是全序枚举（None → ReadOnly → … → Dangerous）。

**三层可见性过滤**（从宽到窄，会话构建期 + run 组装期）：
1. `Agent.visible_tool_names`（`session/types.rs:50`）——主 agent 显式可见白名单，空 = 全部可见（向后兼容）；`subagent_tool_ceiling_names` 是"委托给子代理的继承天花板"（`types.rs:56`）。
2. **ToolPolicySession**（`agent_tool_policy/README.md`）：per-channel 权限上限 → 每工具 `Allow / RequireApproval / Deny / HideFromPrompt` 四分类，生成不可变快照；运行时未知工具名默认 **Deny（fail-closed）**；`visible_tool_names_for_prompt()` 在"有限制但无一允许"时插入 `NO_TOOLS_ALLOWED_SENTINEL` 防止 prompt 误显示无限制。
3. **AgentDefinition 级**（`harness/definition.rs:148-167`）：`tools: ToolScope`（All/None/Named/Except）+ `disallowed_tools` + `skill_filter` + `extra_tools`。

**注册层 fail-closed**（`mod.rs:1916-1965`）：`allowed == None` → 不过滤；`Some(set)` → **恰好**注册 set 内工具（空 set 全拒）。防御性硬约束：**子代理 run 上绝不允许注册 spawn/delegate 类工具**（`is_subagent_spawn_or_delegate_tool`，`mod.rs:1945`），即使 allowlist 拼错也不会把 spawn 能力漏给子代理。

**工具执行 middleware**（tool middleware，`mod.rs:2257-2304`）：
- `ApprovalSecurityMiddleware`：外部副作用工具拦截全局 ApprovalGate，拒绝返回模型可消费的结果 + 审计行；10 分钟 TTL 自动 Deny。
- `CliRpcOnlyMiddleware`：限定 CLI/RPC 的工具不得从模型循环调用。
- `ToolPolicyMiddleware`：builder 配置的 policy 在工具边界强制。
- `CredentialScrubMiddleware`：**最内层**包裹，凭证形状的 secret 从原始工具结果中打码，之后所有层看到的是已打码内容。
- `ArgRecoveryMiddleware`：修复 JSON-encoded-string/markdown-fenced 参数；对 required-field schema 的原样放行给 crate 报错。

**MCP 接入**（`mcp_client/README.md`）：双传输（Streamable HTTP + stdio 子进程 JSON-RPC）；HTTP 支持 OAuth 发现（WWW-Authenticate → 元数据发现）；**allow/deny 在传输前 fail-closed 执行**（`is_tool_allowed`）；`redact_endpoint` 保证 URL 凭证不落日志；stdio 重建 PATH（从登录 shell 探测），缺失 npx/uvx 给可操作安装指引而非裸 ENOENT。`mcp_registry` 是动态安装 + 监管面，`mcp_client` 是纯传输库。

**子代理编排**（`agent-harness.md:272-291` + `agent_orchestration/subagent_sessions/`）：
- `spawn_subagent` 默认**持久化 + 异步**：从会话/线程/agent id/工具范围/模型覆盖/sandbox/任务 key 构建确定性兼容选择器 → 兼容 worker 已运行则注入指令（RunQueue）、空闲/暂停则复用历史（`initial_history`）、不兼容则新建 durable session + worker 线程。
- `wait_subagent` / `steer_subagent`（可传 durable id 或 transient task id）/ `list_subagents` / `close_subagent`；inline blocking 显式传 `blocking: true` 不再是默认。
- 跨 turn 连续性：`[active_subagents]` roster 合并内存 registry + durable store（冷启动也可见旧 worker）；`continue_subagent` 从 pause checkpoint 或 durable store 恢复。
- **合成委托工具**（`delegate_<archetype>`、`delegate_<toolkit>`）在 `agent_orchestration/tools/`，随会话动态合成/刷新（`synthesized_tool_names` 掩码跟踪，`session/types.rs:337-371`）。

**工具结果体积治理**（三级，`agent-harness.md:168-230`）：
1. 每调用 byte 预算（超限硬截断 + 说明性标记）；
2. 超大结果 → summarizer 子代理压缩（保标识符/关键事实），失败有断路器降级硬截断；
3. **artifact offload**：长任务把大结果写到 `action_dir/outputs/`（交付物）/`action_dir/workspace/`（临时），回传 `[artifact] kind=output path=... bytes=...` 指针 + 摘要；路径解析 fail-closed（拒绝对路径/`..`/workspace 内部）。
4. **TokenJuice**（`tokenjuice/README.md`）：内容感知路由压缩（JSON→表、Code→tree-sitter 签名保函数体塌缩、Log→100 规则、Search→top-K、Diff→保留变更 hunk、HTML→去标记），压缩前把原文存入 CCR 存储，`⟦tj:<hash>⟧` 标记可无损取回。

### 值得吸收的点

1. **工具可见性三层过滤 + fail-closed**：小说场景里"主 agent 可见全部、子代理按职责裁剪"（如"角色卡工具"与"正文工具"分离）直接可用。
2. **defense-in-depth 的硬约束**："子代理绝不允许拥有 spawn/delegate 工具"——在注册层（而非 prompt 层）强制，即使 allowlist 出错也不会越权。
3. **失败/拒绝 = 模型可消费结果**：approval 拒绝、未知工具、坏参数都变成一条工具结果消息，模型自己调整策略——这是 agent 循环鲁棒性的核心手段。
4. **工具结果三级治理（截断 → 摘要 → 落盘指针）**：对应我们"章节草稿/设定文档大输出"场景——把大产出移出上下文、传路径比传全文好得多。
5. **CredentialScrub 作为最内层包裹**：任何工具输出进上下文前先打码。
6. **MCP 的 pre-transport allow/deny + endpoint 打码**：如果我们的工具系统将来接 MCP，照抄这两点。

### 不适合我们的原因（若有）

- MCP 双传输 + OAuth 发现是重量级外部集成需求，我们当前不需要；但"工具注册 schema + allow/deny"的最小形态值得保留。
- 动态合成 delegate 工具（会话中途刷新工具集）很精巧但复杂，我们若无"动态连接外部服务"需求可省。

---

## 4. 上下文管理（压缩/摘要/token 计量/记忆/检索）

### 该项目怎么做

**KV-cache 优先的全局设计原则**（反复出现，`agent-harness.md:117-122`、`context/README.md:89`）：
- system prompt **只在第一轮构建**，之后字节级冻结——任何动态内容（记忆召回、新装的技能、新连的集成）都**骑在用户消息上**附加，绝不改 prompt 前缀。
- 会话转录恢复时加载**字节完全一致**的历史（`cached_transcript_messages`），保证推理后端 KV-cache prefix 命中。
- `PromptCacheGuardMiddleware`（`mod.rs:2102`）监控前缀稳定性，易变内容破前缀时发 `CacheLayoutEvent` 诊断事件。

**循环内两层压缩**（`mod.rs:2206-2239`）：
1. `ContextCompressionMiddleware`：token 估算达窗口 90%（`SUMMARIZE_THRESHOLD_FRACTION`）时，把历史**前段**折叠成一条 LLM 生成的 system 摘要（system 消息 + 最近窗口保持原样——KV 稳定性）。
2. `ImageAwareMessageTrimMiddleware`：确定性硬顶——图片按平价 token 计价、system 消息永不丢弃、超限时前端裁剪并打日志。这是"摘要失败后的兜底"，不是首选。
3. `FaultTolerantCachingSummarizer`（`summarize.rs`）：摘要失败不 abort run（warn + 断路器 + 确定性 trim 兜底）；相同输入切片不重复调摘要 LLM（每 turn 缓存）。

**工具结果微观治理**：`MicrocompactMiddleware` 清工具结果体；每调用 byte 预算在 tool-output middleware 强制。

**记忆系统**（`memory_tree/README.md` + `memory_store/`）：
- **Memory Tree**：记忆树 append → 桶满 cascade seal → LLM 摘要生成下一层（`summarise.rs`），SQLite 持久化；评分/嵌入/实体抽取在 `score/`；检索工具 `walk`（agentic）/`drill_down`/`fetch_leaves`/`query_{source,global,topic}`/`search_entities`。每个用户消息前 `MemoryLoader` 注入相关块**并附引用**（UI 显示出处）。
- 分层原则：`memory_tree`（通用机制，kind 无关）→ `memory::tree_global/tree_topic`（策略），`memory_store::trees`（持久化）——**机制/策略/持久化三层分离**。
- **SuperContext**（`tinyagents/middleware.rs:276` + `retriever.rs`）：turn 前 context scout 子代理预扫记忆与文件，把 bundle 折叠进首条用户消息。
- **SessionMemory**（`context/session_memory.rs`）：token 增长 + 工具调用数 + turn 数**三个阈值全过**才触发后台 archivist 提取 → 写入持久 `MEMORY.md`；提取失败保留 delta 下轮重试。
- **Token 计量**：本地 `estimate_tokens` 估算（tinyjuice `tokens.rs`），**不用 tiktoken-rs**（避免重型依赖）；`model_context.rs::context_window_for_model` 提供各模型窗口尺寸用于预派发预算。
- **Goals 记忆**：`MEMORY_GOALS.md`（200-500 token 的持久目标清单，`memory_goals/mod.rs`），goals_agent 反思式增删改，**不注入主 prompt**。

### 值得吸收的点

1. **KV-cache 优先的上下文设计**：prompt 冻结 + 动态内容骑用户消息——对我们的"生成小说"场景 = 世界观/人物卡/文风设定等稳定内容一次性进 prompt，剧情进展/最近上下文作为可变尾部，天然利于缓存与稳定。
2. **两级压缩（LLM 摘要为主 + 确定性裁剪兜底）+ 摘要失败容错**：摘要失败绝不 abort，降级确定性裁剪——写长文时这是保命设计。
3. **机制/策略/持久化三层分离**（memory_tree 的层规则）：通用机制不掺业务策略，可测试性极好。
4. **阈值门控的后台记忆提取**（三阈值全过才提取）——避免每轮都做记忆开销。
5. **记忆注入带引用出处**（citation）——我们的小说 agent 引用设定文档时同样需要可溯源。
6. **本地 token 估算而非 tiktoken 绑定**——轻量、离线可用；如需要精确值再换。

### 不适合我们的原因（若有）

- Memory Tree 的桶/级联摘要/评分是通用记忆引擎，小说项目用"设定库 + 检索"即可，不必复刻树结构。
- SuperContext 预扫子代理对我们可能过重，简单预加载足矣。

---

## 5. 会话状态与持久化

### 该项目怎么做

**转录**（`harness/session/transcript.rs`）：
- 源文件 `{workspace}/session_raw/{stem}.jsonl`（**append-only 事件日志**）：首行 `_meta` 元数据 + 每消息一行 JSON；每次写入后配套渲染 `sessions/YYYY_MM_DD/{stem}.md` 人类可读视图（**从不读回**，round-trip 只用 JSONL）。
- append 策略：纯扩展 → 只追加尾部；压缩/改写（历史被折叠）→ 追加一条 `{"kind":"compaction","replacement":[...]}` 记录，旧行不动。读路径：消息行累积、compaction 记录**替换**累积器、`interrupted:true` 部分行跳过。新记录种类加 `_extra` catch-all 字段，旧核心读新文件跳过未知 kind 不崩溃（**前后向兼容**）。
- `stem = {unix_ts}_{agent_id}`；子代理用 `session_parent_prefix` 链成**目录树**（`session_raw/DDMMYYYY/{parent_key}/{child_key}.jsonl`），嵌套委托在磁盘上形成树（`session/types.rs:177-190`）。

**运行台账（run ledger）**：
- `SqlRunLedgerCheckpointer`（`tinyagents/checkpoint.rs`）：TinyAgents `Checkpointer` trait 适配到 openhuman SQLite `graph_checkpoints` 表——图 run 在每 super-step 边界持久化，崩溃/暂停从最后节点恢复。
- 各产品域自己的 durable ledger：`workflow_runs`、`running_subagents`、`agent_teams`、`command_center`、`subagent_sessions`（`agent-harness.md:517-522`）。
- 子代理 `AwaitingUser` 检查点：`{workspace}/.openhuman/subagent_checkpoints/{task_id}.json`（历史+问题+选项+覆盖项），用户回答后续跑。
- **事件日志**：`StoreEventJournal`（JSONL append store，`{workspace}/tinyagents_store/journal`，`tinyagents/journal.rs`），`FanOutSink`（live bridge + journal）→ `RedactingSink`（持久化前凭证打码），事件 id 为重启稳定的 `{run_id}-evt-{offset}`——**即使没人观察的后台 turn 事后也可完整重建**。
- **双写 shadow 迁移**：session 消息双写到 TinyAgents store（`config.session_dual_write` 默认开），shadow-read 校验 parity——渐进迁移的工程模式。

### 值得吸收的点

1. **append-only 转录 + compaction 记录**（而非全量重写）：缩了历史不丢原始行，显示层能看到完整时间线，模型层回放得到字节一致结果。
2. **schemaless 前向兼容**（未知字段 catch-all、未知记录跳过）——我们改存档格式不再破坏旧会话。
3. **转录目录树**（子代理按父链嵌套）——对应我们的"多 agent 协同写作"（大纲 agent 生成的子会话挂在主会话下）。
4. **"即使无人观察也写 journal"**：一切 run 可事后重放/审计。
5. **持久化前凭证打码**（RedactingSink）。
6. **双写 shadow 迁移**：换存储格式时新老并存、差异打日志——低风险演进。

### 不适合我们的原因（若有）

- 多套 ledger（workflow_runs/agent_teams/command_center）是编排型产品需求，我们一个"会话表 + 事件日志"即可。

---

## 6. 事件与可观测性

### 该项目怎么做

**双层事件模型**（`core/event_bus/README.md:41-63`）：
- **run 内**：TinyAgents `AgentEvent` 流（每轮生命周期、进度、usage、缓存、压缩、工具暴露、steering），持久化到 journal；UI 通过重放 journal 重建 run 时间线（`agent_run_events` RPC，分页/offset/延迟接入）。
- **跨域产品信号**：`DomainEvent` 总线（`core/event_bus/events.rs`，`#[non_exhaustive]` 目录枚举，变体覆盖 Agent/Memory/Channels/Cron/Skills/Tools/Webhooks/System），`tokio::sync::broadcast` 单例（容量 256），`EventHandler` trait + RAII `SubscriptionHandle`，约 33 个调用点。
- **发射政策**：只有跨模块边界（run ledger、通知、cron、成本 footer、频道运行时）才上 DomainEvent 总线；子代理生命周期事件必须走唯一类型化拥有者 `agent_orchestration::subagent_events`，禁止手写 `publish_global`。

**实时进度流**：`AgentProgress` 枚举（`agent/progress.rs:18`）：`TurnStarted` / `IterationStarted{iteration, max_iterations}` / `ToolCallStarted{call_id, tool_name, arguments, display_label, display_detail}` / `ToolCallCompleted{success, output_chars, output, failure: Option<ClassifiedFailure>}` / …——UI 逐 token 渲染、工具状态、"调用工具 X"标签、每迭代成本。

**成本遥测**：每个 provider 响应带 `UsageInfo`（input/output/cached tokens + 权威 `charged_amount_usd`）；`TurnCost` 汇总 turn 内所有调用（含子代理）；`OpenhumanEventBridge`（`tinyagents/observability.rs`）把 harness 事件投影为 AgentProgress + 成本；provider 遥测 id `{provider_id}.{model}` 进 Langfuse。

**日志纪律**：每 turn `tracing::info!` 关键事件带 `[tinyagents]` 等前缀（grep 友好）；预期错误（provider 401/429/未知模型）降级为 warn 避免污染 Sentry，未分类错误才 error。

### 值得吸收的点

1. **run 内事件流持久化 + 事后重放**（journal 是 run 的 canonical record，总线只是跨域信号）——我们如果做"生成过程回放"（用户查看某章节是怎么写出来的），这就是现成范式。
2. **AgentProgress 事件枚举的形状**（call_id 贯穿 started→completed、iteration 计数、display_label）——UI 实时状态机的最小完备集。
3. **跨域事件唯一拥有者**（禁止手写 publish）——防止事件源混乱。
4. **失败分类进事件**（`ToolCallCompleted.failure` 带 ClassifiedFailure）——可观测性与可恢复性数据同源。
5. **预期错误降级日志**——避免监控噪音。

### 不适合我们的原因（若有）

- 双总线 + journal 重放对我们偏重，但"事件流即事实源"的单总线 + 持久化值得。

---

## 7. 任务/规划系统（plan、反思、任务分解）

### 该项目怎么做

**multi-agent 分层的背后是成本/延迟/深度分层**，不是花哨：`chat`（快，如 orchestrator）→ 可 spawn `reasoning`（慢，如 planner）+ `worker`（叶子）；`reasoning` 只能 spawn `worker`；`worker` 不能 spawn 任何东西（`agent-harness.md:293-327`）。理由：chat→chat 无意义（双倍 TTFT 不买新能力）、reasoning→reasoning 跑马（重复分解）、worker→anything 混合执行与编排。**强制双层**：loader 静态校验整个注册表 + 运行时 `MAX_SPAWN_DEPTH=3` task-local 计数器兜底。

**plan → execute ⇄ review → finalize**（`tinyagents/delegation.rs:1-40`）：多阶段委托表达为 durable 图：
```
plan ─▶ execute ─▶ review ──approved/maxed──▶ finalize ─▶ END
          ▲                   │
          └─────revise────────┘
```
- 条件路由（review 返回 Command 决定 revise 或 finalize）、`RecursionPolicy` 上限 revise 循环（+ 状态内 `revisions` 计数器双保险）、`Checkpointer` 每 super-step 持久化 `DelegationState`（崩溃恢复）、`CancellationToken` 协作取消（下一节点边界短路到 finalize）。
- **per-step provenance**：`StepRecord { index, prompt, result }` 记录每次 execute 的确切 prompt 与结果（后续 plan 编辑可 diff）。
- **worker 注入**（`run_delegation`）：编排机制用确定性 mock 单测；生产传闭包跑真实 run_subagent——**图机制与真实 agent 解耦可测**。

**并行 fan-out**：`spawn_parallel_agents` 走 `graph::parallel::map_reduce`（`agent_orchestration/spawn_parallel_graph.rs`）；workflow phase 引擎每阶段 `with_max_concurrency` fan-out，`workflow_runs` ledger 为恢复源；agent_teams 成员运行时是 `execute → complete|fail → done` 条件路由图 + SQL CAS 任务声明。

**目标与反思**：
- `memory_goals`：持久目标清单（`MEMORY_GOALS.md`），goals_agent 反思式维护（初始填充/增量），`enrich` 模块；不注入主 prompt。
- **reflection**（`learning/reflection.rs`）：每合格 turn 后 post-turn hook，构造反思 prompt → LLM（本地或云）→ 结构化 JSON 输出（`observations / patterns / user_preferences / user_reflections`）→ 存记忆（不同 namespace/类别，渲染时位于通用树摘要之上）。
- **subconscious**（`subconscious/README.md`）：Deep Reflection Layer——cron 驱动的离线循环，每"世界"一个 factory profile（`observe → prepare_context → reflect → commit`），以 tinyagents CompiledGraph 实现，含 tick 锁/代际计数器/30min 超时/provider 速率上限/`SqliteCheckpointer` 恢复；输出 to-dos、goals、notify_user、STEERING_DIRECTIVE 等。
- **triage**（`agent/triage/mod.rs`）：外部触发器分类管线（TriggerEnvelope → run_triage → TriageDecision → apply_decision：drop/notify/spawn reactor/spawn orchestrator），小本地模型 + 云端重试回退，决策缓存（相同触发器不重复分类）。
- 循环内轻量任务跟踪：`todo` 工具（`agent/tools/todo.rs`）+ ThreadGoals 预算 + TaskBoard（`tinyagents/todos.rs` 的 shadow CAS）。

### 值得吸收的点

1. **plan → execute ⇄ review → finalize 图**——这就是我们小说"大纲 → 撰写 → 评审（一致性/文风/剧情检查）⇄ 修订 → 定稿"工作流的直接蓝本，且图机制（条件路由/递归上限/持久化）与真实 agent 解耦可测。
2. **per-step provenance（prompt + result 逐条记录）**：修订轮次可审计、可回滚。
3. **反思 = 结构化 JSON 输出（observations/patterns/preferences）分命名空间存储**——小说项目"文风反思""读者反馈反思"可直接套。
4. **tier 分层 spawn 规则**：防止 agent 递归爆炸（我们若做"多 agent 协同写作"，planner/worker 双层足够）。
5. **triage 决策缓存**：相同触发器不重复分类。
6. **持久目标清单小而美**（200-500 token、不注入 prompt、agent 反思式维护）——对应"用户的小说项目长期目标（出版计划/系列设定）"。

### 不适合我们的原因（若有）

- subconscious 双世界工厂 + 代际计数器对我们过重；但"后台定期反思 + 输出定向指令"的形态值得以轻量版吸收。
- tinyplace A2A（Signal E2E 加密 agent 间编排）是社交网络特性，与我们无关。

---

## 8. provider 接入层

### 该项目怎么做

**全链路 `Arc<dyn tinyagents::ChatModel<()>>`**（`agent-harness.md:50-56`）：TinyAgents 的 OpenAI 兼容客户端覆盖 managed/local/BYOK 线路，宿主 `ChatModel` 实现覆盖 Claude SDK/Codex 特殊传输。**openhuman 保留**：凭证解析、OAuth、接入门、端点选择、出站披露（egress disclosure）、计费元数据、错误分类——"模型构造归框架，产品策略归自己"。

**provider-string 语法**（`inference/provider/factory.rs:5-25`）：
```
"openhuman"                    → managed backend（会话 JWT）
"cloud" / 缺省                  → 主云商
"ollama:<model>[@<temp>]"      → 本地 Ollama
"lmstudio:<model>[@<temp>]"    → LM Studio
"<slug>:<model>[@<temp>]"      → 用户配置的 BYOK 云商（按 auth_style 选 OpenAI/Anthropic 风味）
```
- `@<temp>` 后缀钉住每 workload 温度（发给上游前剥掉）；`BYOK_INCOMPLETE_SENTINEL` 表达"用户表达了 BYOK 意图但配置不完整"，早失败给出清晰配置错误而非悄悄回退 managed。

**抽象 tier + 路由**：`model: "hint:reasoning"` / `reasoning-v1` 等抽象 tier 名 → TinyAgents `ModelRouter`（`tinyagents/routes.rs`，声明式，含 fallback 链 + 能力门：`chat / reasoning / agentic / coding / burst / summarization / vision`）→ `inference::provider::factory` 解析为具体 `ChatModel`。`burst-v1` = 低上下文高 fan-out worker（SuperContext scout）用快/便宜模型——**"贵的留给思考，便宜的留给体力活"**。

**流式与解析**：原生流式转发（`native model streaming`）；`MaxTokenModel` 包装输出上限；`RequiredCapabilitiesMiddleware` 在派发前按能力（如 vision）拒绝不合格模型；`FallbackObserverMiddleware` 让跨 route 回退事件可见（`mod.rs:1802-1818`）。温度策略在 `temperature.rs`（per-workload）。

**错误处理**：`error_classify.rs` / `config_rejection.rs` / `billing_error.rs` 把错误分类为 retryable / 配置拒绝 / 预算耗尽；预期失败（未知云商/401/429/model-not-found）降级 warn 不污染 Sentry（`inference/README.md:120`）。

### 值得吸收的点

1. **provider-string 语法 + @temp 后缀**：一行字符串表达"哪个商、哪个模型、什么温度"——我们的多模型配置可直接用（`provider:model@temp`）。
2. **抽象 tier（chat/reasoning/coding/vision...）+ 路由表**：调用方写意图不写具体模型，切换模型零改动。小说项目可定义 `draft / planning / review / summary` tier。
3. **能力门（vision 等）在派发前校验 + 跨 route 回退**。
4. **模型构造归框架、产品策略归自己**的分工边界——对应我们"requests 调用归 util、凭证/重试/计费归业务"。
5. **'BYOK 意图不完整'显式哨兵早失败**——不给静默错误回退。

### 不适合我们的原因（若有）

- 本地运行时管理（Ollama 安装/Whisper/Piper 下载进度）与我们无关。
- 多 provider 全家桶对我们不必要，但统一 `ChatModel` trait + 工厂是必要的。

---

## 9. agent 测试设施

### 该项目怎么做

**分层**（`gitbooks/developing/testing-strategy.md`）：
- **Rust 单元**：同文件 `#[cfg(test)] mod tests` 或兄弟 `tests.rs`/域内 `tests/` 子目录——纯域逻辑、schema、RPC handler 形状、内存状态机。
- **Rust 集成**：仓库根 `tests/*.rs`——真实 Tokio runtime + mock 外部服务 + JSON-RPC 端到端。
- **测试决策树**：在 JSON-RPC 边界内？跨域/外部服务？是→集成，否→单元。跨层都改则每层都测。
- **Failure-path 要求**：每个 feature 至少一条失败/边界断言（happy path 不算完整）。

**agent 循环的确定性测试**（`tests/agent_harness_e2e.rs`）：
- **scripted mock LLM 上游**：本地 HTTP mock server 按**脚本化响应序列**回答，测试断言请求形状与响应顺序——"Most harness tests script the mock-LLM call sequence exactly"（`agent_harness_e2e.rs:347`）。可脚本化 500 错误验证重试（`agent_harness_e2e.rs:2025-2075`：3 attempts，前两次 mock 返回 500）。
- 每测试**隔离 HOME/OPENHUMAN_WORKSPACE**（tempdir + EnvVarGuard）、临时端口、SSE collector 收实时事件断言事件序列。
- 引导栈：mock server → 写最小 config.toml → 起真实 core router → `auth_store_session` 建立认证 → 发 `channel_web_chat` → 等 SSE 终态事件。
- **图机制与 worker 注入解耦**（`delegation.rs:39-42`）：`run_delegation` 接受注入的 stage worker，单测用确定性 mock，生产传真实 run_subagent 闭包。
- **构建期诊断**：loader 测试断言每个内建 agent 的图链校验可编译（malformed chain 直接 CI 失败）。
- **覆盖率门槛**：变更行 ≥80% diff coverage（cargo-llvm-cov + diff-cover），CI Lite 只跑变更域 + 变更文件相关测试。
- 辅助 bin：`harness-subagent-audit`（审计子代理）、`inference-probe`（探针）等，`src/bin/`。

### 值得吸收的点

1. **scripted mock LLM 上游**（脚本化响应序列 + 请求形状断言）——这是 agent 循环测试的黄金模式：不用真模型、全确定性、能测重试/错误路径/工具调用序列。我们的 Python 版可直接在 FastAPI TestClient 前挂一个脚本化 mock LLM 端点。
2. **failure-path 强制要求**（每个 feature 至少一条失败断言）。
3. **测试决策树**（跨域→集成，否则→单元）。
4. **worker/机制注入解耦**（图与真实 agent 分离测）——我们的"大纲→撰写→评审"管线可以先在纯数据结构上测机制。
5. **变更行覆盖率门槛**而不是全量覆盖率——务实。

### 不适合我们的原因（若有）

- WDIO/Appium 桌面 E2E 与我们无关；cargo-llvm-cov 换成 pytest-cov 即可。

---

## 10. 与 hermes-agent / openclaw 相比的独特点（基于本项目内文档与代码）

| 维度 | openhuman | 独特性说明 |
|---|---|---|
| 引擎 | 委托发布版 tinyagents 框架 + 适配层 | 两个对手均自研循环；openhuman 把循环引擎外包，产品价值全在策略层 |
| 记忆 | Memory Tree（评分/压缩/级联摘要）+ Obsidian vault + MEMORY.md | 记忆是"压缩成可读 Markdown 树"，不是向量黑箱；auto-fetch 每 20 分钟同步 |
| 上下文压缩 | TokenJuice 内容感知压缩 + CCR 无损恢复 | 工具输出进模型前先压缩（JSON/code/log/search/diff），最多省 80% token 且可无损取回——独此一家 |
| 编排 | 三层 tier spawn 规则 + durable 图 + checkpointer | "graphs, not loops"：turn 是 checkpointed graph run，可暂停等人类、重启续跑、逐调用成本回放 |
| 会话 | append-only JSONL 转录 + compaction 记录 + 事件 journal | 转录本身是可重放事件日志，UI 与模型读同一文件的两条路径 |
| 失败 | 失败分类学（ClassifiedFailure）+ 无进展/空转断路器 + root-cause 回传 | "卡住的 agent 返回根因报告"而非静默失败 |
| 子代理 | durable subagent_sessions + 兼容选择器复用 worker + 跨 turn 续跑 | 子代理是持久实体（有 id、有历史、可复用），不是一次性调用 |
| 反思 | subconscious（后台反思循环）+ learning reflection + goals_agent | 主动后台思考（晨报、世界 diff），不止 turn 内反思 |
| 成本 | 权威 charged_amount_usd + 日/月预算 gate + per-iteration 遥测 | 预算在模型调用前强制执行（CostBudgetMiddleware），不是事后统计 |
| 测试 | scripted mock LLM 序列 + 真实 RPC 栈 E2E | 对"循环逻辑"做确定性脚本化验证 |

---

## 最值得吸收的设计（总结，按价值排序）

1. **KV-cache 优先的上下文契约**：system prompt 首轮构建后字节冻结；一切动态内容（记忆召回/新技能/状态变化）以用户消息附加。写小说 agent 的"设定/文风/角色卡"进 prompt、剧情进展进对话尾部，天然稳定且省钱。实现参考 `agent-harness.md:117-122`、`context/README.md:89`。
2. **护栏家族**：迭代上限 + USD 预算 + wall-clock（含每调用 timeout）+ 无进展断路器 + 空转断路器 + 未知工具/坏参数降级为可恢复错误 + 优雅暂停返回部分结果。对应我们长章节生成的中断恢复。参考 `tinyagents/mod.rs:186-247`、`middleware.rs`。
3. **plan → execute ⇄ review → finalize durable 图**：条件路由 + 递归上限 + checkpoint 恢复 + per-step provenance（prompt/result 逐条记录）——小说"大纲→撰写→评审⇄修订→定稿"工作流的直接蓝本，且图机制与真实 agent 注入解耦可测。参考 `tinyagents/delegation.rs:1-40`。
4. **工具结果三级治理**：per-call byte 截断 → summarizer 子代理压缩 → artifact 落盘回传路径指针（`[artifact] path=... bytes=...` 契约），大产出移出上下文。写小说场景下"章节草稿写文件、回传路径+摘要"直接可用。参考 `agent-harness.md:168-230`。
5. **scripted mock LLM 测试模式**：本地脚本化响应序列 mock + 请求形状断言 + 每测试隔离环境——agent 循环全确定性可测（含重试/错误路径）。参考 `tests/agent_harness_e2e.rs:339-347,2025-2075`。
6. **fail-closed 工具可见性 + 注册层硬约束**：三层过滤（visible 白名单 / 权限天花板 / 定义级 scope），"子代理绝不携带 spawn/delegate 工具"在注册层强制；未知工具运行时默认 Deny。参考 `mod.rs:1916-1965`、`agent_tool_policy/README.md`。
7. **append-only 转录 + compaction 记录 + 前向兼容**：历史压缩不丢原始行（compaction 记录替换累积器），未知记录/字段可跳过——存档格式演进零成本。参考 `harness/session/transcript.rs`。
8. **事件流持久化 + 重放即真相**：run 内事件 journal（JSONL + 稳定 event id + 凭证打码）是 canonical record，总线只管跨域信号；UI/审计事后重放。参考 `tinyagents/journal.rs`、`core/event_bus/README.md:41-63`。
9. **provider-string 语法 + 抽象 tier 路由**：`<slug>:<model>[@<temp>]` 一行描述模型+温度，调用方只写意图 tier（draft/planning/review），路由表负责 fallback 与能力门。参考 `inference/provider/factory.rs:5-25`、`tinyagents/routes.rs`。
10. **失败分类学 + root-cause 回传**：每次失败分类为 `ClassifiedFailure{class, category, next_action, recoverable}`，断路器 halt 时把根因摘要覆盖为最终文本——"卡住"是报告而非静默。参考 `agent-harness.md:524-538`。

## Caveats / Not Found

- 前端（Tauri/React/app/）完全未研究（任务要求后端）。
- vendor/ 下的 tinyagents/tinycortex/tinyjuice crate 源码只读了适配层引用，未深入框架内部实现（`vendor/` 是 submodule，本地可能未初始化——本次未展开）。
- orchestration（"split brain" 的推理核心）已迁移为**托管后端**（`src/openhuman/orchestration/mod.rs:1-14` 明示"reasoning/wake graph runs server-side"），设备侧只是触发/效果执行器；本地部分（triage/subconscious/medulla）已覆盖。
- `src/openhuman/agent/harness/agent_graph.rs` 与 `agent_graph/` 引擎已在 tinyagents 迁移中移除，相关文档标注为历史设计（`agent-harness.md:448-495`），本报告未将其列为现状。
