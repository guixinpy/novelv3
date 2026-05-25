# Phase105 Report: Intent Projection Report

## Goal Alignment

本阶段继续推进“以对话驱动的专精写作 Agent”。Phase104 已统一 slash/text/button 的 `agent_route`，但自然语言 intent 仍然像黑盒规则：系统知道要生成章节，却不能解释为什么。

本阶段没有把 `IntentRouter` 替换成 LLM planner，也没有改变用户可见流程；只新增可审计 projection/report，让 Agent 能检查当前确定性路由结果，为后续 planner 接管低细节用户输入打基础。

## Implemented

- `IntentRouter.project()`：
  - 返回结构化 `IntentProjection`。
  - `resolve()` 继续复用 projection 的 candidate，保持原有行为兼容。
- `IntentProjection.to_dict()` 新增稳定字段：
  - `version = phase105.intent_projection.v1`
  - `input.normalized_text`
  - `input.input_hash`
  - `input.excerpt`
  - `context`
  - `decision.rule_id`
  - `decision.reason_code`
  - `decision.match_evidence`
  - `tool_selection`
  - `preconditions`
  - `guardrails`
  - `rejected_candidates`
  - `trace.projection_id`
- 保留旧顶层字段：
  - `status`
  - `rule_id`
  - `reason`
  - `candidate`
  - `agent_route`
  - `diagnosis`
  - `extracted_params`
- 新增 Writing Agent 只读工具 `inspect_agent_intent_projection`。

## Reference Learning

子代理只读分析了 `openclaw`、`hermes-agent`、`openhuman`，本阶段吸收如下点：

- projection 与执行分离：projection 只解释当前确定性结果，不产生副作用。
- route explainability 使用稳定字段、规则 ID 和 reason code，不依赖自由文本。
- no-match 不能伪造成工具调用；`candidate`、`agent_route`、`tool_selection.selected_tool` 必须为空。
- tool selection 的 `why_this_tool` 应是可追溯来源，例如 `dialog_action_to_agent_tool.preview_chapter`，不是模型自由解释。
- 输入记录使用 hash 和短 excerpt，避免把完整上下文当作长期审计负载。

## Verification

RED 1:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_dialogs.py backend/tests/test_writing_agent_tool_executor.py -k "intent_router_projection or inspect_agent_intent_projection" -q
```

Result:

```text
AttributeError: 'IntentRouter' object has no attribute 'project'
WritingAgentToolExecutionResult(handled=False, output=None)
4 failed, 124 deselected
```

GREEN 1:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_dialogs.py backend/tests/test_writing_agent_tool_executor.py -k "intent_router_projection or inspect_agent_intent_projection" -q
```

Result:

```text
4 passed, 124 deselected in 0.18s
```

RED 2:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_dialogs.py backend/tests/test_writing_agent_tool_executor.py -k "intent_router_projection or inspect_agent_intent_projection" -q
```

Result:

```text
KeyError: 'version'
KeyError: 'decision'
4 failed, 124 deselected
```

GREEN 2:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_dialogs.py backend/tests/test_writing_agent_tool_executor.py -k "intent_router_projection or inspect_agent_intent_projection" -q
```

Result:

```text
4 passed, 124 deselected in 0.18s
```

T1:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_dialogs.py backend/tests/test_writing_agent_tool_executor.py -k "intent_router or intent_projection or inspect_agent_intent_projection" -q
```

Result:

```text
7 passed, 121 deselected in 0.19s
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

- 本阶段没有改动 `/api/v1/dialog/chat` 的用户可见确认流程。
- 本阶段没有引入 LLM planner；只是让现有确定性规则有可解释投影。
- `inspect_agent_intent_projection` 可以使用显式 diagnosis 参数，也可以从项目当前状态构建 diagnosis。

## Next Phase Suggestion

建议 Phase106 将 intent projection 与 Writing Agent planner 连接起来：当自然语言输入低细节但可识别目标时，先生成只读 agent plan，说明需要哪些上下文、记忆、世界模型和审稿工具，而不是立即要求用户写更详细提示词。
