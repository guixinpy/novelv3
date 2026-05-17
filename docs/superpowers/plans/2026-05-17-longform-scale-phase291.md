# Longform Scale Phase 291 - Manuscript Entry Reloads Active Chapter

## Assumption

After submitting a chapter revision, the user often returns to the manuscript editor to inspect the regenerated result.

## Risk

The manuscript store keeps a short-lived chapter cache. Re-entering the manuscript page for the same project and same remembered chapter could reuse stale chapter content after Hermes regenerated the chapter.

## Change

1. Manuscript page initialization still restores the remembered chapter.
2. The initial chapter selection now forces `loadChapter()`.
3. Sidebar chapter switching keeps `ensureChapter()` cache behavior.

## Verification

- Red: `npm run test:unit -- --run src/views/ManuscriptView.test.ts` failed because remounting did not fetch the remembered chapter again.
- Green: `npm run test:unit -- --run src/views/ManuscriptView.test.ts src/stores/manuscript.test.ts` passed.
- Full verification will run before commit.
