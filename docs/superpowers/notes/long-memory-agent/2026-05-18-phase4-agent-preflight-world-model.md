# Phase 4 Agent Preflight And World Model Readiness

## Runtime

- Date: 2026-05-18.
- Verification tier: T1 plus T2 runtime dogfood preflight.
- Backend base URL: `http://127.0.0.1:8001`.
- Secret handling: the model API key was used only as a runtime environment variable and was not written to source, docs, or `.env`.

## Implementation

- Extended Writing Agent tools:
  - `preflight_writing`.
  - `import_setup_world_model`.
  - `analyze_chapter_world_model`.
- Added run/step `blocked` status handling.
- Added `blocked_step_count` to Agent run output.
- Added preflight checks for:
  - setup existence.
  - target chapter outline existence.
  - world-model profile readiness.
  - previous chapter existence.
  - longform maintenance readiness.
  - retrieval availability.
- Agent now stops executing later tools when preflight returns a blocker.

## Dogfood Evidence

Dogfood project:

- Name: `雾港回声`.
- Project id: `25fa2b20-5b9f-473b-918b-f4ea491cbb60`.
- Generated chapters before Phase 4: `2`.
- Chapter 3 before and after preflight: not generated.

Important discovery:

- The current outline claims `total_chapters=600`, but the `chapters` array contains only Chapter 1.
- This explains why Chapter 2 title fell back to `第2章`.
- It also means continuing to Chapter 3 would be structurally unsafe without rolling outline expansion.

## World Model Import

Agent run:

- id: `8cce5e48-c4a1-4a7e-896d-931c26addacd`.
- status: `success`.
- tool: `import_setup_world_model`.

Result:

```json
{
  "status": "completed",
  "profile_version": 1,
  "project_profile_version_id": "ea66c25f-0864-41b6-86df-85d9b18a6486",
  "created": {
    "profile": 1,
    "characters": 5,
    "locations": 13,
    "factions": 3,
    "artifacts": 1,
    "rules": 1
  }
}
```

## Chapter World Analysis

Agent run:

- id: `5ca56c46-32cb-43c9-8cf2-1469cbc92ff2`.
- status: `success`.
- tools:
  - `analyze_chapter_world_model`, chapter 1.
  - `analyze_chapter_world_model`, chapter 2.

Results:

- Chapter 1 created `6` proposal items.
- Chapter 2 created `9` proposal items.
- Athena proposal review queue after analysis:

```json
{
  "profile_version": 1,
  "total_items": 15,
  "returned_items": 15,
  "has_more": false
}
```

## Chapter 3 Preflight

Agent run:

- id: `8a46fe81-7892-4c03-b2ad-881514970bfe`.
- status: `blocked`.
- requested tools:
  - `preflight_writing`, chapter 3.
  - `generate_chapter`, chapter 3.
- executed steps: `1`.
- blocked steps: `1`.

Preflight output:

```json
{
  "status": "blocked",
  "chapter_index": 3,
  "checks": {
    "setup": {"status": "ready"},
    "outline_chapter": {"status": "missing", "chapter_index": 3},
    "world_model_profile": {"status": "ready", "profile_version": 1},
    "previous_chapter": {"status": "ready", "chapter_index": 2},
    "longform_maintenance": {"status": "ready", "ready_for_writing": true, "issue_count": 0},
    "retrieval": {"status": "ready", "total_documents": 9, "total_chunks": 19}
  },
  "issues": [
    {
      "code": "missing_outline_chapter",
      "severity": "blocker",
      "message": "第3章缺少章节大纲。"
    }
  ]
}
```

Verification that generation was blocked:

- `GET /api/v1/projects/{project_id}/chapters/3` returned `404`.
- No Chapter 3 content was created.

## Issues Found

- The longform outline is not actually longform-ready: it has only one concrete chapter entry.
- Agent generation previously allowed writing beyond outline coverage.
- The project now has 15 reviewable world-model proposal items that need review or a batch triage policy before long batch writing.
- Longform chapter-length policy remains incomplete: Phase 4 blocks missing outline, but does not yet revise or split overlong chapters.

## Issues Fixed

- Agent now has a preflight tool.
- Agent can import Setup into Athena world model.
- Agent can analyze existing chapters into world-model proposals.
- Agent can block later tool execution when preflight finds a blocker.
- The missing outline problem is now visible and prevents unsafe Chapter 3 generation.

## Verification

- T1:
  - Command: `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q`.
  - Result: `11 passed`.
- T1/T2 focused regression:
  - Command: `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_athena_longform.py::test_import_setup_creates_formal_profile_entities_and_rules -q`.
  - Result: `12 passed`.
- Diff hygiene:
  - Command: `git diff --check`.
  - Result: exit code `0`.
- Secret scan:
  - Command: `rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references`.
  - Result: no matches.
- Runtime:
  - Backend health on `8001`: `{"status":"ok"}`.
  - Setup import run succeeded.
  - Chapter 1 and 2 analysis run succeeded.
  - Chapter 3 preflight blocked generation.
  - Chapter 3 endpoint returned `404`.

## Next Phase Recommendation

Phase 5 should solve outline coverage before any more chapter generation:

- Add rolling outline expansion for the next chapter window, such as chapters 2-10 or 3-12.
- Ensure outline expansion does not overwrite existing Chapter 1 outline.
- Make Agent preflight suggest or call an outline-expansion tool when `missing_outline_chapter` appears.
- Review or at least cluster the 15 world-model proposal items before generating more chapters.
- Only generate Chapter 3 after outline coverage exists and preflight returns `ready`.
