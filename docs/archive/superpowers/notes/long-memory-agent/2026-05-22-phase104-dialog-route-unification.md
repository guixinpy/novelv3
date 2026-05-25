# Phase104 Report: Dialog Route Unification

## Goal Alignment

本阶段继续围绕“把 novelv3 升级为专精网络小说写作的长期记忆 Agent”推进。重点不是生成更多小说正文，而是减少旧对话入口边界，让 Agent 能统一理解用户通过自然语言、按钮和斜杠命令提出的生成意图。

Phase103 只覆盖 `/` 命令。本阶段将同一 `agent_route` 契约扩展到：

- `slash_command`
- `text_intent`
- `button_action`

## Implemented

- 新增 `backend/app/core/dialog_agent_routes.py`：
  - `DIALOG_AGENT_ROUTE_VERSION = phase104.dialog_agent_route.v1`
  - `build_dialog_agent_route()`
  - `dialog_action_to_agent_tool_name()`
  - `preview_dialog_action_types()`
- `chat_commands.py` 中的 slash route 变成通用 route helper 的 thin wrapper。
- `dialogs.py` 中三类 pending action 均写入同形态 `agent_route`：
  - `/chapter ...` -> `source=slash_command`
  - “创建主角设定”这类自然语言 intent -> `source=text_intent`
  - 按钮 action -> `source=button_action`
- confirmed Writing Agent run 仍剥离 `agent_route`，不污染工具 params。
- 新增 Agent 自查工具 `inspect_agent_dialog_route_projection`：
  - 输出 slash/text/button 三类入口的 route projection。
  - 标记 tool 是否注册、执行后端是否可用。
  - 保留 Phase103 的 `inspect_agent_slash_command_route`。

## Reference Learning

本阶段让子代理只读分析了 `openclaw`、`hermes-agent`、`openhuman` 的相关设计，吸收了三点：

- OpenClaw：输入语法、通道能力和工具执行应解耦，不能让 slash/text/button 三套入口各自维护业务路径。
- Hermes：slash/skill 是入口，真正事实应进入 tool loop；route projection 只负责说明将要调用哪个工具，能否执行仍由 policy/executor/confirmation gate 决定。
- OpenHuman：工具面应可见、可检查，避免把 route 隐藏在 API handler 的大 if-else 中；小集合可以明确映射，大集合再考虑 mode/enum 折叠。

因此本阶段新增了通用 `inspect_agent_dialog_route_projection`，而不是只在 pending action 上补字段。

## Verification

RED 1:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_dialogs.py -k "chat_command_registry_helpers_cover_expected_commands or chapter_command_leading_index_wins_over_context_mentions or text_intent_creates_pending_setup_action or text_intent_confirm_routes_to_agent_run or chat_button_action or chat_text_start_writing_creates_pending_chapter_action" -q
```

Result:

```text
ModuleNotFoundError: No module named 'app.core.dialog_agent_routes'
```

GREEN 1:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_dialogs.py -k "chat_command_registry_helpers_cover_expected_commands or chapter_command_leading_index_wins_over_context_mentions or text_intent_creates_pending_setup_action or text_intent_confirm_routes_to_agent_run or chat_button_action or chat_text_start_writing_creates_pending_chapter_action" -q
```

Result:

```text
7 passed, 49 deselected in 0.53s
```

RED 2:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py -k "inspect_agent_dialog_route_projection" -q
```

Result:

```text
assert False is True
WritingAgentToolExecutionResult(handled=False, output=None)
```

GREEN 2:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py -k "inspect_agent_dialog_route_projection or inspect_agent_slash_command_route" -q
```

Result:

```text
2 passed, 66 deselected in 0.20s
```

T1:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_dialogs.py backend/tests/test_writing_agent_tool_executor.py -k "command or slash_command or text_intent or chat_button_action or agent_control_plane or inspect_agent_slash_command_route or inspect_agent_dialog_route_projection" -q
```

Result:

```text
24 passed, 100 deselected in 3.25s
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

- 本阶段没有改变用户可见确认流程。
- 没有把 route projection 做成新的 Agent runtime；它只负责统一入口元数据。
- `agent_route` 仍是控制面字段，确认执行后不会进入具体生成工具。

## Next Phase Suggestion

建议 Phase105 处理下一层 Agent 化边界：将 `IntentRouter` 的规则匹配结果也暴露为 Agent 可检查的 intent projection/report，让系统能解释“为什么把这句话路由到某个工具”，并逐步为低细节用户输入接入 planner，而不是靠用户写详细提示词约束章节。
