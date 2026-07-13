# Type Safety

> Type safety patterns in this project.

---

## Overview

The frontend uses **TypeScript 5.6** with `strict: true`. The backend uses
**Pydantic v2** for runtime validation. Types are shared by convention (not by
shared package) — the frontend `api/types.ts` manually mirrors the backend
Pydantic schemas.

---

## Frontend Type Organization

### API types (`api/types.ts`)

A single barrel file (~1233 lines) containing all API request/response types:

```typescript
// api/types.ts
export interface Project {
  id: string
  name: string
  genre: string | null
  created_at: string  // ISO 8601 from backend
  updated_at: string
}

export interface ProjectCreate {
  name: string
  genre?: string
  target_chapter_count?: number
}

export interface ProjectOut extends Project {
  // response-only fields
  stats?: ProjectStats
}
```

### Component props (in component files)

```typescript
// Inline with defineProps generics
const props = withDefaults(defineProps<{
  open: boolean
  title?: string
  width?: string
}>(), { width: '480px' })
```

### Store state (in store files)

```typescript
// Explicit interfaces for store state
interface AgentRun {
  id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  tool_calls: ToolCall[]
  // ...
}
```

---

## Validation

### Backend (Pydantic v2)

Pydantic provides runtime validation on API boundaries:

```python
from pydantic import BaseModel, ConfigDict

class ProjectCreate(BaseModel):
    name: str
    genre: str | None = None
    target_chapter_count: int | None = None

class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    genre: str | None = None
    # ...
```

### Frontend

No runtime validation library (no Zod, Yup, or io-ts). The frontend trusts the
backend to validate input. Display-side validation uses TypeScript types and
simple guards:

```typescript
// Simple type guard for optional fields
function isComplete(project: Project): boolean {
  return project.name.length > 0 && project.genre !== null
}
```

---

## Common Type Patterns

### Discriminated unions for status

```typescript
type RunStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'

interface AgentRun {
  status: RunStatus
  // status-specific fields
  error?: string       // only when status === 'failed'
  result?: unknown     // only when status === 'completed'
}
```

### Literal types with `as const`

```typescript
export const PROJECT_CACHE_TTL_MS = 30_000 as const
export const CHAT_HISTORY_PAGE_SIZE = 50 as const
```

### `satisfies` for route meta

```typescript
const routes = [
  {
    path: '/projects/:id/hermes',
    meta: { title: '写作', icon: 'edit' } satisfies AppRouteMeta,
  },
]
```

### Backend JSON fields → frontend types

SQLAlchemy `JSON` columns map to frontend interfaces:

```typescript
// Backend: metadata = Column(JSON, default=dict)
// Frontend:
interface ProjectMeta {
  target_audience?: string
  themes?: string[]
  style_notes?: string
}
```

---

## Forbidden Patterns

1. **`as` type assertions for API responses** — The client's generic `<T>`
   should match the actual response structure.
2. **`any` in store state** — Use explicit interfaces or `unknown`.
3. **Inline type casts to access nested fields** — Define an interface first.
4. **`// @ts-ignore` without explanation** — If needed, document why.
5. **Mutating props directly** — Props are readonly; use events or v-model.

---

## Common Mistakes

1. **`as` casting API responses** — A wrong cast hides real type mismatches
   between frontend and backend. Let the type system catch them.
2. **Type drift between `api/types.ts` and backend schemas** — When adding
   backend fields, always update the matching frontend type.
3. **Overly broad types** — `string` for a constrained set of values should be
   a union type (`'draft' | 'published'`), not `string`.
4. **Not using `satisfies` for route meta** — Plain object literals in route
   config miss type checking on the meta fields.
