# Phase117 Dialog Chapter Prepare Dispatch Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development. This phase changes only the dialog pending-action control plane for chapter generation.

**Goal:** When a user confirms a dialog chapter-generation pending action, dispatch the Agent prepare step instead of directly writing the chapter.

**Architecture:** Keep `preview_chapter -> generate_chapter` as the public action type so existing UI hints and pending-action routing remain stable. Internally, `dialog_control_plane` maps confirmed `generate_chapter` actions to `prepare_generate_chapter_execution`, and `ActionResultService` records `approval_required` as a non-failure terminal result. The second explicit execute confirmation remains a later phase.

**Tech Stack:** Python, pytest, existing dialog pending-action control plane and Writing Agent runner.

---

## Assumptions

- Phase116 already made dialog intent planning prefer `prepare_generate_chapter_execution`.
- Existing pending-action route metadata can remain `generate_chapter` for compatibility.
- `prepare_generate_chapter_execution` is read-only and returns an approval contract without manuscript side effects.

## Scope

1. Update dialog control plane dispatch for `generate_chapter` so it creates a `prepare_generate_chapter_execution` tool request.
2. Preserve action type as `generate_chapter` in task payload and action result.
3. Preserve command args in the run input for traceability, even though prepare does not consume them yet.
4. Let background completion preserve `approval_required` from the prepare output.
5. Teach `ActionResultService.record_completion` to record `approval_required` as a meaningful system message instead of a failure.
6. Add tests proving:
   - confirmed chapter pending action dispatches `prepare_generate_chapter_execution`;
   - background work records `approval_required` and does not claim chapter success;
   - setup pending-action dispatch still uses `generate_setup`;
   - direct chapter API generation is unchanged.

## Out Of Scope

- Creating the second pending action for `execute_generate_chapter_with_approval`.
- Changing frontend approval UX.
- Changing slash command preview route metadata.
- Changing chapter API or continuous writing endpoints.
- Migrating longform batch generation.
- Generating novel chapters.

## Verification Plan

- T0 RED:
  - Add dialog control plane tests expecting chapter dispatch to use `prepare_generate_chapter_execution`; verify they fail while code still uses `generate_chapter`.
- T0 GREEN:
  - Implement the dispatch mapping and approval-required recording.
- T1:
  - dialog tests for pending-action control plane;
  - writing agent execution tests for approved direct chapter generation;
  - chapter API generation subset.
- Hygiene:
  - `git diff --check`;
  - secret scan over `backend` and active `docs`.

## Success Criteria

- Confirming a chapter pending action creates a Writing Agent run whose first tool is `prepare_generate_chapter_execution`.
- The corresponding background task still says `action_type == "generate_chapter"` for UI compatibility.
- Completion message/action_result status is `approval_required`, not `success` and not generic failure.
- No direct manuscript write happens in this dialog confirmation phase.
