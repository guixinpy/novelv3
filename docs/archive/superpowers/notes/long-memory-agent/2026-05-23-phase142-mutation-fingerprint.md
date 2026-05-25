# Phase142 Mutation Fingerprint Report

## Objective

为 Writing Agent 增加只读 mutation fingerprint 投影，使恢复计划、审批链和冲突诊断可以把写动作绑定到明确项目目标，而不是只依赖工具名或自然语言描述。

本阶段重点回应 Phase141 的后续建议：先覆盖 `generate_chapter`、`generate_chapter_range`、`apply_world_model_proposal_resolution` 三类高价值写动作。

## Implementation

- 新增 `backend/app/services/writing_agent/mutation_fingerprint.py`
  - `build_mutation_fingerprint(project_id, tool_name, params)`
  - `inspect_agent_mutation_fingerprints(project_id, tools)`
  - 使用稳定 JSON 序列化和 SHA-256 生成 fingerprint。
  - 输出 machine-readable components：`version`、`project_id`、`tool_name`、`action`、`target_type`、`target_id`。
- 新增内部只读工具 `inspect_agent_mutation_fingerprints`
  - `category`: `preflight`
  - `target_type`: `agent_mutation_fingerprint`
  - `non_blocking_report`: `true`
  - executor adapter mutability: `read`
- 覆盖目标识别：
  - `generate_chapter` -> `chapter:{chapter_index}`
  - `generate_chapter_range` -> `chapters:{start}-{end}`
  - `apply_world_model_proposal_resolution` -> proposal bundle、proposal plan 或 decisions digest。

## TDD Evidence

RED:

```text
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_mutation_fingerprint.py -q
ModuleNotFoundError: No module named 'app.services.writing_agent.mutation_fingerprint'
```

GREEN:

```text
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_mutation_fingerprint.py -q
4 passed in 0.03s
```

Registry RED:

```text
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_tool_registry.py::test_agent_tool_registry_includes_inspect_agent_mutation_fingerprints -q
assert None is not None
```

Registry GREEN:

```text
1 passed in 0.19s
```

Executor RED:

```text
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_tool_executor.py::test_tool_executor_dispatches_inspect_agent_mutation_fingerprints_adapter -q
assert False is True
```

Executor GREEN:

```text
1 passed in 0.20s
```

## Verification

Targeted regression:

```text
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_mutation_fingerprint.py backend\tests\test_writing_agent_tool_executor.py backend\tests\test_writing_agent_tool_registry.py backend\tests\test_writing_agent_write_gate_coverage.py -q
130 passed in 6.01s
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

本阶段未生成新章节。原因：当前阶段服务于 Agent 写动作恢复、审批和冲突绑定能力，不以推进小说正文为主要产出。

## Known Limits

- fingerprint 目前只读投影，不会阻止执行时目标漂移。
- 未把 fingerprint 持久化到 `WritingAgentStep`、后台任务 payload 或审批 contract。
- `apply_world_model_proposal_resolution` 的 decisions fingerprint 只使用 proposal item 与 action 的稳定摘要，不记录完整 reason/evidence，避免把大型说明文本纳入恢复标识。

## Next Recommendation

Phase143 建议把 mutation fingerprint 接入审批 contract 或执行准备报告：

- `prepare_generate_chapter_execution` 输出 `mutation_fingerprint`。
- `preview_agent_plan_approval_contract` 校验 write step fingerprint 是否存在。
- 后续执行前比较 expected fingerprint 与当前计划 target，先做只读漂移报告，再考虑硬性阻断。
