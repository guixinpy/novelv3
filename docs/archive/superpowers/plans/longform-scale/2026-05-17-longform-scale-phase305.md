# Longform Scale Phase 305 - Inject Project Chapter Length Target

## Goal

Keep long-form chapter pacing aligned with project targets by deriving a per-chapter word range from `target_word_count` and `target_chapter_count`.

## Finding

Chapter generation only applied length constraints when the user explicitly wrote a word range in feedback. A 1000 chapter / 1,000,000 word project therefore did not automatically tell the model that each chapter should stay near 1000 words, which could cause long-term pacing drift.

## TDD Evidence

RED:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_prompting_chapter_migration.py::test_chapter_payload_injects_project_word_target_without_user_range -q
```

Observed failure:

```text
assert '项目计划约1000000字 / 1000章' in message
```

GREEN:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_prompting_chapter_migration.py::test_chapter_payload_injects_project_word_target_without_user_range -q
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_prompting_chapter_migration.py backend\tests\test_chapters.py -q
```

Observed result:

```text
1 passed
46 passed
```

## Change

- Chapter prompt context now adds a high-priority `target_chapter_length` generation constraint when the project has both target words and target chapters.
- The generated range is 85%-115% of average words per chapter.
- Explicit user feedback word ranges still take precedence and suppress the project-derived length block.
- Default chapter `max_tokens` now follows the project-derived upper range when no user word range is present.

## Verification

Full phase gate passed:

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` - 699 passed
- `npm run build` - passed
- `npm run test:unit -- --run` - 441 passed
- `git diff --check` - passed
- DeepSeek key scan - `NO_MATCH`
