---
name: verify
description: Full verification — pytest, vitest, TypeScript type check, and frontend build. Use before marking work complete or creating PRs.
---

Run all verification steps. Stop at the first failure and report it.

1. Backend tests (from `backend/`):
   ```bash
   pytest
   ```

2. Frontend tests (from `frontend/`):
   ```bash
   npm run test:unit
   ```

3. TypeScript type check (from `frontend/`):
   ```bash
   npx vue-tsc --noEmit
   ```

4. Frontend build (from `frontend/`):
   ```bash
   npm run build
   ```

All four must pass. If any step fails, fix the issue and re-run from that step.
