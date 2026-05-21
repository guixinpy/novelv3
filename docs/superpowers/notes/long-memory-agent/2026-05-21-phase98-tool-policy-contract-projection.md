# Phase98 Tool Policy Contract Projection Report

## 目标

将 Phase97 抽离出的报告类工具运行策略投影到 `inspect_agent_tool_contracts`，让 Agent planner 在执行前能读取工具治理约束，而不是只在 `run_service.py` 执行时被动阻断。

## 实现

- `backend/app/services/writing_agent/tool_policy.py`
  - 新增 `report_policy_for_tool(tool_name)`
  - 返回稳定 JSON 可序列化结构：
    - `stop_check_required`
    - `stop_condition`
    - `allowed_followups`
    - `block_message`
- `backend/app/services/writing_agent/tool_contracts.py`
  - 在每个工具 contract 中加入 `report_policy`
  - 在 reference alignment pattern 中加入 `runtime_policy_projection`
- `backend/tests/test_writing_agent_tool_policy.py`
  - 覆盖 stop tool 和 non-stop tool 的 policy 投影
- `backend/tests/test_writing_agent_tool_executor.py`
  - 覆盖 `inspect_agent_tool_contracts` 输出中的 `runtime_policy_projection`
  - 覆盖 `generate_chapter` 与 `seed_continuity_anchor_proposals` 的 `report_policy`

## RED/GREEN

RED:

```text
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_policy.py backend/tests/test_writing_agent_tool_executor.py -k "tool_policy or inspect_agent_tool_contracts" -q
ImportError: cannot import name 'report_policy_for_tool' from 'app.services.writing_agent.tool_policy'
```

GREEN:

```text
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_policy.py backend/tests/test_writing_agent_tool_executor.py -k "tool_policy or inspect_agent_tool_contracts" -q
6 passed, 60 deselected in 0.24s
```

## T1 验证

```text
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_policy.py backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_runs.py -k "tool_policy or inspect_agent_tool_contracts or blocks_followup_generation or allows_resolution_plan_followup or allows_apply_followup" -q
16 passed, 212 deselected in 1.03s
```

静态检查：

```text
git diff --check
```

无输出。

```text
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

无匹配。

## 子代理审查

只读审查子代理 Rawls 未发现阻断问题。审查反馈：

- `report_policy_for_tool` 的投影准确，排序稳定，返回值无 JSON 序列化风险。
- `tool_contracts.py` 只增加只读 contract snapshot 字段，不改变 `run_service.py` 的运行语义。
- 测试覆盖了 stop/non-stop 样例和 contract 输出。

子代理指出 `stops_after_report` 字段名容易被误解为“成功后必停”。已采纳并调整为：

- `stop_check_required`
- `stop_condition = non_terminal_step_and_should_generate_next_chapter_false_without_allowed_followup`

## 参考项目启发

本阶段继续按 `references/agent-projects` 方向推进：参考项目共同强调工具能力需要可见的 typed/tool surface，而不是只在运行时埋规则。novelv3 的对应转译是：把写作领域工具的运行策略、权限、恢复路径、记忆边界和结果结构都投影到 Agent 可检查的 contract 中。

## 下一阶段建议

继续把 `inspect_agent_tool_contracts` 从“诊断快照”推进为 planner 可直接消费的工具治理面，下一步可以优先补：

- `recommended_followup_tools` 的统一 contract 字段；
- 输出中的 `recommended_actions` 与 `recommended_next_tools` 归一化；
- report policy 与 recovery policy 的联合建议，让 Agent 能自动从阻断状态选择治理工具链。
