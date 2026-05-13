---
title: AI 调用上下文审计设计
date: 2026-04-28
status: approved
scope: Hermes 对话、Athena 对话、章节生成的模型调用透明化
---

# AI 调用上下文审计设计

## 概述

为 Hermes、Athena 和章节生成增加统一的 AI 调用上下文审计能力。每次真实模型调用都生成一条不可事后重算的 trace，用户可以查看模型实际收到的 messages、上下文块、来源节点、模型参数和 token 用量。

这个功能的目标不是把 raw prompt 粗暴暴露给用户，而是把模型调用拆成可理解、可追踪、可调优的结构化记录。

## 目标

- 用户能看到每次对话或章节生成实际塞给模型的上下文。
- 用户能判断某次回答或正文偏差来自提示词、历史对话、世界模型、检索证据还是模型本身。
- 开发者能用 trace 调试 Athena world-model、retrieval、prompt 组装和 token budget。
- 后续 prompt 优化、自优化、质量回归测试有真实调用样本可依赖。

## 非目标

- 不做完整成本看板、长期指标系统或 prompt A/B 实验平台。
- 不把所有内部调试信息无差别暴露给用户。
- 不把 API key、环境变量、异常堆栈、数据库连接等敏感信息写入 trace。
- 不用事后重新拼装上下文冒充真实调用记录。

## 覆盖范围

第一版覆盖三类入口：

- `hermes_chat`：Hermes 正文创作对话。
- `athena_chat`：Athena 世界模型对话。
- `chapter_generation`：章节生成。

后续可以扩展到 setup、storyline、outline、dialog compaction、自优化分析等调用，但不纳入第一版。

## 核心原则

### 真实快照

trace 必须在模型调用前后由调用链路直接写入，保存当时实际发送的 messages 和参数。不能在用户点击查看时重新读取当前世界模型再拼一次。

原因很简单：世界模型、检索索引、对话历史都会变化。事后重算会误导用户，也无法用于调试历史问题。

### 结构化优先

默认展示结构化 context blocks：

- 项目基础信息。
- 世界模型实体。
- confirmed facts。
- 世界规则。
- 时间线事件。
- 检索证据。
- 章节目标与大纲。
- 对话历史。
- 用户本轮输入。
- 修订反馈。
- few-shot 示例。
- 风格偏好规则。

raw messages 作为高级视图折叠展示，支持复制。

### 来源可追踪

每个 context block 尽量带来源引用：

```text
source_type: WorldFactClaim | WorldCharacter | WorldRule | RetrievalChunk | DialogMessage | Outline | Setup | PromptTemplate
source_id: 对应记录 id 或稳定标识
label: 用户可读标题
chapter_index: 可选
```

没有稳定来源的内容，例如项目名、目标字数、用户本轮输入，也要标记为 `Project` 或 `UserInput`，不能混成无来源文本。

### 脱敏和截断

- 不记录 API key、Authorization header、环境变量。
- raw messages 可以保存，但要经过敏感字段扫描。
- 超长 block 保留前后片段和长度信息，标记 `truncated: true`。
- token 和字符数要记录，便于判断上下文挤占。

## 后端数据模型

新增模型：`AIModelCallTrace`。

核心字段：

```text
id
project_id
trace_type                  # hermes_chat | athena_chat | chapter_generation
status                      # running | success | failed
model
temperature
max_tokens
prompt_tokens
completion_tokens
latency_ms
error_message               # 脱敏后的错误摘要，可空

dialog_id                   # 对话调用可用
request_message_id          # 用户本轮消息，可空
response_message_id         # AI 回复消息，可空
chapter_id                  # 章节生成可用
chapter_index               # 章节生成可用

messages                    # 实际传给模型的 OpenAI-compatible messages
context_blocks              # 结构化上下文块
metadata                    # prompt template、provider、版本等

created_at
```

`messages` 和 `context_blocks` 使用 JSON 存储。当前项目已经大量使用 SQLite + JSON 字段，第一版保持一致，不引入外部 observability 服务。

## Context Block 结构

统一结构：

```json
{
  "key": "athena_confirmed_facts",
  "title": "已确认世界事实",
  "kind": "world_fact",
  "content": "角色.a.b = c ...",
  "token_estimate": 128,
  "char_count": 512,
  "truncated": false,
  "sources": [
    {
      "source_type": "WorldFactClaim",
      "source_id": "claim-id",
      "label": "角色状态事实",
      "chapter_index": 3
    }
  ]
}
```

`kind` 用于前端分组和样式，不用于业务权限判断。

建议 kind：

```text
project
prompt_template
dialog_history
user_input
setup
outline
chapter_context
world_entity
world_fact
world_rule
timeline
retrieval
style_rule
few_shot
system_instruction
revision_feedback
```

## 后端服务边界

新增核心服务：`app/core/model_call_trace.py`。

职责：

- 创建 trace payload。
- 脱敏 messages。
- 估算字符数和 token。
- 对 block 做长度限制。
- 写入成功或失败状态。
- 给 API 输出做轻量化转换。

它不负责构造业务上下文。业务上下文仍由各模块负责：

- Hermes/Athena 对话继续由 `dialogs.py` 和 `context_injection.py` 组装。
- 章节生成继续由 `chapters.py`、`athena_longform.py`、`athena_retrieval.py` 组装。

但这些组装函数需要返回结构化 blocks，而不是只返回字符串。

## 现有链路改造

### Hermes 对话

现状：

- `_build_chat_messages()` 构造 system prompt 和历史对话。
- `_free_chat_reply()` 调用 `ai_service.complete()`。
- 返回后保存 assistant 消息。

改造：

- 增加 `_build_chat_call_payload()`，返回 `messages` 和 `context_blocks`。
- Hermes 的 `world_context` 由 `build_hermes_world_context()` 同步提供 block 来源。
- 调用模型前创建 trace draft。
- 调用成功后写入 token、latency、assistant message id。
- 调用失败也写入 failed trace。

### Athena 对话

现状：

- Athena 对话复用 `_free_chat_reply()`。
- world update 请求走提案，不一定调用模型。

改造：

- 普通 Athena 对话记录 `athena_chat` trace。
- 走提案短路的请求不记录模型调用 trace，因为没有真实调用模型；可以在响应里说明“本轮未调用模型”。
- `build_athena_world_context()` 拆分出实体、关系、规则、confirmed facts、timeline blocks。

### 章节生成

现状：

- `_build_chapter_context()` 返回字符串。
- `create_or_replace_chapter()` 拼 `generate_chapter` prompt、Athena 世界上下文、用户修订反馈、长度约束、风格规则、few-shot 示例。
- 模型调用 messages 只有一个 user message。

改造：

- 新增 `_build_chapter_call_payload()`，返回：
  - `messages`
  - `context_blocks`
  - `max_tokens`
- 章节上下文 block 包含：
  - Setup 世界观。
  - Setup 角色。
  - 本章大纲。
  - 上一章摘要。
  - Athena 世界上下文。
  - 检索证据。
  - 用户修订反馈。
  - 长度约束。
  - 风格偏好。
  - few-shot 示例。
- 章节保存成功后，把 trace 关联到 `chapter_id`。
- 如果模型成功但章节入库失败，trace 标记 failed，并记录脱敏错误摘要。

## API 设计

新增统一端点：

```text
GET /api/v1/projects/{project_id}/model-call-traces
GET /api/v1/projects/{project_id}/model-call-traces/{trace_id}
```

列表支持过滤：

```text
trace_type=hermes_chat|athena_chat|chapter_generation
chapter_index=1
dialog_id=...
limit=30
offset=0
```

消息或章节关联查询可以用参数完成，不额外增加过多端点。

输出分两层：

- list item：只返回摘要、关联对象、token、时间、status。
- detail：返回 context blocks 和 raw messages。

### 关联字段

聊天和章节接口需要能把业务对象指回 trace：

- `ChatOut` 增加 `trace_id: str | null`。
- `ChatMessageOut` 增加 `id` 和 `trace_id: str | null`；前端当前类型缺少 `id`，需要补齐。
- `ChapterOut` 增加 `last_generation_trace_id: str | null`，指向最近一次章节生成 trace。

后端可以通过 `response_message_id` 或 `chapter_id` 反查 trace，但 API 输出必须直接带 id，避免前端为了一个按钮额外扫列表。

## 前端设计

### Hermes

在 AI 回复气泡旁增加“上下文”入口。点击后打开右侧抽屉。

抽屉默认显示：

- 调用摘要：模型、token、耗时、状态。
- Context blocks：按类型折叠。
- 来源引用：显示表名、记录标题、章节号。
- Raw messages：高级折叠区。

### Athena

Athena 对话面板使用同一套入口。Athena 的 blocks 重点展示世界模型节点：

- 世界实体。
- 关系网络。
- 世界规则。
- 当前确认事实。
- 时间线事件。
- 检索证据。

用户需要能一眼看出：模型本轮是否真的看到了某个世界节点。

### 章节

章节生成结果旁增加“生成上下文”入口。

展示重点：

- 本章生成 prompt。
- Athena 世界上下文。
- retrieval 命中证据。
- 本章大纲和上一章摘要。
- 风格规则和 few-shot 示例。

这个入口应放在章节详情或 Manuscript 相关页面，不放进 Athena 的检索页。

## 前端组件

建议新增：

```text
frontend/src/components/modelTrace/ModelTraceDrawer.vue
frontend/src/components/modelTrace/TraceSummary.vue
frontend/src/components/modelTrace/ContextBlockList.vue
frontend/src/components/modelTrace/ContextSourceList.vue
frontend/src/components/modelTrace/RawMessagesViewer.vue
```

API 和 store：

```text
frontend/src/api/client.ts
frontend/src/api/types.ts
frontend/src/stores/modelTraces.ts
```

ChatMessage 只负责展示入口，不直接承载 trace 数据。

## UI 行为

- 有 trace 的 AI 消息显示“上下文”按钮。
- 没有 trace 的消息不显示按钮。
- 章节存在 `last_generation_trace_id` 时显示“生成上下文”入口。
- trace 失败但有请求 payload 时仍可查看。
- raw messages 默认折叠。
- block 支持关键词搜索。
- 来源引用第一版只展示文本，不跳转；跳转可以后续做。

## 删除与保留

项目删除时清理对应 trace。

第一版不做自动过期清理。原因是当前本地 SQLite 项目规模有限，trace 对调试价值高。后续如果长篇压测导致数据库膨胀，再增加“仅保留最近 N 次”或“清理 raw messages”策略。

## 测试策略

后端：

- Hermes 对话成功后产生 `hermes_chat` trace。
- Athena 对话成功后产生 `athena_chat` trace。
- Athena 提案短路不产生模型 trace。
- 章节生成成功后产生 `chapter_generation` trace，并关联章节。
- 模型调用失败时产生 failed trace。
- trace detail 不包含 API key 或 Authorization。
- 项目删除会清理 trace。

前端：

- ChatMessage 有 trace id 时显示上下文入口。
- Drawer 能展示 summary、blocks、sources、raw messages。
- 章节生成结果能打开生成上下文。
- trace list/detail API 类型匹配。

全链路：

- 使用真实 DeepSeek API 生成一次 Hermes 对话、Athena 对话、章节正文。
- 在 UI 中查看三类 trace。
- 对比 trace raw messages 与实际发送 payload 一致。
- 检查 Athena 世界节点和 retrieval 证据是否出现在对应 block。

## 风险与处理

### trace 记录过大

第一版做 block 截断和 raw messages 字符上限。保留 token、原始长度和截断标记。

### 误暴露敏感信息

模型调用 payload 本身不应包含 API key，但仍要做脱敏扫描。错误信息只记录摘要，不保存完整堆栈。

### 结构化来源不完整

短期允许部分 block 只有粗粒度来源，例如 `PromptTemplate` 或 `Setup`。但 world-model 和 retrieval 相关 block 必须提供记录级来源，否则无法支撑调优。

### 影响主流程稳定性

trace 写入失败不能阻断聊天或章节生成。实现上需要捕获 trace 写入异常，并降级为正常模型调用。

### 事后重算污染审计

API detail 只读取 trace 表，不调用 context builder。这个约束必须写进测试。

## 实施顺序

1. 增加后端模型、迁移、schema 和 trace service。
2. 改造 Hermes/Athena 对话 payload 构造，记录 chat trace。
3. 改造章节生成 payload 构造，记录 chapter trace。
4. 增加 trace list/detail API。
5. 增加前端 API、store、抽屉组件。
6. 接入 Hermes、Athena、章节入口。
7. 补后端、前端和全链路验证。

## 验收标准

- Hermes 对话、Athena 对话、章节生成都能在 UI 查看对应调用上下文。
- trace 详情能看到 raw messages 和结构化 context blocks。
- 章节生成 trace 能看到 Athena 世界上下文和 retrieval 证据。
- world-model / retrieval block 至少包含记录级来源。
- 模型调用失败也能留下 failed trace。
- 删除项目不会留下孤立 trace。
- 测试通过：backend pytest、frontend unit tests、frontend build。
