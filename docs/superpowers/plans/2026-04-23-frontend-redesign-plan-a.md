# Frontend Redesign Plan A: Foundation + Layout Shell

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the design token system, base component library, layout shell, and routing infrastructure for the new minimalist UI.

**Architecture:** Replace the old paper-themed CSS and AppTopNav-based shell with a design-token-driven system and VS Code-style Activity Bar + SubNav + Content layout. Keep existing page views working through the transition.

**Tech Stack:** Vue 3, TypeScript, Pinia, Tailwind CSS, CSS Custom Properties

---

### Task 1: Design Token CSS Files

**Files:**
- Create: `frontend/src/styles/tokens.css`
- Create: `frontend/src/styles/reset.css`
- Create: `frontend/src/styles/base.css`
- Modify: `frontend/src/style.css`
- Modify: `frontend/tailwind.config.js`

- [ ] **Step 1: Create `frontend/src/styles/tokens.css`**

Create directory `frontend/src/styles/` then create the file with all design tokens from the spec:

```css
/* Design Tokens — single source of truth for the entire UI */
:root {
  /* --- Backgrounds --- */
  --color-bg-primary: #FAFAFA;
  --color-bg-secondary: #F5F5F5;
  --color-bg-tertiary: #EFEFEF;
  --color-bg-white: #FFFFFF;

  /* --- Text --- */
  --color-text-primary: #1A1A1A;
  --color-text-secondary: #6B7280;
  --color-text-tertiary: #9CA3AF;
  --color-text-inverse: #FFFFFF;

  /* --- Brand (Indigo) --- */
  --color-brand: #4F46E5;
  --color-brand-hover: #4338CA;
  --color-brand-active: #3730A3;
  --color-brand-light: #EEF2FF;
  --color-brand-subtle: #E0E7FF;

  /* --- Borders --- */
  --color-border: #E5E7EB;
  --color-border-strong: #D1D5DB;

  /* --- Semantic --- */
  --color-success: #16A34A;
  --color-success-light: #F0FDF4;
  --color-warning: #D97706;
  --color-warning-light: #FFFBEB;
  --color-error: #DC2626;
  --color-error-light: #FEF2F2;

  /* --- Activity Bar --- */
  --color-activity-bar-bg: #1E1E2E;
  --color-activity-bar-icon: #9CA3AF;
  --color-activity-bar-icon-active: #FFFFFF;
  --color-activity-bar-accent: var(--color-brand);
  --color-activity-bar-item-active-bg: rgba(255, 255, 255, 0.08);

  /* --- Spacing (4px grid) --- */
  --space-0: 0px;
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-7: 28px;
  --space-8: 32px;
  --space-9: 36px;
  --space-10: 40px;
  --space-11: 44px;
  --space-12: 48px;

  /* --- Typography --- */
  --font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
    'Helvetica Neue', Arial, 'Noto Sans SC', sans-serif;
  --font-mono: 'SF Mono', 'Fira Code', 'Fira Mono', 'Roboto Mono', monospace;

  --text-xs: 0.75rem;
  --text-sm: 0.875rem;
  --text-base: 1rem;
  --text-lg: 1.125rem;
  --text-xl: 1.25rem;
  --text-2xl: 1.5rem;

  --leading-tight: 1.25;
  --leading-normal: 1.5;
  --leading-relaxed: 1.625;

  --font-normal: 400;
  --font-medium: 500;
  --font-semibold: 600;
  --font-bold: 700;

  /* --- Border Radius --- */
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;
  --radius-full: 9999px;

  /* --- Shadows --- */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.07), 0 2px 4px -2px rgba(0, 0, 0, 0.05);

  /* --- Transitions --- */
  --transition-fast: 150ms ease;
  --transition-normal: 200ms ease;

  /* --- Layout Constants --- */
  --topbar-height: 48px;
  --activity-bar-width: 48px;
  --subnav-width: 220px;
  --content-padding: var(--space-6);
  --athena-chat-width: 400px;
}
```

- [ ] **Step 2: Create `frontend/src/styles/reset.css`**

```css
/* Minimal CSS reset */
*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html {
  -webkit-text-size-adjust: 100%;
  -moz-tab-size: 4;
  tab-size: 4;
}

body {
  line-height: var(--leading-normal);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

img, svg, video, canvas, audio, iframe, embed, object {
  display: block;
  max-width: 100%;
}

input, button, textarea, select {
  font: inherit;
  color: inherit;
}

button {
  cursor: pointer;
  background: none;
  border: none;
}

a {
  color: inherit;
  text-decoration: none;
}

ul, ol {
  list-style: none;
}

table {
  border-collapse: collapse;
}
```

- [ ] **Step 3: Create `frontend/src/styles/base.css`**

```css
/* Base element styles using design tokens */
body {
  font-family: var(--font-family);
  font-size: var(--text-base);
  color: var(--color-text-primary);
  background-color: var(--color-bg-primary);
}

h1, h2, h3, h4, h5, h6 {
  font-weight: var(--font-semibold);
  line-height: var(--leading-tight);
}

h1 { font-size: var(--text-2xl); }
h2 { font-size: var(--text-xl); }
h3 { font-size: var(--text-lg); }
h4 { font-size: var(--text-base); }

code, pre {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
}

::selection {
  background-color: var(--color-brand-subtle);
  color: var(--color-text-primary);
}

/* Scrollbar styling */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: var(--color-border-strong);
  border-radius: var(--radius-full);
}

::-webkit-scrollbar-thumb:hover {
  background: var(--color-text-tertiary);
}
```

- [ ] **Step 4: Rewrite `frontend/src/style.css`**

Replace the entire file contents with:

```css
/* Import order matters: reset → tokens → base → tailwind utilities */
@import './styles/reset.css';
@import './styles/tokens.css';
@import './styles/base.css';

@tailwind utilities;

/* Transition helpers (kept from old file, still used by router-view) */
.crossfade-enter-active,
.crossfade-leave-active {
  transition: opacity 0.2s ease;
}
.crossfade-enter-from,
.crossfade-leave-to {
  opacity: 0;
}
```

This removes:
- `@tailwind base` and `@tailwind components` (replaced by reset.css + base.css)
- All old `:root` variables (`--paper-*`, `--ink-*`, `--hermes-*`, `--athena-*`, `--nav-*`, `--accent-*`, `--surface-*`, `--line-soft`)
- Old `body` styles with paper background gradients and grain overlay
- Old `body::before` pseudo-element
- Old `@keyframes pulse-breathe` and `@keyframes athena-glow`
- All `@layer components` rules (`.app-shell`, `.app-top-nav*`, `.app-shell__*`)

- [ ] **Step 5: Update `frontend/tailwind.config.js`**

Replace the entire file contents with:

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    'index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: '#4F46E5',
          hover: '#4338CA',
          active: '#3730A3',
          light: '#EEF2FF',
          subtle: '#E0E7FF',
        },
      },
      fontFamily: {
        sans: ['var(--font-family)'],
        mono: ['var(--font-mono)'],
      },
      borderRadius: {
        sm: '4px',
        md: '6px',
        lg: '8px',
      },
    },
  },
  plugins: [],
}
```

- [ ] **Step 6: Commit**

```bash
cd /home/guixin/project_workspace/novelv3 && git add frontend/src/styles/ frontend/src/style.css frontend/tailwind.config.js && git commit -m "feat: add design token system and replace old CSS variables"
```

---

### Task 2: Base Components

**Files:**
- Create: `frontend/src/components/base/BaseButton.vue`
- Create: `frontend/src/components/base/BaseInput.vue`
- Create: `frontend/src/components/base/BaseModal.vue`
- Create: `frontend/src/components/base/BaseBadge.vue`
- Create: `frontend/src/components/base/BaseTable.vue`
- Create: `frontend/src/components/base/ConfirmDialog.vue`

- [ ] **Step 1: Create `frontend/src/components/base/BaseButton.vue`**

Create directory `frontend/src/components/base/` then create the file:

```vue
<script setup lang="ts">
withDefaults(
  defineProps<{
    variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
    size?: 'sm' | 'md'
    disabled?: boolean
    loading?: boolean
    iconOnly?: boolean
  }>(),
  {
    variant: 'secondary',
    size: 'md',
    disabled: false,
    loading: false,
    iconOnly: false,
  },
)
</script>

<template>
  <button
    class="base-button"
    :class="[
      `base-button--${variant}`,
      `base-button--${size}`,
      { 'base-button--icon-only': iconOnly, 'base-button--loading': loading },
    ]"
    :disabled="disabled || loading"
  >
    <span v-if="loading" class="base-button__spinner" aria-hidden="true" />
    <slot />
  </button>
</template>

<style scoped>
.base-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  border-radius: var(--radius-md);
  font-weight: var(--font-medium);
  font-size: var(--text-sm);
  transition: all var(--transition-fast);
  cursor: pointer;
  border: 1px solid transparent;
  white-space: nowrap;
}

.base-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Sizes */
.base-button--sm { height: 32px; padding: 0 var(--space-3); }
.base-button--md { height: 36px; padding: 0 var(--space-4); }
.base-button--icon-only.base-button--sm { width: 32px; padding: 0; }
.base-button--icon-only.base-button--md { width: 36px; padding: 0; }

/* Variants */
.base-button--primary {
  background: var(--color-brand);
  color: var(--color-text-inverse);
}
.base-button--primary:hover:not(:disabled) {
  background: var(--color-brand-hover);
}
.base-button--primary:active:not(:disabled) {
  background: var(--color-brand-active);
}

.base-button--secondary {
  background: transparent;
  border-color: var(--color-border);
  color: var(--color-text-primary);
}
.base-button--secondary:hover:not(:disabled) {
  background: var(--color-bg-secondary);
}

.base-button--ghost {
  background: transparent;
  color: var(--color-text-secondary);
}
.base-button--ghost:hover:not(:disabled) {
  color: var(--color-text-primary);
  background: var(--color-bg-secondary);
}

.base-button--danger {
  background: transparent;
  border-color: var(--color-error);
  color: var(--color-error);
}
.base-button--danger:hover:not(:disabled) {
  background: var(--color-error);
  color: var(--color-text-inverse);
}

/* Spinner */
.base-button__spinner {
  width: 14px;
  height: 14px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
```

- [ ] **Step 2: Create `frontend/src/components/base/BaseInput.vue`**

```vue
<script setup lang="ts">
defineProps<{
  modelValue: string
  label?: string
  placeholder?: string
  error?: string
  disabled?: boolean
  type?: 'text' | 'password' | 'email'
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

function onInput(e: Event) {
  emit('update:modelValue', (e.target as HTMLInputElement).value)
}
</script>

<template>
  <div class="base-input">
    <label v-if="label" class="base-input__label">{{ label }}</label>
    <input
      class="base-input__field"
      :class="{ 'base-input__field--error': error }"
      :type="type ?? 'text'"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      @input="onInput"
    />
    <p v-if="error" class="base-input__error">{{ error }}</p>
  </div>
</template>

<style scoped>
.base-input {
  display: flex;
  flex-direction: column;
}

.base-input__label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  margin-bottom: var(--space-1);
  color: var(--color-text-primary);
}

.base-input__field {
  height: 36px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  background: var(--color-bg-white);
  transition: border-color var(--transition-fast);
  outline: none;
}

.base-input__field:focus {
  border-color: var(--color-brand);
  box-shadow: 0 0 0 2px var(--color-brand-subtle);
}

.base-input__field--error {
  border-color: var(--color-error);
}

.base-input__field:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: var(--color-bg-secondary);
}

.base-input__error {
  font-size: var(--text-xs);
  color: var(--color-error);
  margin-top: var(--space-1);
}
</style>
```

- [ ] **Step 3: Create `frontend/src/components/base/BaseModal.vue`**

```vue
<script setup lang="ts">
import { onMounted, onUnmounted, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    open: boolean
    title?: string
    width?: string
  }>(),
  {
    width: '480px',
  },
)

const emit = defineEmits<{
  close: []
}>()

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}

function onBackdropClick(e: MouseEvent) {
  if (e.target === e.currentTarget) emit('close')
}

watch(
  () => props.open,
  (val) => {
    if (val) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
  },
)

onMounted(() => {
  document.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', onKeydown)
  document.body.style.overflow = ''
})
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="open"
        class="base-modal__backdrop"
        @click="onBackdropClick"
      >
        <div
          class="base-modal__panel"
          :style="{ width }"
          role="dialog"
          aria-modal="true"
        >
          <header v-if="title || $slots.header" class="base-modal__header">
            <slot name="header">
              <h3 class="base-modal__title">{{ title }}</h3>
            </slot>
            <button
              class="base-modal__close"
              aria-label="关闭"
              @click="emit('close')"
            >
              &times;
            </button>
          </header>
          <div class="base-modal__body">
            <slot />
          </div>
          <footer v-if="$slots.footer" class="base-modal__footer">
            <slot name="footer" />
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.base-modal__backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.3);
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
}

.base-modal__panel {
  background: var(--color-bg-white);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  max-height: 85vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.base-modal__header {
  padding: var(--space-4);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.base-modal__title {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.base-modal__close {
  font-size: var(--text-xl);
  color: var(--color-text-tertiary);
  line-height: 1;
  padding: var(--space-1);
}
.base-modal__close:hover {
  color: var(--color-text-primary);
}

.base-modal__body {
  padding: var(--space-4);
  flex: 1;
  overflow-y: auto;
}

.base-modal__footer {
  padding: var(--space-3) var(--space-4);
  border-top: 1px solid var(--color-border);
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  flex-shrink: 0;
}

/* Transition */
.modal-enter-active,
.modal-leave-active {
  transition: opacity var(--transition-normal);
}
.modal-enter-active .base-modal__panel,
.modal-leave-active .base-modal__panel {
  transition: transform var(--transition-normal);
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
.modal-enter-from .base-modal__panel,
.modal-leave-to .base-modal__panel {
  transform: scale(0.95);
}
</style>
```

- [ ] **Step 4: Create `frontend/src/components/base/BaseBadge.vue`**

```vue
<script setup lang="ts">
withDefaults(
  defineProps<{
    variant?: 'success' | 'warning' | 'error' | 'neutral'
    size?: 'sm' | 'md'
  }>(),
  {
    variant: 'neutral',
    size: 'sm',
  },
)
</script>

<template>
  <span
    class="base-badge"
    :class="[`base-badge--${variant}`, `base-badge--${size}`]"
  >
    <slot />
  </span>
</template>

<style scoped>
.base-badge {
  display: inline-flex;
  align-items: center;
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  white-space: nowrap;
}

.base-badge--sm { padding: 2px 8px; }
.base-badge--md { padding: 4px 10px; }

.base-badge--success {
  background: var(--color-success-light);
  color: var(--color-success);
}
.base-badge--warning {
  background: var(--color-warning-light);
  color: var(--color-warning);
}
.base-badge--error {
  background: var(--color-error-light);
  color: var(--color-error);
}
.base-badge--neutral {
  background: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
}
</style>
```

- [ ] **Step 5: Create `frontend/src/components/base/BaseTable.vue`**

```vue
<script setup lang="ts">
export interface BaseTableColumn {
  key: string
  label: string
  width?: string
  align?: 'left' | 'center' | 'right'
}

const props = withDefaults(
  defineProps<{
    columns: BaseTableColumn[]
    data: Record<string, unknown>[]
    rowKey?: string
    hoverable?: boolean
    clickable?: boolean
    emptyText?: string
  }>(),
  {
    rowKey: 'id',
    hoverable: true,
    clickable: false,
    emptyText: '暂无数据',
  },
)

const emit = defineEmits<{
  'row-click': [row: Record<string, unknown>]
}>()

function getRowId(row: Record<string, unknown>, index: number): string {
  const val = row[props.rowKey]
  return val != null ? String(val) : String(index)
}

function getCellValue(row: Record<string, unknown>, key: string): unknown {
  return row[key]
}
</script>

<template>
  <div class="base-table-wrapper">
    <table class="base-table">
      <thead>
        <tr>
          <th
            v-for="col in columns"
            :key="col.key"
            class="base-table__th"
            :style="{
              width: col.width,
              textAlign: col.align ?? 'left',
            }"
          >
            {{ col.label }}
          </th>
        </tr>
      </thead>
      <tbody v-if="data.length > 0">
        <tr
          v-for="(row, idx) in data"
          :key="getRowId(row, idx)"
          class="base-table__row"
          :class="{
            'base-table__row--hoverable': hoverable,
            'base-table__row--clickable': clickable,
          }"
          @click="clickable ? emit('row-click', row) : undefined"
        >
          <td
            v-for="col in columns"
            :key="col.key"
            class="base-table__td"
            :style="{ textAlign: col.align ?? 'left' }"
          >
            <slot :name="`cell-${col.key}`" :row="row" :value="getCellValue(row, col.key)">
              {{ getCellValue(row, col.key) ?? '' }}
            </slot>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-if="data.length === 0" class="base-table__empty">
      {{ emptyText }}
    </div>
  </div>
</template>

<style scoped>
.base-table-wrapper {
  width: 100%;
}

.base-table {
  width: 100%;
  border-collapse: collapse;
}

.base-table__th {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-tertiary);
  border-bottom: 1px solid var(--color-border);
  padding: var(--space-2) var(--space-3);
}

.base-table__row {
  border-bottom: 1px solid var(--color-border);
}

.base-table__row--hoverable:hover {
  background: var(--color-bg-secondary);
}

.base-table__row--clickable {
  cursor: pointer;
}

.base-table__td {
  padding: var(--space-3);
  font-size: var(--text-sm);
  color: var(--color-text-primary);
}

.base-table__empty {
  padding: var(--space-12) var(--space-4);
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}
</style>
```

- [ ] **Step 6: Create `frontend/src/components/base/ConfirmDialog.vue`**

```vue
<script setup lang="ts">
import BaseModal from './BaseModal.vue'
import BaseButton from './BaseButton.vue'

withDefaults(
  defineProps<{
    open: boolean
    title: string
    message: string
    confirmText?: string
    cancelText?: string
    variant?: 'danger' | 'default'
  }>(),
  {
    confirmText: '确认',
    cancelText: '取消',
    variant: 'default',
  },
)

const emit = defineEmits<{
  confirm: []
  cancel: []
}>()
</script>

<template>
  <BaseModal
    :open="open"
    :title="title"
    width="400px"
    @close="emit('cancel')"
  >
    <p class="confirm-dialog__message">{{ message }}</p>
    <template #footer>
      <BaseButton variant="ghost" size="sm" @click="emit('cancel')">
        {{ cancelText }}
      </BaseButton>
      <BaseButton
        :variant="variant === 'danger' ? 'danger' : 'primary'"
        size="sm"
        @click="emit('confirm')"
      >
        {{ confirmText }}
      </BaseButton>
    </template>
  </BaseModal>
</template>

<style scoped>
.confirm-dialog__message {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  line-height: var(--leading-normal);
}
</style>
```

- [ ] **Step 7: Commit**

```bash
cd /home/guixin/project_workspace/novelv3 && git add frontend/src/components/base/ && git commit -m "feat: add base component library (Button, Input, Modal, Badge, Table, ConfirmDialog)"
```

---

### Task 3: UI Store

**Files:**
- Create: `frontend/src/stores/ui.ts`

- [ ] **Step 1: Create `frontend/src/stores/ui.ts`**

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'

export type Workspace = 'hermes' | 'athena' | 'manuscript'
export type AthenaSection =
  | 'characters' | 'locations' | 'factions' | 'items' | 'relations' | 'rules'
  | 'projection' | 'timeline' | 'knowledge'
  | 'outline' | 'storyline' | 'proposals' | 'consistency'

export const useUiStore = defineStore('ui', () => {
  const activeWorkspace = ref<Workspace>('hermes')
  const subNavCollapsed = ref(false)
  const activeAthenaSection = ref<AthenaSection>('characters')
  const modals = ref<string[]>([])

  function toggleSubNav() {
    subNavCollapsed.value = !subNavCollapsed.value
  }

  function openModal(id: string) {
    if (!modals.value.includes(id)) modals.value.push(id)
  }

  function closeModal(id?: string) {
    if (id) {
      modals.value = modals.value.filter(m => m !== id)
    } else {
      modals.value.pop()
    }
  }

  function setWorkspace(ws: Workspace) {
    activeWorkspace.value = ws
  }

  function setAthenaSection(section: AthenaSection) {
    activeAthenaSection.value = section
  }

  return {
    activeWorkspace,
    subNavCollapsed,
    activeAthenaSection,
    modals,
    toggleSubNav,
    openModal,
    closeModal,
    setWorkspace,
    setAthenaSection,
  }
})
```

- [ ] **Step 2: Commit**

```bash
cd /home/guixin/project_workspace/novelv3 && git add frontend/src/stores/ui.ts && git commit -m "feat: add UI store for workspace, sub-nav, and modal state"
```

---

### Task 4: Layout Shell Components

**Files:**
- Create: `frontend/src/components/layout/TopBar.vue`
- Create: `frontend/src/components/layout/ActivityBar.vue`
- Create: `frontend/src/components/layout/SubNav.vue`
- Create: `frontend/src/components/layout/ContentArea.vue`
- Rewrite: `frontend/src/components/layout/AppShell.vue`

- [ ] **Step 1: Create `frontend/src/components/layout/TopBar.vue`**

```vue
<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  projectName?: string
  projects?: { id: string; title: string }[]
}>()

const emit = defineEmits<{
  'select-project': [id: string]
  'navigate-settings': []
}>()

const dropdownOpen = ref(false)
</script>

<template>
  <header class="topbar">
    <div class="topbar__left">
      <router-link to="/" class="topbar__brand">墨舟</router-link>
      <div v-if="projectName" class="topbar__project-selector">
        <button
          class="topbar__project-btn"
          @click="dropdownOpen = !dropdownOpen"
        >
          {{ projectName }}
          <span class="topbar__chevron">&#9662;</span>
        </button>
        <div v-if="dropdownOpen && projects?.length" class="topbar__dropdown">
          <button
            v-for="p in projects"
            :key="p.id"
            class="topbar__dropdown-item"
            @click="emit('select-project', p.id); dropdownOpen = false"
          >
            {{ p.title }}
          </button>
        </div>
      </div>
    </div>
    <div class="topbar__right">
      <button
        class="topbar__icon-btn"
        aria-label="设置"
        @click="emit('navigate-settings')"
      >
        &#9881;
      </button>
    </div>
  </header>
</template>

<style scoped>
.topbar {
  grid-area: topbar;
  height: var(--topbar-height);
  background: var(--color-bg-white);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--space-4);
  z-index: 40;
}

.topbar__left {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.topbar__brand {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-brand);
}

.topbar__project-selector {
  position: relative;
}

.topbar__project-btn {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-md);
  transition: background var(--transition-fast);
}
.topbar__project-btn:hover {
  background: var(--color-bg-secondary);
}

.topbar__chevron {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.topbar__dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: var(--space-1);
  background: var(--color-bg-white);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  min-width: 200px;
  z-index: 50;
  padding: var(--space-1) 0;
}

.topbar__dropdown-item {
  display: block;
  width: 100%;
  text-align: left;
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  transition: background var(--transition-fast);
}
.topbar__dropdown-item:hover {
  background: var(--color-bg-secondary);
}

.topbar__right {
  display: flex;
  align-items: center;
}

.topbar__icon-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  font-size: var(--text-lg);
  transition: all var(--transition-fast);
}
.topbar__icon-btn:hover {
  background: var(--color-bg-secondary);
  color: var(--color-text-primary);
}
</style>
```

- [ ] **Step 2: Create `frontend/src/components/layout/ActivityBar.vue`**

```vue
<script setup lang="ts">
import type { Workspace } from '../../stores/ui'

defineProps<{
  activeWorkspace: Workspace | null
  projectId: string
}>()

const emit = defineEmits<{
  navigate: [target: string]
}>()

const workspaceItems: { key: Workspace; icon: string; label: string; route: (id: string) => string }[] = [
  { key: 'hermes', icon: '☿', label: 'Hermes', route: (id) => `/projects/${id}/hermes` },
  { key: 'athena', icon: '⏣', label: 'Athena', route: (id) => `/projects/${id}/athena` },
  { key: 'manuscript', icon: '📜', label: 'Manuscript', route: (id) => `/projects/${id}/manuscript` },
]
</script>

<template>
  <aside class="activity-bar">
    <nav class="activity-bar__top">
      <button
        v-for="item in workspaceItems"
        :key="item.key"
        class="activity-bar__item"
        :class="{ 'activity-bar__item--active': activeWorkspace === item.key }"
        :title="item.label"
        :aria-label="item.label"
        @click="emit('navigate', item.route(projectId))"
      >
        <span class="activity-bar__icon">{{ item.icon }}</span>
      </button>
    </nav>
    <nav class="activity-bar__bottom">
      <button
        class="activity-bar__item"
        title="设置"
        aria-label="设置"
        @click="emit('navigate', '/settings')"
      >
        <span class="activity-bar__icon">&#9881;</span>
      </button>
    </nav>
  </aside>
</template>

<style scoped>
.activity-bar {
  grid-area: activity;
  width: var(--activity-bar-width);
  background: var(--color-activity-bar-bg);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) 0;
}

.activity-bar__top,
.activity-bar__bottom {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-1);
}

.activity-bar__item {
  position: relative;
  width: var(--activity-bar-width);
  height: var(--activity-bar-width);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-activity-bar-icon);
  transition: color var(--transition-fast);
}

.activity-bar__item:hover {
  color: var(--color-activity-bar-icon-active);
}

.activity-bar__item--active {
  color: var(--color-activity-bar-icon-active);
  background: var(--color-activity-bar-item-active-bg);
}

.activity-bar__item--active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 24px;
  background: var(--color-activity-bar-accent);
  border-radius: 0 2px 2px 0;
}

.activity-bar__icon {
  font-size: var(--text-lg);
  line-height: 1;
}
</style>
```

- [ ] **Step 3: Create `frontend/src/components/layout/SubNav.vue`**

```vue
<script setup lang="ts">
defineProps<{
  collapsed: boolean
}>()

const emit = defineEmits<{
  'toggle-collapse': []
}>()
</script>

<template>
  <aside
    class="subnav"
    :class="{ 'subnav--collapsed': collapsed }"
  >
    <div class="subnav__content">
      <slot />
    </div>
    <button
      class="subnav__toggle"
      :aria-label="collapsed ? '展开侧栏' : '收起侧栏'"
      @click="emit('toggle-collapse')"
    >
      {{ collapsed ? '›' : '‹' }}
    </button>
  </aside>
</template>

<style scoped>
.subnav {
  grid-area: subnav;
  width: var(--subnav-width);
  background: var(--color-bg-primary);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: width var(--transition-normal);
  position: relative;
}

.subnav--collapsed {
  width: 0;
  border-right: none;
}

.subnav__content {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-2) 0;
}

.subnav--collapsed .subnav__content {
  visibility: hidden;
}

.subnav__toggle {
  position: absolute;
  top: var(--space-2);
  right: var(--space-2);
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
  z-index: 1;
}
.subnav__toggle:hover {
  background: var(--color-bg-secondary);
  color: var(--color-text-primary);
}

.subnav--collapsed .subnav__toggle {
  right: -24px;
  background: var(--color-bg-white);
  border: 1px solid var(--color-border);
}
</style>
```

- [ ] **Step 4: Create `frontend/src/components/layout/ContentArea.vue`**

```vue
<script setup lang="ts">
</script>

<template>
  <main class="content-area">
    <slot />
  </main>
</template>

<style scoped>
.content-area {
  grid-area: content;
  overflow-y: auto;
  padding: var(--content-padding);
  background: var(--color-bg-white);
}
</style>
```

- [ ] **Step 5: Rewrite `frontend/src/components/layout/AppShell.vue`**

Replace the entire file contents with:

```vue
<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUiStore } from '../../stores/ui'
import { useProjectStore } from '../../stores/project'
import TopBar from './TopBar.vue'
import ActivityBar from './ActivityBar.vue'
import SubNav from './SubNav.vue'
import ContentArea from './ContentArea.vue'

const route = useRoute()
const router = useRouter()
const ui = useUiStore()
const projectStore = useProjectStore()

const showSidebar = computed(() => route.meta.showSidebar === true)
const workspace = computed(() => (route.meta.workspace as string | null) ?? null)

const projectId = computed(() => {
  const id = route.params.id
  return typeof id === 'string' ? id : null
})

const projectName = computed(() => projectStore.currentProject?.title)

const projectList = computed(() =>
  projectStore.projects.map((p: any) => ({ id: String(p.id), title: p.title })),
)

function onSelectProject(id: string) {
  router.push(`/projects/${id}/hermes`)
}

function onNavigateSettings() {
  router.push('/settings')
}

function onActivityNavigate(target: string) {
  router.push(target)
}
</script>

<template>
  <div
    class="app-shell"
    :class="{
      'app-shell--no-sidebar': !showSidebar,
      'app-shell--subnav-collapsed': showSidebar && ui.subNavCollapsed,
    }"
  >
    <TopBar
      :project-name="showSidebar ? projectName : undefined"
      :projects="projectList"
      @select-project="onSelectProject"
      @navigate-settings="onNavigateSettings"
    />
    <template v-if="showSidebar && projectId">
      <ActivityBar
        :active-workspace="(workspace as any)"
        :project-id="projectId"
        @navigate="onActivityNavigate"
      />
      <SubNav
        :collapsed="ui.subNavCollapsed"
        @toggle-collapse="ui.toggleSubNav()"
      >
        <!-- Plan B will fill sub-nav content per workspace -->
      </SubNav>
    </template>
    <ContentArea>
      <slot />
    </ContentArea>
  </div>
</template>

<style scoped>
.app-shell {
  display: grid;
  grid-template-rows: var(--topbar-height) 1fr;
  grid-template-columns: var(--activity-bar-width) var(--subnav-width) 1fr;
  grid-template-areas:
    "topbar   topbar   topbar"
    "activity subnav   content";
  height: 100vh;
  overflow: hidden;
}

.app-shell--subnav-collapsed {
  grid-template-columns: var(--activity-bar-width) 0px 1fr;
}

.app-shell--no-sidebar {
  grid-template-columns: 1fr;
  grid-template-areas:
    "topbar"
    "content";
}
</style>
```

- [ ] **Step 6: Commit**

```bash
cd /home/guixin/project_workspace/novelv3 && git add frontend/src/components/layout/ && git commit -m "feat: add layout shell components (TopBar, ActivityBar, SubNav, ContentArea, AppShell)"
```

---

### Task 5: Router Refactor

**Files:**
- Rewrite: `frontend/src/router/index.ts`

- [ ] **Step 1: Rewrite `frontend/src/router/index.ts`**

Replace the entire file contents with:

```typescript
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

// Keep OLD view components as route targets so the app still works.
// Plan B will create the new view components and swap them in.
import ProjectList from '../views/ProjectList.vue'
import ProjectDetail from '../views/ProjectDetail.vue'
import AthenaView from '../views/AthenaView.vue'
import ManuscriptPlaceholder from '../views/ManuscriptPlaceholder.vue'
import SettingsView from '../views/SettingsView.vue'

export interface AppRouteMeta {
  showSidebar: boolean
  workspace: 'hermes' | 'athena' | 'manuscript' | null
}

declare module 'vue-router' {
  interface RouteMeta extends Partial<AppRouteMeta> {}
}

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: ProjectList,
    meta: { showSidebar: false, workspace: null } satisfies AppRouteMeta,
  },
  {
    path: '/projects/:id',
    redirect: (to) => `/projects/${to.params.id}/hermes`,
  },
  {
    path: '/projects/:id/hermes',
    component: ProjectDetail,
    meta: { showSidebar: true, workspace: 'hermes' } satisfies AppRouteMeta,
  },
  {
    path: '/projects/:id/athena',
    component: AthenaView,
    meta: { showSidebar: true, workspace: 'athena' } satisfies AppRouteMeta,
  },
  {
    path: '/projects/:id/athena/:section',
    component: AthenaView,
    meta: { showSidebar: true, workspace: 'athena' } satisfies AppRouteMeta,
  },
  {
    path: '/projects/:id/manuscript',
    component: ManuscriptPlaceholder,
    meta: { showSidebar: true, workspace: 'manuscript' } satisfies AppRouteMeta,
  },
  {
    path: '/settings',
    component: SettingsView,
    meta: { showSidebar: false, workspace: null } satisfies AppRouteMeta,
  },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
```

Key changes from the old router:
- `AppRouteMeta` now uses `showSidebar` + `workspace` instead of `shellMode` + `shellSurface` + `navSection`
- `/projects/:id` redirects to `/projects/:id/hermes` instead of rendering `ProjectDetail` directly
- New `/projects/:id/hermes` route points to `ProjectDetail` (temporary, Plan B swaps to `HermesView`)
- New `/projects/:id/athena/:section` route for deep-linking Athena sections
- `RouteMeta` module augmentation so `route.meta.showSidebar` and `route.meta.workspace` are typed

- [ ] **Step 2: Commit**

```bash
cd /home/guixin/project_workspace/novelv3 && git add frontend/src/router/index.ts && git commit -m "feat: refactor router with workspace-aware meta and hermes redirect"
```

---

### Task 6: Update App.vue

**Files:**
- Rewrite: `frontend/src/App.vue`

- [ ] **Step 1: Rewrite `frontend/src/App.vue`**

Replace the entire file contents with:

```vue
<script setup lang="ts">
import AppShell from './components/layout/AppShell.vue'
</script>

<template>
  <AppShell>
    <router-view />
  </AppShell>
</template>
```

This removes:
- The old `shellMode` / `shellSurface` computed properties
- The old `pageMeta` route meta reading (now handled inside `AppShell`)
- The old prop passing to `AppShell`

- [ ] **Step 2: Commit**

```bash
cd /home/guixin/project_workspace/novelv3 && git add frontend/src/App.vue && git commit -m "feat: simplify App.vue to use new AppShell layout"
```

---

### Task 7: Verification

**Files:** None (verification only)

- [ ] **Step 1: TypeScript type check**

```bash
cd /home/guixin/project_workspace/novelv3/frontend && npx vue-tsc --noEmit
```

Expected: exits 0 with no errors. If there are errors, fix them before proceeding. Common issues:
- Old components referencing removed CSS variables — these still work since the old components use scoped styles or Tailwind classes, not the removed `:root` vars. If any component directly references a removed var (e.g. `var(--paper-bg)`), add a temporary fallback or update the component.
- `route.meta.shellMode` references in old views — the `RouteMeta` augmentation makes these `Partial`, so they won't error, but check for any strict usage.

- [ ] **Step 2: Build check**

```bash
cd /home/guixin/project_workspace/novelv3/frontend && npm run build
```

Expected: exits 0, writes to `../backend/static/`.

- [ ] **Step 3: Run tests**

```bash
cd /home/guixin/project_workspace/novelv3/frontend && npx vitest run
```

Expected: all existing tests pass. If any test references old `AppShell` props (`mode`, `surface`) or old CSS classes (`.app-top-nav`, `.app-shell__surface`), update the test to match the new structure.

Common test fixes needed:
- Tests that mount `AppShell` with `mode`/`surface` props — remove those props
- Tests that assert on `.app-top-nav` — update to `.topbar`
- Tests that check for old CSS variable values — update to new token values

- [ ] **Step 4: Fix any issues found in Steps 1-3, then commit**

```bash
cd /home/guixin/project_workspace/novelv3 && git add -A && git commit -m "fix: resolve type/build/test issues from Plan A foundation"
```

---

### Summary of What Plan A Delivers

After completing all 7 tasks, the app will have:

1. A clean design token system in `src/styles/` replacing the old paper/hermes/athena CSS variables
2. Six base components in `src/components/base/` ready for use by page views
3. A `ui` Pinia store managing workspace state, sub-nav collapse, and modal stack
4. A VS Code-style layout shell with TopBar + ActivityBar + SubNav + ContentArea
5. A workspace-aware router with `/projects/:id/hermes` as the default project route
6. A simplified `App.vue` that delegates layout to `AppShell`

The old page views (`ProjectList`, `ProjectDetail`, `AthenaView`, `ManuscriptPlaceholder`, `SettingsView`) continue to render inside the new shell. Plan B will rebuild each view to use the new base components and design tokens.
