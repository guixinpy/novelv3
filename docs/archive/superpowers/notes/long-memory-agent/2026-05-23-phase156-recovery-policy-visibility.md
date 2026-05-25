# Phase156 Recovery Policy Visibility Report

## Summary

The Writing Agent run drawer now surfaces recovery preview execution policy, guardrails, blockers, and suggested recovery tools from the `plan_recovery_tools` step output.

## Changes

- Derived recovery preview data from the `plan_recovery_tools` step output.
- Displayed execution policy facts:
  - policy status.
  - confirmation requirement.
  - plan-hash requirement.
  - safe auto-execute flag.
- Displayed guardrail status and blocker details.
- Displayed suggested recovery tool names.
- Added frontend regression coverage for blocked recovery policy visibility.

## Novel Progress

No new chapter was generated in this phase. This phase improves the Agent recovery inspection surface, which supports long-running generation by making recovery safety and blockers visible before the user proceeds.

## Validation

RED:

```powershell
Set-Location frontend; npm run test:unit -- src/components/writingAgent/AgentRunDrawer.test.ts
```

Result: failed because the drawer did not render `恢复执行策略`.

GREEN:

```powershell
Set-Location frontend; npm run test:unit -- src/components/writingAgent/AgentRunDrawer.test.ts
```

Result: `1 passed`, `3 passed`.

Targeted frontend regression:

```powershell
Set-Location frontend; npm run test:unit -- src/components/writingAgent/AgentRunDrawer.test.ts src/views/HermesView.test.ts
```

Result: `2 passed`, `6 passed`.

Build/type check:

```powershell
Set-Location frontend; npm run build
```

Result: `vue-tsc --noEmit && vite build` passed.

Hygiene:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

Result: diff check passed; secret scan found no matches.

## Long-Goal Implication

Long-running Agent systems need recoverability and observability. This phase makes recovery planning auditable from the primary UI path, so users can see why a recovery is executable, blocked, or unsafe instead of relying on raw JSON or backend logs.

## Next Recommendation

Continue along the recovery-to-execution path: add a read-only frontend indication for whether a recovery preview can be executed, then introduce a confirmation-gated recovery execution action only where the backend policy marks the plan executable.
