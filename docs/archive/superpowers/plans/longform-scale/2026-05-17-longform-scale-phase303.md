# Longform Scale Phase 303 - Route Core Generation Through Project Model

## Goal

Ensure core long-form generation uses the project configured model, so model choice stays consistent across setup, storyline, outline, and chapter generation.

## Finding

The model call traces recorded `project.ai_model`, but several actual `ai_service.complete()` calls did not pass `model`. They therefore fell back to the adapter default, which could silently diverge from the project model recorded in traces and degrade long-running quality control.

## TDD Evidence

RED:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_setups.py::test_generate_setup_uses_project_ai_model backend\tests\test_storylines.py::test_generate_storyline_uses_project_ai_model backend\tests\test_outlines.py::test_generate_outline_uses_project_ai_model backend\tests\test_chapters.py::test_generate_chapter_uses_project_ai_model -q
```

Observed failure:

```text
KeyError: 'model'
```

GREEN:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_setups.py::test_generate_setup_uses_project_ai_model backend\tests\test_storylines.py::test_generate_storyline_uses_project_ai_model backend\tests\test_outlines.py::test_generate_outline_uses_project_ai_model backend\tests\test_chapters.py::test_generate_chapter_uses_project_ai_model -q
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_setups.py backend\tests\test_storylines.py backend\tests\test_outlines.py backend\tests\test_chapters.py -q
```

Observed result:

```text
4 passed
61 passed
```

## Change

- Setup generation passes `model=project.ai_model or "deepseek-chat"`.
- Storyline generation passes `model=project.ai_model or "deepseek-chat"`.
- Outline generation passes `model=project.ai_model or "deepseek-chat"`.
- Chapter generation passes `model=project.ai_model or "deepseek-chat"`.

## Verification

Full phase gate passed:

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` - 697 passed
- `npm run build` - passed
- `npm run test:unit -- --run` - 440 passed
- `git diff --check` - passed
- DeepSeek key scan - `NO_MATCH`
