# Research: Hermes Agent 架构研究报告

- **Query**: 研究 hermes-agent（Nous Research，Python 开源 agent 框架）后端/核心设计，为我们的写小说 agent（FastAPI + Python）架构重构吸收设计
- **Scope**: internal（本地代码库，约 8,196 文件 / 3,708 py）
- **Date**: 2026-08-02
- **研究对象**: `docs/references/agent-projects/hermes-agent/`（v0.19.1，MIT，Nous Research）

## 0. 项目定位与整体架构

**定位**: 自称 "self-improving AI agent"，核心卖点是学习闭环（技能自建、记忆持久、跨会话检索）。运行时覆盖 CLI / TUI / 多消息平台网关，但**核心循环与前端完全解耦**——所有 UI 交互通过构造函数注入的 callback 进入（见下）。

### 顶层结构（平铺式单包 + 按职责分文件）

```
hermes-agent/
├── run_agent.py        (7551 行) — AIAgent 门面类（瘦壳，仅转发）
├── agent/              (核心逻辑包：循环/压缩/记忆/prompt/预算/provider adapter)
│   ├── conversation_loop.py   (7141 行) — run_conversation 主循环
│   ├── context_compressor.py  (6595 行) — 上下文压缩引擎
│   ├── chat_completion_helpers.py (4315 行) — provider 调用/中断/failover
│   ├── turn_context.py / turn_finalizer.py / turn_retry_state.py — turn 三件套
│   ├── context_engine.py      (489 行) — ContextEngine 抽象基类（可插拔压缩引擎）
│   ├── memory_manager.py      (1241 行) — MemoryProvider 插件式记忆
│   ├── prompt_builder.py / system_prompt.py / prompt_caching.py — prompt 体系
│   ├── tool_executor.py / tool_guardrails.py / tool_result_classification.py — 工具执行
│   └── anthropic_adapter.py / gemini_native_adapter.py / bedrock_adapter.py / vertex_adapter.py / codex_responses_adapter.py — provider 适配器
├── providers/base.py   (232 行) — ProviderProfile 声明式 provider 描述
├── tools/              (~100 个工具文件 + registry.py 注册表)
│   ├── registry.py     (873 行) — ToolRegistry 单例（注册/schema/dispatch）
│   └── todo_tool.py / delegate_tool.py / kanban_tools.py / terminal_tool.py ...
├── model_tools.py      (1448 行) — 工具注册表的编排层（发现 + 公共 API）
├── toolsets.py / toolset_distributions.py — 工具集定义与分发
├── hermes_state.py / hermes_state_schema.py — SQLite 会话数据库
├── trajectory_compressor.py — 轨迹压缩（训练数据用途，非运行时）
├── hermes_cli/ — CLI/配置/gateway 命令
└── tests/ (179 项) — agent/ run_agent/ hermes_state/ 等
```

**关键架构模式**:

1. **AIAgent 是门面，不是实现**（`run_agent.py:409`）。构造函数只做参数转发，全部装配在 `agent/agent_init.py` 的 `init_agent()` 中（`run_agent.py:507` 注释 "Forwarder — see agent.agent_init.init_agent"）。这让初始化逻辑可独立测试，也让 gateway 能按平台参数重建 agent。

2. **UI 解耦靠回调注入**（`run_agent.py:462-476`）：`step_callback` / `tool_start_callback` / `stream_delta_callback` / `interim_assistant_callback` / `status_callback` / `event_callback` 等约 15 个回调，全部在构造时注入。主循环只发事件，不关心是 TUI、Telegram 还是 API server 在消费。

3. **God-file 分解方法论**（`agent/turn_finalizer.py:1-16` 文档字符串自述）：conversation_loop 这种巨型文件通过有计划的拆分运动（`~/.hermes/plans/god-file-decomposition.md`）逐步拆出 turn_context / turn_finalizer / turn_retry_state 等专门模块，**行为中立**（代码原样搬移 + 文档说明拆分的 seam），保证拆完行为不变。这是他们管理 7K 行文件的方法——不是重构优化，而是"拆文件运动"。

4. **依赖方向**: `hermes_cli`（配置/CLI）← `agent`（循环）← `tools`（工具）单向；`agent/turn_finalizer.py` 通过"函数体内惰性 import"避免循环依赖（turn_finalizer.py:15-16）。

### 与我们架构的对比结论

- **值得吸收**: 回调注入解耦 UI/事件；门面类 + init 装配分离；god-file 拆分运动模式。
- **不适合**: 平铺式单包在 8K 文件规模下已依赖"惰性 import"和命名约定维持秩序；我们更小，仍按层分包（api/services/repositories）更清晰。

---

## 1. Agent 循环模型

### 主循环（`agent/conversation_loop.py:1142-1316+`）

`run_conversation(agent, user_message, ...)` 是唯一入口，结构为：

1. **Prologue（turn_context.py:329 `build_turn_context`）** — 所有每轮一次性设置集中于此：用户消息清洗、重试计数归零、todo/记忆水合、系统提示词 restore-or-build、预检压缩（preflight compression）、插件 `pre_llm_call` hook、外部记忆 prefetch、崩溃恢复持久化。注释明确说明这是从内联代码提取的（conversation_loop.py:1203-1211）。
2. **主循环**（conversation_loop.py:1316）:
   ```python
   while (api_call_count < agent.max_iterations and agent.iteration_budget.remaining > 0) or agent._budget_grace_call:
   ```
   每轮迭代：steer 排水 → 中断检查 → 预算消费（`iteration_budget.consume()`）→ step_callback（gateway agent:step 事件）→ 消息净化（tool_call 参数 JSON 修复、role 交替修复、surrogate 清理、空消息修复）→ 组装 api_messages（剥离 api_content/display_kind 等内部字段）→ 压缩压力预检 → provider 调用（内层 retry loop）→ 工具执行。
3. **Tail（turn_finalizer.py `finalize_turn`）** — 循环后统一收尾：预算耗尽摘要、轨迹保存、会话持久化、turn 诊断、结果 dict 组装、steer 排水、记忆/技能审查触发。

### 终止条件与退出原因

- `_turn_exit_reason` 字符串全程记录（"unknown" 初始 → "interrupted_by_user" / "budget_exhausted" / "ollama_runtime_context_too_small" 等），最终随 result dict 返回，是诊断第一抓手（conversation_loop.py:1271）。
- **返回结构固定**: `{"final_response", "messages", "api_calls", "completed", "partial", "error"}` — 失败、中断、截断都以 `partial=True` + `error` 字段表达（conversation_loop.py:3037-3044），调用方无需异常处理。

### 预算控制（`agent/iteration_budget.py:17-59`，全文 62 行）

- 线程安全 consume/refund 计数器。父 agent 上限 `max_iterations`（默认 500，AIAgent 构造默认 90），子 agent 独立上限 `delegation.max_iterations`（默认 50）——总迭代可超父上限，由用户配置控制。
- `refund()`：`execute_code`（编程式工具调用）不消耗预算。
- **Grace call 机制**（conversation_loop.py:1342-1351）：预算耗尽后给模型最后一次机会（`_budget_grace_call` 标志消费后立即退出）。

### 重试策略（`agent/turn_retry_state.py:32-92` + conversation_loop.py:2940-3088）

- **TurnRetryState 对象化一次性 guard**：每次外层迭代创建一个实例，约 16 个恢复分支各有一个 one-shot 布尔（codex/anthopic/nous/copilot/vertex OAuth 刷新、thinking 签名剥离、图片缩小、多模态内容剥离、llama.cpp grammar 回退、429 重试等）。文档明说这是从"~16 个散落局部变量"重构而来（turn_retry_state.py:11-16）。
- **restart_with_* 信号**：内层 retry loop 通过设置 `restart_with_compressed_messages` / `restart_with_length_continuation` / `restart_with_rebuilt_messages` / `restart_with_redirected_messages` 让外层决定如何重建请求。
- **截断重试**（两类，各最多 4 次）:
  - 文本截断（length continuation）：把截断的部分流内容作为 assistant 消息 append，然后追加 `_get_continuation_prompt`（conversation_loop.py:3022-3032），用 "continue" 提示让模型续写。
  - tool_call 截断：不 append 坏消息，直接重发同一请求，且 `max_tokens` 指数加倍（`_tc_boost = base * (2 ** retries)`，封顶 32768+，conversation_loop.py:3073-3079）。
- **Stale-call 检测**（chat_completion_helpers.py:638-641）：超时无响应则杀连接，交给主重试循环做退避/凭据轮换/provider failover。

### Guard / 安全限制（`agent/tool_guardrails.py:273-441`）

每轮一个 `ToolCallGuardrailController`，三层防护：

1. **每轮 runaway-loop 硬上限**（`_check_loop_cap`，447 行）：`loop_caps.max_web_searches` / `max_subagents` 等，达到即 block（不受 hard_stop_enabled 开关影响），计数每轮重置。
2. **精确失败阻断**（hard_stop_enabled 时）：相同 signature（tool_name + 规范化 args）失败 N 次（`exact_failure_block_after`）→ block + 设置 halt_decision。
3. **幂等无进展检测**：对白名单幂等工具（idempotent_tools），相同参数返回相同结果哈希 N 次 → block（"read-only call returned the same result N times"）。
4. 三级决策：`block`（阻止执行）/ `warn`（注入提示文本）/ `halt`（终止循环），`ToolGuardrailDecision` 携带结构化 code 与 message（如 `repeated_exact_failure_block`）。
5. 失败分类 `classify_tool_failure(tool_name, result)`（238 行）判定结果字符串是否为失败。

### 与我们的对比结论

- **值得吸收**: TurnRetryState 对象化（我们 590 个测试中循环逻辑难以测试，正是因为重试状态散落）；固定返回结构 `{final_response, messages, api_calls, completed, partial, error}`；退出原因字符串全程追踪；grace call 比硬性预算边界用户体验好；工具失败三级决策（block/warn/halt）是低成本高价值。
- **不适合**: 16 个恢复分支的规模我们不需要（我们没有多 provider OAuth）；截断重试的 max_tokens 指数加倍需要 streaming 场景才有效。

---

## 2. 工具/技能系统

### 注册方式（`tools/registry.py`）

**显式注册，非装饰器**。每个工具文件在模块导入时调用：

```python
# tools/todo_tool.py:327-338
registry.register(
    name="todo",
    toolset="todo",
    schema=TODO_SCHEMA,          # 手写 JSON Schema（OpenAI 格式）
    handler=lambda args, **kw: todo_tool(...),
    check_fn=check_todo_requirements,   # 能力探测
    emoji="📋",
)
```

`register()`（registry.py:438-520）关键行为：

- **跨 toolset 覆盖保护**: 同名工具来自不同 toolset 时拒绝注册，除非 `override=True` 显式声明；插件（hermes_plugins.*）覆盖内置工具需要操作者配置 `allow_tool_override: true` 的 opt-in 政策（registry.py:461-498），且**授权绑定在 handler 定义模块**（`handler.__globals__["__name__"]`，registry.py:398-420），防止回调洗白。
- `deregister` 有所有权检查（registry.py:522-587），MCP 动态刷新走 nuke-and-repave 豁免路径。
- `dynamic_schema_overrides`: 零参 callable，每次 `get_definitions()` 时执行，用于描述依赖运行时配置的工具（如 delegate_task 描述需反映当前并发上限，registry.py:182-189, 628-638）。

### 能力探测与 TTL 缓存（registry.py:192-288）

- `check_fn` 探测外部状态（Docker 守护进程、playwright 是否安装），结果 **30 秒 TTL 缓存** + **失败宽容窗口**：最近 60 秒内有成功记录时，短暂失败被当作抖动（flake）返回 last-good True 且**不缓存失败**（registry.py:257-269）——防止一次超时把整个 toolset 从会话中静默剥除。
- 工具可用性派生自 per-tool check_fn，而非 toolset 级门控（`_toolset_has_exposable_tools`，registry.py:323-345）。

### Schema 与结果契约

- Schema 是**手写 JSON**（`TODO_SCHEMA`），无 docstring 解析、无 pydantic 生成。每个工具 schema 有详细的行为指导描述（todo_tool.py:8-11 设计注释："Behavioral guidance lives entirely in the tool schema description"）。
- **结果归一化**（`_normalize_handler_result`，registry.py:646-675）：handler 只能返回 str 或 `{"_multimodal": True, "content": [...]}` 信封；其他类型一律转成结构化错误 `tool_error(..., error_type="tool_result_contract")`，防止日志/预算/持久化收到无法切分的数据。
- `tool_error(message, **extra)` / `tool_result(data, **kwargs)`（registry.py:847-873）：结构化错误/结果工厂。

### 执行（`dispatch`，registry.py:677+ 与 `agent/tool_executor.py`）

- 异步 handler 自动桥接（`_run_async`，model_tools.py:97-150：三态——已有运行中 loop 时起新线程、CLI 路径用持久 loop、worker 线程用 thread-local loop，防 "Event loop is closed"）。
- 所有异常捕获后转为统一错误字符串。
- `agent/tool_executor.py`（2054 行）承担执行期职责：检查点路径、结果大小上限（`max_result_size_chars`）、输出截断。

### 与我们的对比结论

- **值得吸收**: check_fn + TTL + 失败宽容窗口的"能力自检"模式（我们小说 agent 有本地模型/远程模型能力差异）；结果归一化契约（我们目前工具返回格式不统一的话值得收敛）；覆盖保护 + 显式 opt-in（插件安全）；`tool_error` 结构化错误。
- **不适合**: 手写 JSON schema（我们用 pydantic 生成更省力——但 schema 里的"行为指导写在描述里"理念值得保留）；插件 override 政策体系我们暂无插件生态。

---

## 3. 上下文管理

### Token 计量（`agent/model_metadata.py:2860-2909`）— 核心发现

**不用 tiktoken**，用启发式估算：

```python
def estimate_tokens_rough(text):
    if text.isascii():                       # O(1) 快路径
        return (len(text) + 3) // 4          # ~4 字符/token
    dense = CJK/Hangul/Kana 字符数
    return dense + ((sparse + 3) // 4)       # CJK 1 字符 ≈ 1 token
```

- **CJK/韩文/假名按 1 字符 = 1 token**（model_metadata.py:2862-2868），其余按 4 字符/token。理由：CJK 在主流 tokenizer 下密度远高于英文。**这对我们中文小说 agent 直接适用**。
- 图片按固定 1500 token/张（Anthropic 定价模型，model_metadata.py:2905），避免 base64 字符长度误触发压缩。
- **指纹缓存**（model_metadata.py:2912-2975）：按消息结构的深度指纹（str 按 `id()` + 强引用 pin，dict/list 结构递归）缓存估算结果，未变消息 O(1) 命中。因为 api_messages 每轮浅拷贝共享 content 字符串，缓存命中率高。

### 压缩引擎（`agent/context_compressor.py`，6595 行）

**ContextEngine 抽象基类**（agent/context_engine.py:89）：`should_compress(prompt_tokens)` / `should_compress_preflight` / `compress(messages, focus_topic, force, memory_context)` / `select_context` / `on_turn_complete(usage)` 等——压缩引擎可插拔，ContextCompressor 是其默认实现。

**阈值计算**（context_compressor.py:2075 `_compute_threshold_tokens`）：context_length − 输出预算（max_tokens 预留）− 安全余量。`update_from_response(usage)` 用 API 报告的 last_prompt_tokens 校准（2335 行）。

**compress() 算法**（context_compressor.py:5840-5969，文档注释自述五步）：

1. **Phase 0 廉价预处理（无 LLM）**: 裁剪旧 tool results（保护尾 N 条/尾 token 预算）+ 剥离空回显行。
2. **Phase 1 边界确定**: `_protect_head_size` 保护系统提示词 + 首个交换；`_align_boundary_forward` 对齐。
3. **Phase 2 token 预算切尾**: `_find_tail_cut_by_tokens`（~20K tokens 保留），`_ensure_last_user/assistant_message_in_tail` 确保尾部完整性。
4. **Phase 3 LLM 结构化摘要中间轮次**：独立 `summary_model`（便宜模型）执行，失败自动降级回主模型（aux model fallback，3345-3372 行）。
5. **重新压缩时迭代更新之前的摘要**（不是重新生成）。

**关键防护机制**:

- **失败冷却**（`_record_compression_failure_cooldown`，1854 行）：摘要失败后 30-60s 内不再自动压缩；`force=True` 手动压缩绕过（5900-5904）。
- **无效压缩计数**（`ineffective_compression_count`，1720 行）：压缩不生效（消息数不足）时累计并持久化，防反复空转（5916 行注释：当无法压缩时每次 turn 都触发 should_compress=True 会让 CLI 看起来卡死）。
- **focus_topic 引导压缩**（5868-5871）：提供焦点主题时优先保留相关信息、更激进压缩其余（明确注明灵感来自 Claude Code 的 /compact）。
- **两级压缩（micro-compact）**: `_micro_compact`（5399 行）— 滚动摘要机制：每次只摘要一个交换对（`_find_one_exchange`），更新滚动摘要消息（`_defrag_rolling_summary`），比一次性全量摘要便宜且稳定。
- **状态重注入**: 压缩后 todo 列表以固定头 `[Your active task list was preserved across context compression]` 重新注入（tools/todo_tool.py:24-26 + format_for_injection，116 行）；技能标记、路径提及等保护项（`_collect_protected_skill_names` / `_collect_path_mentions`）。

### 记忆系统（`agent/memory_manager.py:364-877`）

- **MemoryProvider 插件式**: `add_provider`（404 行）注册多个记忆后端，`prefetch_all(query)`（525 行）在 turn 开始时异步预取注入用户消息，`sync_all`（638 行）后台异步持久化（ThreadPoolExecutor，`_submit_background`）。
- `StreamingContextScrubber`（182 行）：流式输出时剔除记忆标签格式（防注入/泄漏）。
- 记忆注入点：**注入用户消息而非系统提示词**（conversation_loop.py:1597-1603 明确注释：插件上下文进 user message，因为改系统提示词会破坏 prompt cache 前缀）。

### Prompt 缓存体系（`agent/prompt_caching.py` + conversation_loop.py:1595-1615）

- **不变量**：系统提示词每会话构建一次（`_cached_system_prompt`），逐字重放；字节稳定性（byte-stable prefix）是最高优先级——所有注入（记忆、插件上下文、steer）都设计为不触碰系统提示词。
- `api_content` sidecar（turn_context.py:87）：持久化存干净内容，API 发送存精确字节（含注入），两侧永不漂移，历史消息重放时用 sidecar 保持 cache 前缀字节一致（conversation_loop.py:1524-1549）。
- `build_prompt_cache_plan`（prompt_caching.py:288）：请求局部 cache 标记，在**所有消息变异完成之后**最后应用（conversation_loop.py:1761-1793，有专门注释解释顺序原因——标记会重写 content 结构，必须先于所有依赖 `isinstance(content, str)` 的规范化）。
- 工具 call 参数 JSON 规范化（sort_keys + 紧凑分隔符）也服务于前缀一致（conversation_loop.py:1727-1744）。

### 与我们的对比结论

- **值得吸收**: CJK token 估算（中文小说场景直接收益）；指纹缓存估算；压缩失败冷却 + 无效压缩计数（防抖动）；两级压缩（滚动摘要 vs 全量）；状态重注入（我们的小说设定/大纲/人物卡就是 todo 的同类物）；注入不碰系统提示词（如果我们也做 prompt cache）。
- **不适合**: summary_model 独立模型（我们单模型场景用主模型即可，但"摘要失败降级"理念保留）；micro-compact 的交换对切割复杂度对我们现阶段过重（我们的对话是小说生成，结构不同）。

---

## 4. 会话状态与持久化

### SQLite 会话库（`hermes_state.py` 8767 行 + `hermes_state_schema.py`）

- 单文件 SQLite（WAL 默认，自动降级 DELETE；`resolve_journal_mode`，hermes_state.py:539）。WAL 不可用时 `WalUnsupportedError`（565 行）+ `apply_wal_with_fallback`（579 行）。
- **声明式 schema 管理**（hermes_state_schema.py:179-183 自述）：`SCHEMA_SQL` 是唯一真相源；`_parse_schema_columns`（hermes_state_schema.py:141）用**内存 SQLite 执行 DDL + PRAGMA table_info 提取列定义**（零正则解析）；`_reconcile_columns` 对线上库自动 `ALTER TABLE ADD COLUMN` 补齐缺失列——加列零迁移代码。schema_version 表仅保留给数据迁移（改行）场景。模式来源注明 Beets/sqlite-utils。
- 特殊 PK 修复：`_heal_gateway_routing_pk` / `_heal_session_model_usage_pk`（SQLite 不能 ALTER 主键，需重建表；每次打开无条件运行，PRAGMA 检查短路）。
- FTS5 全文检索（trigram tokenizer 可选），messages 表内容建索引（hermes_state_schema.py:100-130）。
- 损坏恢复：`_claim_repair_attempt` / `_backup_db_file`（hermes_state.py:973-988）、malformed/disk-full 错误分类（931-971）、macOS checkpoint barrier（444）。

### 持久化与 API 内容的分离

- **`api_content` sidecar**（见上文 3）：`{"role": "user", "content": 干净内容, "api_content": 精确发送字节}`，`compose_user_api_content`（turn_context.py:52）负责组装。发送时 pop（conversation_loop.py:1497），持久化时保存。`display_kind` / `_row_id` 等其他 bookkeeping 字段同样在发送前剥离（conversation_loop.py:1503-1510）。
- 增量持久化失败只中止当前 turn（`agent._incremental_persistence_failed`，conversation_loop.py:1250），缓存 agent 下轮自愈。

### 日志（`hermes_logging.py`）

- **非 JSONL**：RotatingFileHandler + RedactingFormatter（secret 脱敏格式化器），Windows 用 ConcurrentRotatingFileHandler 别名（hermes_logging.py:14-66）。多文件（agent.log 等）分 size 轮转。
- 检查点：`tools/checkpoint_manager.py`（`_checkpoint_mgr.new_turn()` 每迭代一次快照，conversation_loop.py:1328；快照数/总大小/单文件大小上限可配，run_agent.py:500-503）。

### 与我们的对比结论

- **值得吸收**: 声明式 schema + 自动列补齐（我们 FastAPI + SQLite 加列零迁移）；持久化内容与 API 发送内容分离的 sidecar 模式（防止注入内容污染存储）；日志脱敏 formatter。
- **不适合**: 修复型 PK 重建等 8K 行状态层的防御深度我们不需要；FTS5 全文检索对我们小说场景可后续按需加。

---

## 5. 事件与可观测性

### Observer hooks 契约（`docs/observability/README.md`）

- **只读遥测契约**：插件注册 `pre_api_request` / `post_api_request` / `pre_tool_call` / `post_tool_call` 等 hook（README 示例代码），全部接收 `**kwargs`（向前兼容）；每个 payload 注入 `telemetry_schema_version = "hermes.observer.v1"`。
- **Fail-open**：hook 回调异常只记录 warning，不中断 agent 循环。
- 少数 hook 是行为性的（返回值生效）：`pre_llm_call` 可注入上下文、`pre_tool_call` 可 block、`transform_tool_result` / `transform_llm_output` 可替换输出。其余忽略返回值。
- 明确边界："Observer hooks should report what happened; they should not replace provider requests, tool arguments, or execution callbacks"。

### 监控事件（`agent/monitoring/events.py:1-60`）

- **内容无关原则**：`GatewayHealthEvent` / `GatewayDiagnosticEvent` 只含名称、状态机、计数、时间戳——明确注释 "no prompts, messages, tool args/results, session history, or usage analytics"。隐私优先的观测设计。
- 导出路径：`otlp_exporter.py`（OpenTelemetry）+ `emitter.py` + `redaction.py`（脱敏）+ `policy.py`。

### 用量统计（`hermes_state_schema.py:354-405` session_model_usage 表）

- 六维复合主键：`(session_id, model, billing_provider, billing_base_url, billing_mode, task)`——同一会话切模型/切 provider 分别记账。
- 分维度 token 列：`input_tokens / output_tokens / cache_read_tokens / cache_write_tokens / reasoning_tokens` + `api_call_count`。
- 成本双轨：`estimated_cost_usd` 与 `actual_cost_usd` + `cost_status / cost_source`（估算与账单实计分离）。
- 记账在 `agent/account_usage.py` / `agent/aux_accounting.py` 中聚合（异步 token 记账有专项测试 test_async_token_accounting.py）。

### 与我们的对比结论

- **值得吸收**: 只读 hook + fail-open + 版本化 schema 的观测契约（比日志 grep 强得多，也比旁路监听干净）；内容无关监控事件（我们如果做用量统计，不需要存 prompt 本身）；六维记账表结构（我们按 会话×模型×任务 记账即够）；估算/实计成本分离。
- **不适合**: OTLP exporter 等重观测设施现阶段不需要；observer hook 插件体系依赖插件框架。

---

## 6. 任务/规划系统

### 三层并存

1. **TodoStore（内存规划辅助）**（tools/todo_tool.py:34-135）：单 agent 一个实例，`write(todos, merge)` 写 / `read()` 读，每次调用返回完整列表。上限：单条 4000 字符、共 256 条（todo_tool.py:18-21）。**不修改系统提示词、不修改工具响应**——设计原则是"行为指导全部在 schema 描述里"。压缩后以固定头重新注入（见 3）。
2. **Kanban（持久化看板）**（tools/kanban_tools.py:1-31）：worker/orchestrator 场景（`HERMES_KANBAN_TASK` 环境变量或显式启用 toolset 时才注册）。文档自述选工具而非 shell 的理由：后端可移植性（terminal 可能指向 Docker/SSH 容器）、免 shell 转义、结构化错误。人类用 CLI/dashboard 走独立路径。
3. **delegate_task（并行子代理）**（tools/delegate_tool.py）：spawn 隔离子 agent 并行工作；子 agent 独立迭代预算（`delegation.max_iterations` 默认 50）；`execute_code` 形式的 RPC 调用（README 提到 "collapse multi-step pipelines into zero-context-cost turns"）；`set_spawn_paused` 全局暂停闸（delegate_tool.py:153）。
4. **Cron 调度**（cron/scheduler.py + jobs.py + executions.py）：内置定时任务，自然语言创建（README 主打功能），按平台投递。

### 与我们的对比结论

- **值得吸收**: "规划状态与系统提示词解耦 + 压缩后重注入"的模式（我们的小说大纲/人物卡/设定集正是需要跨压缩存活的"规划状态"，todo 的 header 重注入方案可直接借鉴）；任务列表上限防失控。
- **不适合**: kanban 的 dispatcher 场景；cron 我们 FastAPI 有现成方案；delegate 多 agent 并行超出当前需求（但"子 agent 独立预算"的边界思想可留作多 agent 化的预案）。

---

## 7. Agent 测试设施

### 总体结构（tests/ 179 项）

```
tests/
├── conftest.py        (~1300 行，自动 fixture 体系)
├── agent/             (adapter/压缩/记忆单测，~150+ 文件)
├── run_agent/         (循环级测试，~80+ 文件)
├── hermes_state/      (SQLite 层)
├── integration/ e2e/ stress/ conformance/
└── fakes/             (fake_ha_server.py)
```

### 循环测试方法论（对我们最有参考价值）

- **单元为主**：大量测试直接调用 `AIAgent._sanitize_api_messages` 等静态/纯方法（tests/run_agent/test_agent_guardrails.py:29-90），构造最小消息序列断言净化结果——无网络、无 agent 实例化。
- **最小 agent fixture**（tests/run_agent/test_run_agent.py:44-57）：`patch("run_agent.get_tool_definitions")` + `patch("run_agent.OpenAI")` + `a.client = MagicMock()`，构造无网络 AIAgent。`quiet_mode=True` 关闭打印。
- **Hermetic 环境 autouse fixture**（tests/conftest.py:401-507）：`_hermetic_environment`（隔离 HOME/env）+ `_isolate_hermes_home`（临时 HERMES_HOME）——测试永不触碰真实用户目录。
- **系统调用防护**（conftest.py:1010-1268 `_live_system_guard`）：monkeypatch 拦截 `os.kill` / `os.killpg` / `subprocess` 全家桶，标记测试意图（`_is_own_subtree` / `_is_blocked_systemctl`），防止测试误杀真实进程。
- **循环级测试**：tests/run_agent/ 里约 80 个文件覆盖特定回归场景（test_1630_context_overflow_loop.py、test_413_compression.py、test_24996_fallback_exhaustion_cooldown.py）——mock client 的 `create()` 返回预置响应序列，驱动真实 run_conversation 走完整循环。**注意**：循环级测试多为"特定 bug 回归"而非通用行为测试（命名即 issue 号）。
- fakes 只有 fake_ha_server（HomeAssistant 工具用），provider 一律 MagicMock，无 FakeChatCompletion 类库。

### 与我们的对比结论

- **值得吸收**: 静态方法/纯函数直接测（把循环逻辑拆成可测函数——TurnRetryState/guardrails 都是这个思路的产物）；最小 agent fixture 模式（mock provider client + 预置响应序列驱动循环）；hermetic 环境 autouse fixture；**我们 590 个测试但循环测试少，根本解法是把循环逻辑拆成纯函数 + mock provider 驱动端到端循环**——hermes 的 "issue 号命名回归测试" 模式值得照搬。
- **不适合**: _live_system_guard 的进程防护我们无需（无子进程执行）；无 fake provider 类库说明他们也没建通用循环测试框架——不必羡慕，也不需要。

---

## 8. Provider / LLM 接入层

### ProviderProfile 声明式描述（`providers/base.py:38-232`）

一个 dataclass 集中描述 provider 全部行为：

- 身份（name / api_mode / aliases）、认证（auth_type: api_key | oauth_device_code | oauth_external | copilot | aws_sdk）、端点（base_url / models_url）。
- **能力 flag**: `supports_vision` / `supports_vision_tool_messages`（有的 provider 接受多模态 user 消息但拒绝 list 型 tool content，如小米 MiMo，base.py:69-73）。
- **请求怪癖**: `fixed_temperature`（None=用调用方默认，`OMIT_TEMPERATURE` 哨兵=不发送该字段——Kimi 由服务端管理温度）、`default_max_tokens`、`default_aux_model`（辅助任务便宜模型）。
- **Hook 方法**: `prepare_messages` / `build_extra_body` / `build_api_kwargs_extras`（部分 provider 把 reasoning 放 extra_body，如 OpenRouter；部分放顶层 api_kwargs，如 Kimi reasoning_effort——base.py:128-146）/ `get_max_tokens(model)`（按模型变化输出上限）/ `fetch_models`（活模型目录，失败回退静态列表）。
- 声明式原则（base.py:7-10 注释）：profile 描述行为，不拥有 client 构建/凭据轮换/流式——那些在 AIAgent 上。
- **API 模式（api_mode）**: `chat_completions` / `anthropic_messages` / `bedrock_converse` / `codex_responses` / `codex_app_server`——协议维度与 provider 正交；适配器（agent/anthropic_adapter.py 等）按 api_mode 分派。

### 中断式调用（`agent/chat_completion_helpers.py:629-728`）

`interruptible_api_call`：API 调用跑在后台线程，主循环无需等待完整 HTTP 往返即可检测中断。

- **每请求独立 client**（worker-local），中断只关该 client，不影响共享 client 后续重试（629-636 注释）。
- **stranger-thread 关闭协议**（683-727）：谁拥有 client 谁负责 close；陌生人线程（中断检查/stale 检测器）只做 socket shutdown 让阻塞的 recv 解开（EPIPE），避免 FD 回收竞争（有真实事故：#29507 SQLite 头被 TLS 记录写坏）。
- `_request_cancelled` 标志区分"我们自己的中断导致传输错误"与真实网络错误（#6600 级联中断修复，671 行）。
- Stale 检测：`_derive_stream_stale_timeout`（348 行）+ `_check_stale_giveup`（334 行）跨轮熔断。

### Failover 链（`chat_completion_helpers.py:1695-1874`）

`try_activate_fallback(agent, reason)`:

- 按 `FailoverReason` 分类（error_classifier.py）触发；429/billing 触发 60s 主 provider 冷却（1707-1715）。
- 遍历 `_fallback_chain`，跳过：已标记不可用（`_unavailable_fallback_keys`）、本地不可用（`_fallback_entry_unavailable_without_network`）、**解析到同一后端**（`BackendIdentity.build` + `should_skip_candidate`，1764-1782——防止 fallback 到刚失败的同名后端循环）。
- client 构建走集中路由 `resolve_provider_client`（agent/auxiliary_client.py:1788），无重复的 provider→key 映射。
- 链耗尽后冷却（`_FALLBACK_EXHAUSTED_COOLDOWN_S`，1716-1732），防 #24996 跨轮重放风暴。
- `api_mode` 按 provider/URL/model 推导（1823-1867，Azure 判定、anthropic 主机名判定等）。

### 与我们的对比结论

- **值得吸收**: ProviderProfile 声明式——"一个 dataclass 描述一个 provider 的全部怪癖"比散落的 if provider == 分支好得多；api_mode 协议维度与 provider 正交；每请求独立 client + stranger-thread 关闭协议（中断安全）；failover 的 BackendIdentity 防自循环 + 冷却。
- **不适合**: 6+ 协议适配器规模我们只有 OpenAI 兼容一种；OAuth 凭据池体系。

---

## 9. 配置系统

### 分层（`hermes_cli/config.py` + .env + cli-config.yaml.example）

- **YAML 主配置**（`~/.hermes/config.yaml`，示例 cli-config.yaml.example 约 90KB）：`model` / `database` / `terminal` / `compression` / `delegation` / `plugins` 等分段。`hermes config set <section.key> <value>` 写。
- **环境变量**（.env 经 python-dotenv）：只放 secret；注释明确 "only documented secret environment variables in .env take precedence over their corresponding settings"。
- **env → config 桥**：`TERMINAL_CONFIG_ENV_MAP`（config.py:3187-3210 附近）——细粒度映射表，供容器化/无配置文件部署。
- **加载缓存**（config.py:3107-3138）：按 `(mtime_ns, size)` 缓存；`load_config`（deepcopy 版，给写者）与 `load_config_readonly`（免 deepcopy，给 agent 循环热路径——注释给出实测成本：缓存命中 ~265us，deepcopy 占一半，agent 循环每轮读配置 20-50 次）。
- **原子写**：`atomic_yaml_write`（utils.py）。
- **表驱动迁移**（hermes_cli/config_migrations.py:1-39）：替代原来 768 行 `if current_ver < N` 阶梯——每步是 `_migrate_to_N(results, quiet)` 函数，驱动按升序应用 target > current 的条目；步内所有 helper 惰性经模块对象解析（`_cfg`）防循环导入并保 monkeypatch 可测。

### 与我们的对比结论

- **值得吸收**: mtime+size 缓存 + readonly 免拷贝双路径（我们 FastAPI 每请求读配置的场景同样收益）；表驱动迁移替代 if 阶梯；原子写；"secret 走 env、结构走 YAML"的边界。
- **不适合**: 90KB 示例配置的规模；`hermes config set` 的 dotpath 写回机制我们 FastAPI 配置可用 pydantic-settings 替代。

---

## 10. 最值得吸收的设计（总结）

按对我们（FastAPI + Python 写小说 agent，590 测试但循环测试薄弱）的净价值排序：

1. **TurnRetryState 一次性 guard 对象化**（agent/turn_retry_state.py:32-92）— 把散落局部变量收敛为可命名、可单测的对象；这是他们循环逻辑可测性的根基。我们重构循环时照抄此模式，直接解决"循环测试少"的病根。
2. **CJK 感知的启发式 token 估算**（agent/model_metadata.py:2860-2888）— 中文场景 1 字 ≈ 1 token 的估算规则 + 指纹缓存。不引 tiktoken 依赖、O(1) 快路径，对中文小说生成是直接收益。
3. **压缩失败冷却 + 无效压缩计数防抖动**（context_compressor.py:1720-1882）— 摘要失败 30-60s 冷却、压缩不生效时记录并止住空转；配 `force` 手动覆盖。我们若做小说上下文压缩，这两个 guard 是防止"每轮都触发压缩又每轮失败"的关键。
4. **规划状态重注入模式**（tools/todo_tool.py:24-26, 116-135）— 内存任务列表 + 固定 header 标记 + 压缩后重注入，且刻意不改系统提示词。我们的小说设定/大纲/人物卡/场景状态正是"需要跨压缩存活的状态"，该模式直接可搬。
5. **api_content sidecar：持久化与 API 发送内容分离**（turn_context.py:87, conversation_loop.py:1497-1549）— 存储干净内容、发送精确字节（含临时注入），注入内容永不污染持久化层，同时保住 prompt cache 前缀字节稳定。
6. **工具结果归一化契约**（tools/registry.py:646-675）— 工具只能返回 str 或多媒体信封，违规转结构化错误。一个简单约定消灭一整类"下游解析炸掉"的问题。
7. **check_fn 能力探测 + TTL + 失败宽容窗口**（tools/registry.py:192-288）— 工具按外部环境自检可用性；30s 缓存 + 60s last-good 宽容防抖动。我们本地/远程模型能力差异可用同构方案。
8. **固定返回结构 + 退出原因追踪**（conversation_loop.py:1271, 3037-3044）— `{final_response, messages, api_calls, completed, partial, error}` + `_turn_exit_reason` 字符串。调用方不需要异常处理，诊断第一眼看到退出原因。
9. **声明式 schema + 自动列补齐**（hermes_state_schema.py:141-183）— SCHEMA_SQL 唯一真相源、内存 SQLite 解析 DDL、自动 ALTER TABLE。我们 SQLite 持久化加列从此零迁移代码。
10. **Observer hooks 只读契约**（docs/observability/README.md）— 只读、fail-open、`**kwargs` 兼容、schema 版本化。比旁路监听干净、比日志 grep 结构化的用量/追踪方案。
11. **（备选）ProviderProfile 声明式 quirk 集中**（providers/base.py:38-146）— 若我们后续接多个模型提供商，这是"不散落 if 分支"的教科书答案。
12. **（备选）Mtime+size 配置缓存 + readonly 快路径**（hermes_cli/config.py:3107-3138）— FastAPI 每请求读配置的优化样板。

## Caveats

- **规模差异显著**：hermes 是 8K 文件、多 provider、多平台的生产级 agent；我们的写小说 agent 需要吸收的是**模式**而非**体量**。上表 1-10 均为可独立落地的小模式。
- 本报告基于静态阅读，未运行其测试/未验证运行时行为；行号引用对应 `docs/references/agent-projects/hermes-agent/` 内文件（仓库快照）。
- hermes 的压缩/记忆设计围绕"多轮对话 + 工具调用"轨迹，与小说生成的"长文档 + 设定一致性"需求有本质差异——吸收时注意场景映射。
- 未研究前端（TUI/Telegram/gateway/dashboard/web），符合任务范围。
- hermes 循环级测试以 issue 回归为主（命名即 issue 号），没有通用 agent 循环测试框架——我们不必期待现成方案，而应吸收其"把逻辑拆成可测函数"的方法。
