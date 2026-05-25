# Phase98 Tool Policy Contract Projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Phase97 抽离出的运行时报告阻断策略投影到 `inspect_agent_tool_contracts`，让 Agent planner 能在执行前看见工具治理约束。

**Architecture:** `tool_policy.py` 继续保存运行时策略事实；新增只读投影函数返回单个工具的报告策略。`tool_contracts.py` 在构建每个工具 contract 时嵌入该投影，并扩展 reference alignment pattern，保持 `run_service.py` 无新增逻辑。

**Tech Stack:** Python backend, pytest, Writing Agent static tool adapter.

---

### Task 1: 写 RED 测试

**Files:**
- Modify: `backend/tests/test_writing_agent_tool_policy.py`
- Modify: `backend/tests/test_writing_agent_tool_executor.py`

- [ ] **Step 1: 测试 policy 投影函数**

```python
from app.services.writing_agent.tool_policy import report_policy_for_tool


def test_agent_tool_policy_projects_report_policy_for_planner():
    policy = report_policy_for_tool("seed_continuity_anchor_proposals")
    assert policy == {
        "stop_check_required": True,
        "stop_condition": "non_terminal_step_and_should_generate_next_chapter_false_without_allowed_followup",
        "allowed_followups": ["apply_world_model_proposal_resolution"],
        "block_message": "稳定连续性锚点提案尚未审批，已停止后续写作工具。",
    }
```

- [ ] **Step 2: 测试 contract snapshot 暴露 runtime policy**

```python
assert "runtime_policy_projection" in result.output["reference_alignment"]["patterns"]
assert tools_by_name["seed_continuity_anchor_proposals"]["report_policy"]["stop_check_required"] is True
assert tools_by_name["seed_continuity_anchor_proposals"]["report_policy"]["allowed_followups"] == [
    "apply_world_model_proposal_resolution"
]
assert tools_by_name["generate_chapter"]["report_policy"]["stop_check_required"] is False
```

- [ ] **Step 3: 运行 RED**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_policy.py backend/tests/test_writing_agent_tool_executor.py -k "tool_policy or inspect_agent_tool_contracts" -q`
Expected: FAIL，因为 `report_policy_for_tool` 和 `report_policy` contract 字段尚不存在。

### Task 2: 实现策略投影

**Files:**
- Modify: `backend/app/services/writing_agent/tool_policy.py`
- Modify: `backend/app/services/writing_agent/tool_contracts.py`

- [ ] **Step 1: 在 `tool_policy.py` 新增投影函数**

```python
def report_policy_for_tool(tool_name: str) -> dict[str, object]:
    stops_after_report = tool_name in REPORT_STOP_TOOLS
    allowed_followups = sorted(
        next_tool for current_tool, next_tool in ALLOWED_REPORT_FOLLOWUPS if current_tool == tool_name
    )
    return {
        "stop_check_required": stops_after_report,
        "stop_condition": (
            "non_terminal_step_and_should_generate_next_chapter_false_without_allowed_followup"
            if stops_after_report
            else None
        ),
        "allowed_followups": allowed_followups,
        "block_message": successful_report_block_message(tool_name) if stops_after_report else None,
    }
```

- [ ] **Step 2: 在 contract 中嵌入策略**

`tool_contracts.py` 引入 `report_policy_for_tool`，并在 `_tool_contract()` 返回值加入：

```python
"report_policy": report_policy_for_tool(descriptor.name),
```

同时在 `REFERENCE_ALIGNMENT["patterns"]` 中加入 `runtime_policy_projection`。

- [ ] **Step 3: 运行 GREEN**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_policy.py backend/tests/test_writing_agent_tool_executor.py -k "tool_policy or inspect_agent_tool_contracts" -q`
Expected: PASS。

### Task 3: 验证、审查和报告

**Files:**
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-21-phase98-tool-policy-contract-projection.md`

- [ ] **Step 1: T1 验证**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_policy.py backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_runs.py -k "tool_policy or inspect_agent_tool_contracts or blocks_followup_generation or allows_resolution_plan_followup or allows_apply_followup" -q`
Expected: PASS。

- [ ] **Step 2: 静态检查**

Run: `git diff --check`
Expected: 无输出。

Run: `rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"`
Expected: 无匹配。

- [ ] **Step 3: 只读子代理审查**

请子代理审查 runtime policy 投影是否准确、是否改变运行语义、是否有过度扩展。

- [ ] **Step 4: 写阶段报告、提交并推送**

报告记录 RED/GREEN/T1 证据、参考项目启发、子代理审查结论和下一阶段建议。
