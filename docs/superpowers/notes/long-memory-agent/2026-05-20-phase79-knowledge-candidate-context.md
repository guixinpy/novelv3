# Phase79 Report: Knowledge Candidate Context

## Summary

Phase79 makes Knowledge Base candidates usable by chapter generation through a bounded prompt provider.

The new provider injects only prompt-safe creative-memory candidates into chapter generation:

- `author_preference`
- `project_strategy`
- `writing_pattern`
- `decomposition_pattern`

It excludes:

- `self_optimization_lesson`
- low-confidence candidates
- `muted` and `rejected` candidates

## Why This Matters

Phase78 allowed the Agent to record creative-memory candidates. Without controlled prompt consumption, those candidates would remain report-only and not improve generation.

This phase closes that read/write/use loop for prompt-safe candidates while keeping system/process lessons out of prose prompts.

## Changes

- Added `backend/app/prompting/providers/knowledge_base.py`.
- Added `knowledge_base_candidates` context block to chapter prompt assembly.
- Added prompt test ensuring only eligible candidates enter generation context.
- Kept `self_optimization_lesson` out of prose prompts.

## Prompt Eligibility

Injected:

- status `active`;
- status `candidate` with confidence >= `0.7`;
- prompt-safe memory type;
- non-empty title and summary.

Excluded:

- status `muted`;
- status `rejected`;
- low-confidence candidate memories;
- system/process memory type `self_optimization_lesson`.

The block is capped to `4` candidates and truncated to `2000` chars by the normal context-block mechanism.

## Runtime Dogfood Check

Recorded one prompt-safe dogfood candidate:

```json
{
  "memory_type": "writing_pattern",
  "title": "章末保留下一步压力",
  "summary": "长篇续写章节结尾应保留下一步行动压力和未解决威胁，不要把追击、证物或身份线一次性解决。",
  "source_refs": [
    "chapter:24",
    "docs/superpowers/notes/long-memory-agent/2026-05-20-phase77-dogfood-pre-generation-route.md"
  ],
  "confidence": 0.82
}
```

Live Chapter 25 payload check:

- `knowledge_base_candidates` block present: `true`
- contains `章末保留下一步压力`: `true`
- contains `低细节续写需要先走 Agent 生成前路线`: `false`
- context block count: `11`
- max tokens: `3800`

This confirms prose prompts consume writing-pattern candidates but not Agent process lessons.

## Verification

RED before implementation:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_prompting_chapter_migration.py::test_chapter_payload_injects_only_prompt_safe_knowledge_candidates -q
```

Result before implementation: failed because `【知识库创作记忆】` was not in the chapter prompt.

Focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_prompting_chapter_migration.py::test_chapter_payload_injects_only_prompt_safe_knowledge_candidates -q
```

Result: `1 passed in 0.14s`.

Related prompt/preference regression:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_prompting_chapter_migration.py tests\test_preferences.py -q
```

Result: `19 passed in 1.43s`.

Broader related regression:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_prompting_chapter_migration.py tests\test_writing_agent_knowledge_base_route.py tests\test_preferences.py tests\test_writing_agent_runs.py -q
```

Result: `179 passed in 19.57s`.

Known baseline failure observed during broader static prompting check:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_prompting_chapter_migration.py tests\test_prompting_static_quality.py tests\test_preferences.py -q
```

Result: `31 passed, 2 failed`.

The two failures point to files not changed in this phase:

- `backend/app/api/outlines.py`: static contract expects `generate_outline`, scan now sees `expand_outline_window`.
- `backend/app/core/chapter_compression.py:554`: existing large inline prompt constant.

No Phase79 code touched those files. They should be handled separately if desired.

## Novel Progress

No new chapter was generated in this phase.

Live dogfood state:

- latest generated chapter: `24`
- latest title: `雾中栖身`
- next target: Chapter 25
- Knowledge Base candidates: `2`

## Fixed Issues

- Knowledge Base candidates were persisted but not consumed by chapter generation.
- Process lessons could have polluted prose prompts if all candidates were naively injected; the provider now excludes them.
- Prompt candidate injection now has type/status/confidence gates.

## Remaining Boundary

- Relevance is still rule-based, not semantic retrieval.
- Candidate approval UI does not exist yet.
- Candidate storage is still the `Project.style_config` bridge.
- The provider does not yet personalize candidate selection by chapter arc, character, or plot thread.

## Next Phase Recommendation

Phase80 should continue dogfood generation to Chapter 25 using this controlled candidate injection and then inspect whether the chapter actually reflects the writing-pattern memory without becoming over-constrained.
