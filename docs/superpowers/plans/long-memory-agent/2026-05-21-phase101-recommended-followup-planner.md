# Phase101 Recommended Followup Planner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 Phase100 的 runtime `canonical_followups` 进入 planner 可消费面：continuation state 能暴露最近推荐后继，Agent 能调用只读工具生成推荐后继计划。

**Architecture:** 新增 `recommended_followup_planner.py` 作为只读 planner。它从指定 run 的 step envelope 中读取 `agent_tool_result.recommendations.canonical_followups`，过滤 registry 内可执行工具，补齐章节/run 参数，输出 preview-only 工具计划。`run_service.py` 只在 continuation state 中投影最近推荐，不直接自动执行推荐工具。

**Tech Stack:** Python backend, SQLAlchemy, Writing Agent tool executor, pytest.

---

### Task 1: 写 RED 测试

**Files:**
- Modify: `backend/tests/test_writing_agent_runs.py`
- Modify: `backend/tests/test_writing_agent_tool_executor.py`

- [x] **Step 1: continuation state 暴露最近推荐后继**

在生成章节的直接 run 测试中断言：

```python
payload = response.json()
state = payload["output"]["continuation_state"]
assert state["recommended_followups"]["status"] == "recommended"
assert state["recommended_followups"]["source_tool"] == "generate_chapter"
assert state["recommended_followups"]["next_tool"] == "review_chapter_quality"
assert state["recommended_followups"]["canonical_followups"] == [
    "review_chapter_quality",
    "review_chapter_continuity",
    "analyze_chapter_world_model",
]
```

- [x] **Step 2: 新增 planner tool executor 测试**

新增测试：

```python
@pytest.mark.asyncio
async def test_tool_executor_handles_plan_recommended_followups(db_session):
    project = Project(name="Recommended Followup Planner")
    db_session.add(project)
    run = WritingAgentRun(project_id=project.id, goal="生成第2章", status="success", input={})
    db_session.add(run)
    db_session.flush()
    db_session.add(
        WritingAgentStep(
            run_id=run.id,
            project_id=project.id,
            step_index=1,
            tool_name="generate_chapter",
            status="success",
            chapter_index=2,
            input={"params": {"chapter_index": 2}},
            output={
                "status": "success",
                "chapter_index": 2,
                "agent_tool_result": {
                    "recommendations": {
                        "canonical_followups": [
                            "review_chapter_quality",
                            "review_chapter_continuity",
                            "not_a_tool",
                        ],
                        "runtime_followups": ["review_chapter_quality", "review_chapter_continuity"],
                        "non_tool_recommendations": ["revise_chapter"],
                    }
                },
            },
        )
    )
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-followup"),
        WritingAgentToolRequest(tool_name="plan_recommended_followups", params={"run_id": run.id}),
    )

    assert result.handled is True
    assert result.output["status"] == "completed"
    assert result.output["source_step"]["tool_name"] == "generate_chapter"
    assert [tool["tool_name"] for tool in result.output["tools"]] == [
        "review_chapter_quality",
        "review_chapter_continuity",
    ]
    assert result.output["tools"][0]["params"] == {"chapter_index": 2}
    assert result.output["trace"]["rejected_tools"] == [{"tool_name": "not_a_tool", "reason": "not_allowed"}]
```

- [x] **Step 3: 运行 RED**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py backend/tests/test_writing_agent_tool_executor.py -k "recommended_followups or plan_recommended_followups" -q`

Expected: FAIL，因为 `recommended_followups` state 和 `plan_recommended_followups` 工具尚不存在。

### Task 2: 实现 recommended followup planner

**Files:**
- Create: `backend/app/services/writing_agent/recommended_followup_planner.py`
- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/app/services/writing_agent/tool_registry.py`
- Modify: `backend/app/services/writing_agent/tool_executor.py`

- [x] **Step 1: 新增 planner 模块**

实现：

```python
FOLLOWUP_PLANNER_VERSION = "phase101.recommended_followup_planner.v1"

def latest_recommended_followup_state(steps):
    ...

def build_recommended_followup_tool_plan(db, project_id, run_id):
    ...
```

规则：

- 从最新 step 向前查找 `agent_tool_result.recommendations.canonical_followups`
- 只把 `allowed_tool_names()` 中的名称提升为工具计划
- 非 registry 工具进入 `trace.rejected_tools`
- 从 source step / output / step input 继承 `chapter_index`
- 对带 `run_id` 输入的工具补 `run_id`
- 输出 preview-only plan，不自动执行后继工具

- [x] **Step 2: continuation state 接入**

在 `_continuation_state()` 中新增：

```python
recommended_followups = latest_recommended_followup_state(steps)
...
"recommended_followups": recommended_followups,
```

- [x] **Step 3: tool registry 增加 descriptor**

新增 internal read tool：

```python
AgentToolDescriptor(
    name="plan_recommended_followups",
    module="writing_agent",
    category="preflight",
    description="根据指定 Writing Agent run 的运行时推荐生成只读后继工具计划。",
    ...
)
```

- [x] **Step 4: tool executor 接入 static adapter**

新增 `_plan_recommended_followups()` 并注册到 `_STATIC_TOOL_ADAPTERS`，mutability 为 `read`。

- [x] **Step 5: 运行 GREEN**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py backend/tests/test_writing_agent_tool_executor.py -k "recommended_followups or plan_recommended_followups" -q`

Expected: PASS。

### Task 3: 验证、审查和报告

**Files:**
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-21-phase101-recommended-followup-planner.md`

- [x] **Step 1: T1 验证**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_recommendations.py backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_runs.py -k "tool_recommendations or plan_recommended_followups or recommended_followups or inspect_agent_tool_contracts or seed_continuity_anchor_proposals_creates_missing_anchor_items or blocks_followup_generation or allows_resolution_plan_followup or allows_apply_followup" -q`

Expected: PASS。

- [x] **Step 2: 静态检查**

Run: `git diff --check`

Expected: exit 0。

Run: `rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"`

Expected: 无匹配。

- [x] **Step 3: 只读子代理审查**

请子代理审查：推荐后继是否可能绕过确认、是否误执行 guarded write、是否和 recovery planner 冲突、是否有循环导入。

- [x] **Step 4: 写阶段报告、提交并推送**

报告记录 RED/GREEN/T1、参考项目启发、子代理审查结论和下一阶段建议。
