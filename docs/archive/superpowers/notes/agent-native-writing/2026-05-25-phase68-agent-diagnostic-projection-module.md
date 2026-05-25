# Phase68: Agent 诊断动作投影模块拆分

## 目标

继续降低 `agentRunProjection.ts` 的维护压力，把 Trace、任务队列、健康、命令契约、控制平面、记忆路由与知识库路由这些 Agent 基础设施诊断 action view 迁入独立模块。

## 变更

1. 新增 `frontend/src/components/chat/agentDiagnosticRunProjection.ts`。
2. 新模块导出：
   - `DIAGNOSTIC_AGENT_RUN_ACTION_TYPES`
   - `DIAGNOSTIC_AGENT_RUN_ACTION_DESCRIPTORS`
3. 覆盖 7 个诊断工具：
   - `inspect_agent_trace_audit`
   - `inspect_agent_job_projection`
   - `inspect_agent_health_projection`
   - `inspect_agent_command_contracts`
   - `inspect_agent_control_plane_readiness`
   - `inspect_agent_memory_route`
   - `inspect_agent_knowledge_base_route`
4. `agentRunProjection.ts` 改为聚合诊断模块、写作工具模块、长篇批次模块。
5. 文件规模变化：
   - `agentRunProjection.ts`: 1707 行 -> 671 行
   - `writingToolAgentRunProjection.ts`: 704 行
   - `agentDiagnosticRunProjection.ts`: 459 行

## TDD 证据

RED：

```text
npm run test:unit -- agentRunProjection
Failed to load url ./agentDiagnosticRunProjection
```

GREEN：

```text
npm run test:unit -- agentRunProjection
58 passed
```

## 验证

```text
npm run test:unit -- agentRunProjection
58 passed

npm run test:unit -- ChatMessage
29 passed

npm run build
vue-tsc --noEmit && vite build 成功

git diff --check
通过；仅保留既有 backend/tests/test_writing_agent_runs.py CRLF 警告。
```

## 下一阶段建议

继续拆分 `agentRunProjection.ts` 中剩余的恢复/推荐后继/路由升级投影，或为这些投影模块增加更细粒度的独立测试文件，减少单个 `agentRunProjection.test.ts` 的增长。
