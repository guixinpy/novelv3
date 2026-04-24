---
name: test
description: Run all tests — backend pytest and frontend vitest. Use before marking work complete.
---

Run the full test suite for both backend and frontend.

1. Backend (from `backend/`):
   ```bash
   pytest
   ```

2. Frontend (from `frontend/`):
   ```bash
   npm run test:unit
   ```

If either fails, report the failure and do not claim the work is complete until tests pass.
