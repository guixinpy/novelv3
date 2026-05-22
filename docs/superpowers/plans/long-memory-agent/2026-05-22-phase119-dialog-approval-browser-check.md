# Phase119 Dialog Approval Browser Check Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use browser/playwright verification before changing frontend behavior.

**Goal:** Verify the dialog chapter approval flow in a real browser and fix immediate backend/frontend gaps found by the flow.

**Architecture:** Use the running local backend/frontend. Seed or reuse a small project with setup/storyline/outline, then drive Hermes through the browser: request a chapter, confirm prepare, observe approval-required pending action, confirm execute, and record whether the UI state is coherent.

**Tech Stack:** FastAPI, Vue/Vite, agent-browser or Playwright CLI, pytest/vitest only if code changes are needed.

---

## Scope

1. Start or reuse local servers on `127.0.0.1:8000` and `127.0.0.1:5173`.
2. Create a small browser-test project if needed.
3. Drive Hermes dialog through:
   - text request for chapter generation;
   - first confirmation;
   - approval-required state;
   - second confirmation.
4. Record visible UX/API gaps.
5. Fix only narrow issues that block the flow.

## Out Of Scope

- Full visual redesign.
- Long chapter generation quality work.
- Large frontend component refactor.
- Longform batch approval flow.

## Verification Plan

- Browser:
  - open Hermes project route;
  - snapshot visible state after each step;
  - check console/page errors if possible.
- Backend:
  - rerun dialog tests if backend fixes are needed.
- Frontend:
  - run focused vitest/build only if frontend code changes.

## Success Criteria

- The first confirmation does not write a chapter immediately.
- The UI exposes a second pending action after approval prepare.
- The second confirmation dispatches the execute path or produces a clear blocked/failed result.
- Any remaining UX gaps are recorded in the phase report.
