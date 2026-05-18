# Phase 329: Show Prose Quality Diagnostics In Hermes

## Goal

Expose outline-like chapter warnings directly in the Hermes dashboard writing diagnostics summary.

## Scope

- Add frontend API typing for `generation_diagnostics.prose_quality`.
- Include outline-like chapter count in the "本轮诊断" summary.
- Show the affected chapter indexes as "大纲式章节".

## Verification

- RED confirmed:
  - `npm run test:unit -- --run src/components/shared/ProjectDashboard.test.ts`
  - Failed because the dashboard did not contain `大纲式 1`.
- GREEN confirmed:
  - `npm run test:unit -- --run src/components/shared/ProjectDashboard.test.ts`
  - `12 passed`
  - `npm run test:unit -- --run src/stores/project.workspace.test.ts`
  - `31 passed`
- Browser smoke:
  - Opened `http://127.0.0.1:5173/projects/b9d50481-6f5c-4f54-9b60-984c43e40808/hermes` with local Chrome through Playwright.
  - Confirmed dashboard content loaded and there were no non-favicon console errors or 4xx/5xx responses.

## Follow-Up

- Future quality diagnostics can reuse the same result/recommendation channel without adding new task polling endpoints.
