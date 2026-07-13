# Directory Structure

> How frontend code is organized in this project.

---

## Overview

The frontend is a Vue 3 + TypeScript SPA built with Vite.
Vue components use `PascalCase.vue`, TypeScript modules use `camelCase.ts`.

---

## Directory Layout

```
frontend/
├── src/
│   ├── main.ts                 # App entry: createApp, Pinia, Router
│   ├── App.vue                 # Root component: AppShell + <router-view>
│   ├── style.css               # @import tokens, reset, base, Tailwind
│   ├── api/                    # REST API client
│   │   ├── client.ts           # fetch-based client (/api/v1/*)
│   │   ├── types.ts            # All API type definitions (~1233 lines)
│   │   ├── agentV2.ts          # SSE streaming agent session client
│   │   └── *.test.ts           # Co-located API client tests
│   ├── router/
│   │   └── index.ts            # Route definitions
│   ├── stores/                 # Pinia stores (one file per domain)
│   │   ├── project.ts / chat.ts / athena.ts / ...
│   │   ├── requestCache.ts     # Dedup & freshness cache (generic)
│   │   └── athenaModules/      # Athena sub-modules (proposals, retrieval)
│   ├── views/                  # Top-level page components
│   │   ├── ProjectListView.vue / HermesView.vue / AthenaView.vue
│   │   ├── ManuscriptView.vue / SettingsView.vue / AgentV2View.vue
│   │   └── *.ts                # View-level logic modules (navigation, hydration)
│   ├── components/             # Vue components, grouped by domain
│   │   ├── layout/             # AppShell, ActivityBar, TopBar, SubNav
│   │   ├── base/               # BaseModal, BaseButton, BaseInput, BaseBadge, BaseTable
│   │   ├── shared/             # ProjectDashboard, ChapterList, ExportModal
│   │   ├── chat/               # ChatMessage, ChatInput, ActionCard, run projections
│   │   ├── manuscript/         # ManuscriptEditor, RevisionSummaryPanel
│   │   ├── athena/             # AthenaOverview, NarrativeAtlas*, Proposal*, ...
│   │   ├── athena/catalog/     # Catalog node UI
│   │   ├── modelTrace/         # ModelTraceDrawer, TraceSummary
│   │   ├── workspace/          # Chat commands, workspace meta utilities
│   │   ├── world/              # WorldProposalBundleList, ProposalClaimDiffEditor
│   │   └── writingAgent/       # AgentRunDrawer + ~30 AgentRun*Panel components
│   ├── styles/                 # CSS architecture
│   │   ├── tokens.css          # Design tokens (CSS variables)
│   │   ├── reset.css           # CSS reset
│   │   └── base.css            # Base element styles
│   └── utils/                  # Utility modules
│       └── workspacePerfProbe.ts
├── e2e/                        # Playwright E2E tests
├── index.html
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.js
├── eslint.config.js
└── package.json
```

---

## Naming Conventions

| Category | Convention | Example |
|----------|-----------|---------|
| Vue components | `PascalCase.vue` | `ProjectDashboard.vue`, `AgentRunDrawer.vue` |
| TypeScript modules | `camelCase.ts` | `client.ts`, `narrativeAtlasGraph.ts` |
| Pinia stores | `camelCase.ts` | `project.ts`, `worldModel.ts` |
| Store accessor | `useXxxStore` | `useProjectStore`, `useChatStore` |
| CSS classes | BEM-like | `base-modal__backdrop`, `base-modal__panel` |
| CSS variables | `--kebab-case` | `--color-bg-primary`, `--space-4` |
| Component tests | `ComponentName.test.ts` | `BaseModal.test.ts`, `ChatMessage.test.ts` |
| Store tests | `domain.scope.test.ts` | `project.workspace.test.ts`, `athena.chat.test.ts` |
| E2E tests | `kebab-case.spec.ts` | `app-shell.spec.ts`, `project-workspaces.spec.ts` |

---

## Module Organization

- **Components** are grouped by domain (`chat/`, `athena/`, `writingAgent/`, etc.),
  not by type. There is no `components/ui/` — base UI components go in `base/`.
- **Stores** are one file per domain. Domain sub-modules live in subdirectories
  (e.g., `athenaModules/`).
- **View-level logic** (hydration, navigation, replay) is extracted into
  standalone `.ts` files in `views/`, not inlined in `.vue` files.
- **API layer** is a thin fetch wrapper. Each endpoint is a named function,
  not a generic REST client.
- **Tests** are co-located next to the source file they test.
