# Longform Scale Phase 171 - Consistency Issue Frontend Pagination

## Problem

The consistency issues backend already returns paginated responses, but the Athena frontend flattened the response into a plain issue array.
As a result, long-running projects with many saved consistency issues had no UI path to load beyond the first page or display how much history existed.

## Change

- Athena store now records consistency issue pagination metadata:
  - total
  - offset
  - limit
  - has more
  - loading-more state
- Added `loadMoreConsistencyIssues(projectId)` to append the next page.
- First-page loading now requests a bounded page explicitly.
- `ConsistencyList` shows `已显示 X / Y` when more issue history exists.
- `ConsistencyList` emits `loadMore`, and `AthenaView` connects it to the store.

## Tests

Red failures confirmed before implementation:

- Store test failed because `loadMoreConsistencyIssues` did not exist.
- Component test failed because the list had no pagination footer.

Verification after implementation:

- `npm run test:unit -- athena.scope ConsistencyList AthenaView`
- `npm run test:unit`
- `npx vue-tsc --noEmit`
- `npm run build`

## Result

Athena consistency review can now page through large issue histories instead of silently truncating to the first backend page.
