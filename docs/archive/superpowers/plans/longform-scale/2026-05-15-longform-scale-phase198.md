# Phase 198 - Project Athena Dialog Plotline Previews

## Problem

Athena dialog planning context only displayed five storyline previews, but it
retrieved each preview with `json_extract(storylines.plotlines, '$[n]')`. When a
plotline contains a large milestone tree, this still reads a full plotline object
before the prompt summary is compacted.

## Change

- Strengthened the long-form regression test so storyline previews include 1000
  milestones per plotline.
- Replaced indexed full-object `json_extract(storylines.plotlines, '$[n]')`
  preview columns with a `json_each(storylines.plotlines)` projection.
- Projected only preview fields needed by the summary: title/name/id, summary,
  description, and theme.
- Kept the existing visible dialog behavior:
  - total storyline count is still reported.
  - only the first five storyline summaries are shown.
  - milestone details are not included in dialog context.

## Tests

- RED: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_athena_dialog_planning_summary_does_not_select_large_narrative_json -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_athena_dialog_planning_summary_does_not_select_large_narrative_json -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py backend\tests\test_athena_dialog.py backend\tests\test_prompting_dialog_migration.py -q` (`65 passed`)
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` (`601 passed`)
- GREEN: `npm run build` from `frontend`
- GREEN: `npm run test:unit` from `frontend` (`407 passed`)
- GREEN: `git diff --check`
- GREEN: DeepSeek key scan returned `NO_MATCH`

## Result

Athena dialog context no longer reads full plotline preview objects when building
the narrative-planning summary. This keeps ordinary user conversations cheaper
and safer for thousand-chapter projects with dense milestone planning.
