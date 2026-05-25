# Phase100 Runtime Recommendation Normalizer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将运行时工具输出中的 `recommended_next_tools` / `recommended_actions` 统一归一化到 `agent_tool_result.recommendations`，让 Agent 能稳定读取下一步工具建议。

**Architecture:** 新增 `tool_recommendations.py` 作为只读 normalizer，负责解析输出字段、过滤真实工具名、保留非工具建议，并合并 Phase98 report policy 的 allowed followups。`run_service.py` 只在构建 `agent_tool_result` envelope 时调用该 normalizer，不改变原始工具输出。

**Tech Stack:** Python backend, pytest, Writing Agent run service.

---

### Task 1: 写 RED 测试

**Files:**
- Create: `backend/tests/test_writing_agent_tool_recommendations.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [ ] **Step 1: 新增 normalizer 单元测试**

```python
from app.services.writing_agent.tool_recommendations import normalize_tool_recommendations


def test_normalize_tool_recommendations_keeps_tool_followups_and_non_tool_actions_separate():
    result = normalize_tool_recommendations(
        "generate_chapter",
        {
            "recommended_next_tools": ["review_chapter_quality", "review_chapter_quality"],
            "recommended_actions": ["revise_chapter", "apply_world_model_proposal_resolution"],
        },
        allowed_tools={"review_chapter_quality", "apply_world_model_proposal_resolution"},
    )

    assert result["source_fields"] == ["recommended_next_tools", "recommended_actions"]
    assert result["raw_recommendations"] == [
        "review_chapter_quality",
        "revise_chapter",
        "apply_world_model_proposal_resolution",
    ]
    assert result["runtime_followups"] == ["review_chapter_quality", "apply_world_model_proposal_resolution"]
    assert result["non_tool_recommendations"] == ["revise_chapter"]
    assert result["canonical_followups"] == ["review_chapter_quality", "apply_world_model_proposal_resolution"]
```

- [ ] **Step 2: 在 run service 测试里断言 envelope recommendations**

在 `test_agent_seed_continuity_anchor_proposals_creates_missing_anchor_items` 中新增：

```python
recommendations = output["agent_tool_result"]["recommendations"]
assert recommendations["source_fields"] == ["recommended_actions"]
assert recommendations["runtime_followups"] == ["apply_world_model_proposal_resolution"]
assert recommendations["policy_followups"] == ["apply_world_model_proposal_resolution"]
assert recommendations["canonical_followups"] == ["apply_world_model_proposal_resolution"]
```

- [ ] **Step 3: 运行 RED**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_recommendations.py backend/tests/test_writing_agent_runs.py -k "tool_recommendations or seed_continuity_anchor_proposals_creates_missing_anchor_items" -q`

Expected: FAIL，因为 `tool_recommendations.py` 尚不存在。

### Task 2: 实现 runtime normalizer

**Files:**
- Create: `backend/app/services/writing_agent/tool_recommendations.py`
- Modify: `backend/app/services/writing_agent/tool_contracts.py`
- Modify: `backend/app/services/writing_agent/run_service.py`

- [ ] **Step 1: 新增 normalizer 模块**

```python
RECOMMENDATION_OUTPUT_FIELDS = ("recommended_next_tools", "recommended_actions")
TOOL_RECOMMENDATION_VERSION = "phase100.tool_recommendations.v1"

def normalize_tool_recommendations(tool_name, output, *, allowed_tools=None):
    ...
```

输出字段：

- `version`
- `source_fields`
- `raw_recommendations`
- `runtime_followups`
- `non_tool_recommendations`
- `policy_followups`
- `canonical_followups`

- [ ] **Step 2: 让 `tool_contracts.py` 复用常量**

从 `tool_recommendations.py` 引入 `RECOMMENDATION_OUTPUT_FIELDS`，避免 contract 与 runtime normalizer 使用两套字段名。

- [ ] **Step 3: 接入 `agent_tool_result` envelope**

在 `_agent_tool_result_envelope()` 返回值中加入：

```python
"recommendations": normalize_tool_recommendations(step.tool_name, output),
```

- [ ] **Step 4: 运行 GREEN**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_recommendations.py backend/tests/test_writing_agent_runs.py -k "tool_recommendations or seed_continuity_anchor_proposals_creates_missing_anchor_items" -q`

Expected: PASS。

### Task 3: 验证、审查和报告

**Files:**
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-21-phase100-runtime-recommendation-normalizer.md`

- [ ] **Step 1: T1 验证**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_recommendations.py backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_runs.py -k "tool_recommendations or inspect_agent_tool_contracts or seed_continuity_anchor_proposals_creates_missing_anchor_items or blocks_followup_generation or allows_resolution_plan_followup or allows_apply_followup" -q`

Expected: PASS。

- [ ] **Step 2: 静态检查**

Run: `git diff --check`
Expected: 无输出。

Run: `rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"`
Expected: 无匹配。

- [ ] **Step 3: 只读子代理审查**

请子代理审查 normalizer 是否误把非工具动作当成工具、是否改变运行输出语义、是否有循环导入风险。

- [ ] **Step 4: 写阶段报告、提交并推送**

报告记录 RED/GREEN/T1 证据、子代理审查结论和下一阶段建议。
