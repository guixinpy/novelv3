# Phase143 Approval Mutation Fingerprint Report

## Objective

把 Phase142 的 mutation fingerprint 从只读检查工具接入 Writing Agent 审批链路，使 write step 在审批 contract 中绑定具体目标，减少“预览 A、确认后执行 B”的目标漂移风险。

本阶段仍不把 fingerprint 当作权限边界。权限与资源归属仍应由后端从 project、plan、DB 和执行上下文派生并校验。

## Reference Check

本阶段派出只读 explorer 检查三个参考 Agent 项目的目标绑定模式：

- `references/agent-projects/openclaw/extensions/codex/src/app-server/session-binding.ts`
- `references/agent-projects/openclaw/src/agents/pi-embedded-runner/effective-tool-policy.ts`
- `references/agent-projects/openclaw/src/agents/pi-embedded-runner/run/attempt.tool-call-normalization.ts`
- `references/agent-projects/hermes-agent/tools/approval.py`
- `references/agent-projects/hermes-agent/tools/checkpoint_manager.py`
- `references/agent-projects/openhuman/src/openhuman/agent/harness/tool_loop.rs`
- `references/agent-projects/openhuman/src/openhuman/approval/ops.rs`
- `references/agent-projects/openhuman/src/openhuman/security/audit.rs`

可转译结论：

- write/action step 需要稳定 `tool_call_id` 或等价 trace id 贯穿审批、进度和结果。
- 会改章节、世界模型或记忆的 action 需要 `mutation_fingerprint` 防止目标漂移。
- 不信任模型或调用方自报的目标身份；可信绑定应由后端从上下文派生。
- 危险/不可逆写入应保持 `preview -> approval -> apply` 两段式。
- 不照搬 Hermes 的 shadow git checkpoint 到 SQL 写入；后续更适合做 DB before snapshot / version / affected count。

## Implementation

- `build_agent_plan_approval_contract()` 现在会为 write step 自动附加 `mutation_fingerprint`。
- `verify_agent_plan_approval_contract()` 现在输出：
  - `mutation_fingerprint_checked`
  - `mutation_fingerprint_drift_count`
  - `mutation_fingerprints`
- 当 write step 的 fingerprint 不可用时，验证会返回：
  - `status`: `blocked`
  - `reason`: `mutation_fingerprint_not_ready`
  - `recommended_next_tools`: `["inspect_agent_mutation_fingerprints"]`
- `prepare_generate_chapter_execution()` 现在在 direct chapter plan step 和顶层输出中暴露同一个 `mutation_fingerprint`。
- `prepare_generate_chapter_execution` 工具 schema 增加 `mutation_fingerprint` 输出字段。

## TDD Evidence

Approval contract RED:

```text
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_approval_contract.py::test_approval_contract_attaches_mutation_fingerprint_to_write_steps backend\tests\test_writing_agent_approval_contract.py::test_verify_approval_contract_blocks_when_mutation_fingerprint_not_ready -q
KeyError: 'mutation_fingerprint'
AssertionError: assert 'ready' == 'blocked'
```

Approval contract GREEN:

```text
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_approval_contract.py -q
14 passed in 0.07s
```

Direct prepare RED:

```text
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_chapter_generation_execution.py::test_prepare_generate_chapter_execution_returns_agent_approval_contract -q
KeyError: 'mutation_fingerprint'
```

Direct prepare GREEN:

```text
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_chapter_generation_execution.py -q
4 passed in 0.39s
```

Registry RED:

```text
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_tool_registry.py::test_agent_tool_registry_includes_approved_direct_chapter_generation_tools -q
KeyError: 'mutation_fingerprint'
```

Registry GREEN:

```text
1 passed in 0.04s
```

## Verification

Targeted regression:

```text
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_approval_contract.py backend\tests\test_writing_agent_chapter_generation_execution.py backend\tests\test_writing_agent_tool_registry.py backend\tests\test_writing_agent_tool_executor.py backend\tests\test_writing_agent_mutation_fingerprint.py -q
143 passed in 6.24s
```

Narrow integration smoke:

```text
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_chapter_prepare_background_work_records_approval_required_without_generating backend\tests\test_dialogs.py::test_chapter_approval_pending_message_uses_specific_description backend\tests\test_dialogs.py::test_chapter_approval_followup_dispatches_execute_tool backend\tests\test_dialogs.py::test_chapter_approval_followup_resolve_action_records_decision_metadata backend\tests\test_writing_agent_runs.py::test_agent_run_execute_longform_chapter_batch_requires_agent_plan_approval_contract backend\tests\test_writing_agent_runs.py::test_agent_run_execute_longform_chapter_batch_blocks_agent_plan_approval_hash_drift -q
6 passed in 0.94s
```

Hygiene:

```text
git diff --check
<no output>
```

```text
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
<no matches>
```

## Novel Progress

本阶段未生成新章节。原因：当前阶段是 Agent 写动作审批绑定能力建设，直接服务长篇自动生成的执行可靠性。

## Known Limits

- fingerprint 已进入 approval contract，但还未持久化到 `WritingAgentStep` 行。
- 当前 direct chapter prepare 已暴露 fingerprint；批量章节执行准备仍只通过 `agent_plan_approval_contract` 间接携带。
- fingerprint 仍不能代替权限、资源归属或用户确认。
- 尚未实现 write action 的 `tool_call_id` 贯穿链路。

## Next Recommendation

Phase144 建议引入 server-derived `tool_call_id` / `resource_binding`：

- 为 write step 派生稳定 `tool_call_id`，贯穿 `WritingAgentStep`、approval verification event、pending action 和 trace audit。
- 为章节、世界模型 proposal、任务队列写入增加 `resource_binding`，明确 `project_id`、`target_type`、`target_id`、`source_trace_id`。
- 后续再考虑执行时比较 expected fingerprint 与当前 target binding。
