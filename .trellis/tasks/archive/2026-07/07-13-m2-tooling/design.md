# M2 技术设计

## 执行策略：分两阶段

### Phase A：新增（构建模式，系统保持可用）
### Phase B：删除（绞杀式移除）

---

## Phase A：写入工具

### 工具模式（沿用 M1 @tool 约定）

```python
@tool(
    registry=registry,
    name="write_chapter",
    description="创建或覆盖指定章节的正文。会先清空该章节的现有内容再写入新内容。",
    permission="write",  # ← 新权限等级
    parameters={...},
)
async def write_chapter(ctx: ToolContext, chapter_index: int, content: str) -> ToolResult:
    ...
```

### 审批门设计

**位置**：`agent/approval.py`（新建）

**流程**：
1. LLM 发起 permission=write 的工具调用
2. Harness 拦截，不执行工具，改为发出 `approval_pending` SSE 事件
3. Harness 等待外部审批信号
4. 前端展示审批卡片 → 用户点「批准」或「拒绝」
5. 批准 → harness 执行工具 → 结果回 LLM
6. 拒绝 → harness 通知 LLM 用户拒绝，让模型调整方案

**API 扩展**：

```
POST /api/v2/sessions/{session_id}/approve — 批准当前待审批工具
POST /api/v2/sessions/{session_id}/reject — 拒绝当前待审批工具
Events: approval_pending {tool_name, arguments, id}
```

**审批状态**：存放在 Harness 中，不持久化到 JSONL（审批与回合绑定）。

### 工具清单

| 工具 | 参数 | 实现要点 |
|------|------|---------|
| write_chapter | chapter_index, content | 查重章节索引 → 删除旧内容 → 插入新内容 → 更新字数 |
| revise_chapter | chapter_index, instructions | 读取原文 + 模型用 revision 管线生成 diff |
| propose_world_change | entity_type, entity_id, changes | 创建 WorldProposalItem |
| update_outline | chapter_index, new_outline | 更新 Outline 记录 |
| update_setup | field, value | 更新 Setup JSON 字段 |

---

## Phase B：删除顺序（绞杀式）

### 批次 A：描述符-适配器层（~8,396 LOC）

删除条件：写入工具已上线并通过测试。

删除的文件：
```
services/writing_agent/tool_descriptor_types.py
services/writing_agent/tool_adapter_types.py
services/writing_agent/agent_core_tool_descriptors.py
services/writing_agent/agent_core_tool_adapters.py
services/writing_agent/agent_generation_tool_descriptors.py
services/writing_agent/agent_generation_tool_adapters.py
... (共 27 文件)
```

同时清理：`tool_contracts.py`、`tool_executor.py`、`tool_registry.py`、`tool_lifecycle_hooks.py`
（这些是适配器层的骨架，适配器删除后无实质内容）

### 批次 B：生成执行管线（~1,005 LOC）

```
services/writing_agent/chapter_generation_execution.py
services/writing_agent/outline_generation_execution.py
services/writing_agent/setup_generation_execution.py
services/writing_agent/storyline_generation_execution.py
services/writing_agent/api_control_plane.py
```

### 批次 C：附属文件（~890 LOC）

```
services/writing_agent/slash_command_route.py
services/writing_agent/dialog_control_plane.py
services/writing_agent/dialog_intent_planner.py
```

### 批次 D：测试清理

删除只为旧编排服务的测试文件，不再维护它们。

---

## 安全策略

1. **每批次删除后运行 `pytest tests/ -q` 全绿才进入下一批**
2. 删除文件前用 `grep -r "module_name" backend/app/` 确认无外部引用
3. `intent_router`/`planner`/`run_service`/`dialogs.py` 在最终 v1 API 下线前**不碰**
4. 最终 LOC 目标：27K → ≤19K（包含 Phase A 新增的 ~500 行）
