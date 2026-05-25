# Long Memory Writing Agent Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish the first executable baseline for the long-memory writing Agent goal: working directories, current-system inventory, reference-Agent study protocol, and a real longform dogfood novel protocol.

**Architecture:** Phase 1 is intentionally non-invasive. It creates the documentation-driven control surface for the long-running goal, maps existing novelv3 modules into candidate Agent tools, and defines how real chapter generation will be used to drive later implementation.

**Tech Stack:** Markdown docs, Git, PowerShell, existing novelv3 backend/frontend tests only when required by the selected verification tier.

---

## Phase Metadata

- **Phase:** 1
- **Date:** 2026-05-18
- **Verification Tier:** T0 for documentation changes; T1 only if this phase discovers and fixes a blocking script/config issue.
- **Primary Output:** Baseline notes and dogfood protocol under `docs/superpowers/notes/long-memory-agent/`.
- **No Code Implementation In This Phase:** Do not modify backend, frontend, database models, API contracts, or prompts unless a blocking issue prevents baseline discovery.

## Phase 1 Success Criteria

- The goal has active plan and notes directories.
- The current novelv3 module map is documented from source, not memory.
- The three reference projects have a focused study checklist.
- The first real longform dogfood novel protocol is defined before chapter generation begins.
- The next phase can start from documents alone after context compression.

## Files

- Create: `docs/superpowers/plans/long-memory-agent/2026-05-18-phase1-baseline-and-dogfood-protocol.md`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-18-phase1-baseline.md`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-18-reference-agent-study.md`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-18-dogfood-novel-protocol.md`
- Modify: `docs/superpowers/README.md`

## Task 1: Prepare Active Goal Directories

- [x] **Step 1: Create plan and notes directories**

Run:

```powershell
New-Item -ItemType Directory -Force -Path `
  docs\superpowers\plans\long-memory-agent, `
  docs\superpowers\notes\long-memory-agent | Out-Null
```

Expected: both directories exist.

- [x] **Step 2: Confirm existing goal spec is active**

Run:

```powershell
Test-Path docs\superpowers\specs\2026-05-18-long-memory-writing-agent-goal.md
```

Expected: `True`

## Task 2: Document Current novelv3 Agent-Relevant Baseline

- [x] **Step 1: Inventory backend and frontend module paths**

Run:

```powershell
rg --files backend frontend scripts docs | rg "(athena|world|retriev|dialog|writing|chapter|trace|background|task|queue|hermes|review|knowledge|memory|longform)" | Sort-Object
```

Expected: output lists current Agent-relevant code and docs.

- [x] **Step 2: Inventory existing longform tests and scripts**

Run:

```powershell
rg --files backend frontend scripts | rg "(longform|scale|athena|retrieval|world|background|writing|chapter)" | Sort-Object
```

Expected: output includes longform, Athena, retrieval, world model, writing, and background test files.

- [x] **Step 3: Write `2026-05-18-phase1-baseline.md`**

The note must contain these sections:

```markdown
# Phase 1 Baseline

## Source Snapshot

- Branch:
- HEAD:
- Ahead/behind:
- Active goal spec:

## Existing Candidate Agent Tools

| Candidate Tool | Existing Files | Current Role | Risk / Gap |
| --- | --- | --- | --- |

## Existing Verification Assets

| Area | Test / Script | Suggested Tier |
| --- | --- | --- |

## Immediate Observations

- Record at least one source-grounded observation.

## Next Phase Inputs

- Record at least one concrete next-phase input.
```

No empty bullet may remain in the final note.

## Task 3: Study Reference Agent Projects Without Copying Architecture

- [x] **Step 1: Confirm local reference snapshots**

Run:

```powershell
Get-ChildItem references\agent-projects -Directory | Select-Object Name
```

Expected: `openclaw`, `hermes-agent`, and `openhuman` are present.

- [x] **Step 2: Ask subagents to study independent reference slices**

Dispatch separate subagents for:

- openclaw: long memory, tool registry, extension/plugin architecture.
- hermes-agent: agent loop, tool execution, plans/routines, context handling.
- openhuman: memory model, human/profile persistence, agent state.

Each subagent must return:

```markdown
## What to Learn

## What Not to Copy

## Relevant Paths

## Novelv3 Implications
```

- [x] **Step 3: Write `2026-05-18-reference-agent-study.md`**

The note must synthesize subagent findings into:

```markdown
# Reference Agent Study

## Scope

## openclaw

## hermes-agent

## openhuman

## Cross-Project Patterns

## Recommended novelv3 Adaptation Principles

## Open Questions For Later Phases
```

## Task 4: Define the Real Longform Dogfood Novel Protocol

- [x] **Step 1: Inspect current app data and project conventions**

Run:

```powershell
Get-ChildItem data -Force -ErrorAction SilentlyContinue | Select-Object Mode,Name
rg -n "Dogfood|longform|chapter|project" docs backend frontend scripts | Select-Object -First 120
```

Expected: enough context to avoid inventing a dogfood process disconnected from current data model.

- [x] **Step 2: Write `2026-05-18-dogfood-novel-protocol.md`**

The protocol must define:

```markdown
# Longform Dogfood Novel Protocol

## Purpose

## Novel Target

## Chapter Standard

## Generation Loop

## Review Loop

## Memory / World Model Loop

## Metrics

## Stop Conditions

## Phase 2 Starting Task
```

The first real dogfood novel should not start until this protocol exists.

## Task 5: Update Active Docs Index

- [x] **Step 1: Update `docs/superpowers/README.md`**

Add the active Phase 1 plan and notes directory under current effective documents.

- [x] **Step 2: Verify docs formatting**

Run:

```powershell
git diff --check
```

Expected: no output and exit code 0.

## Task 6: Phase 1 Report And Commit

- [x] **Step 1: Update this plan with completion notes**

Add a `Phase 1 Completion Notes` section at the bottom containing:

```markdown
## Phase 1 Completion Notes

## Actual Completed Work

## Novel Progress

## Issues Found

## Issues Fixed

## Verification

## Next Phase Recommendation
```

- [ ] **Step 2: Commit Phase 1 docs**

Run:

```powershell
git add docs/superpowers/README.md docs/superpowers/plans/long-memory-agent docs/superpowers/notes/long-memory-agent
git commit -m "docs: start long memory agent phase 1"
```

Expected: commit succeeds. Do not push unless the user asks or this phase becomes a merge checkpoint.

## Phase 1 Completion Notes

## Actual Completed Work

- Created active goal execution directories under `docs/superpowers/plans/long-memory-agent/` and `docs/superpowers/notes/long-memory-agent/`.
- Created the Phase 1 plan document.
- Updated `docs/superpowers/README.md` to list active long-memory Agent plan and notes directories.
- Wrote current-system baseline: `docs/superpowers/notes/long-memory-agent/2026-05-18-phase1-baseline.md`.
- Dispatched three independent reference-study subagents for openclaw, hermes-agent, and openhuman.
- Wrote synthesized reference study: `docs/superpowers/notes/long-memory-agent/2026-05-18-reference-agent-study.md`.
- Wrote the first real longform dogfood novel protocol: `docs/superpowers/notes/long-memory-agent/2026-05-18-dogfood-novel-protocol.md`.

## Novel Progress

- No chapter generation was started in Phase 1 by design.
- The dogfood novel protocol now defines the initial original test novel: `《雾港回声》`.
- Phase 2 is responsible for creating/selecting the actual project and generating chapter 1 through the application path.

## Issues Found

- novelv3 already has many strong components, but no single Writing Agent Core that treats them as typed tools.
- Existing longform memory handles chapter/arc/volume/global summaries, but not author preference facets or拆书/writing-pattern memory.
- Synthetic scale smoke cannot replace real prose dogfood.
- The branch is currently ahead of `origin/main` by documentation commits.

## Issues Fixed

- No runtime issues were fixed in Phase 1.
- Documentation drift was reduced by creating active Phase 1 plan and notes that survive context compression.

## Verification

- Verification tier: T0.
- Ran `git diff --check`; it passed before Phase 1 note synthesis and should be rerun before commit.
- No backend/frontend tests were run because Phase 1 made documentation-only changes.

## Next Phase Recommendation

Phase 2 should create or select the `《雾港回声》` dogfood project, verify runtime model configuration without committing secrets, generate chapter 1 with at least 2000 Chinese characters, and record which existing modules fail to support the Agent-driven loop.
