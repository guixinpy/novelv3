# Phase97 Agent Tool Policy Module Report

## 目标

把 Writing Agent run service 中残留的报告类工具停止策略抽离为独立策略模块，让运行服务只负责执行编排，工具治理规则由可测试的 Agent tool policy 承载。

## 实现

- 新增 `backend/app/services/writing_agent/tool_policy.py`
  - `REPORT_STOP_TOOLS`
  - `ALLOWED_REPORT_FOLLOWUPS`
  - `REPORT_BLOCK_MESSAGES`
  - `allowed_report_followup()`
  - `should_stop_after_report()`
  - `successful_report_block_message()`
- 修改 `backend/app/services/writing_agent/run_service.py`
  - 删除本地 `_should_stop_after_report`、`_allowed_report_followup`、`_successful_report_block_message`
  - 改为调用 `tool_policy.py` 中的策略函数
- 新增 `backend/tests/test_writing_agent_tool_policy.py`
  - 覆盖报告类工具阻断
  - 覆盖允许治理后继工具放行
  - 覆盖末尾步骤和非报告工具放行
  - 覆盖特定阻断文案与默认文案

## 验证

RED:

```text
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_policy.py -q
ERROR backend\tests\test_writing_agent_tool_policy.py
ModuleNotFoundError: No module named 'app.services.writing_agent.tool_policy'
```

GREEN:

```text
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_policy.py -q
3 passed in 0.03s
```

T1:

```text
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "blocks_followup_generation or allows_resolution_plan_followup or allows_apply_followup" -q
10 passed, 152 deselected in 1.26s
```

静态检查：

```text
git diff --check
```

无输出。

```text
Select-String -Path backend\app\services\writing_agent\run_service.py -Pattern 'def _should_stop_after_report|def _allowed_report_followup|def _successful_report_block_message'
```

无输出。

```text
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

无匹配。

## 子代理审查

只读审查子代理 Descartes 未发现阻断问题。审查结论：

- 新策略集合与旧 `run_service.py` helper 语义一致。
- `run_service.py` 调用顺序未改变。
- 未发现本地 helper 残留。
- 测试覆盖关键分支。

剩余风险：新增单测是代表性覆盖，不是全量 golden table；现有集成测试已经覆盖主要阻断和允许后继链路，当前阶段不扩展测试面。

## 下一阶段建议

继续从 `run_service.py` 抽离剩余非执行职责，优先处理 planner/runtime policy 可复用的工具可见性、阻断原因和 next-tool recommendation 合约，为后续 Agent 自主规划提供更清晰的工具治理边界。
