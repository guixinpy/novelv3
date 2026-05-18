# Longform Scale Phase 289 - Version Rollback Refresh Consistency

## Assumption

Chapter version rollback changes both chapter content and project-level word totals on the backend.

## Risk

If Hermes only refreshes version history and chapter content, dashboard totals can remain stale after rolling back a long chapter. In a million-word project, stale totals make progress and completion signals unreliable.

## Change

1. Add a version rollback refresh target helper that can return multiple targets.
2. Make chapter rollback refresh `project` with `content`.
3. Keep setup/storyline/outline rollback refreshes scoped to their own target.

## Verification

- Red: `npm run test:unit -- --run src/components/workspace/workspaceMeta.test.ts` failed because `getVersionRefreshTargets` did not exist.
- Green: the same targeted test passed after implementation.
- Full verification will run before commit.
