# Phase84 Plan: Revelation Strength and Video Signals

## Phase Goal

Turn two Chapter 26 dogfood findings into Agent-visible checks:

- warn when a chapter phrases major mystery evidence as final truth too early;
- extract Chapter 26-style high-value video, memory, parent, fog-disaster, and unknown-operator signals into Athena world-model proposals.

## Novel Work

Primary validation target remains `《雾港回声》` Chapter 26 `深处的回响`.

This phase does not generate Chapter 27 yet. It improves the review and world-model feedback loop before the next low-detail generation command.

## System Capability To Improve

1. `review_chapter_quality` should report a non-blocking `revelation_strength_overreach` warning when a chapter uses hard final-truth wording such as `不是天灾，是人祸` or `打开潘多拉魔盒的人` around unresolved core mysteries.
2. Athena chapter analysis should create high-priority proposal items for:
   - `historical_video_evidence`
   - `memory_erasure_hypothesis`
   - `parental_involvement_hypothesis`
   - `fog_disaster_cause_hypothesis`
   - `unknown_operator_intervention`
3. The review queue should classify those predicates as high risk.
4. The Agent's guarded high-value proposal draft tool should conservatively mark those predicates as uncertain instead of confirming them as world truth.

## Assumptions

- These signals are diagnostic and proposal-oriented. They should not directly rewrite Chapter 26 and should not become confirmed world facts without review.
- `revelation_strength_overreach` is a warning, not a blocker, because a chapter may intentionally use strong subjective realization while still requiring later verification.
- Extraction should stay deterministic and bounded. This phase should not add LLM extraction or broad NLP dependencies.

## Verification Level

Planned verification is T1/T2:

- TDD focused tests for quality review and Athena extraction.
- Related backend test slices for writing-agent tool runs, Athena longform analysis, and high-value proposal drafting.
- Runtime dogfood re-analysis of Chapter 26 to confirm the new signals appear and can be drafted through the Agent tool.

## Not Doing

- No Chapter 27 generation in this phase.
- No frontend changes.
- No external Agent architecture rewrite.
- No exact 2000-word hard constraint changes.
- No API key or secret persisted to disk.
