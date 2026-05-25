# Phase 18 Report: Continuity State Card and Drift Gates

## Summary

Phase18 converted Chapter 6 dogfood findings into deterministic Agent gates.

The Writing Agent now exposes a previous-chapter state card during `preflight_writing` and appends the same continuity card to `generate_chapter` command arguments when a previous chapter exists. Chapter quality review now flags three high-value longform risks:

- character profile drift;
- ability-boundary drift;
- too-convenient key item acquisition.

This phase intentionally did not force Chapter 7 generation because the new Chapter 6 review gates found blocker-level continuity issues.

## Code Changes

- `backend/app/services/writing_agent/run_service.py`
  - Added `previous_chapter_state_card` to preflight checks.
  - Added `agent_continuity_feedback` for `generate_chapter` tool calls.
  - Preserved existing user command args and Phase17 length feedback order.
- `backend/app/core/chapter_quality_review.py`
  - Added deterministic setup-aware profile drift findings.
  - Added deterministic setup-rule-aware ability boundary findings.
  - Added warning for key item acquisition without local cost/risk language.
  - Routed blocker drift findings into `revise_chapter` recommendations.
- `backend/tests/test_writing_agent_runs.py`
  - Added RED/GREEN coverage for preflight state card, generation context injection, profile drift, ability drift, and convenience review.

## TDD Evidence

RED command:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_preflight_reports_previous_chapter_state_card tests\test_writing_agent_runs.py::test_agent_generate_chapter_appends_previous_state_card tests\test_writing_agent_runs.py::test_agent_review_chapter_quality_flags_character_profile_drift tests\test_writing_agent_runs.py::test_agent_review_chapter_quality_flags_ability_boundary_drift tests\test_writing_agent_runs.py::test_agent_review_chapter_quality_warns_on_convenient_key_item_acquisition -q
```

Initial result: `5 failed`.

Failure reasons:

- `previous_chapter_state_card` missing from preflight checks.
- chapter command args did not include `上一章状态卡`.
- review findings did not include `character_profile_drift`.
- review findings did not include `ability_boundary_drift`.
- review findings did not include `convenient_key_item_acquisition`.

GREEN command:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_preflight_reports_previous_chapter_state_card tests\test_writing_agent_runs.py::test_agent_generate_chapter_appends_previous_state_card tests\test_writing_agent_runs.py::test_agent_review_chapter_quality_flags_character_profile_drift tests\test_writing_agent_runs.py::test_agent_review_chapter_quality_flags_ability_boundary_drift tests\test_writing_agent_runs.py::test_agent_review_chapter_quality_warns_on_convenient_key_item_acquisition -q
```

Result: `5 passed in 0.49s`.

Focused regression:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_review_chapter_quality_flags_generic_title_and_length tests\test_writing_agent_runs.py::test_agent_review_chapter_quality_warns_on_modest_over_target_length tests\test_writing_agent_runs.py::test_agent_review_chapter_quality_flags_future_outline_overlap tests\test_writing_agent_runs.py::test_agent_review_chapter_quality_ignores_single_future_character_name_match -q
```

Result: `4 passed in 0.36s`.

T2 verification:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_world_proposals.py -q
```

Result: `124 passed in 13.49s`.

## Dogfood: Chapter 6 Review Gate

Project: `25fa2b20-5b9f-473b-918b-f4ea491cbb60`

Run id: `5351250e-21c3-4146-a904-3d0f312f3601`

Tool: `review_chapter_quality`, Chapter 6.

Result:

- status: `blocked`
- finding count: `2`
- blocker count: `2`
- recommended actions: `revise_chapter`

Findings:

- `character_profile_drift`: `叶知秋` was described as formerly a `雾安局` researcher, conflicting with the established profile of a neuro-science professor who participated in a secret project and later left.
- `ability_boundary_drift`: Chapter 6 used `制造幻觉`, conflicting with existing world-rule boundaries around fog crystal and memory phenomena.

This confirms the new deterministic gates caught the main issues identified by the Phase17 subagent review.

## Dogfood: Chapter 7 Preflight

Run id: `e2597a59-226e-428a-b8da-3059ed3340a0`

Tool: `preflight_writing`, Chapter 7.

Result:

- status: `ready`
- previous chapter: ready, Chapter 6 `黑市雾晶`
- `previous_chapter_state_card`: ready
- length policy: `review_required`, reason `repeated_over_target`
- retrieval: ready, `25` documents and `47` chunks

State card excerpt correctly preserved Chapter 6 ending context:

- `叶知秋`
- `记忆雾晶`
- `谁的记忆`
- `记忆即牢笼，真相即回声`

## Chapter 7 Decision

Chapter 7 was not generated in Phase18.

Reason: Chapter 6 review is now blocker-level because profile drift and ability-boundary drift remain unresolved. Continuing generation would propagate known bad continuity into the longform sample. This is a successful gate, not a generation failure.

Current project state after Phase18 dogfood:

- generated chapters: `6`
- pending world proposal items: `0`
- proposal reviews: `47`
- world fact claims: `0`

## Remaining Issues

- The new checks are deterministic and conservative. They catch explicit drift, not subtle semantic drift.
- `叶知秋` gender drift is indirectly caught through profile drift, but a stronger gender/pronoun check should be added later.
- The convenience gate is covered by tests but did not trigger in Chapter 6 because blocker drift already dominated review. It should be observed again after the Chapter 6 revision pass.
- World fact claims remain `0`, so later generation still lacks approved durable truth facts.
- The state card currently uses a compact excerpt and fixed keyword list; later phases should upgrade it into a richer structured state card: location, held items, unresolved hooks, emotional state, and next action.

## Next Phase Recommendation

Phase19 should revise or patch Chapter 6 before continuing generation:

- Create a revision plan for Chapter 6 from the new review findings.
- Produce a revision draft or safe patch that fixes `叶知秋` identity, `苏晚晴` ability boundary, and fog crystal distinction.
- Re-review Chapter 6 until blocker count is 0.
- Only then generate Chapter 7 with the state card and Phase17 length feedback active.

This preserves the goal-loop discipline: generate, review, fix the system and content, then continue.
