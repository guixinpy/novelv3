# M2 执行计划

## Phase A：新增写入工具 + 审批门

### A1：approval.py + Harness 审批拦截
- `agent/approval.py` — ApprovalGate 类
- Harness.send_message() 拦截 permission=write → 发 approval_pending 事件
- API: POST approve/{id} / reject/{id}
- 测试: approval 流程单测

### A2：写入工具（5 个 @tool）
- `tools/chapters.py` 追加 write_chapter / revise_chapter
- `tools/world.py` 追加 propose_world_change
- `tools/project.py` 追加 update_outline / update_setup
- 测试: 工具单测（成功/失败/参数验证）

### A3：前端审批 UI
- AgentV2View.vue 或独立组件：approval card
- SSE 事件 handler 处理 approval_pending
- 审批按钮调用 POST approve/reject
- `v2_sessions.py` SSE 流支持 approval_pending 事件类型

**验证**：`pytest backend/tests/agent/ -q` + 前端 build

---

## Phase B：删除旧编排层

### B1：删除描述符-适配器层
删除 27 个文件（~8,396 LOC）：
```
rm services/writing_agent/tool_descriptor_types.py
rm services/writing_agent/tool_adapter_types.py
rm services/writing_agent/agent_*_tool_descriptors.py
rm services/writing_agent/agent_*_tool_adapters.py
rm services/writing_agent/*_generation_tool_descriptors.py
rm services/writing_agent/*_generation_tool_adapters.py
rm services/writing_agent/world_model_tool_descriptors.py
rm services/writing_agent/world_model_tool_adapters.py
rm services/writing_agent/hermes_action_tool_descriptors.py
rm services/writing_agent/knowledge_base_tool_descriptors.py
rm services/writing_agent/knowledge_base_tool_adapters.py
rm services/writing_agent/longform_tool_descriptors.py
rm services/writing_agent/longform_tool_adapters.py
rm services/writing_agent/memory_tree_tool_descriptors.py
rm services/writing_agent/memory_tree_tool_adapters.py
rm services/writing_agent/review_revision_tool_descriptors.py
rm services/writing_agent/review_revision_tool_adapters.py
rm services/writing_agent/agent_task_queue_tool_descriptors.py
rm services/writing_agent/agent_task_queue_tool_adapters.py
```
删除依赖文件：
```
rm services/writing_agent/tool_contracts.py
rm services/writing_agent/tool_executor.py
rm services/writing_agent/tool_lifecycle_hooks.py
rm services/writing_agent/tool_policy.py
rm services/writing_agent/tool_registry.py
rm services/writing_agent/tool_request_validation.py
rm services/writing_agent/tool_recommendations.py
```
**验证**：`pytest tests/ -q` 全绿

### B2：删除生成执行管线
```
rm services/writing_agent/chapter_generation_execution.py
rm services/writing_agent/outline_generation_execution.py
rm services/writing_agent/setup_generation_execution.py
rm services/writing_agent/storyline_generation_execution.py
rm services/writing_agent/api_control_plane.py
```
**验证**：`pytest tests/ -q` 全绿

### B3：附属文件
```
rm services/writing_agent/slash_command_route.py
rm services/writing_agent/dialog_control_plane.py
rm services/writing_agent/dialog_intent_planner.py
```
**验证**：`pytest tests/ -q` 全绿

### B4：测试清理
- 删除只为旧编排服务的测试文件
- 更新 test_support/
- **验证**：`pytest tests/ -q` 全绿 + `git diff --stat` 确认 LOC 下降

---

## 最终验证

```bash
# LOC 统计
git diff --stat main
cloc backend/app/

# 无残留引用
git grep -E "intent_router|run_service|tool_descriptor" -- backend/app/

# 全量测试
cd backend && pytest tests/ -q

cd frontend && npm run build && npx vitest run
```

---

## 回滚策略

每一批删除前：
```bash
git add -A && git commit -m "checkpoint before B<N>"
```
删除后测试不通过则：
```bash
git reset --hard HEAD~1
```
