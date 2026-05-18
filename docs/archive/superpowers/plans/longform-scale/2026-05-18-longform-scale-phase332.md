# Phase 332: Prevent Outline-Like Chapter Output In Prompt

## Goal

Move the outline-like chapter defense earlier in the generation path by making the chapter prompt explicitly require continuous prose.

## Scope

- Update `chapter.generate` template.
- Require continuous novel prose scenes.
- Forbid outline, scene list, role list, summary, objective, conflict, foreshadowing, ending, bullets, or numbered-list formats as substitutes for prose.

## Verification

- RED confirmed:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_prompting_chapter_migration.py::test_chapter_payload_requires_continuous_prose_not_outline_format -q`
  - Failed because the final model message did not contain the prose-format constraint.
- GREEN confirmed:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_prompting_chapter_migration.py::test_chapter_payload_requires_continuous_prose_not_outline_format -q`
  - `1 passed`
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_prompting_chapter_migration.py -q`
  - `11 passed`

## Notes

This complements the existing post-generation `chapter_prose_quality` warning. The prompt now reduces the chance of outline-like output, while diagnostics still catch violations.
