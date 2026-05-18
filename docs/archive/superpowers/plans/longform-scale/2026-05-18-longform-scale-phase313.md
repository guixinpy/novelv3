# Longform Scale Phase 313 - Report Project Word Target Drift

## Goal

Expose project-level chapter word-count drift in longform maintenance diagnostics.

## Finding

Single-chapter drift is useful while reviewing one chapter, but 1000-chapter projects need an aggregate view: how many chapters are below range, within range, or above range, and which chapters need attention first.

## TDD Evidence

RED:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_maintenance_diagnostics_reports_word_target_drift -q
```

Observed failure:

```text
KeyError: 'word_target'
```

GREEN:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_maintenance_diagnostics_reports_word_target_drift -q
```

Observed result:

```text
1 passed
```

## Change

- Longform maintenance diagnostics now include `word_target`.
- The payload reports target average/range, under/within/over counts, and limited chapter index lists for under-target and over-target chapters.
- The diagnostics query still avoids selecting chapter content.
- Frontend API types now include the optional `word_target` diagnostics shape.

## Verification

Stage gate:

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py -q` -> `47 passed`

Full phase gate:

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` -> `704 passed`
- `npm run build` -> passed
- `npm run test:unit -- --run` -> `444 passed`
- `git diff --check` -> passed
- DeepSeek key scan -> `NO_MATCH`
