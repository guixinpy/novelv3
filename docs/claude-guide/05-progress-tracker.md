# 05 · 进度追踪

> 每次 session 开始先读本文档，结束前更新本文档。只追踪活跃工作；完成的里程碑折叠为一行。

## 当前状态

- **阶段**：M1 代码完成（退出标准 2/3 已验证；标准 1 需真实 API key dogfood）
- **分支**：`claude/agent-refactor`
- **最近更新**：2026-06-11

## 已完成

- ✅ 2026-06-11 仓库克隆、工作分支建立、旧 codex-guide 归档、参考快照更新、全库勘察、claude-guide 编写
- ✅ 2026-06-11 **M0 完成**：Provider 层（原生 tool-call + 流式 + 重试，TDD）、目录骨架 + 依赖规则测试、保留模块独立回归、verify_refactor.sh。全量 1766 passed
- ✅ 2026-06-11 **M1 代码完成**：
  - `agent/loop.py` 无状态回合引擎（流式、工具执行、观察回填、steering 注入点、事件 sink 带背压）
  - `agent/harness.py` 有状态外壳（JSONL 会话日志、断点恢复、steering/follow-up 队列）
  - `agent/tooling.py` @tool 自注册 + read/propose/write 三级权限 + 模型可操作错误
  - `agent/budget.py` 迭代预算（含 refund）+ 令牌预算
  - `tools/` 首批只读工具：get_project_state / list_chapters / read_chapter / query_world / search_text
  - `/api/v2` 会话 API（创建/列表/历史/SSE 消息流）
  - 前端：`api/agentV2.ts`（SSE 客户端）+ `AgentV2View.vue`（开发验证页，路由 `/projects/:id/agent-v2`，未入导航）
  - 验证：后端 1813 passed、前端 691 passed + build 通过

## M1 退出标准核对

1. 🔴 真实对话 ≥2 工具调用——**待真实 DeepSeek API key dogfood**（机制已由 FakeProvider 测试覆盖）
2. ✅ 中断/恢复：JSONL 重建会话（test_resume_from_jsonl / test_tool_messages_persisted_and_resumed）
3. ✅ 内核单测：循环终止、预算耗尽、工具错误回填、流式事件序列、审批拦截钩子

## 下一步

1. 用户提供 API key 后做 M1 真实 dogfood（标准 1）
2. 启动 M2：写入类工具（write_chapter / revise_chapter / propose_world_change / update_outline / update_setup）+ 审批门
3. M2 删除阶段前先把前端审批 UI 迁到 v2

## 问题清单（dogfood / 评审发现，修复优先于新功能）

（空）

## 阻塞 / 待用户决策

- DeepSeek API key 可用性确认（M1 退出标准 1 的真实 dogfood 需要）
