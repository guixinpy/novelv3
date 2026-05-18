# Phase 188 - Avoid Eager Hermes Optional Hydration

## Problem

Workspace bootstrap already returns partial setup/storyline/outline summaries,
but Hermes initialization still used completed diagnosis items to immediately
hydrate full optional resources. On thousand-chapter projects that can turn a
cold overview load into full setup, storyline, and outline JSON requests.

## Change

- Updated the hydration regression test to require no eager optional target
  loads on initial Hermes overview.
- Changed `getInitialProjectHydrationTargets` to return no optional resources.
- Kept panel switching behavior intact: completed optional panels still hydrate
  when the user navigates to that panel.

## Tests

- RED: `npm run test:unit -- src/stores/project.workspace.test.ts -t "Hermes 初始水合不自动加载完整可选资源"`
- GREEN: `npm run test:unit -- src/stores/project.workspace.test.ts -t "Hermes 初始水合不自动加载完整可选资源"`
- GREEN: `npm run test:unit -- src/stores/project.workspace.test.ts src/views/AthenaView.test.ts src/components/shared/ProjectDashboard.test.ts`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` (`593 passed`)
- GREEN: `npm run test:unit` from `frontend` (`402 passed`)
- GREEN: `npm run build` from `frontend`
- GREEN: `git diff --check`
- GREEN: DeepSeek key scan returned `NO_MATCH`

## Result

Hermes cold start now uses bootstrap summaries for overview instead of
immediately requesting full setup/storyline/outline payloads. This preserves the
bounded bootstrap path for long projects and defers large optional reads until a
user navigates to the corresponding panel.
