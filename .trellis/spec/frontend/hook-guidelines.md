# Hook Guidelines

> How composable functions and hooks are used in this project.

---

## Overview

The project uses **Vue 3 Composition API** — composable functions (`useXxx`)
for reusable stateful logic, and **Pinia stores** (`useXxxStore`) for shared
global state. Standalone pure functions go in `.ts` module files without `use`
prefix.

---

## Custom Composable Patterns

### When to create a composable

- Logic is reused across multiple components
- Complex lifecycle management (subscriptions, intervals, event listeners)
- Integration with browser APIs (resize observer, intersection observer)

### Naming

- Composables: `useXxx` (e.g., `useProjectStore`, `useRouter`)
- Pure utility functions: descriptive name without prefix
  (e.g., `projectAgentRun()`, `chatCommands()`, `workspaceMeta()`)

### Example pattern

```typescript
// Prefer store actions over standalone composables for data fetching
// Prefer pure functions in .ts modules over composables for transformations

// Good: pure function module (no Vue dependency)
// components/chat/agentRunProjection.ts
export function projectAgentRun(run: AgentRun): ProjectedRun {
  return {
    status: run.status,
    toolCalls: run.tool_calls?.length ?? 0,
    // ...
  }
}

// Good: imported in component
// <script setup>
import { projectAgentRun } from './agentRunProjection'
const projected = computed(() => projectAgentRun(props.run))
```

---

## Data Fetching

The project does not use a dedicated data-fetching library (no TanStack Query
or SWR). Instead:

1. **Store actions** call the API client directly
2. **`requestCache` store** provides dedup and freshness checks
3. **Snapshot pattern** prevents stale updates

```typescript
// In a component
const projectStore = useProjectStore()
onMounted(() => {
  projectStore.loadProjects()  // store action handles the fetch
})
```

---

## Component → Store Data Flow

```
Component (onMounted / user action)
  → Store action (async, calls api.*)
    → API client (fetch /api/v1/*)
    → Response
    → State mutation (store refs)
  → Reactive update (component re-renders)
```

Derived state uses `computed()`:

```typescript
const activeProjects = computed(() =>
  projectStore.projects.filter(p => p.status === 'active')
)
```

---

## Common Mistakes

1. **Creating composables for simple transformations** — Use standalone
   pure functions in `.ts` modules instead.
2. **Mixing store and component concerns** — Data fetching logic belongs in
   store actions, not in composables.
3. **Over-using composables for one-off logic** — Inline `ref()` + `watch()`
   in the component is fine for component-specific behavior.
4. **Missing cleanup in composables** — Always return/register cleanup in
   `onUnmounted()` for event listeners and intervals.
