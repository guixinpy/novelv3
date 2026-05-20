# Phase70 Report: Writing Task Agent Provenance

## Summary

Phase70 connects continuous writing task results to the Agent run provenance produced by Phase69.

After Phase69, `build_generate_chapter_work()` and `build_retry_chapter_work()` already call a chapter generation function that creates `WritingAgentRun` records. This phase preserves those `agent_run_id` and `control_plane` values in the background task result so range generation, retry, task inspection, and future recovery can see which Agent run produced each chapter.

This does not yet convert the task type itself to `writing_agent_run`. It is an incremental observability bridge for long-running writing tasks.

## Reference Assimilation

Adopted:

- `openclaw`: background work should expose its control-plane execution unit.
- `hermes-agent`: long-running tasks should keep references to durable run/step records.
- `openhuman`: parent task summaries should stay compact but retain references to detailed runs.

Not adopted:

- changing `generate_chapter` task type;
- rewriting queue/resume semantics;
- frontend task provenance display;
- real model generation in tests.

## Changes

- Updated `backend/app/api/writing.py`.
- Updated `backend/tests/test_writing.py`.
- Added `_chapter_agent_provenance()` helper.
- `build_generate_chapter_work()` now:
  - collects per-chapter Agent provenance;
  - returns `agent_runs`;
  - returns latest `agent_run_id`.
- `build_retry_chapter_work()` now returns `agent_run_id` and `control_plane` when available.
- Existing fake generation paths without Agent metadata remain compatible.

## Result Contract

Range generation result can now include:

```json
{
  "chapter_index": 2,
  "agent_run_id": "run-2",
  "agent_runs": [
    {
      "chapter_index": 1,
      "agent_run_id": "run-1",
      "control_plane": {
        "source": "chapter_generate",
        "chapter_index": 1
      }
    },
    {
      "chapter_index": 2,
      "agent_run_id": "run-2",
      "control_plane": {
        "source": "chapter_generate",
        "chapter_index": 2
      }
    }
  ]
}
```

Retry result can now include:

```json
{
  "chapter_index": 3,
  "agent_run_id": "run-retry-3",
  "control_plane": {
    "source": "chapter_generate",
    "chapter_index": 3
  }
}
```

## Verification

RED before implementation:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing.py -q -k "agent_run_provenance"
```

Result before implementation: `2 failed`; task results did not expose `agent_run_id` or `agent_runs`.

Focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing.py -q -k "agent_run_provenance"
```

Result: `2 passed, 28 deselected in 0.19s`.

T1/T2 related backend regression:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing.py tests\test_chapters.py tests\test_background.py -q
```

Result: `103 passed in 7.41s`.

Static checks:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

Result:

- `git diff --check` passed.
- secret scan returned no matches.

## Novel Progress

No production novel chapter was generated in this phase. This phase improves the execution traceability required before long-running dogfood generation can be treated as an auditable Agent workflow.

## Discovered Issues

- Continuous writing range tasks could indirectly create Agent runs through Phase69, but the parent task result did not expose those run IDs.
- Retry task results also dropped Agent provenance.

## Fixed Issues

- Range task results now include latest `agent_run_id`.
- Range task results now include `agent_runs` for each generated chapter with provenance.
- Retry results now preserve `agent_run_id` and `control_plane`.

## Remaining Boundary

Continuous writing still uses `generate_chapter` background task type and directly controls range iteration. Remaining work:

- make task creation itself Agent-aware;
- expose Agent run provenance in frontend task views;
- connect pause/resume/retry recovery planning to Agent recovery tools;
- run real longform dogfood generation through the new provenance path.

Next phase should either migrate task creation toward an Agent-planned queue contract or begin a controlled dogfood generation smoke using the Agent-backed chapter path.
