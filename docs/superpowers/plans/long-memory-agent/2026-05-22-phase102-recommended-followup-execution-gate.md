# Phase102 Recommended Followup Execution Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 Writing Agent 能把上一轮 `canonical_followups` 通过显式确认门转成下一轮可执行工具链，而不是要求用户手动指定后继工具。

**Architecture:** 复用 Phase101 的 `plan_recommended_followups` preview plan。`build_auto_plan_tools()` 新增 recommended followup branch：默认只预览，只有 `execute_recommended_followups + confirm_execute + matching plan_hash` 同时满足时，才把 preview 中的安全工具转成当前 run 的执行工具。recovery branch 仍优先；写工具仍由 planner 拒绝，不进入本阶段执行面。

**Tech Stack:** Python backend, FastAPI agent-runs endpoint, SQLAlchemy models, pytest.

---

## Task 1: RED - auto plan 默认预览 recommended followups

**Files:**
- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: 新增默认预览测试**

在 recovery auto-plan 测试附近新增：

```python
def test_agent_run_auto_plan_previews_recommended_followups_by_default(client, db_session):
    project_id = _create_project(client, "Recommended Followup Preview")
    source_run = WritingAgentRun(project_id=project_id, goal="生成第2章", status="success", input={})
    db_session.add(source_run)
    db_session.flush()
    db_session.add(
        WritingAgentStep(
            run_id=source_run.id,
            project_id=project_id,
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
                        "canonical_followups": ["review_chapter_quality", "review_chapter_continuity"],
                    }
                },
            },
        )
    )
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "规划上一轮推荐后继",
            "input": {"auto_plan": True, "recommended_followup_run_id": source_run.id},
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["input"]["planner"]["mode"] == "preview"
    assert payload["input"]["planner"]["source_run_id"] == source_run.id
    assert payload["input"]["planner"]["execution_policy"]["requires_confirmation"] is True
    assert payload["input"]["tools"][0]["tool_name"] == "plan_recommended_followups"
    assert payload["input"]["tools"][0]["params"] == {"run_id": source_run.id}
    assert [step["tool_name"] for step in payload["steps"]] == ["plan_recommended_followups"]
    preview = payload["steps"][0]["output"]
    assert preview["plan_hash"]
    assert preview["preview_only"] is True
    assert [tool["tool_name"] for tool in preview["tools"]] == ["review_chapter_quality", "review_chapter_continuity"]
```

- [x] **Step 2: 运行 RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "recommended_followups_by_default" -q
```

Expected: FAIL，因为 `recommended_followup_run_id` 还不会进入 auto plan preview branch。

## Task 2: RED - 哈希确认后执行 safe recommended followups

**Files:**
- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: 新增确认执行测试**

```python
def test_agent_run_auto_plan_executes_recommended_followups_after_hash_confirmation(client, db_session, monkeypatch):
    project_id = _create_project(client, "Recommended Followup Execute")
    source_run = WritingAgentRun(project_id=project_id, goal="生成第2章", status="success", input={})
    db_session.add(source_run)
    db_session.flush()
    db_session.add(
        WritingAgentStep(
            run_id=source_run.id,
            project_id=project_id,
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
                        "canonical_followups": ["review_chapter_quality", "review_chapter_continuity"],
                    }
                },
            },
        )
    )
    db_session.commit()

    preview = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={"goal": "预览推荐后继", "tools": [{"tool_name": "plan_recommended_followups", "params": {"run_id": source_run.id}}]},
    )
    plan_hash = preview.json()["steps"][0]["output"]["plan_hash"]

    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "执行推荐后继",
            "input": {
                "auto_plan": True,
                "recommended_followup_run_id": source_run.id,
                "execute_recommended_followups": True,
                "confirm_execute": True,
                "recommended_followup_plan_hash": plan_hash,
            },
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["input"]["planner"]["mode"] == "execute"
    assert payload["input"]["planner"]["plan_hash"] == plan_hash
    assert payload["input"]["planner"]["execution_policy"]["confirmed"] is True
    assert [tool["tool_name"] for tool in payload["input"]["tools"]] == ["review_chapter_quality", "review_chapter_continuity"]
    assert [step["tool_name"] for step in payload["steps"]] == ["review_chapter_quality", "review_chapter_continuity"]
```

- [x] **Step 2: 运行 RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "executes_recommended_followups_after_hash_confirmation" -q
```

Expected: FAIL，因为 execute branch 尚不存在。

## Task 3: RED - stale hash 回退到 preview

**Files:**
- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: 新增 hash mismatch 测试**

```python
def test_agent_run_auto_plan_rejects_recommended_followup_hash_mismatch(client, db_session):
    project_id = _create_project(client, "Recommended Followup Hash Mismatch")
    source_run = WritingAgentRun(project_id=project_id, goal="生成第2章", status="success", input={})
    db_session.add(source_run)
    db_session.flush()
    db_session.add(
        WritingAgentStep(
            run_id=source_run.id,
            project_id=project_id,
            step_index=1,
            tool_name="generate_chapter",
            status="success",
            chapter_index=2,
            input={"params": {"chapter_index": 2}},
            output={
                "status": "success",
                "chapter_index": 2,
                "agent_tool_result": {
                    "recommendations": {"canonical_followups": ["review_chapter_quality"]},
                },
            },
        )
    )
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project_id}/agent-runs",
        json={
            "goal": "执行过期推荐后继",
            "input": {
                "auto_plan": True,
                "recommended_followup_run_id": source_run.id,
                "execute_recommended_followups": True,
                "confirm_execute": True,
                "recommended_followup_plan_hash": "stale-plan-hash",
            },
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["input"]["planner"]["mode"] == "preview"
    assert payload["input"]["planner"]["execution_policy"]["status"] == "hash_mismatch"
    assert payload["input"]["tools"][0]["tool_name"] == "plan_recommended_followups"
    assert [step["tool_name"] for step in payload["steps"]] == ["plan_recommended_followups"]
```

- [x] **Step 2: 运行 RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "recommended_followup_hash_mismatch" -q
```

Expected: FAIL，因为 hash mismatch 分支尚不存在。

## Task 4: GREEN - run_service 接入 recommended followup execute gate

**Files:**
- Modify: `backend/app/services/writing_agent/run_service.py`

- [x] **Step 1: 导入 planner build 函数**

将 import 扩展为：

```python
from app.services.writing_agent.recommended_followup_planner import (
    FOLLOWUP_PLANNER_VERSION,
    build_recommended_followup_tool_plan,
    latest_recommended_followup_state,
)
```

- [x] **Step 2: 在 recovery branch 后增加 recommended followup branch**

在 `build_auto_plan_tools()` 中，`recovery_run_id` 分支之后、普通 planner 之前新增：

```python
recommended_followup_run_id = str(run_input.get("recommended_followup_run_id") or "").strip() or None
if recommended_followup_run_id:
    if run_input.get("execute_recommended_followups") is not True:
        return _recommended_followup_preview_auto_plan(recommended_followup_run_id)

    plan = build_recommended_followup_tool_plan(self.db, project_id, recommended_followup_run_id)
    expected_hash = str(run_input.get("recommended_followup_plan_hash") or "").strip()
    confirmed = run_input.get("confirm_execute") is True
    actual_hash = str(plan.get("plan_hash") or "")
    executable = bool(plan.get("tools")) and plan.get("status") == "completed"
    if not confirmed or not expected_hash or expected_hash != actual_hash or not executable:
        status = "confirmation_required"
        if expected_hash and expected_hash != actual_hash:
            status = "hash_mismatch"
        elif not executable:
            status = str(((plan.get("execution_policy") or {}).get("status")) or plan.get("status") or "not_executable")
        return _recommended_followup_preview_auto_plan(recommended_followup_run_id, status=status)

    plan = dict(plan)
    plan["mode"] = "execute"
    plan["preview_only"] = False
    plan["can_execute"] = True
    plan["execution_policy"] = {
        **(plan.get("execution_policy") or {}),
        "mode": "execute",
        "status": "confirmed",
        "confirmed": True,
        "requires_confirmation": True,
        "requires_plan_hash": True,
    }
    tools = [WritingAgentToolRequest(**tool) for tool in plan.get("tools", []) if isinstance(tool, dict)]
    return tools, plan
```

- [x] **Step 3: 新增 preview helper**

在 `_recovery_preview_auto_plan()` 附近新增：

```python
def _recommended_followup_preview_auto_plan(
    recommended_followup_run_id: str,
    *,
    status: str = "preview_required",
) -> tuple[list[WritingAgentToolRequest], dict[str, Any]]:
    preview_tool = WritingAgentToolRequest(
        tool_name="plan_recommended_followups",
        params={"run_id": recommended_followup_run_id},
        planner={
            "mode": "preview",
            "reason": "预览上一轮运行时推荐的后继工具链，不直接执行。",
            "on_missing": "stop",
            "on_failure": "stop",
            "expected_output": "推荐后继工具链预览。",
            "post_generation": False,
            "planner_version": "phase102.recommended_followup_preview_gate.v1",
        },
    )
    planner_output = {
        "status": "preview_required",
        "mode": "preview",
        "source_run_id": recommended_followup_run_id,
        "preview_only": True,
        "tools": [preview_tool.model_dump()],
        "trace": {"selected_tools": ["plan_recommended_followups"], "rejected_tools": []},
        "execution_policy": {
            "status": status,
            "mode": "preview",
            "requires_confirmation": True,
            "requires_plan_hash": True,
        },
    }
    return [preview_tool], planner_output
```

- [x] **Step 4: 运行 GREEN**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "recommended_followups_by_default or executes_recommended_followups_after_hash_confirmation or recommended_followup_hash_mismatch" -q
```

Expected: PASS。

## Task 5: T1 验证、报告、提交

**Files:**
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-22-phase102-recommended-followup-execution-gate.md`

- [x] **Step 1: 相关测试**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py backend/tests/test_writing_agent_tool_executor.py -k "recommended_followup or recommended_followups or recovery" -q
```

Expected: PASS。

- [x] **Step 2: 静态检查和密钥扫描**

Run:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

Expected: `git diff --check` exit 0；密钥扫描无匹配。

- [x] **Step 3: 阶段报告**

报告记录：

- Goal 文档已重新读取。
- 用户补充原则：核心是 Agent 化，不是手动写小说。
- RED/GREEN/T1 验证结果。
- 参考项目吸收：OpenHuman controller registry / Hermes tool schema normalization / OpenClaw tool-call result trace。
- 下一阶段建议：把 slash commands 接入 Agent tool registry，避免 `/chapter` 等命令绕过 Agent 编排。

- [x] **Step 4: 提交并推送**

Run:

```powershell
git add backend/app/services/writing_agent/run_service.py backend/tests/test_writing_agent_runs.py docs/superpowers/plans/long-memory-agent/2026-05-22-phase102-recommended-followup-execution-gate.md docs/superpowers/notes/long-memory-agent/2026-05-22-phase102-recommended-followup-execution-gate.md
git commit -m "feat: gate recommended followup execution"
git push origin main
```
