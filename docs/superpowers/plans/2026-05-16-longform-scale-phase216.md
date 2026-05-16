# Phase 216: Bound Outline Setup Loading

## Goal

Remove full `Setup` JSON materialization from outline generation so long-form projects can generate thousand-chapter outlines without loading oversized setup payloads into the request path.

## Verification

- RED: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_outlines.py::test_generate_outline_uses_bounded_setup_context_without_selecting_full_json -q`
  - Failed because outline generation selected full setup JSON fields.
- GREEN: same targeted test passes after switching the setup lookup to bounded SQL projections.

## Notes

- Storyline context was already windowed through `json_each`; this phase targets the remaining setup payload.
- The prompt still includes readable Chinese setup keys after JSON snippet normalization.
