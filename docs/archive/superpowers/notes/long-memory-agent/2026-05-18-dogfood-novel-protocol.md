# Longform Dogfood Novel Protocol

## Purpose

Use a real longform novel as the main pressure source for the long-memory writing Agent goal. The dogfood novel must reveal failures in prose generation, long-term continuity, memory recall, world model governance, review loops, task queue behavior, and front-end scale.

This protocol is not a benchmark-only fixture. It is the operating loop for discovering what novelv3 must become.

## Novel Target

- Working title: `《雾港回声》`
- Genre: 都市悬疑 + 轻科幻 + 群像成长
- Long-term target: 600 chapters minimum, designed so the same system can later extend to 1000 chapters.
- Initial arc target: 30 chapters before the first major architecture checkpoint.
- Chapter length target: each generated chapter must contain at least 2000 Chinese characters of prose-like正文, not outline summaries.
- Originality boundary: this is an original dogfood novel. Reference projects and拆书 results may inform structure and review criteria, but must not provide copied plot or prose.

## Chapter Standard

Each chapter must satisfy:

- At least 2000 Chinese characters.
- Scene-based narrative prose, not bullet outlines or synopsis paragraphs.
- Clear point-of-view control for the current scene.
- A concrete scene goal, conflict, and consequence.
- At least one continuity link to prior chapters after chapter 2.
- At least one future-facing hook unless the chapter closes an arc.
- No unexplained contradiction against confirmed world facts.
- Generated content must be stored in the project, indexed for retrieval, and eligible for world model extraction.

## Generation Loop

For each batch:

1. Agent reviews current project state, latest chapters, world model, retrieval diagnostics, and longform memory diagnostics.
2. Agent selects the next writing task: setup, outline repair, chapter generation, revision, or memory maintenance.
3. Hermes/chapter generation produces prose for the next chapter or batch.
4. Generated content is saved as chapter content.
5. Retrieval index and longform memory are updated.
6. Athena/world model extraction proposes new facts through proposal flow rather than direct truth mutation.
7. Trace/context evidence is recorded so failures can be debugged.

Initial batch size should be conservative:

- Phase 2: 1 chapter.
- Early stable loop: 3 to 5 chapters.
- Later queue validation: 10+ chapter batches.

## Review Loop

Every generated chapter must be reviewed from at least three perspectives:

- Continuity editor: checks facts, timeline, character knowledge, unresolved hooks, and contradiction risk.
- Prose editor: checks whether the chapter is actual narrative prose, not outline-like output.
- Reader/commercial editor: checks tension, pacing, hook strength, emotional payoff, and chapter-end drive.

Review results must be written into phase notes. Later phases should convert repeatable review criteria into automated review tools.

## Memory / World Model Loop

After each chapter or batch:

- Confirm retrieval can recall important prior events.
- Confirm longform memory layers update when enough chapters exist.
- Confirm world model candidates are proposed, reviewed, and traceable.
- Keep user/project/reference-pattern memory separate from world truth.
- If a user preference or stable writing rule emerges, record it as knowledge-base candidate rather than prompt-only text.

## Metrics

Track these in every phase report:

| Metric | Target |
| --- | --- |
| Generated chapters | Monotonic increase |
| Chapter character count | `>= 2000` |
| Outline-like chapters | `0` accepted |
| Continuity issues | Recorded and triaged |
| World model proposal lag | Recorded after each batch |
| Retrieval misses | Recorded with query examples |
| Review findings converted to fixes | Increasing over time |
| Frontend friction | Recorded from real use |
| Task failures | Must include recoverability notes |

## Stop Conditions

Pause generation and fix the system when:

- A chapter is saved as outline-like content.
- The system cannot retrieve major facts from prior chapters.
- World model proposals are not generated or cannot be reviewed.
- A task failure leaves unclear state or cannot be resumed.
- The UI makes it impractical to inspect, navigate, or review the current chapter set.
- The Agent cannot explain what context it used for a generation or review decision.

## Phase 2 Starting Task

Phase 2 should create or select the actual dogfood project, verify runtime model configuration without writing secrets to disk, and generate the first real 2000+ character chapter through the application path.

Phase 2 should use T1/T2 verification:

- Targeted backend/API or UI checks for the exact generation path used.
- Browser verification if the frontend path is used.
- No full backend/frontend suite unless Phase 2 changes shared runtime code.
