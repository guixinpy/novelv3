# Phase56 报告：命令契约投影模块

## 目标

将 `agent_command_contracts` 从 `run_service` 的私有抽取逻辑中拆出，形成可复用的纯函数模块。该投影用于稳定展示 planner trace 中的命令契约摘要，后续 Trace audit、Job projection 或前端详情面板需要复用时不再复制路径解析逻辑。

## 变更

1. 新增 `backend/app/services/writing_agent/command_contract_projection.py`。
   - 暴露 `COMMAND_CONTRACTS_SOURCE`。
   - 暴露 `command_contracts_from_run_input(run_input)`。
   - 只返回有界 summary：`total_commands`、`public_commands`、`agent_control_commands`、`available_commands`、`gap_count`。
   - 不透出原始 `commands` 列表，避免 run detail 负载继续膨胀。
2. 新增 `backend/tests/test_command_contract_projection.py`。
   - 覆盖正常摘要提取。
   - 覆盖无摘要时返回 `None`。
3. 替换 `backend/app/services/writing_agent/run_service.py` 中 `detail_payload()` 的命令契约来源。
4. 删除本阶段抽取后不再被调用的 `_planner_health_projection_from_run`。

## 验证

T0/T1 验证结果：

```powershell
pytest backend/tests/test_command_contract_projection.py -q
# 2 passed

pytest backend/tests/test_command_contract_projection.py backend/tests/test_control_plane_readiness_projection.py -q
# 4 passed

pytest backend/tests/test_writing_agent_runs.py -k "agent_run_detail_exposes_agent_profile_projection_for_auto_plan or recommended_followup" -q
# 8 passed, 177 deselected

pytest backend/tests/test_dialogs.py -k "agent_command_contract_detail_items or agent_control_plane_readiness_detail_items" -q
# 2 passed, 103 deselected

rg -n "_planner_health_projection_from_run|_agent_command_contracts_from_run|_control_plane_readiness_from_run|_agent_control_plane_readiness_from_run|_control_plane_needs_attention\(" backend/app/services/writing_agent
# no matches

git diff --check
# pass; existing warning only: backend/tests/test_writing_agent_runs.py CRLF will be replaced by LF
```

## 结论

Phase56 完成了命令契约 run detail 投影的模块化收口。当前 API 字段形状保持不变，后续可以继续把该共享投影接入 Trace audit / Job projection，或推进前端对命令契约摘要的展示一致性。
