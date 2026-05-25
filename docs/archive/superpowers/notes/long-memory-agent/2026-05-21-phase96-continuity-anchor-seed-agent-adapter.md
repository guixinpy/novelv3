# Phase96 Continuity Anchor Seed Agent Adapter Report

## Goal

将 `seed_continuity_anchor_proposals` 从 `WritingAgentRunService` legacy execution branch 迁移为 Agent-native static adapter，使稳定连续性锚点提案生成成为 Writing Agent 可统一编排、可投影、可审计的工具能力。

## Changes

- 新增 `backend/app/services/writing_agent/continuity_anchor_seed_tool.py`
  - 包装 `app.core.continuity_anchor_proposals.seed_continuity_anchor_proposals()`
  - 保留领域函数返回的 `recommended_actions`、`should_generate_next_chapter` 和统计字段
- 更新 `backend/app/services/writing_agent/tool_executor.py`
  - 新增 `_seed_continuity_anchor_proposals()` handler
  - 注册 `seed_continuity_anchor_proposals` static adapter
- 更新 `backend/app/services/writing_agent/tool_registry.py`
  - 新增 `_CONTINUITY_ANCHOR_SEED_OUTPUT`
  - 将 `seed_continuity_anchor_proposals.output_schema` 从 `_STATUS_OUTPUT` 改为结构化契约
- 更新 `backend/app/services/writing_agent/run_service.py`
  - 删除 `seed_continuity_anchor_proposals` legacy execution branch
  - 当前 `_execute_tool()` 不再包含已知 internal tool execution special-case
- 更新测试
  - `backend/tests/test_writing_agent_tool_executor.py`
  - `backend/tests/test_writing_agent_tool_registry.py`

## RED Evidence

命令：

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py -k "seed_continuity_anchor_proposals or inspect_agent_tool_contracts or unhandled_internal_tools or static_adapter_names" -q
```

结果：`6 failed, 2 passed, 82 deselected`

预期失败点：

- static adapter names 缺少 `seed_continuity_anchor_proposals`
- unhandled migration tracking 仍包含 `seed_continuity_anchor_proposals`
- adapter metadata 返回 `None`
- contract snapshot 中 adapter_type 仍为 `None`
- dispatch test 找不到 `continuity_anchor_seed_tool`
- registry output schema 仍只有 `status`

## GREEN Evidence

命令：

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py -k "seed_continuity_anchor_proposals or inspect_agent_tool_contracts or unhandled_internal_tools or static_adapter_names" -q
```

结果：`8 passed, 82 deselected`

## Regression Evidence

命令：

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "seed_continuity_anchor_proposals" -q
```

结果：`1 passed, 161 deselected`

## Static Checks

- `git diff --check`：通过，无 whitespace error。
- `rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"`：无命中。
- `Select-String backend\app\services\writing_agent\run_service.py`：未发现 `seed_continuity_anchor_proposals` legacy execution branch 或 `app.core.continuity_anchor_proposals` import/call 残留。

## Subagent Review

Reviewer: `019e4a13-8174-75f3-b0e2-8e6c55381c45`

结论：

- `seed_continuity_anchor_proposals` 已从 `WritingAgentRunService._execute_tool()` legacy execution branch 移到 static adapter。
- adapter metadata、category、mutability、handler name 与测试一致。
- output schema 已不再使用 `_STATUS_OUTPUT`，足以支撑 Agent 判断阻塞、审批动作和是否继续生成。
- 测试覆盖 static adapter、migration tracking、contract snapshot、dispatch 和 registry schema。

Reviewer 必须处理项：

- `backend/app/services/writing_agent/continuity_anchor_seed_tool.py` 是新增文件，提交前必须显式 `git add`。本报告提交前会一并暂存。

Reviewer 结构化提醒：

- `run_service.py` 仍包含非执行类 tool-specific policy：报告阻塞、允许后续工具、阻塞消息映射。这不是本阶段的 legacy execution branch，但后续应抽离为 Agent tool policy / transition contract，减少 run service 中的工具名特判。

## Next

下一阶段高价值候选：

- 将 `run_service.py` 中的报告阻塞、后续工具允许、阻塞消息映射抽离为独立 Agent tool policy 模块。
- 继续从 `inspect_agent_tool_contracts` 输出中挑选 `missing_agent_native_adapter` 或 `output_schema_too_generic` 的高价值工具。
