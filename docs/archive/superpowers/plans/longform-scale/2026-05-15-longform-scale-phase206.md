# Phase 206 - Fix Chapter Window Pagination

## Problem

The frontend project store can load a bounded chapter window around a selected
chapter, for example chapters 801-850 in a thousand-chapter project. However,
`loadMoreChapters()` calculated the next request offset from
`chapters.length`.

For non-zero windows this caused the next page request to jump backwards. A
window loaded at offset 800 with 50 chapters requested offset 50 instead of 850.

## Change

- Added a frontend regression test for `loadMoreChapters()` after a non-zero
  chapter window.
- Added an internal `chaptersWindowStartOffset` to preserve the first loaded
  window offset.
- `loadMoreChapters()` now requests
  `chaptersWindowStartOffset + chapters.length`.
- Existing public chapter pagination metadata remains unchanged.

## Tests

- RED: `npm run test:unit -- src/stores/project.workspace.test.ts -t "非零章节窗口"`
  - failed because the request used `offset: 50` instead of `offset: 850`.
- GREEN: `npm run test:unit -- src/stores/project.workspace.test.ts -t "非零章节窗口"` (`1 passed`)
- GREEN: `npm run test:unit -- src/stores/project.workspace.test.ts src/views/ManuscriptView.test.ts src/views/AthenaView.test.ts` (`36 passed`)
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` (`607 passed`)
- GREEN: `npm run build` from `frontend`
- GREEN: `npm run test:unit` from `frontend` (`408 passed`)
- GREEN: `git diff --check`
- GREEN: DeepSeek key scan returned `NO_MATCH`

## Result

Chapter list pagination now continues from the loaded window tail. This keeps
large-project navigation stable when a user jumps directly into late chapters
and then scrolls forward.
