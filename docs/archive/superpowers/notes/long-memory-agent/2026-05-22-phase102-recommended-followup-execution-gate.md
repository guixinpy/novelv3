# Phase102 Recommended Followup Execution Gate Report

## 目标

本阶段把 Phase101 的推荐后继预览推进到可确认执行的 Agent 编排入口。重点不是生成更多小说正文，而是让 Writing Agent 在生成、审查、世界模型分析等工具之间能自主衔接下一步，并保留用户确认、计划哈希和 Trace 审计。

## 目标校准

- 已重新读取 `docs/superpowers/specs/2026-05-18-long-memory-writing-agent-goal.md`。
- 当前 goal 的核心是把 novelv3 升级成专精网络小说写作的长期记忆 Agent。
- 小说生成只作为暴露系统问题和验证系统能力的主线，不是本阶段主要交付。
- 本阶段服务于“模块工具化”和“Agent 自主编排”：让上一个 run 的工具推荐进入下一轮 auto-plan，而不是要求用户手动指定 `review_chapter_quality`、`review_chapter_continuity` 等后继工具。

## 实现摘要

- `WritingAgentRunService.build_auto_plan_tools()` 新增 `recommended_followup_run_id` 分支。
- 默认行为：`auto_plan=True + recommended_followup_run_id` 只执行 `plan_recommended_followups` 预览。
- 执行行为：只有同时满足以下条件才把预览工具链转成当前 run 的实际工具：
  - `execute_recommended_followups=True`
  - `confirm_execute=True`
  - `recommended_followup_plan_hash` 与实时重建 plan 的 `plan_hash` 一致
  - plan 状态为 `completed` 且包含工具
- recovery 分支仍优先于 recommended followup 分支。
- guarded/write followup 仍由 Phase101 planner 拒绝；本阶段只执行 planner 输出的安全工具。

## RED 证据

新增测试后，生产代码修改前运行：

```text
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "recommended_followups_by_default" -q
```

结果：失败，`payload["input"]["planner"]["mode"]` 不存在。

```text
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "executes_recommended_followups_after_hash_confirmation" -q
```

结果：失败，`payload["input"]["planner"]["mode"]` 不存在。

```text
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "recommended_followup_hash_mismatch" -q
```

结果：失败，`payload["input"]["planner"]["mode"]` 不存在。

这些失败说明 auto-plan 尚未识别 recommended followup 分支，符合预期。

## GREEN 证据

实现确认门后运行：

```text
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "recommended_followups_by_default or executes_recommended_followups_after_hash_confirmation or recommended_followup_hash_mismatch" -q
```

结果：

```text
3 passed, 163 deselected
```

子代理审查指出低风险测试缺口后，补充：

- `execute_recommended_followups=True` 但缺 `confirm_execute` 或缺 `recommended_followup_plan_hash` 时回退 preview。
- `canonical_followups` 含 `apply_planner_revision_patch` 时，auto-plan 执行只允许安全的 `review_chapter_quality`，写工具保留在 rejected trace。

补充测试结果：

```text
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "recommended_followup_execute_without_confirmation or does_not_execute_guarded_recommended_followups" -q
```

结果：

```text
2 passed, 166 deselected
```

## T1 验证

相关 run-service、planner、executor 回归：

```text
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py backend/tests/test_writing_agent_tool_executor.py -k "recommended_followup or recommended_followups or recovery" -q
```

结果：

```text
20 passed, 214 deselected in 1.87s
```

静态检查：

```text
git diff --check
```

结果：exit 0。PowerShell 输出 `backend/tests/test_writing_agent_runs.py` 的 CRLF 提示，但没有 whitespace error。

密钥扫描：

```text
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

结果：exit 1，无匹配。

## 子代理审查

只读审查结论：

- 未发现当前 diff 会绕过 hash/confirm 执行 recommended followup auto-plan。
- recovery 优先级未被破坏。
- write/guarded tools 没有进入执行面。
- `run.input` 的 planner、plan_hash、hash_payload、source step、trace/rejected_tools 基本满足可审计性。

采纳的建议：

- 补 auto-plan 层负向测试，覆盖缺确认、缺 plan hash 和 guarded write followup。

## 参考项目吸收

- OpenHuman 的 controller registry 思路：外部入口不应各自绕过注册面，功能要通过统一 registry/contract 暴露。
- Hermes-agent 的 tool schema normalization 思路：执行前必须重新使用当前工具面和 schema 计算 plan，而不是信任旧客户端 payload。
- OpenClaw 的 tool-call trace 思路：计划、确认、执行和拒绝项都应进入可审计状态。

## 下一阶段建议

1. 将 slash commands 接入 Agent tool registry，避免 `/chapter`、`/outline` 等命令继续绕过 Agent 编排。
2. 把 recommended followup preview/execute 状态展示到 Agent run UI 或 Trace 面板。
3. 继续把高价值 legacy action 迁到 executor-native，减少 ActionExecutionService 的旧路径占比。
