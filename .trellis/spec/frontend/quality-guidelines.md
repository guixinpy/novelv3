# Quality Guidelines

> Code quality standards for frontend development.

---

## Overview

- **Language**: TypeScript 5.6 (strict mode)
- **Framework**: Vue 3.5 with Composition API
- **Build**: Vite 5.4
- **Linter**: ESLint 10 + `eslint-plugin-vue` + `typescript-eslint`
- **Unit tests**: Vitest 2.1 + `@vue/test-utils` 2.4
- **E2E tests**: Playwright 1.59
- **CSS**: TailwindCSS 3.4 + CSS variables + scoped styles

Configuration files: `frontend/eslint.config.js`, `frontend/tsconfig.json`,
`frontend/vite.config.ts`, `frontend/playwright.config.ts`.

---

## TypeScript Configuration

```jsonc
// frontend/tsconfig.json (strict mode)
{
  "compilerOptions": {
    "strict": true,
    "target": "ES2020",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "preserve",
    "paths": { "@/*": ["./src/*"] }
  }
}
```

---

## Testing Requirements

### Unit tests (Vitest)

- **Location**: Co-located next to source file: `ComponentName.test.ts`
- **DOM environment**: `// @vitest-environment jsdom` at top of file
- **Structure**: `describe` / `it` blocks, Vitest globals

```typescript
// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import BaseModal from './BaseModal.vue'

describe('BaseModal', () => {
  it('emits close on backdrop click', async () => {
    const wrapper = mount(BaseModal, { props: { open: true } })
    await wrapper.find('.base-modal__backdrop').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })
})
```

### E2E tests (Playwright)

- **Location**: `frontend/e2e/*.spec.ts`
- **Configuration**: `frontend/playwright.config.ts`

---

## Required Patterns

- **`<script setup lang="ts">`** on all Vue components
- **TypeScript strict mode** — avoid `any`, prefer `unknown` + type guards
- **`model_config = ConfigDict(from_attributes=True)`** on Pydantic `XOut` schemas
- **`as const`** for literal types and constants
- **`satisfies` operator** for Vue Router meta types

---

## Forbidden Patterns

1. **`any` type** — Use `unknown` with type guards instead.
2. **Direct DOM manipulation** — Use Vue refs and template bindings.
3. **`watch` with deep:true on large objects** — Use computed or specific paths.
4. **`setTimeout` for polling** without cleanup — Always clear in `onUnmounted()`.
5. **Magic strings in multiple places** — Extract to constants or `as const` enums.
6. **`console.log()` in production code** — Remove before committing.
7. **`any` cast in API client** — Response types must match the endpoint.

---

## Code Review Checklist

- [ ] TypeScript strict — no `any`, no `@ts-ignore` without comment
- [ ] Component uses `<script setup lang="ts">`
- [ ] Props and emits are typed with generics
- [ ] No `console.log()` statements
- [ ] No magic strings — extracted to constants or enums
- [ ] Test covers rendering and at least one interaction
- [ ] Scoped styles use BEM-like class names, not element selectors
- [ ] Unused imports removed
