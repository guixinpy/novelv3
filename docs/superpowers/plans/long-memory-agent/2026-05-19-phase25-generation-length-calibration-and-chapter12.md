# Phase 25 Generation Length Calibration and Chapter 12 Plan

## Context

Phase24 completed Chapter 11 inside the 2000-2300 word target, but the Writing Agent still reported a repeated length drift warning because early over-target chapters remain in the historical diagnostics window.

The current behavior is too blunt for long-running writing:

- Historical debt from earlier chapters can keep triggering "recent chapters are too long".
- Generation feedback may over-correct even after several recent chapters are already within target.
- Preflight warnings do not clearly separate recent generation risk from old cleanup debt.

## Goal

Improve chapter-generation length calibration so future chapters react to recent drift instead of stale historical debt, then continue the dogfood novel to Chapter 12.

## Scope

1. Split recent length drift from historical length debt.
2. Keep strict revision decisions when the current generated chapter is out of range.
3. Make generation prompt feedback active only when recent chapters show repeated drift.
4. Keep historical over/under target chapters visible as cleanup debt, but do not label them as recent drift.
5. Generate, review, and world-model-analyze Chapter 12 after the calibration fix.

Out of scope:

- Compressing old over-target Chapters 1-3 and 5.
- Changing project word target defaults.
- Reworking longform memory diagnostics UI.

## Assumptions

- The target chapter range remains 2000-2300 words for this dogfood project.
- A recent-window signal is enough for generation-time feedback; old chapter debt should be handled by a separate cleanup phase.
- Current-chapter over/under decisions must still be conservative and may require policy review when recent drift exists.

## Implementation Plan

1. Add tests proving historical over-target debt does not trigger generation feedback when recent chapters are within target.
2. Add tests proving recent repeated over/under target chapters still trigger feedback.
3. Implement a small recent-window length policy in `run_service.py`.
4. Preserve the existing chapter-length decision output shape where possible.
5. Run targeted backend tests.
6. Generate Chapter 12, then run review, world-model analysis, and proposal resolution if needed.
7. Write Phase25 report with code evidence, dogfood evidence, and next-stage recommendation.

## Verification Strategy

- T0: `git diff --check` and targeted secret scan.
- T1: targeted pytest for length-policy and generation-feedback behavior.
- T2: `backend/tests/test_writing_agent_runs.py` plus world proposal regressions if world-model proposal handling is touched.
- Dogfood: Chapter 12 preflight, generation, quality review, world-model analysis, and pending-proposal count check.

Full T3 verification is not planned for this phase because the change is localized and Phase24 recently ran the relevant backend suite.

## Success Criteria

- Historical length debt is visible but no longer misrepresented as recent drift.
- Clean recent chapters do not receive repeated-over-target generation feedback.
- Recent repeated drift still triggers explicit calibration feedback.
- Chapter 12 is generated at or repaired into the 2000-2300 target range.
- Chapter 12 review has no blocker findings and actionable world-model proposals are resolved or explicitly documented.
