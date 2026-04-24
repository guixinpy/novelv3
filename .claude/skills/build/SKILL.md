---
name: build
description: Build the frontend and verify TypeScript + Vite compilation. Use after frontend changes.
---

Build the frontend SPA bundle into `backend/static/`.

From `frontend/`:
```bash
npm run build
```

This runs `vue-tsc --noEmit && vite build`. If TypeScript compilation or Vite bundling fails, fix the errors before proceeding.

Note: FastAPI serves the built bundle from `backend/static/` with SPA fallback. Rebuild is required for backend to serve updated UI.
