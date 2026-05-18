# Phase 331: Show Prose Quality Warnings In Trace Drawer

## Goal

Make single-generation prose quality warnings visible in the model trace drawer without requiring users to inspect raw JSON metadata.

## Scope

- Parse `trace_metadata.chapter_prose_quality`.
- Render an additional "正文质量" diagnostic card when output is `outline_like`.
- Show the outline marker density and warning message in Chinese.

## Verification

- RED confirmed:
  - `npm run test:unit -- --run src/components/modelTrace/ModelTraceDrawer.test.ts`
  - Failed because the longform diagnostics section did not contain `正文质量`.
- GREEN confirmed:
  - `npm run test:unit -- --run src/components/modelTrace/ModelTraceDrawer.test.ts`
  - `9 passed`
  - `npm run test:unit -- --run src/stores/modelTraces.test.ts`
  - `6 passed`
- Browser smoke:
  - Opened Hermes with local Chrome through Playwright.
  - Confirmed dashboard content loaded and there were no non-favicon console errors or 4xx/5xx responses.

## Follow-Up

- If more generation quality checks are added, keep them in the same structured trace diagnostics section rather than adding more raw JSON-only fields.
