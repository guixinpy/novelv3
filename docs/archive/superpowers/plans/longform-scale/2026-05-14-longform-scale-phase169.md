# Longform Scale Phase 169 - Catalog Projection Load Narrowing

## Problem

Opening Athena Catalog loaded both ontology and the full world-model projection.
The ontology endpoint is already bounded, but the projection path can aggregate all facts and events for the project. For thousand-chapter novels, that makes a simple setting-library visit unnecessarily expensive.

## Change

- Catalog route loading now requests ontology only.
- Existing projection data is still passed into `CatalogWorkbench` if already available from another view.
- Truth projection and knowledge views still load world-model projection explicitly.
- Retrieval diagnostics still load when the Catalog retrieval tool is active.

## Tests

Red failure confirmed before implementation:

- `athenaSectionLoader` still called `worldModel.loadOverview(projectId)` for Catalog.

Verification after implementation:

- `npm run test:unit -- athenaSectionLoader CatalogWorkbench`
- `npm run test:unit`
- `npx vue-tsc --noEmit`
- `npm run build`

## Result

Catalog no longer forces a full projection load on entry. This keeps the setting-library path bounded by ontology pagination while preserving richer detail when projection data is already in store.
