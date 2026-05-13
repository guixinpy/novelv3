# Frontend Redesign Plan C: Cleanup

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove all old components, styles, and store complexity that were superseded by the new UI system.

**Architecture:** Systematic deletion of ~40 old files, CSS cleanup, store simplification, and test pruning. Each task deletes a logical group, verifies no broken imports, and commits.

**Tech Stack:** Vue 3, TypeScript, Vitest

---

### Task 1: Delete Old View Files

Old views replaced by new ones in Plan B.

**Delete:**
- `frontend/src/views/ProjectList.vue` (replaced by `ProjectListView.vue`)
- `frontend/src/views/ProjectDetail.vue` (replaced by `HermesView.vue`)
- `frontend/src/views/ManuscriptPlaceholder.vue` (replaced by `ManuscriptView.vue`)

- [ ] **Step 1:** `git rm frontend/src/views/ProjectList.vue frontend/src/views/ProjectDetail.vue frontend/src/views/ManuscriptPlaceholder.vue`
- [ ] **Step 2:** Verify no remaining imports: `grep -rn 'ProjectList\|ProjectDetail\|ManuscriptPlaceholder' frontend/src/ --include='*.ts' --include='*.vue'` — should return nothing (ignore test files deleted later)
- [ ] **Step 3:** `cd frontend && npx vue-tsc --noEmit` — zero errors
- [ ] **Step 4:** Commit: `git commit -m "chore: delete old view files (ProjectList, ProjectDetail, ManuscriptPlaceholder)"`

---

### Task 2: Delete Old Layout Components

**Delete:**
- `frontend/src/components/layout/AppTopNav.vue` (replaced by `TopBar.vue`)

- [ ] **Step 1:** `git rm frontend/src/components/layout/AppTopNav.vue`
- [ ] **Step 2:** Verify: `grep -rn 'AppTopNav' frontend/src/ --include='*.ts' --include='*.vue'` — nothing
- [ ] **Step 3:** `cd frontend && npx vue-tsc --noEmit`
- [ ] **Step 4:** Commit: `git commit -m "chore: delete AppTopNav.vue (replaced by TopBar.vue)"`

---

### Task 3: Delete Old Workspace Components

**Delete:**
- `frontend/src/components/workspace/ProjectWorkspaceShell.vue`
- `frontend/src/components/workspace/AnnotationSidebar.vue`
- `frontend/src/components/workspace/InspectorPanel.vue`
- `frontend/src/components/workspace/ChatWorkspace.vue`
- `frontend/src/components/workspace/ChatCommandMenu.vue` (replaced by `chat/CommandMenu.vue`)

**Keep:**
- `frontend/src/components/workspace/chatCommands.ts` — still imported by `stores/chat.ts` for `ChatCommandName` type. Move or re-export in Task 9 if desired.
- `frontend/src/components/workspace/chatCommands.test.ts` — tests pure logic, keep.

- [ ] **Step 1:** `git rm frontend/src/components/workspace/ProjectWorkspaceShell.vue frontend/src/components/workspace/AnnotationSidebar.vue frontend/src/components/workspace/InspectorPanel.vue frontend/src/components/workspace/ChatWorkspace.vue frontend/src/components/workspace/ChatCommandMenu.vue`
- [ ] **Step 2:** Verify: `grep -rn 'ProjectWorkspaceShell\|AnnotationSidebar\|InspectorPanel\|ChatWorkspace\|ChatCommandMenu' frontend/src/ --include='*.ts' --include='*.vue'` — only `chatCommands.test.ts` references should remain (for the test file, not the deleted components)
- [ ] **Step 3:** `cd frontend && npx vue-tsc --noEmit`
- [ ] **Step 4:** Commit: `git commit -m "chore: delete old workspace components (Shell, Inspector, ChatWorkspace, etc.)"`

---

### Task 4: Delete Old Tab Components

**Delete all files in `frontend/src/components/tabs/`:**
- `OverviewTab.vue`
- `SetupTab.vue`
- `SetupDetailModal.vue`
- `SetupSummaryCard.vue`
- `SetupWorldPanel.vue`
- `SetupCharactersPanel.vue`
- `SetupConceptPanel.vue`
- `SetupSectionTabs.vue`
- `StorylineTab.vue`
- `OutlineTab.vue`
- `ContentTab.vue`
- `TopologyTab.vue`
- `VersionsTab.vue` (logic moved to `VersionsModal.vue`)
- `PreferencesTab.vue` (logic moved to `SettingsView.vue`)
- `VersionDiff.vue`
- `setupPresentation.ts`
- `setupSummaryPresentation.ts`

- [ ] **Step 1:** `git rm frontend/src/components/tabs/OverviewTab.vue frontend/src/components/tabs/SetupTab.vue frontend/src/components/tabs/SetupDetailModal.vue frontend/src/components/tabs/SetupSummaryCard.vue frontend/src/components/tabs/SetupWorldPanel.vue frontend/src/components/tabs/SetupCharactersPanel.vue frontend/src/components/tabs/SetupConceptPanel.vue frontend/src/components/tabs/SetupSectionTabs.vue frontend/src/components/tabs/StorylineTab.vue frontend/src/components/tabs/OutlineTab.vue frontend/src/components/tabs/ContentTab.vue frontend/src/components/tabs/TopologyTab.vue frontend/src/components/tabs/VersionsTab.vue frontend/src/components/tabs/PreferencesTab.vue frontend/src/components/tabs/VersionDiff.vue frontend/src/components/tabs/setupPresentation.ts frontend/src/components/tabs/setupSummaryPresentation.ts`
- [ ] **Step 2:** Verify: `grep -rn 'components/tabs/' frontend/src/ --include='*.ts' --include='*.vue'` — only test files (deleted in Task 11)
- [ ] **Step 3:** `cd frontend && npx vue-tsc --noEmit`
- [ ] **Step 4:** Commit: `git commit -m "chore: delete all old tab components and presentation helpers"`

---

### Task 5: Delete Old Shared Components

**Delete:**
- `frontend/src/components/ProjectCard.vue`
- `frontend/src/components/ProjectSidebar.vue`
- `frontend/src/components/ActionCard.vue`
- `frontend/src/components/ChatSummaryCard.vue`
- `frontend/src/components/WorkspaceTabs.vue`
- `frontend/src/components/InspectorDetailModal.vue`
- `frontend/src/components/ConfirmDialog.vue` (replaced by `base/ConfirmDialog.vue`)

- [ ] **Step 1:** `git rm frontend/src/components/ProjectCard.vue frontend/src/components/ProjectSidebar.vue frontend/src/components/ActionCard.vue frontend/src/components/ChatSummaryCard.vue frontend/src/components/WorkspaceTabs.vue frontend/src/components/InspectorDetailModal.vue frontend/src/components/ConfirmDialog.vue`
- [ ] **Step 2:** Verify: `grep -rn 'ProjectCard\|ProjectSidebar\|ActionCard\|ChatSummaryCard\|WorkspaceTabs\|InspectorDetailModal' frontend/src/ --include='*.ts' --include='*.vue'` — nothing
- [ ] **Step 3:** Verify ConfirmDialog imports now point to `base/ConfirmDialog.vue`: `grep -rn 'ConfirmDialog' frontend/src/ --include='*.ts' --include='*.vue'` — all should reference `base/`
- [ ] **Step 4:** `cd frontend && npx vue-tsc --noEmit`
- [ ] **Step 5:** Commit: `git commit -m "chore: delete old shared components (ProjectCard, ActionCard, etc.)"`

---

### Task 6: Delete Old List Components

**Delete:**
- `frontend/src/components/list/ProjectMatrixHero.vue`
- `frontend/src/components/list/ProjectFocusRail.vue`
- `frontend/src/components/list/projectListMeta.ts`
- `frontend/src/components/list/projectMatrixHeroSubmit.ts`

- [ ] **Step 1:** `git rm frontend/src/components/list/ProjectMatrixHero.vue frontend/src/components/list/ProjectFocusRail.vue frontend/src/components/list/projectListMeta.ts frontend/src/components/list/projectMatrixHeroSubmit.ts`
- [ ] **Step 2:** Verify: `grep -rn 'components/list/' frontend/src/ --include='*.ts' --include='*.vue'` — only test file (deleted in Task 11)
- [ ] **Step 3:** `cd frontend && npx vue-tsc --noEmit`
- [ ] **Step 4:** Commit: `git commit -m "chore: delete old list components (ProjectMatrixHero, ProjectFocusRail, etc.)"`

---

### Task 7: Delete Old Athena Components

**Delete:**
- `frontend/src/components/athena/AthenaMiniDialog.vue` (replaced by `AthenaChatPanel.vue`)
- `frontend/src/components/athena/AthenaOntologyPanel.vue` (replaced by EntityTable, RelationTable, RuleList)
- `frontend/src/components/athena/AthenaStatePanel.vue` (replaced by ProjectionViewer, TimelineView, KnowledgeViewer)
- `frontend/src/components/athena/AthenaEvolutionPanel.vue` (replaced by ProposalList, ConsistencyList)
- `frontend/src/components/athena/AthenaFloatingChat.vue` (replaced by AthenaChatPanel.vue)

- [ ] **Step 1:** `git rm frontend/src/components/athena/AthenaMiniDialog.vue frontend/src/components/athena/AthenaOntologyPanel.vue frontend/src/components/athena/AthenaStatePanel.vue frontend/src/components/athena/AthenaEvolutionPanel.vue frontend/src/components/athena/AthenaFloatingChat.vue`
- [ ] **Step 2:** Verify: `grep -rn 'AthenaMiniDialog\|AthenaOntologyPanel\|AthenaStatePanel\|AthenaEvolutionPanel\|AthenaFloatingChat' frontend/src/ --include='*.ts' --include='*.vue'` — nothing
- [ ] **Step 3:** `cd frontend && npx vue-tsc --noEmit`
- [ ] **Step 4:** Commit: `git commit -m "chore: delete old Athena tab panels (replaced by new section components)"`

---

### Task 8: Clean Up Old CSS

**Modify:** `frontend/src/style.css`

Remove all old paper/hermes/athena theming. The file should only contain Tailwind directives and imports of the new style system.

- [ ] **Step 1:** Replace the entire contents of `frontend/src/style.css` with:

```css
@import './styles/tokens.css';
@import './styles/reset.css';
@import './styles/base.css';
@import './styles/utilities.css';

@tailwind base;
@tailwind components;
@tailwind utilities;
```

This removes:
- All `--paper-*`, `--ink-*`, `--nav-*`, `--line-*`, `--surface-*`, `--accent*` CSS variables
- All `--hermes-*` palette variables
- All `--athena-*` palette variables
- The old `body` background-image/color/::before grain overlay
- `@keyframes pulse-breathe` and `@keyframes athena-glow`
- `.crossfade-*` transition classes
- All `@layer components` rules (`.app-shell`, `.app-top-nav*`, `.app-shell__*`)

- [ ] **Step 2:** Verify no old variable references remain: `grep -rn 'paper-bg\|hermes-bg\|athena-bg\|ink-strong\|pulse-breathe\|athena-glow\|app-top-nav' frontend/src/ --include='*.css' --include='*.vue'` — nothing
- [ ] **Step 3:** `cd frontend && npx vue-tsc --noEmit && npm run build`
- [ ] **Step 4:** Commit: `git commit -m "chore: remove old paper/hermes/athena CSS, use new token system"`

---

### Task 9: Simplify workspace.ts Store

**Modify:** `frontend/src/stores/workspace.ts`

The old store has complex panel/lock/mode logic for InspectorPanel. Now that navigation is sidebar-driven, most of this is dead code.

- [ ] **Step 1:** Check what still imports from workspace store: `grep -rn 'useWorkspaceStore\|from.*workspace' frontend/src/ --include='*.ts' --include='*.vue'` (exclude test files and the store itself)
- [ ] **Step 2:** Based on findings, either:
  - **Option A (gut it):** If nothing references `applyUiHint`, `settleUiAction`, `toggleLock`, `mode`, `lockedPanel`, `returnPanel`, `source`, `reason`, `lastUserPanel` — remove all of them. Keep only `panel`, `applyUserPanel`, and `reset`.
  - **Option B (stub it):** If `chat.ts` still calls `applyUiHint`/`settleUiAction` for response handling — keep those two functions but simplify their internals (remove lock logic, just set panel).

Simplified target shape:

```typescript
export const useWorkspaceStore = defineStore('workspace', () => {
  const panel = ref<WorkspacePanel>('overview')

  function applyUserPanel(p: WorkspacePanel) {
    panel.value = p
  }

  function reset() {
    panel.value = 'overview'
  }

  return { panel, applyUserPanel, reset }
})
```

- [ ] **Step 3:** Remove exported helper functions that are no longer needed: `createWorkspaceState`, `applyUiHint`, `settleUiAction`, `toggleLockState`
- [ ] **Step 4:** Remove the `WorkspaceMode`, `WorkspaceSource` type exports
- [ ] **Step 5:** `cd frontend && npx vue-tsc --noEmit`
- [ ] **Step 6:** Commit: `git commit -m "refactor: simplify workspace store — remove lock/mode/hint complexity"`

---

### Task 10: Clean Up chat.ts Store

**Modify:** `frontend/src/stores/chat.ts`

- [ ] **Step 1:** Remove `dialogType` ref and `setDialogType` function (Athena chat is now separate in `athena.ts`)
- [ ] **Step 2:** Remove `dialogType` from the return object
- [ ] **Step 3:** Update `loadHistory` / `getMessages` calls — if they pass `dialogType.value`, change to always pass `'hermes'` (or remove the parameter if the API defaults to hermes)
- [ ] **Step 4:** Update the import of `ChatCommandName` — if `chatCommands.ts` is still in `workspace/`, keep the import. If it was moved to `chat/`, update the path.
- [ ] **Step 5:** `cd frontend && npx vue-tsc --noEmit`
- [ ] **Step 6:** Commit: `git commit -m "refactor: remove dialogType from chat store (Athena chat uses athena.ts)"`

---

### Task 11: Delete Old Test Files

Delete tests that test deleted components. Keep tests for preserved logic.

**Delete:**
- `frontend/src/components/workspace/InspectorPanel.compact.test.ts`
- `frontend/src/components/workspace/ChatWorkspace.commands.test.ts`
- `frontend/src/components/tabs/SetupTab.structured.test.ts`
- `frontend/src/components/tabs/SetupDetailModal.test.ts`
- `frontend/src/components/tabs/setupPresentation.test.ts`
- `frontend/src/components/tabs/setupSummaryPresentation.test.ts`
- `frontend/src/components/list/projectListMeta.test.ts`
- `frontend/src/views/projectListDeleteDialog.test.ts`

**Keep:**
- `frontend/src/stores/chat.workspace.test.ts` — tests chat store logic (update if API changed)
- `frontend/src/stores/workspace.test.ts` — update to match simplified store
- `frontend/src/stores/project.workspace.test.ts` — update if it imports from deleted `projectDetailHydration.ts`
- `frontend/src/stores/worldModel.test.ts` — unchanged
- `frontend/src/api/client.worldModel.test.ts` — unchanged
- `frontend/src/components/workspace/chatCommands.test.ts` — tests pure logic, keep

- [ ] **Step 1:** `git rm frontend/src/components/workspace/InspectorPanel.compact.test.ts frontend/src/components/workspace/ChatWorkspace.commands.test.ts frontend/src/components/tabs/SetupTab.structured.test.ts frontend/src/components/tabs/SetupDetailModal.test.ts frontend/src/components/tabs/setupPresentation.test.ts frontend/src/components/tabs/setupSummaryPresentation.test.ts frontend/src/components/list/projectListMeta.test.ts frontend/src/views/projectListDeleteDialog.test.ts`
- [ ] **Step 2:** Update `frontend/src/stores/workspace.test.ts` to match the simplified store API (remove tests for `toggleLock`, `applyUiHint`, `settleUiAction` if those were removed)
- [ ] **Step 3:** Update `frontend/src/stores/project.workspace.test.ts` — if it imports from `projectDetailHydration.ts` (deleted in Task 12), update or delete the import
- [ ] **Step 4:** `cd frontend && npx vitest run` — all remaining tests pass
- [ ] **Step 5:** Commit: `git commit -m "chore: delete old test files, update remaining tests for simplified stores"`

---

### Task 12: Delete Old Workspace Metadata

**Delete (if no longer imported):**
- `frontend/src/components/workspace/workspaceMeta.ts`
- `frontend/src/views/projectDetailHydration.ts`
- `frontend/src/views/projectListDeleteDialog.ts`

- [ ] **Step 1:** Verify no remaining imports: `grep -rn 'workspaceMeta\|projectDetailHydration\|projectListDeleteDialog' frontend/src/ --include='*.ts' --include='*.vue'`
- [ ] **Step 2:** If clean, `git rm frontend/src/components/workspace/workspaceMeta.ts frontend/src/views/projectDetailHydration.ts frontend/src/views/projectListDeleteDialog.ts`
- [ ] **Step 3:** If `project.workspace.test.ts` imports from `projectDetailHydration.ts`, update the test first (move needed helpers inline or to a test util)
- [ ] **Step 4:** `cd frontend && npx vue-tsc --noEmit && npx vitest run`
- [ ] **Step 5:** Commit: `git commit -m "chore: delete old workspace metadata and hydration helpers"`

---

### Task 13: Final Verification

Full build + test + import audit.

- [ ] **Step 1:** `cd frontend && npx vue-tsc --noEmit` — zero errors
- [ ] **Step 2:** `cd frontend && npm run build` — clean build, no warnings about missing modules
- [ ] **Step 3:** `cd frontend && npx vitest run` — all remaining tests pass
- [ ] **Step 4:** Grep for any dangling imports of deleted files:

```bash
grep -rn 'ProjectList\b\|ProjectDetail\b\|ManuscriptPlaceholder\|AppTopNav\|ProjectWorkspaceShell\|AnnotationSidebar\|InspectorPanel\|ChatWorkspace\|ChatCommandMenu\|OverviewTab\|SetupTab\|SetupDetailModal\|SetupSummaryCard\|SetupWorldPanel\|SetupCharactersPanel\|SetupConceptPanel\|StorylineTab\|OutlineTab\|ContentTab\|TopologyTab\|VersionsTab\|PreferencesTab\|VersionDiff\|ProjectCard\|ProjectSidebar\|ActionCard\|ChatSummaryCard\|WorkspaceTabs\|InspectorDetailModal\|ProjectMatrixHero\|ProjectFocusRail\|projectListMeta\|AthenaMiniDialog\|AthenaOntologyPanel\|AthenaStatePanel\|AthenaEvolutionPanel\|AthenaFloatingChat' frontend/src/ --include='*.ts' --include='*.vue'
```

Should return nothing.

- [ ] **Step 5:** Visual check in browser — navigate all routes: `/`, `/projects/:id/hermes`, `/projects/:id/athena`, `/projects/:id/manuscript`, `/settings`
- [ ] **Step 6:** Final commit if any fixups were needed: `git commit -m "chore: final cleanup fixups"`
