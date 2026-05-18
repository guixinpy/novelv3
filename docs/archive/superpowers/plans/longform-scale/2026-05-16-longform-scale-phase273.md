# Longform Scale Phase 273 - Advance Writing Pointer After Completion

## Goal

After a chapter generation succeeds, the reloadable writing state should point to the next chapter to write. This prevents Hermes writing controls from regenerating the same completed chapter on the next start.

## Scope

- Advance `writing_states.current_chapter` to at least `chapter_index + 1` in `complete_chapter`.
- Do not move the pointer backward when an older chapter is regenerated.
- Update backend tests to treat `current_chapter` as the next writing target after success.

## RED

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py -q -k "after_completed_chapter"`
  - Failed because completing chapter 1 left `current_chapter=1`, so the next start queued chapter 1 again.

## GREEN

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py -q -k "after_completed_chapter"`
  - `1 passed`, `11 deselected`
- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py backend\tests\test_chapters.py -q -k "writing_state"`
  - `4 passed`, `37 deselected`

## Related Verification

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py backend\tests\test_chapters.py -q`
  - `41 passed`

## Full Verification

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
  - `662 passed`
- `npm run build`
  - `vue-tsc --noEmit && vite build` passed
- `npm run test:unit -- --run`
  - `64 passed`, `431 passed`
- `git diff --check`
  - Passed
- DeepSeek key scan
  - `NO_MATCH`
