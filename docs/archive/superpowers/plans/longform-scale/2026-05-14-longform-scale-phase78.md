# Longform Scale Phase 78 - Background Task Idempotency

## Goal

Reduce duplicate long-running chapter-range work at thousand-chapter scale by reusing an active background task when the caller submits the same `idempotency_key` again.

## Success Criteria

- `create_chapter_range` returns the existing pending/running task for the same project, task type, and idempotency key.
- Failed, cancelled, or completed tasks are not reused, so explicit retries can still create new work.
- Existing range progress, retry, interruption recovery, and task listing behavior remains green.

## Verification

- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_background.py -k "idempotency" -q --basetemp .tmp\pytest`  
  Result: `1 passed, 18 deselected`
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_background.py -q --basetemp .tmp\pytest`  
  Result: `19 passed`
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests -q --basetemp .tmp\pytest`  
  Result: `506 passed`

