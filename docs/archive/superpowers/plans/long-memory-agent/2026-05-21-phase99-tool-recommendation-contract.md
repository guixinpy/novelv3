# Phase99 Tool Recommendation Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `inspect_agent_tool_contracts` 中暴露统一的工具后继推荐契约，让 Agent planner 能判断工具输出里的推荐字段和确定性治理后继工具。

**Architecture:** 不改变任何工具实际输出。`tool_contracts.py` 从 output schema、Phase98 的 `report_policy`、现有 `recovery_tools` 推导只读 `recommendation_contract`，用于 planner 预判后继工具来源。

**Tech Stack:** Python backend, pytest, Writing Agent static tool adapter.

---

### Task 1: 写 RED 测试

**Files:**
- Modify: `backend/tests/test_writing_agent_tool_executor.py`

- [ ] **Step 1: 为 contract snapshot 增加推荐契约断言**

```python
assert "recommendation_surface_normalization" in result.output["reference_alignment"]["patterns"]
assert tools_by_name["generate_chapter"]["recommendation_contract"] == {
    "output_fields": ["recommended_next_tools"],
    "canonical_output_field": "recommended_next_tools",
    "legacy_output_fields": [],
    "policy_followups": [],
    "recovery_followups": ["plan_recovery_tools", "inspect_agent_trace_audit"],
    "deterministic_followups": ["plan_recovery_tools", "inspect_agent_trace_audit"],
}
assert tools_by_name["seed_continuity_anchor_proposals"]["recommendation_contract"] == {
    "output_fields": ["recommended_actions"],
    "canonical_output_field": "recommended_actions",
    "legacy_output_fields": ["recommended_actions"],
    "policy_followups": ["apply_world_model_proposal_resolution"],
    "recovery_followups": ["plan_recovery_tools", "inspect_agent_trace_audit"],
    "deterministic_followups": [
        "apply_world_model_proposal_resolution",
        "plan_recovery_tools",
        "inspect_agent_trace_audit",
    ],
}
assert tools_by_name["review_world_model_proposals"]["recommendation_contract"]["policy_followups"] == [
    "plan_world_model_proposal_resolution"
]
```

- [ ] **Step 2: 运行 RED**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py -k "inspect_agent_tool_contracts" -q`
Expected: FAIL，因为 `recommendation_contract` 和 `recommendation_surface_normalization` 尚不存在。

### Task 2: 实现推荐契约投影

**Files:**
- Modify: `backend/app/services/writing_agent/tool_contracts.py`

- [ ] **Step 1: 增加输出推荐字段常量**

```python
RECOMMENDATION_OUTPUT_FIELDS = ("recommended_next_tools", "recommended_actions")
```

- [ ] **Step 2: 在 `_tool_contract()` 中复用 policy/recovery 结果**

先计算：

```python
recovery_tools = _recovery_tools(descriptor, mutability)
report_policy = report_policy_for_tool(descriptor.name)
```

再写入 contract：

```python
"recovery_tools": recovery_tools,
"report_policy": report_policy,
"recommendation_contract": _recommendation_contract(descriptor, report_policy, recovery_tools),
```

- [ ] **Step 3: 新增 `_recommendation_contract()` 和 `_dedupe()`**

```python
def _recommendation_contract(
    descriptor: AgentToolDescriptor,
    report_policy: dict[str, object],
    recovery_tools: list[str],
) -> dict[str, object]:
    properties = descriptor.output_schema.get("properties") if isinstance(descriptor.output_schema, dict) else {}
    output_fields = [field for field in RECOMMENDATION_OUTPUT_FIELDS if isinstance(properties, dict) and field in properties]
    policy_followups = [str(tool) for tool in report_policy.get("allowed_followups") or []]
    return {
        "output_fields": output_fields,
        "canonical_output_field": output_fields[0] if output_fields else None,
        "legacy_output_fields": [field for field in output_fields if field != "recommended_next_tools"],
        "policy_followups": policy_followups,
        "recovery_followups": list(recovery_tools),
        "deterministic_followups": _dedupe(policy_followups + recovery_tools),
    }
```

- [ ] **Step 4: 运行 GREEN**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py -k "inspect_agent_tool_contracts" -q`
Expected: PASS。

### Task 3: 验证、审查和报告

**Files:**
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-21-phase99-tool-recommendation-contract.md`

- [ ] **Step 1: T1 验证**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_runs.py -k "inspect_agent_tool_contracts or blocks_followup_generation or allows_resolution_plan_followup or allows_apply_followup" -q`
Expected: PASS。

- [ ] **Step 2: 静态检查**

Run: `git diff --check`
Expected: 无输出。

Run: `rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"`
Expected: 无匹配。

- [ ] **Step 3: 只读子代理审查**

请子代理审查推荐契约是否准确、是否改变运行语义、是否有命名或稳定性问题。

- [ ] **Step 4: 写阶段报告、提交并推送**

报告记录 RED/GREEN/T1 证据、参考项目启发、子代理审查结论和下一阶段建议。
