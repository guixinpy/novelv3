# Phase 193 - Bound Frontend Athena Ontology Loads

## Problem

The Athena ontology backend already supports bounded entity, relation, and rule
windows, but the frontend API client could not pass those parameters. Normal
`loadOntology()` and Athena chat `ontology` refreshes therefore used the backend's
larger defaults whenever the user opened or refreshed the setup library.

## Change

- Added an `AthenaOntologyQuery` frontend type and query serialization.
- Updated `api.getAthenaOntology()` to accept ontology window parameters.
- Added a shared frontend default ontology window:
  - entities: 120 per entity bucket
  - relations: 160
  - rules: 120
- Routed `loadOntology()`, chat-triggered ontology refresh, and setup import
  refresh through that bounded query.

## Tests

- RED: `npm run test:unit -- src/api/client.worldModel.test.ts src/stores/athena.scope.test.ts src/stores/athena.chat.test.ts`
- GREEN: `npm run test:unit -- src/api/client.worldModel.test.ts src/stores/athena.scope.test.ts src/stores/athena.chat.test.ts src/stores/athena.proposals.test.ts`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` (`597 passed`)
- GREEN: `npm run build` from `frontend`
- GREEN: `npm run test:unit` from `frontend` (`407 passed`)
- GREEN: `git diff --check`
- GREEN: DeepSeek key scan returned `NO_MATCH`

## Result

Frontend Athena ontology loads now use explicit bounded windows on high-frequency
paths. This keeps longform setup browsing and chat-triggered setup refreshes from
pulling unnecessarily wide ontology payloads by default.
