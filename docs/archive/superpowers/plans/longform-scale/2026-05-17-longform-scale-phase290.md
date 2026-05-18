# Longform Scale Phase 290 - Forced Refresh After Revision Regeneration

## Assumption

Chapter revision regeneration mutates chapter content, project word count, version history, and writing-state progress through the same chapter generation path.

## Risk

`refreshTargets()` was expected to refresh mutated targets, but several loaders still honored the fresh-cache guard. After a quick user action, project totals and version history could stay stale until the cache TTL expired.

## Change

1. After revision regeneration, Hermes refreshes `project`, `content`, `versions`, and `writing_state`.
2. `project.refreshTargets()` now forces loaders for project/setup/storyline/outline/topology/versions/preferences instead of relying on cached values.
3. Normal lazy panel loading still keeps cache behavior.

## Verification

- Red: `npm run test:unit -- --run src/views/HermesView.test.ts` failed because `api.getProject` was never called after revision regeneration.
- Green: `npm run test:unit -- --run src/views/HermesView.test.ts src/stores/project.workspace.test.ts` passed.
- Full verification will run before commit.
