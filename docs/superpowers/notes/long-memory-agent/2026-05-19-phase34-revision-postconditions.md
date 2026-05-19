# Phase34 Revision Postconditions Report

## Objective

Prevent chapter compression/revision from reporting `completed` when explicit forbidden terms remain in the revised chapter.

## Why This Phase

Phase33 showed a concrete dogfood failure: Chapter 19 needed hard N-07 reveal phrases removed, but `compress_chapter_to_target` returned `completed` while forbidden reveal content still remained. Manual deterministic correction fixed the chapter, but the tool contract was too weak for long autonomous writing.

## Implementation

- Added optional `forbidden_terms` support to `compress_chapter_to_target`.
- Threaded `forbidden_terms` through the Writing Agent `compress_chapter_to_target` tool params.
- Added deterministic postcondition checks after every candidate:
  - length must be inside target range;
  - all forbidden terms must be absent;
  - otherwise the attempt is marked failed and retried.
- Added `forbidden_terms_remaining` blocked result when all attempts still contain forbidden terms.
- Added retry prompt guidance for the forbidden-term failure case.
- Added response metadata:
  - `forbidden_terms`;
  - `remaining_forbidden_terms`;
  - `postcondition_retry_count`;
  - per-attempt `remaining_forbidden_terms`.

## Tests

New focused tests:

- `test_agent_compress_chapter_to_target_retries_when_forbidden_terms_remain`
  - First model candidate contains `我就是N-07`.
  - Tool retries.
  - Second candidate removes it and writes the revision.
- `test_agent_compress_chapter_to_target_blocks_when_forbidden_terms_survive_all_attempts`
  - All model candidates contain `我就是N-07`.
  - Tool returns `blocked`.
  - Original chapter content is not overwritten.

Existing compression tests were updated where needed to pass `target_max_word_count=2300`. This keeps those tests focused on compression mechanics after the project default range changed to elastic `2000-3000`.

## Validation

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_retries_when_forbidden_terms_remain tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_blocks_when_forbidden_terms_survive_all_attempts -q
```

Result: `2 passed in 0.32s`.

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "compress_chapter_to_target or premature_mystery_reveal or review_chapter_quality"
```

Result: `26 passed, 85 deselected in 2.59s`.

## Dogfood State

Project: `25fa2b20-5b9f-473b-918b-f4ea491cbb60`

- latest chapter index: `19`
- Chapter 19 title: `暗网迷途`
- Chapter 19 word count: `2322`
- forbidden reveal terms present: `[]`
- pending world proposals: `0`
- longform maintenance: `current`
- ready for writing: `True`
- maintenance issue count: `0`
- latest synced chapter index: `19`

## Notes

- The new postcondition is intentionally literal and explicit. It does not attempt semantic contradiction detection.
- For future Agent tools, explicit “must remove X” requirements should become structured postconditions wherever possible, not only natural-language prompt text.
- A later phase can add equivalent postconditions to `expand_chapter_to_target` and planner patch flows if dogfood exposes the same failure class there.
