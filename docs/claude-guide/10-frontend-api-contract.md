# 10 · 前后端对接契约（v2 agent API）

前端重写时的唯一权威接口文档（2026-08-10 定稿）。后端实现：`backend/app/api/v2/agent.py`、`backend/core/events.py`、`backend/core/harness.py`。

## 一、概览

- API 前缀：`/api/v2`；数据：`data/agent_sessions_v2/{session_id}/`（meta.json + transcript JSONL + artifacts/）
- 交互模型：**会话中心**。创建会话 → 持有 harness（进程内 registry）；发消息 → SSE 事件流（含审批交互）
- 事件流时序：`agent_start → [assistant_delta* → assistant_message → tool_started → tool_finished]* → turn_end → agent_end`
- 事件 id：`{session_id}-evt-{n}`，n 为**会话级递增**（跨 send 不重置）

## 二、端点明细

### 1. 创建项目
`POST /api/v2/projects`
```json
请求: {"name": "书名", "genre": "悬疑"}   // genre 可空
返回: {"id": "...", "name": "...", "genre": "..."}
```

### 2. 创建会话
`POST /api/v2/agent/sessions`
```json
请求: {"project_id": "...", "system_prompt": "可选，默认网文作者 prompt，≤4000 字"}
返回: {"session_id": "...", "project_id": "...", "system_prompt": "..."}
```
404：project 不存在。

### 3. 发送消息（核心，SSE 流）
`POST /api/v2/agent/sessions/{sid}/messages`
```json
请求: {"content": "写第一章", "idempotency_key": "可选（重复投递安全，成功才标记）"}
返回: text/event-stream，逐事件推送（见第三节）
```
- 会话写锁：同一会话并发 send 串行（后者等待）
- follow-up 链：模型自然结束后若队列有追加要求则续跑（上限 5 回合）
- **stream 结束 = agent_end 之后**（服务端随后执行章末自省，不产生事件）
- 幂等键语义：执行中失败/中断不标记 → 客户端可安全重试

### 4. 生成中注入方向（steer）
`POST /api/v2/agent/sessions/{sid}/steer`
```json
请求: {"content": "节奏放慢"}
返回: {"queued": "steer", "session_id": "..."}
```
语义：当前工具批完成后、下次 LLM 调用前注入（one-at-a-time 排空）。

### 5. 完成后追加要求（follow-up）
`POST /api/v2/agent/sessions/{sid}/followup`
```json
请求: {"content": "继续写第二章"}
返回: {"queued": "followup", "session_id": "..."}
```
语义：agent 本要停止时再续跑一轮（"连写 N 章"驱动）。

### 6. 审批通过 / 7. 审批拒绝
`POST /api/v2/agent/sessions/{sid}/approve?call_id=...`
`POST /api/v2/agent/sessions/{sid}/reject?call_id=...`（可选 body: {"reason": "..."}）
- call_id 来自 approval_pending 事件；已处理/不存在 → 404
- 审批超时：600s 未决自动拒绝（fail-closed）

### 8. 待审批列表
`GET /api/v2/agent/sessions/{sid}/pending-approvals`
```json
返回: {"session_id": "...", "pending": [{"call_id": "...", "name": "write_chapter", "arguments": {...}}]}
```

### 9. 事件重放
`GET /api/v2/agent/sessions/{sid}/events`
```json
返回: {"session_id": "...", "events": [{"type": "message|compaction|turn_ended|...", "data": {...}}]}
```
来源：transcript JSONL（append-only）。`turn_ended` 是日志记录（含 exit_detail），**不是**对话消息。

## 三、SSE 事件协议

事件格式：`event: {kind}\ndata: {json}\n\n`。data 含 `kind`、`event_id` 及事件字段。

| kind | 字段 | 含义 |
|---|---|---|
| `agent_start` | session_id | 一次 send 开始 |
| `assistant_delta` | text | 流式文本增量（正文生成中实时显示） |
| `assistant_message` | content, tool_call_names | 完整助手消息（无工具调用 = 回合正文回复） |
| `tool_started` | call_id, name, arguments | 工具开始执行 |
| `tool_finished` | call_id, name, is_error, result_text, error_code, next_action | 工具完成（失败分类 error_code：unknown_tool/validation/transient/permanent/permission/internal） |
| `guard_tripped` | level, reason, diagnosis | 护栏触发（L1-L5），回合中止 |
| `context_warning` | usage_pct, total_tokens, max_tokens | 上下文用量超 75% 阈值 |
| `compaction` | before_count, after_count, summary | 上下文压缩发生 |
| `approval_pending` | call_id, name, arguments | **write 工具被审批门拦截**（独立通道，恰好一次） |
| `turn_end` | stop_reason, iterations, prompt_tokens, completion_tokens, exit_detail | 回合结束（stop_reason: completed/iteration_budget_exhausted/token_budget_exhausted/wall_clock_exceeded/interrupted/guard_tripped） |
| `agent_end` | turns | 一次 send 完成（**前端收到此事件即可关闭连接**；后续自省在服务端流外执行） |

前端渲染规则：
- 正文 = 收集 `assistant_delta` 累积显示，`assistant_message` 为权威内容
- 工具活动 = tool_started/tool_finished 对（可做工具进度 UI）
- 审批 = approval_pending → 弹窗（工具名 + 参数）→ approve/reject 端点

## 四、数据模型（SQLite，7 活跃表）

| 表 | 关键字段 | 用途 |
|---|---|---|
| projects | name, genre, target_word_count, current_word_count, status, style_config | 项目 |
| outlines | chapters(JSON: chapter_index/title/summary) | 大纲 |
| chapter_contents | chapter_index, title, content, word_count, status | 章节正文 |
| longform_memories | memory_type(plotline/story_arc/arc_summary/writing_experience/introspect_log...), scope_key, summary, status, memory_metadata(JSON) | 记忆（含写作经验系统） |
| setups | characters(JSON), world_building(JSON), core_concept | 设定 |
| entity_candidates | name, source(rule/l2), chapter_count, first/last_chapter | 实体候选（转正：≥2 章或 l2） |
| entity_relations | entity_a, entity_b, count, last_chapter | 实体共现图 |

## 五、前端约定与注意

1. **会话生命周期**：session 持久在磁盘（meta.json + transcript），服务重启后懒重建；会话空闲 1 小时惰性清理。前端可基于 session_id 恢复历史（/events 重放 + transcript）
2. **幂等键**：重试场景（网络中断后重新 send）必须携带原 idempotency_key，避免重复执行
3. **审批是全自动写作的关键交互**：write 类工具（write_chapter/plan_arc/track_plotline/get_entities）都被拦截；前端应提供"自动批准/逐条确认"两种模式
4. **per-book 自优化**：章末自省在流外执行（agent_end 后 ~1-2k token LLM 调用）；`NOVELV3_SELF_OPTIMIZE=0` 可全局关闭（快照经验段 + 自省同时关）
5. **事件重放 vs 消息流**：turn_ended/compaction 等只进 transcript 日志，**不**是对话消息；渲染历史用 /events 重放
6. **附件**：write_chapter 的 artifact 落盘于 `data/agent_sessions_v2/{sid}/artifacts/chapters/chapter_NNN.md`（工具返回 artifact 路径指针）

## 六、待前端定盘时追加的接口（已预留）

- 写作经验作者入口（delete/pin——domain 函数已就绪，API 待接线）
- 人工章节标注（方案 B：新交互 → 新 API → pipeline revise，`extra_feedback` 为预留入口）
- 章节回滚（versions 按需重建）
