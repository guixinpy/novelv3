# Phase199 Route Opt-In Apply Approval Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only approval contract preview for the pending action route opt-in apply diff, so the future mutation tool can require a stable confirmation hash before modifying `PendingAction.params`.

**Architecture:** Extend the Phase198 read-only preview chain instead of adding mutation behavior. `slash_command_route.py` owns the pure contract builder and canonical hash input; `agent_core_tool_adapters.py` reads the pending action and delegates to the Phase198 preview plus Phase199 contract builder; `agent_core_tool_descriptors.py` exposes a new internal preflight report tool. The contract hashes a narrow stable payload, not the full preview output.

**Tech Stack:** Python, pytest, SQLAlchemy test DB, existing Writing Agent tool adapter/descriptor registry.

---

## Scope

- New internal tool: `preview_pending_action_route_approval_opt_in_apply_contract`.
- No write execution and no real apply mutation in this phase.
- Confirmation contract only applies when Phase198 preview is `ready` and has a non-empty `params_diff`.
- `already_declared`, `noop`, and blocked previews remain non-mutating and must not require confirmation.
- Secret handling: do not write runtime API keys to code, docs, or commit messages.

## Files

- Modify: `backend/app/services/writing_agent/slash_command_route.py`
  - Add `PENDING_ACTION_ROUTE_OPT_IN_APPLY_CONTRACT_VERSION`.
  - Add canonical hash helper for this route contract.
  - Add `build_pending_action_route_approval_opt_in_apply_contract(...)`.
- Modify: `backend/app/services/writing_agent/agent_core_tool_adapters.py`
  - Add adapter map entry.
  - Add handler that reuses Phase198 preview path and attaches the Phase199 contract.
- Modify: `backend/app/services/writing_agent/agent_core_tool_descriptors.py`
  - Add descriptor after Phase198 preview descriptor.
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
  - Add adapter order, executor behavior, stability, blocked/noop, and metadata tests.
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
  - Add descriptor test.
- Add: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase199-route-opt-in-apply-approval-contract.md`

## Acceptance Criteria

- Ready Phase198 preview returns:
  - `status == "requires_confirmation"`
  - `required_confirmation is True`
  - `approval_contract_hash` starts with `approval:`
  - `approval_contract.approval.approval_contract_hash == approval_contract_hash`
  - `route_apply_preview.write_performed is False`
  - DB `PendingAction.params` unchanged.
- Hash changes when `pending_action_id` or `route_after` changes.
- Hash does not change when `trace` or unrelated pending params change.
- Blocked Phase198 preview returns `status == "blocked"` and no confirmation hash.
- Already-declared/no-diff preview returns `status == "not_required"` and no confirmation hash.
- Tool registry exposes the new descriptor as internal, preflight, non-blocking.
- T0/T1/T2 validations pass with no secret matches.

## Tasks

### Task 1: RED Tests

- [x] Add failing executor tests to `backend/tests/test_writing_agent_tool_executor.py`:

```python
@pytest.mark.asyncio
async def test_tool_executor_previews_pending_route_opt_in_apply_contract(db_session):
    project = Project(name="Pending Route Opt In Apply Contract")
    db_session.add(project)
    db_session.commit()
    dialog = Dialog(project_id=project.id, state="pending_action")
    db_session.add(dialog)
    db_session.commit()
    route = build_dialog_agent_route("preview_setup", source="slash_command", command_name="setup")
    pending = PendingAction(
        dialog_id=dialog.id,
        type="preview_setup",
        params={"project_id": project.id, "agent_route": route, "command_args": "雾港悬疑"},
    )
    db_session.add(pending)
    db_session.commit()
    original_params = dict(pending.params)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-route-contract"),
        WritingAgentToolRequest(
            tool_name="preview_pending_action_route_approval_opt_in_apply_contract",
            params={"pending_action_id": pending.id},
        ),
    )

    db_session.refresh(pending)
    assert result.handled is True
    assert result.output["status"] == "requires_confirmation"
    assert result.output["required_confirmation"] is True
    assert result.output["approval_contract_hash"].startswith("approval:")
    assert result.output["approval_contract"]["approval"]["approval_contract_hash"] == result.output["approval_contract_hash"]
    assert result.output["route_apply_preview"]["status"] == "ready"
    assert result.output["route_apply_preview"]["write_performed"] is False
    assert result.output["approval_contract"]["mutation_target"] == "PendingAction.params.agent_route"
    assert result.output["approval_contract"]["mutation_path"] == "params.agent_route.use_agent_approval_chain"
    assert pending.params == original_params
```

- [x] Add pure stability tests:

```python
def test_pending_route_opt_in_apply_contract_hash_is_stable_for_trace_and_unrelated_params():
    from app.services.writing_agent.slash_command_route import (
        build_pending_action_route_approval_opt_in_apply_contract,
        preview_pending_action_route_approval_opt_in_apply,
    )

    route_plan = {
        "status": "ready",
        "version": "phase196.route_approval_opt_in_plan.v1",
        "metadata_patch": {"use_agent_approval_chain": True},
        "route_before": {"agent_tool_name": "generate_setup"},
        "route_after": {"agent_tool_name": "generate_setup", "use_agent_approval_chain": True},
        "preference": {"preferred_prepare_tool_name": "prepare_generate_setup_execution", "preferred_execute_tool_name": "execute_generate_setup_with_approval"},
        "risk": {"codes": []},
        "trace": {"volatile": "a"},
    }
    preview_a = preview_pending_action_route_approval_opt_in_apply(
        pending_action_id="pending-1",
        pending_action_type="preview_setup",
        pending_params={"agent_route": {"agent_tool_name": "generate_setup"}, "command_args": "A"},
        route_plan=route_plan,
    )
    preview_b = preview_pending_action_route_approval_opt_in_apply(
        pending_action_id="pending-1",
        pending_action_type="preview_setup",
        pending_params={"command_args": "B", "agent_route": {"agent_tool_name": "generate_setup"}},
        route_plan={**route_plan, "trace": {"volatile": "b"}},
    )

    contract_a = build_pending_action_route_approval_opt_in_apply_contract(project_id="project-1", route_apply_preview=preview_a)
    contract_b = build_pending_action_route_approval_opt_in_apply_contract(project_id="project-1", route_apply_preview=preview_b)

    assert contract_a["approval_contract_hash"] == contract_b["approval_contract_hash"]
```

- [x] Add blocked and already-declared executor tests.
- [x] Add adapter metadata test for `preview_pending_action_route_approval_opt_in_apply_contract`.
- [x] Add descriptor test in `backend/tests/test_writing_agent_tool_registry.py`.
- [x] Run RED:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "route_opt_in_apply_contract" -q
pytest backend/tests/test_writing_agent_tool_registry.py -k "route_opt_in_apply_contract" -q
```

Expected: failures because tool, adapter metadata, descriptor, and pure builder do not exist.

### Task 2: GREEN Implementation

- [x] Add contract builder in `slash_command_route.py`.
- [x] Add adapter entry and handler in `agent_core_tool_adapters.py`.
- [x] Add descriptor in `agent_core_tool_descriptors.py`.
- [x] Run T1:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "route_opt_in_apply_contract" -q
pytest backend/tests/test_writing_agent_tool_registry.py -k "route_opt_in_apply_contract" -q
```

Expected: all selected tests pass.

### Task 3: Targeted Regression

- [x] Run T2 route-approval slice:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "route_opt_in_apply_contract or route_opt_in_apply or pending_action_route_opt_in_plan or route_approval_opt_in_plan or static_adapter_names or unhandled_internal or agent_core_tool_adapters" -q
pytest backend/tests/test_writing_agent_tool_registry.py -k "route_opt_in_apply_contract or route_opt_in_apply_preview or route_approval_opt_in_plan or agent_core_tool_descriptors" -q
python -m compileall backend/app/services/writing_agent
```

Expected: all selected tests pass and compile exits 0.

### Task 4: Documentation, Hygiene, Commit

- [x] Write phase report:

```text
docs/superpowers/notes/long-memory-agent/2026-05-23-phase199-route-opt-in-apply-approval-contract.md
```

- [x] Run hygiene:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

Expected: diff check exits 0; secret scan exits 1 with no matches.

- [x] Commit and push:

```powershell
git add backend/app/services/writing_agent/slash_command_route.py backend/app/services/writing_agent/agent_core_tool_adapters.py backend/app/services/writing_agent/agent_core_tool_descriptors.py backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase199-route-opt-in-apply-approval-contract.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase199-route-opt-in-apply-approval-contract.md
git commit -m "feat: preview route opt in apply contract"
git push origin main
```

## Subagent Notes

Explorer `019e5462-c6ae-7fd3-a76e-1f4ae9a84ed1` recommended:

- Keep this as a read-only preflight report tool.
- Hash a narrow canonical payload.
- Exclude trace, risk guardrails, entire params snapshots, UI text, timestamps, and DB object references.
- Treat `already_declared` as no-op, not a confirmation-required mutation.
- Future real apply must recompute preview and contract before accepting caller-provided hash.
