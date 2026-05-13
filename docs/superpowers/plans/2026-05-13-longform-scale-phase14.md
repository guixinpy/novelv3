# Longform Scale Phase 14 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the frontend continue loading paginated chapter summaries so 1000-chapter projects do not become inaccessible after the first bounded page.

**Architecture:** Keep the backend API unchanged and build on the existing `offset`/`limit` response metadata. Add one Pinia append action, then expose a small "loaded / total / load more" control in the manuscript chapter sidebar.

**Tech Stack:** Vue 3, Pinia, Vitest, TypeScript, existing project API client.

---

### Task 1: Store Append Action

**Files:**
- Modify: `frontend/src/stores/project.ts`
- Test: `frontend/src/stores/project.workspace.test.ts`

- [x] **Step 1: Write the failing test**

Add a test that starts with page 1 metadata, calls `loadMoreChapters('A')`, and expects:
- API called with `{ offset: current loaded count, limit: current page limit }`
- New chapter summaries appended, not replacing existing ones
- `chaptersTotal`, `chaptersOffset`, `chaptersLimit`, and `chaptersHasMore` updated from the second page response

- [x] **Step 2: Run test to verify it fails**

Run: `cd frontend; npm run test:unit -- src/stores/project.workspace.test.ts`

Expected: FAIL because `loadMoreChapters` does not exist.

- [x] **Step 3: Write minimal implementation**

Add `loadMoreChapters(id)` to the project store. It should no-op when `chaptersHasMore` is false, request the next page using the current loaded count as offset, append returned chapters, and expose the action from the store.

- [x] **Step 4: Run test to verify it passes**

Run: `cd frontend; npm run test:unit -- src/stores/project.workspace.test.ts`

Expected: PASS.

### Task 2: Manuscript Sidebar Load More

**Files:**
- Modify: `frontend/src/components/shared/ChapterList.vue`
- Modify: `frontend/src/views/ManuscriptView.vue`
- Test: `frontend/src/views/ManuscriptView.test.ts`

- [x] **Step 1: Write the failing test**

Add a view test where `listChapters` first returns 200 of 250 chapters and then returns the next 50. Assert the sidebar shows `已加载 200 / 250 章`, clicking `加载更多章节` calls the next page, and the rendered chapter options grow to 250.

- [x] **Step 2: Run test to verify it fails**

Run: `cd frontend; npm run test:unit -- src/views/ManuscriptView.test.ts`

Expected: FAIL because the sidebar has no pagination footer or load-more control.

- [x] **Step 3: Write minimal implementation**

Extend `ChapterList` with optional `total`, `hasMore`, and `loadingMore` props plus a `load-more` event. In `ManuscriptView`, compute metadata from the project store and call `project.loadMoreChapters(pid)` from the sidebar button.

- [x] **Step 4: Run test to verify it passes**

Run: `cd frontend; npm run test:unit -- src/views/ManuscriptView.test.ts`

Expected: PASS.

### Task 3: Verification And Commit

**Files:**
- Verify all files changed in Tasks 1-2.

- [x] **Step 1: Run focused frontend tests**

Run:
- `cd frontend; npm run test:unit -- src/stores/project.workspace.test.ts src/views/ManuscriptView.test.ts`

Expected: PASS.

- [x] **Step 2: Run frontend build**

Run:
- `cd frontend; npm run build`

Expected: PASS.

- [x] **Step 3: Run full verification**

Run:
- backend full test suite
- frontend full unit tests
- frontend build
- `git diff --check`
- exact DeepSeek key scan
- broad secret scan

Expected: all pass; exact key absent; broad scan only contains existing fake sanitizer fixtures.

- [x] **Step 4: Commit**

Commit message: `feat: append paginated chapter summaries`
