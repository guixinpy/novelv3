# Longform Scale Phase 322 - Million Word Gate Check

## Goal

Record a current 1000 chapter / 1,000,000 word synthetic longform smoke baseline with the new writing diagnostics gates enabled.

## Command

```powershell
backend\.venv\Scripts\python.exe scripts\longform_scale_smoke.py --chapters 1000 --words-per-chapter 1000 --target-chapter 500 --cleanup --max-elapsed-ms 30000 --max-stage-ms seed_project=15000 --max-stage-ms memory_rebuild=10000 --max-stage-ms retrieval_reindex=15000 --max-stage-ms context_build=10000 --max-stage-ms post_generation_maintenance=10000 --max-stage-ms writing_worker=10000 --max-writing-under-target 0 --max-writing-over-target 0 --max-writing-warnings 0
```

## Result

Passed.

Key evidence:

- Total elapsed: `28068ms`
- Memory: `1000` chapter memories, `50` arc memories, `10` volume memories, `1` global memory
- Retrieval: `2061` documents, `3061` chunks, `3061` embeddings
- Repeat retrieval reindex: `0` indexed documents, `2061` preserved documents, `0` removed documents
- Context: `5` sections, `3736` prompt chars, `6` query-aware retrieval items, `0` out-of-range items
- Narrative plan window: `1000` total chapters, `100` returned, `has_more=true`
- Writing worker: `1000/1000` completed, pending count `0`, writing state `completed`, current chapter `1001`
- Writing diagnostics: under-target `0`, within-target `1000`, over-target `0`, post-generation warnings `0`

## Timing Breakdown

- `seed_project`: `159ms`
- `task_progress`: `9ms`
- `memory_rebuild`: `300ms`
- `retrieval_reindex`: `12429ms`
- `retrieval_diagnostics`: `1919ms`
- `retrieval_repeat_reindex`: `243ms`
- `post_generation_maintenance`: `3950ms`
- `context_build`: `497ms`
- `narrative_plan_window`: `14ms`
- `dialog_planning_context`: `8ms`
- `writing_worker`: `8533ms`
- `task_complete`: `2ms`

## Interpretation

The synthetic million-word gate currently proves the foundation can handle scale-critical maintenance paths under bounded timing and zero writing diagnostic drift. It does not prove real model quality for a true million-word novel; that still requires long-cycle dogfood with actual generated chapters.
