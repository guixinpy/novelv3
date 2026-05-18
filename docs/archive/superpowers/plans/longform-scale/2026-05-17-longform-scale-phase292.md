# Longform Scale Phase 292 - Real Continuous Writing Range Tasks

## Assumption

For long web novels, "start writing" should not require the author to manually click once per chapter when the project has a known chapter target.

## Risk

The previous background task only generated the current chapter. In a 1000 chapter project, that made the continuous-writing control effectively single-step and unsuitable for long-running production writing.

## Change

1. When a project has an effective chapter target, writing start/resume creates a range-backed `generate_chapter` task from current chapter to target.
2. The background work loops through the range, generates chapters sequentially, and records compact range progress.
3. If the user pauses while a chapter is being generated, chapter completion preserves the paused state and the range task stops before the next chapter.
4. Projects without a known chapter target still use the previous one-chapter task behavior.

## Verification

- Red: `backend\\.venv\\Scripts\\python.exe -m pytest backend\\tests\\test_writing.py -q` failed because start did not create a chapter range and work stopped after one chapter.
- Green: `backend\\.venv\\Scripts\\python.exe -m pytest backend\\tests\\test_writing.py -q` passed with 22 tests.
- Related: `backend\\.venv\\Scripts\\python.exe -m pytest backend\\tests\\test_background.py backend\\tests\\test_writing.py -q` passed with 53 tests.
- Full verification will run before commit.
