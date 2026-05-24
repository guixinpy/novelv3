# Phase217 Trace Profile Policy Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development. This phase is backend-only and read-only: expose audit evidence through `inspect_agent_trace_audit`, without changing planner, executor, profile filtering, or runtime delegation.

**Goal:** Make `inspect_agent_trace_audit` return profile policy audit evidence so the Writing Agent can discover profile/tool policy risks through its Trace tool.

**Architecture:** Reuse the same source as run detail: the latest `describe_agent_tools` step output containing `agent_profile_tool_projection.consistency_audit`. Add a compact, sanitized `profile_policy_audit` section to the Trace audit output and mirror status/issue count into `audit`. Do not add recovery recommendations or execution gates in this phase.

**Tech Stack:** Python, pytest.

---

## Reference Project Inputs

- OpenClaw: policy findings are surfaced as machine-readable status/issue snapshots, separate from runtime tool enforcement.
- Hermes Agent: delegation/toolset progress reports return compact summaries rather than child-agent internals.
- OpenHuman: visible tool specs and full registry are inspectable, but subagent execution remains a separate runtime concern.

## Files

- Modify: `backend/tests/test_writing_agent_trace_audit.py`
  - Add a RED test for `profile_policy_audit`.
- Modify: `backend/app/services/writing_agent/agent_trace_audit.py`
  - Extract latest profile policy audit from `describe_agent_tools` step.
  - Return compact `profile_policy_audit` and `audit.profile_policy_*` fields.
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-24-phase217-trace-profile-policy-audit.md`

## Tasks

### Task 1: RED Test

- [x] **Step 1: Add test**

Add `test_inspect_agent_trace_audit_includes_profile_policy_audit()`:

```python
def test_inspect_agent_trace_audit_includes_profile_policy_audit(db_session):
    project = Project(name="Trace Profile Policy Audit")
    db_session.add(project)
    db_session.flush()
    run = WritingAgentRun(project_id=project.id, goal="检查 profile 策略", status="success", entrypoint="api")
    db_session.add(run)
    db_session.flush()
    db_session.add(
        WritingAgentStep(
            run_id=run.id,
            project_id=project.id,
            step_index=1,
            tool_name="describe_agent_tools",
            status="success",
            input={"params": {"agent_profile": "orchestrator"}},
            output={
                "status": "completed",
                "agent_profile_tool_projection": {
                    "consistency_audit": {
                        "version": "phase215.agent_profile_policy_audit.v1",
                        "status": "needs_attention",
                        "summary": {"issues": 1, "delegate_edges": 4},
                        "issues": [
                            {
                                "code": "delegate_target_missing_definition",
                                "severity": "error",
                                "profile": "orchestrator",
                                "target": "ghost_worker",
                            }
                        ],
                        "delegate_edges": [{"source": "orchestrator", "target": "ghost_worker"}],
                    }
                },
            },
            target_type="agent_tool_plan",
        )
    )
    db_session.commit()

    output = inspect_agent_trace_audit(db_session, project.id, run_id=run.id)

    assert output["audit"]["profile_policy_status"] == "needs_attention"
    assert output["audit"]["profile_policy_issue_count"] == 1
    assert output["profile_policy_audit"]["status"] == "needs_attention"
    assert output["profile_policy_audit"]["summary"]["issues"] == 1
    assert output["profile_policy_audit"]["issues"][0]["code"] == "delegate_target_missing_definition"
    assert "delegate_edges" not in output["profile_policy_audit"]
```

Run:

```powershell
pytest backend/tests/test_writing_agent_trace_audit.py -k "profile_policy_audit" -q
```

Expected: FAIL because trace audit does not expose profile policy audit yet.

### Task 2: Implementation

- [x] **Step 1: Extract audit**

Add `_profile_policy_audit_from_steps(steps)` scanning latest `describe_agent_tools` step output.

- [x] **Step 2: Sanitize audit**

Add `_profile_policy_audit_summary(audit)` returning:

```python
{
    "version": "...",
    "status": "...",
    "summary": {"issues": int, "delegate_edges": int},
    "issues": [{"code": str, "severity": str, "profile": str, "target": str}],
}
```

Do not include `delegate_edges` in the Trace audit output in this phase.

- [x] **Step 3: Attach output**

In `inspect_agent_trace_audit(...)`:

- compute `profile_policy_audit`;
- add `audit.profile_policy_status`;
- add `audit.profile_policy_issue_count`;
- add top-level `profile_policy_audit`.

### Task 3: Validation, Report, Commit

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_trace_audit.py -k "profile_policy_audit or successful_run" -q
python -m compileall backend/app/services/writing_agent
git diff --check
```

- [x] Run DeepSeek key prefix scan without embedding a key in files:

```powershell
$pat='sk-'+'f6aa'; rg -n $pat backend frontend docs --glob '!frontend/node_modules/**'
```

- [x] Write phase report.
- [ ] Commit and push:

```text
feat: expose profile policy audit in trace tool
```
