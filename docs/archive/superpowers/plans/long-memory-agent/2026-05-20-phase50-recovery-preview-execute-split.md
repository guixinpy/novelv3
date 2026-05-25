# Phase50 Recovery Preview Execute Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split recovery planning into a read-only preview path and an explicitly confirmed execute path.

**Architecture:** Keep `plan_recovery_tools` as the read-only preview tool. Enrich `build_recovery_tool_plan()` with a deterministic `plan_hash`, confirmation metadata, and preview trace. Update `WritingAgentRunService.build_auto_plan_tools()` so `input.auto_plan + recovery_run_id` previews by default, while execution requires `execute_recovery: true`, `confirm_execute: true`, and a matching `recovery_plan_hash`.

**Tech Stack:** FastAPI service layer, SQLAlchemy session, Pydantic `WritingAgentToolRequest`, pytest API tests, deterministic JSON hashing.

---

## Reference Assimilation

Phase50 adapts patterns from the local reference projects without adding dependencies:

- `openclaw`: plans are first-class, preview/apply paths are separate, and execution is bound to the planned context.
- `hermes-agent`: planning output remains distinct from tool execution; guardrails reject stale or unsafe execution.
- `openhuman`: preview is read-only; execute requires explicit confirmation and should revalidate the current state.

The novelv3-specific translation is narrower: recovery is a writing workflow repair path, not a general retry engine. It repairs blockers such as missing outline windows before the Agent resumes longform writing.

## Task 1: Write Failing Tests

**Files:**

- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: Update default recovery auto-plan test to expect preview**

Rename `test_agent_run_auto_plan_consumes_recovery_tool_plan` to `test_agent_run_auto_plan_previews_recovery_tool_plan_by_default`.

Expected assertions:

```python
assert payload["status"] == "success"
assert payload["input"]["planner"]["mode"] == "preview"
assert payload["input"]["planner"]["source_run_id"] == blocked_run_id
assert payload["input"]["planner"]["preview_only"] is True
assert payload["input"]["planner"]["execution_policy"]["requires_confirmation"] is True
assert payload["input"]["tools"][0]["tool_name"] == "plan_recovery_tools"
assert payload["input"]["tools"][0]["params"] == {"run_id": blocked_run_id}
assert [step["tool_name"] for step in payload["steps"]] == ["plan_recovery_tools"]
preview = payload["steps"][0]["output"]
assert preview["plan_hash"]
assert preview["can_execute"] is True
assert preview["preview_only"] is True
assert preview["tools"][0]["tool_name"] == "expand_outline_window"
```

- [x] **Step 2: Add confirmed execute test**

Add `test_agent_run_auto_plan_executes_recovery_after_hash_confirmation`.

Test setup:

1. Create the same blocked preflight run.
2. Call explicit `plan_recovery_tools` once and read `plan_hash`.
3. Monkeypatch `app.api.outlines.expand_outline_window`.
4. Call auto-plan with:

```json
{
  "auto_plan": true,
  "recovery_run_id": "<blocked_run_id>",
  "execute_recovery": true,
  "confirm_execute": true,
  "recovery_plan_hash": "<plan_hash>"
}
```

Expected assertions:

```python
assert payload["status"] == "success"
assert payload["input"]["planner"]["mode"] == "execute"
assert payload["input"]["planner"]["plan_hash"] == plan_hash
assert payload["input"]["planner"]["execution_policy"]["confirmed"] is True
assert payload["input"]["tools"][0]["tool_name"] == "expand_outline_window"
assert [step["tool_name"] for step in payload["steps"]] == ["expand_outline_window"]
```

- [x] **Step 3: Add stale/mismatched hash test**

Add `test_agent_run_auto_plan_rejects_recovery_execute_hash_mismatch`.

Expected assertions:

```python
assert payload["status"] == "success"
assert payload["input"]["planner"]["mode"] == "preview"
assert payload["input"]["planner"]["execution_policy"]["status"] == "hash_mismatch"
assert payload["input"]["tools"][0]["tool_name"] == "plan_recovery_tools"
assert [step["tool_name"] for step in payload["steps"]] == ["plan_recovery_tools"]
```

- [x] **Step 4: Verify RED**

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "recovery_tool_plan or recovery_after_hash or recovery_execute_hash"
```

Expected: FAIL because current auto-plan executes recovery directly and recovery preview has no `plan_hash`.

## Task 2: Enrich Recovery Preview

**Files:**

- Modify: `backend/app/services/writing_agent/recovery_planner.py`

- [x] **Step 1: Add deterministic plan hash**

Add imports:

```python
import hashlib
import json
```

Add constant:

```python
RECOVERY_PREVIEW_VERSION = "phase50.recovery_preview.v1"
```

Add helper:

```python
def _plan_hash(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
```

- [x] **Step 2: Enrich completed preview output**

For a recommended recovery with a tool, include:

```python
hash_payload = {
    "preview_version": RECOVERY_PREVIEW_VERSION,
    "source_run_id": run_id,
    "source_step_id": step.id,
    "source_step_index": step.step_index,
    "reason_code": recovery.get("reason_code"),
    "tools": [tool] if tool else [],
}
plan_hash = _plan_hash(hash_payload)
```

Return fields:

```python
"preview_version": RECOVERY_PREVIEW_VERSION,
"preview_only": True,
"can_execute": tool is not None and not bool(recovery.get("requires_user_input")),
"requires_confirmation": True,
"approval_required": True,
"plan_hash": plan_hash,
"hash_payload": hash_payload,
"source_step_id": step.id,
"reason_code": recovery.get("reason_code"),
"execution_policy": {
    "mode": "preview",
    "requires_confirmation": True,
    "requires_plan_hash": True,
    "safe_auto_execute": tool["tool_name"] in {"expand_outline_window", "backfill_outline_gaps"} if tool else False,
},
```

## Task 3: Split Auto-Plan Preview and Execute

**Files:**

- Modify: `backend/app/services/writing_agent/run_service.py`

- [x] **Step 1: Import only when recovery branch is used**

Inside `build_auto_plan_tools()`, keep the local import:

```python
from app.services.writing_agent.recovery_planner import build_recovery_tool_plan
```

- [x] **Step 2: Default recovery branch returns preview tool**

When `recovery_run_id` exists and the request is not confirmed execution, return:

```python
preview_tool = WritingAgentToolRequest(
    tool_name="plan_recovery_tools",
    params={"run_id": recovery_run_id},
    planner={
        "mode": "preview",
        "reason": "预览上一轮阻塞的恢复工具链，不直接执行写操作。",
        "on_missing": "stop",
        "on_failure": "stop",
        "expected_output": "恢复工具链预览。",
        "post_generation": False,
        "planner_version": "phase50.recovery_preview_gate.v1",
    },
)
planner_output = {
    "status": "preview_required",
    "mode": "preview",
    "source_run_id": recovery_run_id,
    "preview_only": True,
    "tools": [preview_tool.model_dump()],
    "trace": {"selected_tools": ["plan_recovery_tools"], "rejected_tools": []},
    "execution_policy": {
        "status": "preview_required",
        "requires_confirmation": True,
        "requires_plan_hash": True,
    },
}
return [preview_tool], planner_output
```

- [x] **Step 3: Confirmed recovery branch verifies plan hash**

When `execute_recovery is True`:

```python
plan = build_recovery_tool_plan(self.db, project_id, recovery_run_id)
expected_hash = str(run_input.get("recovery_plan_hash") or "").strip()
confirmed = run_input.get("confirm_execute") is True
if not confirmed or not expected_hash or expected_hash != plan.get("plan_hash"):
    planner_output = _recovery_preview_gate(recovery_run_id, status="confirmation_required" or "hash_mismatch")
    return [preview_tool], planner_output
plan["mode"] = "execute"
plan["execution_policy"] = {
    **(plan.get("execution_policy") or {}),
    "mode": "execute",
    "confirmed": True,
    "requires_confirmation": True,
}
tools = [WritingAgentToolRequest(**tool) for tool in plan.get("tools", []) if isinstance(tool, dict)]
return tools, plan
```

Use a small private helper if needed to avoid duplicating preview-tool construction.

## Task 4: Verify and Report

**Files:**

- Modify: this plan checklist.
- Add: `docs/superpowers/notes/long-memory-agent/2026-05-20-phase50-recovery-preview-execute-split.md`

- [x] **Step 1: Run focused GREEN**

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "recovery_tool_plan or recovery_after_hash or recovery_execute_hash"
```

- [x] **Step 2: Run T1 module verification**

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py tests\test_writing_agent_planner.py tests\test_writing_agent_tool_registry.py -q
```

- [x] **Step 3: Static checks**

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

- [x] **Step 4: Write report, commit, push**
