# Phase39 Report: Agent Constraint Orchestration

## Summary

Phase39 was corrected from "continue writing Chapter 24 with detailed operator prompts" to "make the Writing Agent assemble its own chapter constraints." The correction is important because the long-term goal is a writing Agent with autonomous tool orchestration, not a workflow where the user must manually provide chapter-level continuity constraints.

User guidance added during this phase:

- Most users will not provide detailed chapter constraints.
- Users usually provide ideas, worldviews, character concepts, and high-level feedback.
- The Agent must autonomously plan, retrieve context, apply world-model constraints, generate, review, revise, and record lessons.
- Real chapter generation is a diagnostic pressure test, not the goal's center of gravity.
- The most important engineering direction is upgrading the project into an Agent system by making existing modules tool-like and callable by the Agent.
- Future phases should study `references/agent-projects/openclaw`, `references/agent-projects/hermes-agent`, and `references/agent-projects/openhuman` with emphasis on tool registration, tool contracts, planning/execution loops, memory, failure handling, and Trace/audit design.

The global goal spec was updated with this principle in `docs/superpowers/specs/2026-05-18-long-memory-writing-agent-goal.md`.

## Failure Evidence

The first Phase39 outline expansion relied on a long external `command_args` paragraph. Even with that manual steering, Chapter 24 outline still contained unsafe or incorrect elements:

- "左臂内侧似乎是 N-07"
- `G-07` treated as a lower-city lab area
- special fog crystal purchased to open access controls

This showed that the system did not yet have a reliable Agent-side constraint chain. The old flow was too dependent on user/operator prompt detail.

## Implementation

Added `backend/app/core/writing_agent_constraints.py`.

The new Agent constraint package is built from existing project state:

- previous chapter ending state;
- current story milestone window;
- recent action leads such as `G-07`, `EV-2045-0812-07`, and `E-0047`;
- unresolved foreshadowing and planned resolution distance;
- limiting world facts, such as `N-07` being a confirmed-limited identifier whose concrete subject remains unresolved.

Injected the constraint block into:

- chapter generation via `backend/app/prompting/providers/chapter.py`;
- rolling outline expansion via `backend/app/api/outlines.py`.

The block is included in model prompt content and Trace context blocks as `agent_chapter_constraints`.

## Chapter 24 Diagnostic Result

After removing the unsafe Chapter 24 outline and re-expanding with no long manual `command_args`, the first new result no longer hard-confirmed `N-07`, but drifted into a black-clinic/old-record route. This revealed that the Agent also needed to preserve recent action leads, not only unresolved foreshadowing.

After adding recent action lead extraction and original-context constraints, Chapter 24 outline improved:

- title: `雾中栖身`
- preserved temporary shelter and Su Wanqing's fever;
- preserved pursuit/scanning pressure;
- connected `G-07` and `EV-2045-0812-07` as evidence-direction leads;
- did not confirm `N-07`;
- did not introduce the earlier lower-city-lab-area shortcut;
- did not introduce the old-record/clinic shortcut;
- did not open the second iris door or enter a core database.

Latest accepted正文 remains Chapter 23. Phase39 did not generate Chapter 24正文.

## Current State

- latest accepted chapter: `23`
- latest accepted title: `暗渠追兵`
- outline chapter count: `24`
- Chapter 24 outline: `雾中栖身`
- pending world proposals: `0`
- longform maintenance: `current`
- latest synced longform chapter index: `23`
- retrieval documents/chunks: `82 / 159`
- `陆辞` query returned vector-only unrelated results (`lexical_score=0.0`), not confirmed text contamination.

## Verification

Targeted tests:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_prompting_chapter_migration.py tests\test_outlines.py::test_expand_outline_window_appends_missing_chapters_without_overwriting_existing tests\test_outlines.py::test_expand_outline_window_injects_agent_constraints_without_manual_command_args -q
```

Result: `15 passed`

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "premature_mystery_reveal or review_chapter_quality or review_chapter_continuity or event_summary"
```

Result: `21 passed, 90 deselected`

## Commit And Push

- implementation commit: `e33823c feat: add agent chapter constraints`
- remote: pushed to `origin/main`

## Remaining Risks

- The Agent constraint package is still a first-stage capability, not a full autonomous writing Agent.
- Recent action lead extraction is lexical and should later become more semantic, using retrieval and world model facts together.
- Outline expansion can now receive constraints, but it does not yet automatically loop through self-review and repair.
- The Agent still lacks a high-level planner that can decide "expand outline -> preflight -> generate -> review -> revise -> proposal resolution -> memory/retrieval sync" without a manually supplied tool list.

## Next Phase Recommendation

Phase40 should build the next layer of autonomy: Agent toolization and an Agent run planner that can choose a safe tool chain from a high-level goal such as "continue writing the next chapter" with minimal user detail.

Recommended scope:

- read and summarize the three reference Agent projects with a focus on tool contracts and orchestration patterns;
- map current novelv3 modules into a first Agent tool registry;
- define standard tool input/output/error/trace contracts;
- derive next writing task from project state;
- assemble constraints;
- expand missing outline if needed;
- run preflight;
- generate chapter;
- run quality/continuity review;
- stop for revision or proposal handling when needed;
- record Trace evidence for every decision.
