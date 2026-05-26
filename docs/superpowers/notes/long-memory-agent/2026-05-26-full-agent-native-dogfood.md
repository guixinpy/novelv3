# Full Agent-Native Dogfood

## Runtime

- Date: 2026-05-26
- Branch: `codex/full-agent-native-long-memory`
- Backend: `http://127.0.0.1:8000`
- Frontend: `http://127.0.0.1:5173`
- Dogfood database: `data/agent_native_dogfood_20260526.db`

The default `data/mozhou.db` was not modified for dogfood. It has schema/version
drift: alembic current reported `20260429_add_retrieval_terms`, while
`longform_memories`, `writing_agent_runs`, and `writing_agent_steps` already
exist. To avoid damaging the user's existing local data, the backend was
started with an isolated `MOZHOU_DATABASE_URL`.

## Service Checks

```powershell
backend\.venv\Scripts\python.exe -m alembic upgrade head
# passed against data/agent_native_dogfood_20260526.db

Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
# {"status":"ok"}

Invoke-WebRequest http://127.0.0.1:5173
# status=200 length=357
```

## Seed

- Project: `3f85aed4-4f6f-413f-bd1a-03fbe02ea0f4`
- Setup: `a8caf120-29ce-4e9a-b4a6-7f8af98ffe55`
- Storyline: `a4d56ee6-7cdf-49ed-8689-d1f51b627a14`
- Outline: `fe55c24d-bf55-4651-b3e5-b62f69e7058b`

The seed created a five-chapter suspense/SF outline with explicit foreshadowing
for `black_tide_gate` and `lin_deep_signature`.

## Loop Evidence

### Generate

- Chapter 1 generated through API:
  - Chapter: `37fb2030-29e0-4b92-8475-193aec372434`
  - Trace: `8d3c8402-fe7e-4d9a-8d76-c0b019d88bef`
  - Agent run: `2cf665ff-cd9e-4af2-8a00-8546df9f13b5`
  - Word count: 1327
- Chapter 2 generated through API:
  - Chapter: `14299eb5-17a7-40b5-ab02-d806cea685c9`
  - Trace: `a4358b98-29f0-42e3-8a43-46d0f553ab11`
  - Agent run: `7a16d3c0-ada5-4ea4-afd4-edcd54c0ccde`
  - Word count: 1114

### Review And Inspect

- Review/inspection run: `758d980d-5625-4993-9206-07360ae8b967`
- Steps: quality review, continuity review, world-model analysis, health,
  context compression, memory tree, event projection.
- Findings:
  - `review_chapter_quality` blocked chapter 2 for `chapter_over_target` and
    `future_outline_overlap`.
  - `review_chapter_continuity` warned on `identifier_semantic_drift`.
  - Initial `analyze_chapter_world_model` skipped with
    `missing_world_model_profile`.
  - `inspect_agent_event_projection` projected 25 events at that point.

### Recovery Action 1: World Model Profile And Proposal Queue

- Import/analyze run: `a690967f-3f07-4878-9977-a4d814165f57`
  - `import_setup_world_model`: completed.
  - `analyze_chapter_world_model`: completed and created 7 proposal items in
    bundle `4400ed22-bc83-4747-b428-1b90134e2414`.
- Resolution plan run: `60e79765-e782-409a-845e-805416ebdcfb`
  - Planned 4 proposal resolution steps.
- Draft run: `bfa2c791-e318-4efc-8e1e-53829a258d16`
  - Drafted 6 guarded decisions.
  - Left 1 unclassified `memory_erasure_hypothesis`.
- Apply run: `b38c5fef-cab9-440b-83ea-b7f6f7d18293`
  - Applied 6 guarded decisions.
  - Actionable items dropped from 7 to 1.
- Custom draft run: `dc6b884b-244f-4968-b89d-546884b24906`
  - Drafted 1 custom `mark_uncertain` decision for
    `memory_erasure_hypothesis`.
- Final apply run: `e6b2dcb6-1f77-4c93-a47b-70067af4b07f`
  - Applied 1 decision.
  - Actionable items dropped from 1 to 0.

### Recovery Action 2: Chapter Repair

- First compression run: `33003c4d-b0dd-44ae-828a-55726e13625c`
  - Blocked after 3 model attempts.
  - Each candidate was within word target but still contained forbidden term
    `潮下车站`.
  - Failed traces:
    - `c9fc894c-132f-44a2-8289-095bfa358050`
    - `757ddde0-6ef9-4a94-9e34-26a72ff44871`
    - `2962bb73-35f0-4208-8fdf-a7d04d7f54f2`
- Retry compression run: `dbf78517-a4f7-474e-b268-5e7a940284bc`
  - Stronger forbidden terms: `潮下车站`, `潮下`, `车站`, `林深的签名`.
  - Compression trace: `bb4a1713-ea8c-49e2-9010-60ac4dae87ef`
  - Revision: `ed2f7b54-e771-47a0-b95c-c370de868ad5`
  - Chapter 2 reduced from 1114 to 567 words.
  - Forbidden terms cleared.
  - Follow-up quality review returned `ready` with no findings.

### Continue

- Continue run: `03600c85-fbe3-43eb-96bb-6d3049184d73`
  - `preflight_writing` for chapter 3: ready.
  - `generate_chapter` for chapter 3: success.
  - Trace: `df7b128e-3c48-4639-ae32-6178730f77fc`
  - Chapter 3 word count: 1156.
  - Chapter 3 review found the next iteration's issues:
    `chapter_over_target` and `pending_world_model_proposals`.

## Final Observability Snapshot

- Snapshot run: `5d298e4c-56d0-47c4-b180-de297cda35cd`
- Chapters:
  - Chapter 1: 1327 words, generated.
  - Chapter 2: 567 words, generated after repair.
  - Chapter 3: 1156 words, generated.
- Traces:
  - Chapter generation success: 3 traces.
  - Chapter compression failed: 3 traces.
  - Chapter compression success: 1 trace.
- Health:
  - Status: degraded.
  - Diagnostics: `narrative_trend_watch`, `agent_write_gate_high_risk`.
  - Narrative trend status: watch.
- Context compression:
  - Status: ready.
  - Prompt context chars: 2009.
  - Usage ratio: 0.5022.
  - Truncated sections: 1.
  - Memory provenance status: `truncated`.
  - Source count: 5.
- Memory Tree:
  - Status: ready.
  - Volume nodes: 1.
  - Chapter nodes: 3.
- Event projection:
  - Status: completed.
  - Total events in snapshot: 100.
  - Event counts: `run_created=14`, `run_started=14`, `tool_started=30`,
    `tool_completed=28`, `run_completed=11`, `run_blocked=2`, `tool_error=1`.
- World model queue after chapter 3:
  - Status: blocked.
  - Actionable items: 5.
  - Risk counts: `high=1`, `medium=0`, `low=4`.

## Dogfood Findings

1. The default local SQLite database has alembic version drift. Dogfood should
   continue using isolated DBs unless explicitly repairing the user's local DB.
2. World-model analysis can be skipped until `import_setup_world_model` runs.
   This is a good candidate for a preflight/health recommendation.
3. `review_world_model_proposals` correctly enforces the controlled plan path;
   direct draft after report is stopped by the report StopHook.
4. Compression correctly blocks when forbidden terms remain after retries. In
   this run, stronger forbidden-term expansion solved the issue without code
   changes.
5. The loop can continue after repair, and the next generated chapter exposes
   the next round of concrete quality/world-model work.

## Verification Addendum

- Focused regression after adding event projection:
  `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_tool_executor.py::test_agent_task_queue_tool_adapters_live_in_dedicated_module backend\tests\test_writing_agent_event_projection.py backend\tests\test_writing_agent_job_projection.py backend\tests\test_writing_agent_tool_registry.py -q`
  -> `75 passed`.
- Full local quality:
  `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\verify_local_quality.ps1`
  -> backend `1353 passed`, frontend unit `567 passed`, frontend build passed.
- Perf smoke was skipped by the script because `PERF_SMOKE_BASE_URL`,
  `PERF_SMOKE_PROJECT_ID`, and `PERF_SMOKE_SESSION` were not set.
- Frontend E2E was skipped by the script because `-RunE2E` / `RUN_E2E=1` was
  not enabled.
- Substitute E2E evidence for this goal is the API-backed dogfood above:
  local backend health returned `ok`, local frontend returned HTTP 200, and the
  loop completed generate -> review -> recover -> revise -> continue generation.
- Non-blocking residue: the full quality script exited `0`; pytest emitted one
  ignored Windows `PermissionError` while cleaning a temp directory at atexit.
