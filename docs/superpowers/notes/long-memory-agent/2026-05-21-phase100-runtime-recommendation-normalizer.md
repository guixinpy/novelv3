# Phase100 Runtime Recommendation Normalizer Report

## 目标

将工具运行输出里的 `recommended_next_tools` / `recommended_actions` 统一投影到 `agent_tool_result.recommendations`，让 Writing Agent 能稳定读取下一步可执行工具建议。

本阶段保持原始工具输出不变，只增加 envelope 层的规范化视图。

## 实现

- `backend/app/services/writing_agent/tool_recommendations.py`
  - 新增 `normalize_tool_recommendations()`
  - 统一输出 `source_fields`、`raw_recommendations`、`runtime_followups`、`non_tool_recommendations`、`policy_followups`、`canonical_followups`
  - 支持字符串推荐、字符串列表推荐，以及 `{"tool_name": "..."}` / `{"action": "..."}` 结构化 action
  - 使用 `allowed_tool_names()` 过滤真实可执行工具，保留非工具动作作为 `non_tool_recommendations`
  - 合并 Phase98 report policy 的 `allowed_followups`
- `backend/app/services/writing_agent/run_service.py`
  - 在 `agent_tool_result` envelope 中加入 `recommendations`
- `backend/app/services/writing_agent/tool_contracts.py`
  - 复用 `RECOMMENDATION_OUTPUT_FIELDS`，避免 contract 投影与 runtime normalizer 字段名漂移
- `backend/tests/test_writing_agent_tool_recommendations.py`
  - 覆盖工具推荐、非工具动作、policy followup 去重、结构化 action 提取和 JSON 可序列化
- `backend/tests/test_writing_agent_runs.py`
  - 覆盖 `seed_continuity_anchor_proposals` 真实 run envelope 中的 recommendations

## RED/GREEN

初始 RED：

```text
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_recommendations.py backend/tests/test_writing_agent_runs.py -k "tool_recommendations or seed_continuity_anchor_proposals_creates_missing_anchor_items" -q
FAILED ... ModuleNotFoundError: No module named 'app.services.writing_agent.tool_recommendations'
```

初始 GREEN：

```text
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_recommendations.py backend/tests/test_writing_agent_runs.py -k "tool_recommendations or seed_continuity_anchor_proposals_creates_missing_anchor_items" -q
3 passed, 161 deselected in 0.29s
```

子代理审查后补充 RED：

```text
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_recommendations.py -q
FAILED ... assert [] == ['inspect_agent_memory_route', 'plan_recovery_tools', 'revise_chapter']
```

补充 GREEN：

```text
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_recommendations.py -q
3 passed in 0.02s
```

## T1 验证

```text
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_recommendations.py backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_runs.py -k "tool_recommendations or inspect_agent_tool_contracts or seed_continuity_anchor_proposals_creates_missing_anchor_items or blocks_followup_generation or allows_resolution_plan_followup or allows_apply_followup" -q
16 passed, 211 deselected in 1.30s
```

静态检查：

```text
git diff --check
```

Exit code 0。PowerShell 输出了既有 Windows 行尾提示：

```text
warning: in the working copy of 'backend/tests/test_writing_agent_runs.py', CRLF will be replaced by LF the next time Git touches it
```

密钥扫描：

```text
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

Exit code 1，无匹配。

## 子代理审查

只读审查子代理 Peirce 发现 1 个 P1 问题：

- `agent_trace_audit.py` 等工具可能返回结构化 `recommended_actions`，例如 `{"tool_name": "inspect_agent_memory_route"}`。
- 初版 normalizer 只识别字符串和字符串列表，会丢失这些真实可执行 followup。

已补充失败测试并修复。当前规则：

- `tool_name` 优先作为可执行工具候选；
- 缺少 `tool_name` 时读取 `action`，用于保留非工具动作；
- 所有候选都再经过 `allowed_tool_names()` 过滤，避免把普通动作误当工具。

## 参考项目启发

本阶段继续参考外部 Agent 项目的工具治理思路：

- `hermes-agent` 使用 `valid_tool_names` 约束工具调用，并在 runtime helpers 中尝试修复模型发出的工具名变体。novelv3 当前不做模糊修复，但先建立 canonical followup surface，让 planner 后续只消费已知工具名。
- `openclaw` 多处强调 tool policy、tool schema 和 action enum 的稳定化。novelv3 本阶段对应地把 legacy action 字段保留下来，同时只把通过 registry 的名称提升为可执行工具。

## 下一阶段建议

- 将 `agent_tool_result.recommendations.canonical_followups` 接入 planner 的下一步候选生成，而不是只作为 envelope 元数据。
- 在 Trace 视图中展示 runtime followups 与 non-tool recommendations，方便审查 Agent 为什么选择下一步工具。
- 针对结构化 `recommended_actions` 继续收紧 schema，让输出契约逐步从 legacy 自由文本过渡到 typed tool/action object。
