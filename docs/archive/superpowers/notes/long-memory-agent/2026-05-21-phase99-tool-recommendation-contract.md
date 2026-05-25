# Phase99 Tool Recommendation Contract Report

## 目标

将工具输出里的后继建议面投影到 `inspect_agent_tool_contracts`，让 Agent planner 能在执行前理解：

- 哪些 output schema 字段承载后继推荐；
- 哪些字段仍是 legacy `recommended_actions`；
- report policy 会放行哪些治理后继工具；
- recovery policy 会建议哪些恢复工具；
- 确定性后继工具的稳定合并顺序。

本阶段不改变任何工具真实运行输出。

## 实现

- `backend/app/services/writing_agent/tool_contracts.py`
  - 新增 `RECOMMENDATION_OUTPUT_FIELDS = ("recommended_next_tools", "recommended_actions")`
  - 新增 `recommendation_surface_normalization` reference alignment pattern
  - 每个 tool contract 新增 `recommendation_contract`
  - 新增 `_recommendation_contract()`
  - 新增 `_dedupe()`
- `backend/tests/test_writing_agent_tool_executor.py`
  - 覆盖 `generate_chapter` 的 canonical `recommended_next_tools`
  - 覆盖 `seed_continuity_anchor_proposals` 的 legacy `recommended_actions`
  - 覆盖 `review_world_model_proposals` 的 policy/recovery 重叠去重路径

## RED/GREEN

RED:

```text
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py -k "inspect_agent_tool_contracts" -q
FAILED ... AssertionError: assert 'recommendation_surface_normalization' in [...]
```

GREEN:

```text
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py -k "inspect_agent_tool_contracts" -q
2 passed, 60 deselected in 0.26s
```

## T1 验证

```text
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_runs.py -k "inspect_agent_tool_contracts or blocks_followup_generation or allows_resolution_plan_followup or allows_apply_followup" -q
12 passed, 212 deselected in 1.16s
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

只读审查子代理 Einstein 未发现阻断问题。审查结论：

- `recommendation_contract` 只读取 descriptor output schema，不扫描运行时输出，符合只读契约投影范围。
- `report_policy.allowed_followups` 与 `_recovery_tools()` 被复用，没有另起规则。
- `_dedupe()` 保留首次出现顺序，当前顺序稳定。
- 运行语义未变化，改动仅进入 `inspect_agent_tool_contracts` snapshot 构建路径。

子代理提出一个低风险建议：补充 policy/recovery 重叠去重测试。已采纳，补充了 `review_world_model_proposals` 完整断言。

## 参考项目启发

本阶段继续转译参考 Agent 项目的 typed tool surface 思路：工具不只需要 schema，还需要把推荐后继、恢复路径和治理放行规则一起暴露给 planner。novelv3 的领域化落点是让写作 Agent 在进入真实生成前，能基于 contract 选择审稿、世界模型治理、恢复或继续写作工具，而不是依赖用户手动串工具。

## 下一阶段建议

继续把推荐契约从“可见”推进到“可执行”：

- 增加一个只读 normalizer，统一读取运行时输出中的 `recommended_next_tools` / `recommended_actions`；
- 在 `agent_tool_result` 或 Trace 中追加 canonical recommended followups；
- 后续再让 planner 基于 `recommendation_contract` 和 canonical followups 自动生成下一步工具链。
