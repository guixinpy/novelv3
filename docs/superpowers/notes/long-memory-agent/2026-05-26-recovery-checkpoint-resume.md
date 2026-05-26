# Recovery Checkpoint Resume Slice

## Scope

Task 8 adds a checkpoint resume preview for longform chapter batch work. It does
not introduce a new queue or event store. The preview is derived from persisted
`BackgroundTask`, `WritingAgentStep`, chapter records, and batch execution
checkpoints.

## Implementation

- Added `CHECKPOINT_RESUME_PREVIEW_VERSION` and a small resume policy builder.
- Added `execution_checkpoints_for_resume(...)` to normalize batch execution
  checkpoints for recovery planning.
- Added `build_checkpoint_resume_preview(...)` to report:
  - completed/skipped chapter indexes;
  - blocked chapter indexes;
  - pending chapter indexes;
  - next chapter index and resume range;
  - checkpoint evidence from task progress, execution checkpoints, chapter
    records, and writing-agent steps.

## Verification

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_recovery_checkpoint_resume.py -q
# 1 passed

backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_recovery_checkpoint_resume.py backend\tests\test_writing_agent_planner.py backend\tests\test_writing_agent_runs.py -k "recovery or checkpoint_resume or recovery_tool_plan" -q
# 14 passed, 181 deselected

backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_tool_executor.py -k "recovery or execute_longform_chapter_batch or prepare_longform_chapter_batch" -q
# 8 passed, 151 deselected

git diff --check
# no output
```

## Boundary

The preview deliberately reports the next recovery boundary instead of mutating
task payloads. If dogfood shows that preflight must consume progress directly,
that should be handled as a separate execution-path fix with its own regression
test.
