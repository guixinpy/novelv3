# Phase85 Plan: Agent Tool Contract Baseline

## Phase Goal

Create a first formal Agent tool-contract baseline for novelv3, informed by `openclaw`, `hermes-agent`, and `openhuman`, so future refactors can measure whether existing modules are truly becoming Agent-callable tools.

## Why This Phase

The goal has shifted from improving isolated writing pages to rebuilding novelv3 around a domain-specific writing Agent. Existing modules may be refactored if their shape does not serve Agent orchestration.

Before performing larger refactors, the system needs an inspectable contract snapshot for the current Writing Agent tools:

- which module owns the tool;
- whether it is read/write/guarded;
- whether it is internal or user-visible;
- whether it has schema, availability checks, and diagnostics;
- which Agent capability area it serves;
- what contract gaps remain.

## Reference Learning Work

Read-only subagent analysis will inspect:

- `references/agent-projects/openclaw/`
- `references/agent-projects/hermes-agent/`
- `references/agent-projects/openhuman/`

The focus is not feature copying. The focus is extracting portable engineering patterns for:

- tool registry and visibility projection;
- parameter schema and execution-result normalization;
- memory/tool separation;
- failure handling and recovery;
- trace/audit visibility;
- multi-agent or long-task orchestration.

The output should be summarized in the Phase85 report and translated into novelv3-specific next steps.

## System Capability To Build

Add a read-only internal Writing Agent tool that returns a normalized tool-contract snapshot and gap report.

Proposed tool:

- `inspect_agent_tool_contracts`

Expected output:

- `status`
- `summary`
- `coverage`
- `tools`
- `gaps`
- `reference_alignment`
- `recommended_next_steps`

This tool should not execute writing actions and should not mutate data.

## Files Expected To Change

- `backend/app/services/writing_agent/tool_contracts.py`
- `backend/app/services/writing_agent/tool_registry.py`
- `backend/app/services/writing_agent/tool_executor.py`
- `backend/tests/test_writing_agent_tool_registry.py`
- `backend/tests/test_writing_agent_tool_executor.py`
- `docs/superpowers/notes/long-memory-agent/2026-05-20-phase85-agent-tool-contract-baseline.md`

## Validation Level

T1 focused backend tests:

- tool registry exposes `inspect_agent_tool_contracts`;
- executor handles the tool;
- snapshot contains mutability, capability/module grouping, schema coverage, and gap codes;
- all internal tools are represented in the contract snapshot.

T0 checks:

- `git diff --check`
- secret scan over `backend` and non-archived `docs`

No frontend verification is planned because no frontend files should change.

## Not Doing

- No Chapter 27 generation in this phase.
- No broad module rewrite yet.
- No importing external reference-project code as runtime dependency.
- No UI changes.
- No full backend/frontend test suite unless focused tests expose cross-cutting risk.
