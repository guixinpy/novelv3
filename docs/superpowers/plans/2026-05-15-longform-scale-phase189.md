# Phase 189 - Respect Partial Setup Generated Status

## Problem

Hermes overview now avoids eager full setup hydration and relies on bootstrap
summaries. The bootstrap setup payload intentionally omits large JSON fields, so
`ProjectDashboard` saw empty setup arrays/objects and displayed the generated
setup as `待完善`.

## Change

- Added a Dashboard regression test for partial generated setup payloads.
- Updated setup stage status to treat `setup.status === "generated"` as
  generated even when large setup fields are omitted from bootstrap.
- Kept detailed field counts unchanged for full setup payloads.

## Tests

- RED: `npm run test:unit -- src/components/shared/ProjectDashboard.test.ts -t "uses generated setup status"`
- GREEN: `npm run test:unit -- src/components/shared/ProjectDashboard.test.ts -t "uses generated setup status"`
- GREEN: `npm run test:unit -- src/components/shared/ProjectDashboard.test.ts src/stores/project.workspace.test.ts`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` (`593 passed`)
- GREEN: `npm run test:unit` from `frontend` (`403 passed`)
- GREEN: `npm run build` from `frontend`
- GREEN: `git diff --check`
- GREEN: DeepSeek key scan returned `NO_MATCH`

## Result

Hermes overview can now stay on bounded bootstrap summaries without misleading
the user that a generated setup is incomplete solely because large setup fields
were intentionally omitted from cold-start payloads.
