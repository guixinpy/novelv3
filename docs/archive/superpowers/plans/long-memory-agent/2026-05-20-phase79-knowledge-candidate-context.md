# Phase79 Plan: Knowledge Candidate Context

## Phase Goal

Make Knowledge Base candidates usable by chapter generation without prompt pollution.

Phase78 added candidate persistence and read projection. Phase79 adds a controlled prompt-context provider for candidates that are actually relevant to prose generation.

## Design

Add a chapter prompt context block named `knowledge_base_candidates`.

Eligibility rules:

- include `active` candidates;
- include `candidate` candidates only when confidence is high enough;
- exclude `muted` and `rejected`;
- exclude `self_optimization_lesson` from prose prompts because those are Agent/process lessons, not writing style or story guidance;
- cap the number of injected candidates.

Allowed prompt-facing memory types:

- `author_preference`
- `project_strategy`
- `writing_pattern`
- `decomposition_pattern`

## Why This Matters

The Agent can now record creative memory, but generation still needs a bounded way to consume it. Without this, Knowledge Base remains visible in reports but does not affect output quality.

## Verification Level

T1 local backend verification.

Planned checks:

- RED test that chapter prompt includes only eligible candidates;
- focused GREEN test for chapter prompt migration;
- related prompting tests;
- Writing Agent related tests only if registry or Agent execution changes.

## Not Doing

- No LLM call.
- No automatic extraction.
- No frontend UI.
- No injection of all candidates.
- No self-optimization/system lessons in prose prompt.
