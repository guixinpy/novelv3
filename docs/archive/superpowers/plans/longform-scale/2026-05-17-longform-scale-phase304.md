# Longform Scale Phase 304 - Expose Project Model Selection

## Goal

Make the project model route configurable by users instead of only honoring a database field that could not be set through normal project creation or update.

## Finding

Phase 303 made setup, storyline, outline, and chapter generation respect `project.ai_model`, but the project create/update API ignored `ai_model`, and the new project form had no model selector. That left the model routing capability incomplete for real long-form use.

## TDD Evidence

RED:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_projects.py::test_project_persists_ai_model -q
npm run test:unit -- --run src/views/ProjectListView.test.ts -t "AI model|target word"
```

Observed failures:

```text
assert 'deepseek-chat' == 'deepseek-reasoner'
expected spy to be called with ai_model
expected model select to be truthy
```

GREEN:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_projects.py::test_project_persists_ai_model -q
npm run test:unit -- --run src/views/ProjectListView.test.ts -t "AI model|target word"
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_projects.py -q
npm run test:unit -- --run src/views/ProjectListView.test.ts
```

Observed result:

```text
1 passed
2 passed, 3 skipped
13 passed
5 passed
```

## Change

- `ProjectCreate` accepts `ai_model`, defaulting to `deepseek-chat`.
- `ProjectUpdate` accepts `ai_model`.
- The new project modal includes a model select with `DeepSeek Chat` and `DeepSeek Reasoner`.
- Project creation sends `ai_model` in the payload and resets it to the default after successful creation.

## Verification

Browser rendering check passed using local Chrome against a temporary Vite server:

```text
options: deepseek-chat, deepseek-reasoner
visible: true
select size: 369 x 36
```

Full phase gate passed:

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` - 698 passed
- `npm run build` - passed
- `npm run test:unit -- --run` - 441 passed
- `git diff --check` - passed
- DeepSeek key scan - `NO_MATCH`
