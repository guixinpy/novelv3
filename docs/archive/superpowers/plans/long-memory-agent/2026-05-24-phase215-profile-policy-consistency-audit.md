# Phase215 Profile Policy Consistency Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development. A read-only reference-project subagent should inspect OpenClaw/Hermes/OpenHuman while implementation proceeds locally.

**Goal:** Add a structured consistency audit to the Agent profile tool projection so declared delegate targets can be checked against known profile definitions and tool policy profiles before runtime delegation is enabled.

**Architecture:** Keep the audit inside `agent_tool_surface_policy.py` because it owns profile definitions and profile-scoped tool projection. The audit is read-only metadata under `agent_profile_tool_projection["consistency_audit"]`; it does not alter planner choice, executor behavior, profile visibility filtering, or task queue execution.

**Tech Stack:** Python, pytest.

---

## Reference Project Inputs

- Hermes Agent: delegation has explicit role/depth/runtime limits; this phase only adopts preflight visibility of delegation constraints.
- OpenHuman: agent definitions separate tools and subagents; this phase audits definition consistency without treating subagents as direct tool calls.
- OpenClaw: tool/subagent inventory should be compact and machine-readable; this phase emits a compact audit projection with rule codes and issues.

## Files

- Modify: `backend/app/services/writing_agent/agent_tool_surface_policy.py`
  - Add `AGENT_PROFILE_POLICY_AUDIT_VERSION`.
  - Add `build_agent_profile_policy_audit()`.
  - Include `consistency_audit` in `build_agent_profile_tool_projection()`.
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
  - Assert the normal ready-project tool plan exposes a passing audit.
  - Add a direct helper test proving unknown delegate targets produce issues.
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-24-phase215-profile-policy-consistency-audit.md`

## Tasks

### Task 1: RED Tests

- [x] **Step 1: Backend projection RED**

Extend `test_agent_tool_plan_exposes_agent_profile_tool_projection()`:

```python
audit = projection["consistency_audit"]
assert audit["version"] == "phase215.agent_profile_policy_audit.v1"
assert audit["status"] == "passed"
assert audit["summary"]["issues"] == 0
assert audit["summary"]["delegate_edges"] == 4
assert {"source": "orchestrator", "target": "drafting_worker"} in audit["delegate_edges"]
```

Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py -k "agent_profile_tool_projection" -q
```

Expected: FAIL because `consistency_audit` does not exist.

- [x] **Step 2: Helper RED**

Import `build_agent_profile_policy_audit` and add:

```python
def test_agent_profile_policy_audit_flags_unknown_delegate_targets():
    audit = build_agent_profile_policy_audit(
        {
            "version": "test",
            "profiles": {
                "orchestrator": {
                    "profile": "orchestrator",
                    "delegation_allowed": True,
                    "delegate_to_profiles": ["ghost_worker"],
                }
            },
        },
        {"orchestrator": {"profile": "orchestrator"}},
    )

    assert audit["status"] == "needs_attention"
    assert any(issue["code"] == "delegate_target_missing_definition" for issue in audit["issues"])
    assert any(issue["code"] == "delegate_target_missing_tool_rule" for issue in audit["issues"])
```

Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py -k "profile_policy_audit" -q
```

Expected: FAIL because the helper does not exist.

### Task 2: Minimal Audit Implementation

- [x] **Step 1: Add version constant**

Add:

```python
AGENT_PROFILE_POLICY_AUDIT_VERSION = "phase215.agent_profile_policy_audit.v1"
```

- [x] **Step 2: Add audit helper**

Implement `build_agent_profile_policy_audit(profile_definitions_projection, profiles_projection)` to return:

```python
{
    "version": AGENT_PROFILE_POLICY_AUDIT_VERSION,
    "status": "passed" | "needs_attention",
    "summary": {
        "profile_definitions": int,
        "profile_tool_rules": int,
        "delegate_edges": int,
        "issues": int,
    },
    "delegate_edges": [{"source": profile, "target": target}],
    "issues": [{"code": str, "severity": "error" | "warning", ...}],
    "rules": [{"code": str, "status": "passed" | "failed"}],
}
```

Rules:

- every definition has a tool rule;
- every tool rule has a definition;
- delegate targets must have definitions;
- delegate targets must have tool rules;
- non-delegating profiles must not declare delegate targets;
- delegated profiles should be leaf profiles until runtime nesting exists.

- [x] **Step 3: Attach audit to projection**

In `build_agent_profile_tool_projection()`, compute definitions once and attach:

```python
profile_definitions = build_agent_profile_definitions_projection()
...
"profile_definitions": profile_definitions,
"consistency_audit": build_agent_profile_policy_audit(profile_definitions, profiles),
```

### Task 3: GREEN and Validation

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py -k "agent_profile_tool_projection or profile_policy_audit" -q
```

- [x] Run:

```powershell
python -m compileall backend/app/services/writing_agent
git diff --check
```

- [x] Run DeepSeek key prefix scan without embedding a key in files:

```powershell
$pat='sk-'+'f6aa'; rg -n $pat backend frontend docs --glob '!frontend/node_modules/**'
```

### Task 4: Report and Commit

- [x] Write the phase report with RED/GREEN evidence and reference-project subagent summary.
- [x] Commit and push:

```text
feat: audit agent profile policy consistency
```
