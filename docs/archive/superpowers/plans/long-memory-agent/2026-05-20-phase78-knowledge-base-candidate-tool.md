# Phase78 Plan: Knowledge Base Candidate Tool

## Phase Goal

Add the first write-side Knowledge Base tool for the Writing Agent.

Phase77 proved the read-side route can expose `knowledge_base_sparse`, but the Agent has no durable way to record creative-memory candidates from dogfood evidence. This phase adds a minimal candidate recorder.

## Design Decision

Use a low-risk bridge storage:

- store candidates in `Project.style_config["knowledge_base_candidates"]`;
- do not add a new database table or migration in this phase;
- keep the data shape explicit enough to migrate later.

This avoids touching local dogfood DB schema while proving the Agent contract.

## Candidate Shape

Each candidate should include:

- `id`
- `memory_type`
- `title`
- `summary`
- `source_refs`
- `confidence`
- `status`
- `tags`
- `created_at`
- `updated_at`
- `observed_count`

Supported initial memory types:

- `author_preference`
- `project_strategy`
- `writing_pattern`
- `self_optimization_lesson`
- `decomposition_pattern`

## System Capability

Add `record_agent_knowledge_base_candidate`.

The tool should:

- be Agent-callable;
- mutate only `Project.style_config`;
- reject missing source refs;
- deduplicate repeated candidates by stable fingerprint;
- return provenance and trace metadata;
- not write Athena world facts;
- not inject the candidate into generation prompts automatically.

Also update `inspect_agent_knowledge_base_route` to display candidate counts/items and treat candidate presence as enough to avoid `knowledge_base_sparse`.

## Verification Level

T1 local backend verification.

Planned checks:

- RED service/registry/executor tests;
- focused GREEN tests;
- related Knowledge Base/preference/self-optimization tests;
- all Writing Agent related tests because the read route and registry are shared.

## Dogfood Work

After implementation, record one live dogfood candidate from Phase77:

- type: `self_optimization_lesson`
- source refs: Phase77 report, Agent run id, Chapter 24
- lesson: low-detail continuation can succeed when the Agent route reads Knowledge Base, longform memory, world model, context summary, and preflight before generation.

## Not Doing

- No Knowledge Base table.
- No frontend UI.
- No automatic memory extraction from arbitrary chat.
- No prompt injection of all candidates.
- No world-model writes.
