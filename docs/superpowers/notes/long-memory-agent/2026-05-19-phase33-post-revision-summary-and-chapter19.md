# Phase33 Post-Revision Summary Refresh and Chapter 19 Report

## Objective

Fix stale post-revision `event_summary` handling, align chapter length policy with the clarified elastic `2000+` target, and continue the `《雾港回声》` dogfood loop through Chapter 19.

## Code Changes

- `backend/app/core/athena_longform.py`
  - Allows a new pending `event_summary` proposal when an existing Athena-generated summary is terminal and the revised candidate payload has changed.
  - Keeps unchanged terminal summaries and non-summary duplicates on the existing duplicate path.
- `backend/app/core/chapter_quality_review.py`
  - Treats moderate over-target length as a warning and blocks only extreme over-target drift.
  - Adds `premature_mystery_reveal` blocker for the current N-07 hard-reveal failure mode.
- `backend/app/services/writing_agent/run_service.py`
  - Changes repeated-length feedback from hard `必须` wording to advisory target-range wording.
- `backend/tests/test_writing_agent_runs.py`
  - Adds coverage for stale event summary refresh.
  - Adds coverage for soft over-target review behavior.
  - Adds coverage for premature N-07 identity reveal detection.
- `backend/tests/test_prompting_chapter_migration.py`
  - Updates the 600-chapter / 1.2M-word prompt expectation to `2000-3000`.

## Dogfood Result

Project: `25fa2b20-5b9f-473b-918b-f4ea491cbb60`

- Refreshed Chapter 18 post-revision event summary:
  - new proposal item: `4b8f4f76-b366-4661-aedc-04af096f7436`
  - Chapter 18 memory source became `reviewed_event_summary`
  - pending proposals returned to `0`
- Generated Chapter 19:
  - run: `dd6dd4d0-73d2-4248-a650-85eecad5e3eb`
  - title: `暗网迷途`
  - initial word count: `3846`
  - initial issue: hard-confirmed N-07 / 苏晚晴 relation and revealed third-research-institute backstory too early
- Resolved pre-revision Chapter 19 proposals:
  - draft run: `f40d816c-4c47-431a-933a-a51893aa04ea`
  - apply run: `5e5caaf8-b3e0-4718-b37d-c837e4d6c364`
  - applied decisions: `7`
  - pending proposals after apply: `0`
- Revised Chapter 19:
  - compression/revision runs: `c96d774d-8ce2-44f4-ab26-07fa48d93319`, `beb16d4c-0fb1-4322-8eb0-56820fbea2b5`
  - deterministic versioned correction applied after the compression tool failed to fully obey the N-07 constraint
  - final word count: `2322`
  - forbidden checks: no `我就是N-07`, `那是我`, `N-017`, `第三研究所逃出来`, `十年前那场雾灾，是他们制造的`, or `苏晚晴是实验体`
- Final review and maintenance:
  - quality review: `ready`, `0` findings
  - continuity review: `ready`, `0` findings
  - pending proposals: `0`
  - longform maintenance: `current`
  - latest synced chapter: `19`

## Validation

Read-only explorer `019e3ff6-2c06-7e70-a550-194f7c8a811a` was dispatched for independent review, but did not return before timeout and was closed without findings. The completion evidence below is from main-thread verification.

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_analyze_chapter_world_model_creates_new_event_summary_after_terminal_summary_goes_stale tests\test_writing_agent_runs.py::test_refresh_longform_memory_prefers_reviewed_event_summary_proposal tests\test_prompting_chapter_migration.py::test_chapter_payload_uses_2000_floor_for_600_chapter_longform tests\test_writing_agent_runs.py::test_agent_generate_chapter_appends_length_feedback_after_repeated_over_target_drift tests\test_writing_agent_runs.py::test_agent_generate_chapter_appends_length_feedback_after_repeated_under_target_drift tests\test_writing_agent_runs.py::test_agent_review_chapter_quality_warns_on_soft_over_target_without_blocking tests\test_writing_agent_runs.py::test_agent_review_chapter_quality_blocks_premature_n07_identity_reveal -q
```

Result: `7 passed in 0.68s`.

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "review_chapter_quality or length_decision or event_summary"
```

Result: `15 passed, 94 deselected in 1.21s`.

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

Result:

- `git diff --check` passed, with only a CRLF normalization warning for `backend/tests/test_writing_agent_runs.py`.
- secret scan returned no matches.

## Open Notes

- The compression tool accepted the task as completed even when it failed to remove every explicitly forbidden reveal. The added `premature_mystery_reveal` reviewer catches this failure class after revision, but a future phase should add post-condition validation inside chapter compression/revision tools.
- Chapter 19 memory currently falls back to `source=chapter_content` because the deterministic event summary extractor still summarizes only the opening sentence and did not create a materially changed post-revision summary. This is acceptable for continuing, but the event summary extractor remains too shallow for long chapters.
