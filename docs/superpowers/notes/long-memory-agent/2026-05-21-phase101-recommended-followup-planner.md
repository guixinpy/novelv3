# Phase101 Recommended Followup Planner Report

## 目标

让 Phase100 规范化后的 `agent_tool_result.recommendations.canonical_followups` 进入 Writing Agent 可消费面，但不自动执行后继工具。当前阶段只做两件事：

- 在 run `continuation_state` 中投影最近一次推荐后继，供上层 Agent/前端/Trace 判断下一步。
- 新增只读 internal tool `plan_recommended_followups`，把推荐后继转换为 preview-only 工具计划。

## 实现摘要

- 新增 `backend/app/services/writing_agent/recommended_followup_planner.py`。
- `run_service._continuation_state()` 新增 `recommended_followups` 字段；当 recovery 已推荐时，推荐后继被标记为 `suppressed`，优先恢复链路。
- `tool_registry.py` 注册 `plan_recommended_followups`，`tool_executor.py` 通过 static read adapter 执行。
- planner 只接受安全只读/规划类工具。guarded write 或未知工具进入 `trace.rejected_tools`，不会进入 `tools`。
- planner 禁止自循环和 source tool 复用循环，避免推荐链路把自己再次规划进去。

## RED 证据

初始 RED：

```text
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py backend/tests/test_writing_agent_tool_executor.py -k "recommended_followups or plan_recommended_followups" -q
```

结果：失败。原因符合预期：

- `continuation_state["recommended_followups"]` 尚不存在。
- `plan_recommended_followups` 尚未被 executor 处理。

审查反馈后的风险 RED：

- `apply_planner_revision_patch` 一类写工具若出现在 `canonical_followups`，必须被拒绝。
- source run 处于 blocked/failed 且 recovery 已推荐时，recommended followup planner 必须阻断。
- `plan_recommended_followups` 推荐自身时，必须拒绝 planner loop。

新增对应测试后，在修复前这些风险路径不可满足。

## GREEN 证据

聚焦测试：

```text
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py backend/tests/test_writing_agent_tool_executor.py -k "recommended_followups or plan_recommended_followups" -q
```

结果：

```text
5 passed, 224 deselected
```

## T1 验证

相关 Writing Agent 推荐链路、executor 和 run-service 测试：

```text
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_recommendations.py backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_runs.py -k "tool_recommendations or plan_recommended_followups or recommended_followups or inspect_agent_tool_contracts or seed_continuity_anchor_proposals_creates_missing_anchor_items or blocks_followup_generation or allows_resolution_plan_followup or allows_apply_followup" -q
```

结果：

```text
21 passed, 211 deselected in 1.67s
```

静态检查：

```text
git diff --check
```

结果：exit 0。PowerShell 输出了 `backend/tests/test_writing_agent_runs.py` 的 CRLF 提示，但没有 whitespace error。

密钥扫描：

```text
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

结果：exit 1，无匹配。

## 子代理审查

第一轮只读审查指出 3 个有效风险：

- 高风险：写工具可能通过推荐链路进入可执行工具计划。
- 中风险：blocked/failed run 在 recovery 未处理前可能同时暴露推荐后继。
- 中风险：planner 可能把自己规划进后继链路形成循环。

处理结果：

- 增加 `SAFE_RECOMMENDED_FOLLOWUP_TOOLS`，非安全推荐进入 `requires_confirmation`。
- recovery recommended 时，run continuation state 抑制 recommended followups，planner 返回 blocked。
- 增加 `LOOPING_FOLLOWUP_TOOLS`，拒绝 planner 自循环和 source tool 循环。
- 为三类风险均补了测试。

第二轮子代理复审因本地 agent quota 限制未能启动；本阶段以本地 T1 验证和风险测试补足。

## 参考项目吸收

- Hermes-agent 启发：推荐结果不应直接等于执行计划，必须经过 tool contract 和 valid tool surface。
- OpenClaw 启发：从候选能力到可执行动作之间要有 policy/confirmation 层；本阶段把写工具保留为拒绝项，后续再接确认门。
- OpenHuman 启发：长期记忆/推荐链路应保留 trace，而不是只返回下一步文本建议。

## 下一阶段建议

1. 将 `plan_recommended_followups` 的 preview plan 暴露到 Trace 或前端 Agent 面板，方便用户看到“为什么建议下一步工具”。
2. 为 guarded write 建立显式确认门，让 `requires_confirmation` 可以进入人工确认或 Agent policy 确认流程，而不是长期停留在拒绝项。
3. 继续迁移高价值推荐工具为 executor-native，使推荐链路逐步从“可见”走向“可受控执行”。
