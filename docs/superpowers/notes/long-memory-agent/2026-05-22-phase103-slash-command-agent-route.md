# Phase103 Report: Slash Command Agent Route

## Goal Alignment

本阶段落实用户补充约束：长期 goal 的核心是把 novelv3 升级为专精网络小说写作的长期记忆 Agent，而不是把主要时间花在手动写小说上。小说生成只作为压力测试和问题发现主线。

因此本阶段选择处理 `/` 命令边界：它原本只是对话 UI 的快捷入口，现在需要先成为 Writing Agent 可见、可检查、可审计的工具路由。

## Implemented

- 在 `backend/app/core/chat_commands.py` 中为生成类命令补充 Agent route 契约：
  - `/setup` -> `generate_setup`
  - `/storyline` -> `generate_storyline`
  - `/outline` -> `generate_outline`
  - `/chapter` -> `generate_chapter`
- 非生成类命令 `/clear`、`/compact` 不暴露为 Agent 生成工具。
- 在 command pending action params 中写入 `agent_route`，保留对话入口到 Agent 工具的审计信息。
- 在 dialog control plane 中剥离 `agent_route` 和 `project_id`，确保具体工具只收到业务参数。
- 新增 Writing Agent 只读检查工具 `inspect_agent_slash_command_route`，用于 Agent 自查当前斜杠命令路由投影。
- route 自查结果会标记执行后端：
  - `static_adapter`：由 Writing Agent tool executor 直接处理。
  - `action_execution_service`：由 Writing Agent run service fallback 到既有 action execution 链路处理。

## Verification

RED:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_dialogs.py backend/tests/test_writing_agent_tool_executor.py -k "chat_command_registry_helpers_cover_expected_commands or chapter_command_leading_index_wins_over_context_mentions or agent_control_plane_routes_confirmed_setup_through_writing_agent_run or inspect_agent_slash_command_route" -q
```

Result:

```text
ImportError: cannot import name 'CHAT_COMMAND_AGENT_ROUTE_VERSION'
66 deselected, 1 error
```

GREEN:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_dialogs.py backend/tests/test_writing_agent_tool_executor.py -k "chat_command_registry_helpers_cover_expected_commands or chapter_command_leading_index_wins_over_context_mentions or agent_control_plane_routes_confirmed_setup_through_writing_agent_run or inspect_agent_slash_command_route" -q
```

Result:

```text
4 passed, 119 deselected in 0.33s
```

T1:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_dialogs.py backend/tests/test_writing_agent_tool_executor.py -k "command or slash_command or agent_control_plane or inspect_agent_slash_command_route" -q
```

Result:

```text
17 passed, 106 deselected in 1.33s
```

Architecture review:

```text
Subagent read-only review confirmed the direction is aligned with module toolization.
It also recommended proving route execution support, so the route projection now includes execution_supported/execution_backend.
```

Completion checks:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

Result:

```text
git diff --check: no output
secret scan: no matches
```

## Notes

- 本阶段没有改动章节生成内容策略，也没有新增手动小说写作流程。
- 这是为后续统一“对话输入 -> Agent 计划 -> 工具选择 -> 工具执行 -> Trace 审计”打基础。
- 当前 route 仍复用 pending action 确认机制；后续可以继续把 `/` 命令 UI 改造成 Agent command palette 或 tool invocation preview。

## Next Phase Suggestion

建议 Phase104 继续处理对话入口 Agent 化：让普通自然语言 intent 与 `/` 命令共享同一套 Agent route projection，而不是保留两套并行入口逻辑。这样可以逐步减少旧 intent router 与 Agent planner 的重复边界。
