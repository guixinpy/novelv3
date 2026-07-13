# Component Guidelines

> How components are built in this project.

---

## Overview

Components use Vue 3 Composition API with `<script setup lang="ts">`.
TypeScript is required for all component props and emits.
CSS uses a combination of TailwindCSS utility classes and scoped BEM-style styles.

---

## Component Structure

```vue
<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useProjectStore } from '../../stores/project'

// Props with TypeScript generics
const props = withDefaults(defineProps<{
  open: boolean
  title?: string
  width?: string
}>(), { width: '480px' })

// Events
const emit = defineEmits<{ close: [] }>()

// Reactive state
const panelRef = ref<HTMLElement | null>(null)
const localOpen = ref(false)

// Computed
const panelStyle = computed(() => ({ width: props.width }))

// Watch
watch(() => props.open, (val) => { localOpen.value = val })
</script>

<template>
  <Teleport to="body">
    <div class="base-modal__backdrop" @click.self="emit('close')">
      <div ref="panelRef" class="base-modal__panel" :style="panelStyle" role="dialog">
        <header class="base-modal__header">
          <slot name="header">
            <h2>{{ title }}</h2>
          </slot>
        </header>
        <main class="base-modal__body">
          <slot />
        </main>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.base-modal__backdrop {
  position: fixed;
  inset: 0;
  background: var(--color-overlay);
  z-index: var(--z-modal);
}
.base-modal__panel {
  background: var(--color-bg-white);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
}
</style>
```

---

## Props Conventions

- **TypeScript generics** with `defineProps<{...}>()` — no runtime prop validation.
- **Defaults** via `withDefaults()` for optional props with fallback values.
- **Boolean props** default to `false` unless explicitly set.
- **`defineEmits<{ eventName: [payloadType] }>()`** for typed emits.

---

## Composition Patterns

### Named slots for flexible layouts

```vue
<div class="card">
  <div class="card__header"><slot name="header" /></div>
  <div class="card__body"><slot /></div>
  <div class="card__footer" v-if="$slots.footer"><slot name="footer" /></div>
</div>
```

### Teleport for modals and overlays

Modal components use `<Teleport to="body">` to avoid z-index and overflow issues.

### Pure-function modules for complex logic

Complex component logic (projection, rendering, comparison) is extracted into
standalone `.ts` files imported by the component, not inlined:

```typescript
// components/chat/agentRunProjection.ts — pure functions, no Vue dependency
export function projectAgentRun(run: AgentRun): ProjectedRun { ... }
```

---

## Styling Patterns

- **TailwindCSS** for layout, spacing, typography, and color utilities.
- **CSS variables** (defined in `styles/tokens.css`) for design tokens:
  `--color-primary`, `--space-4`, `--radius-lg`, `--shadow-md`.
- **Scoped BEM classes** for component-specific styles:
  `component-name__element--modifier`.
- **`<style scoped>`** is the default. Global styles are limited to `styles/`.

---

## Accessibility

- Semantic HTML elements (`<button>`, `<nav>`, `<header>`, `<main>`, `<dialog>`).
- `role` attributes for custom interactive elements.
- Keyboard event handlers for custom interactions (Enter/Escape).
- Focus management via `ref` and `.focus()` on open/close.
- Color contrast relies on the CSS variable token system.

---

## Testing Patterns

Tests use `@vue/test-utils` + Vitest, co-located next to the component:

```typescript
// BaseModal.test.ts
// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'

describe('BaseModal', () => {
  it('renders content when open', async () => {
    const wrapper = mount(BaseModal, { props: { open: true } })
    expect(wrapper.text()).toContain('expected content')
  })

  it('emits close on backdrop click', async () => {
    const wrapper = mount(BaseModal, { props: { open: true } })
    await wrapper.find('.base-modal__backdrop').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })
})
```

---

## Common Mistakes

1. **Missing `lang="ts"` on `<script setup>`** — Props and emits won't be type-checked.
2. **Inline complex logic** — Extract projections and transformations to `.ts` modules.
3. **Direct store mutation outside of actions** — Always use store actions.
4. **Over-nesting scoped styles** — Keep specificity low; prefer single-class selectors.
5. **Forgetting `v-if="$slots.footer"`** — An empty `<slot name="footer">` still renders the wrapping DOM element.
