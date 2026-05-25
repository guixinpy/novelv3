# Phase57 报告：Trace / Job 命令契约投影

## 目标

让命令契约健康度不只停留在 run detail 中，也能进入 Trace audit 与 Job projection，成为 Agent 运行面可审计、可推荐修复工具的一部分。

## 变更

1. `backend/app/services/writing_agent/command_contract_projection.py`
   - 新增 `command_contracts_needs_attention(command_contracts)`。
   - 判定规则保持简单：`summary.gap_count > 0`。
2. `backend/app/services/writing_agent/agent_trace_audit.py`
   - 输出新增 `command_contracts`。
   - `audit` 摘要新增 `command_contract_gap_count` 与 `command_contract_available_commands`。
   - 无 failure 且命令契约存在 gap 时，`recommended_actions` 追加 `inspect_agent_command_contracts`。
3. `backend/app/services/writing_agent/agent_job_projection.py`
   - selected task 新增 `command_contracts`。
   - `agent_runs` 中每个 run 新增有界 `command_contracts` 摘要。
   - selected task 的命令契约存在 gap 时，`recommended_tools` 推荐 `inspect_agent_command_contracts`。
4. 测试覆盖：
   - Trace audit 命令契约摘要与推荐动作。
   - Job projection 命令契约摘要与推荐工具。

## 验证

TDD RED：

```powershell
pytest backend/tests/test_writing_agent_trace_audit.py -k "command_contracts" -q
# failed: KeyError: 'command_contract_gap_count'

pytest backend/tests/test_writing_agent_job_projection.py -k "command_contracts" -q
# failed: KeyError: 'command_contracts'
```

GREEN / 回归：

```powershell
pytest backend/tests/test_writing_agent_trace_audit.py -k "command_contracts" -q
# 1 passed, 7 deselected

pytest backend/tests/test_writing_agent_job_projection.py -k "command_contracts" -q
# 1 passed, 4 deselected

pytest backend/tests/test_command_contract_projection.py -q
# 2 passed

pytest backend/tests/test_writing_agent_trace_audit.py -k "control_plane_readiness or command_contracts" -q
# 2 passed, 6 deselected

pytest backend/tests/test_writing_agent_job_projection.py -k "active_control_plane or command_contracts" -q
# 2 passed, 3 deselected

pytest backend/tests/test_command_contract_projection.py backend/tests/test_control_plane_readiness_projection.py -q
# 4 passed

git diff --check
# pass; existing warning only: backend/tests/test_writing_agent_runs.py CRLF will be replaced by LF
```

## 结论

Phase57 让命令契约摘要进入 Agent 的 Trace 与 Job 运行投影。现在控制面 readiness 与 `/` 命令迁移契约都能在后端审计层被统一观察，并能给出下一步自检工具推荐。
