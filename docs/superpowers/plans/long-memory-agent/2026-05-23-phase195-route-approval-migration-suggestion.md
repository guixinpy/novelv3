# Phase195 Route Approval Migration Suggestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 route preference projection 输出可审计的 approval-chain opt-in 迁移建议包，供后续 Agent 决策是否写入 route metadata。

**Architecture:** 在 `_route_preference` 中为需要 approval gate 的 route 增加 `approval_chain_opt_in_suggestion`。该建议包只描述 route metadata patch、预期 prepare/execute 工具与 guardrail，不执行写入、不改变默认 runtime。

**Tech Stack:** Python 3、pytest、Writing Agent route projection。

---

## Files

- Modify: `backend/app/services/writing_agent/slash_command_route.py`
- Modify: `backend/tests/test_writing_agent_route_preference.py`
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
- Add: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase195-route-approval-migration-suggestion.md`

## Success Criteria

- For approval-gated legacy routes, projection emits `approval_chain_opt_in_suggestion.status == "available"`.
- Suggestion includes:
  - `param_name == "use_agent_approval_chain"`
  - `route_metadata_patch == {"use_agent_approval_chain": True}`
  - `expected_prepare_tool_name`
  - `expected_execute_tool_name`
  - `runtime_default_preserved is True`
  - guardrails documenting explicit opt-in and control param stripping.
- For opt-in declared routes, suggestion status is `already_declared`.
- For non-gated routes, suggestion is `None`.
- Agent tool adapter output includes the suggestion.

## Non-Scope

- Do not write pending action params.
- Do not change route builder defaults.
- Do not change control plane dispatch.

## Tasks

### Task 1: RED Suggestion Tests

- [x] Add route preference tests for:
  - available suggestion on default setup route
  - already_declared suggestion when opt-in metadata is simulated
  - no suggestion for a synthetic no-gate route.
- [x] Add tool executor assertion that suggestion is present in adapter output.
- [x] Run expected RED:

```powershell
pytest backend/tests/test_writing_agent_route_preference.py -k "migration_suggestion" -q
pytest backend/tests/test_writing_agent_tool_executor.py -k "route_preference_projection and migration_suggestion" -q
```

Expected: `approval_chain_opt_in_suggestion` is missing.

### Task 2: Implement Suggestion Package

- [x] Add `_approval_chain_opt_in_suggestion(...)` helper in `slash_command_route.py`.
- [x] Return `None` when `approval_gate_required` is false.
- [x] Return `status="already_declared"` when opt-in metadata is present.
- [x] Return `status="available"` when opt-in metadata is absent and preferred tools are supported.
- [x] Include route metadata patch and guardrails.

### Task 3: GREEN/T2 Verification

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_route_preference.py -q
pytest backend/tests/test_writing_agent_tool_executor.py -k "route_preference_projection" -q
python -m compileall backend/app/services/writing_agent
```

### Task 4: Report, Hygiene, Commit, Push

- [x] Run:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

- [x] Write report:

```text
docs/superpowers/notes/long-memory-agent/2026-05-23-phase195-route-approval-migration-suggestion.md
```

- [ ] Commit and push:

```powershell
git add backend/app/services/writing_agent/slash_command_route.py backend/tests/test_writing_agent_route_preference.py backend/tests/test_writing_agent_tool_executor.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase195-route-approval-migration-suggestion.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase195-route-approval-migration-suggestion.md
git commit -m "feat: suggest route approval opt in patches"
git push origin main
```
