# Long Memory Writing Agent Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create or select the `《雾港回声》` dogfood project and generate the first real 2000+ character chapter through the application path.

**Architecture:** Phase 2 uses existing project/setup/storyline/outline/chapter generation APIs. It does not introduce the Writing Agent Core yet; instead it captures real workflow gaps that the future Agent must solve.

**Tech Stack:** FastAPI backend, DeepSeek-compatible API via runtime `DEEPSEEK_API_KEY`, SQLite app data, existing chapter generation, Athena post-generation maintenance, targeted verification only.

---

## Phase Metadata

- **Phase:** 2
- **Date:** 2026-05-18
- **Verification Tier:** T1/T2.
- **Primary Output:** First real dogfood chapter and a Phase 2 note under `docs/superpowers/notes/long-memory-agent/`.
- **Secret Handling:** Do not write API keys to docs, commits, or `.env`. Use runtime environment variables only.

## Phase 2 Success Criteria

- Runtime model configuration is verified without committing secrets.
- A project named `雾港回声` exists with `target_chapter_count=600`, `target_word_count>=1200000`, and `ai_model=deepseek-chat`.
- Setup, storyline, outline, and chapter 1 are generated through the backend API path.
- Chapter 1 contains at least 2000 Chinese characters of prose-like正文.
- The chapter generation trace exists and includes prose quality metadata.
- Post-generation maintenance state is inspected: retrieval, longform memory, and Athena/world proposal behavior.
- A Phase 2 note records commands, project id, chapter metrics, problems found, and recommended fixes.

## Files

- Create: `docs/superpowers/notes/long-memory-agent/2026-05-18-phase2-first-dogfood-chapter.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-18-phase2-first-dogfood-chapter.md`

## Task 1: Verify Runtime Readiness

- [ ] **Step 1: Check working tree**

Run:

```powershell
git status --short --branch
```

Expected: only intended docs changes, or clean working tree.

- [ ] **Step 2: Verify backend import path and database are usable**

Run:

```powershell
backend\.venv\Scripts\python.exe - <<'PY'
from app.db import Base, engine
from app.models import Project
Base.metadata.create_all(bind=engine)
print(Project.__tablename__)
PY
```

Expected: prints `projects`.

- [ ] **Step 3: Verify API key availability at runtime**

Run with runtime env var set in the shell, not in files:

```powershell
$env:DEEPSEEK_API_KEY = '<runtime only>'
backend\.venv\Scripts\python.exe - <<'PY'
from app.config import load_api_key
print('configured' if load_api_key() else 'missing')
PY
```

Expected: `configured`.

## Task 2: Start Backend Server

- [ ] **Step 1: Stop conflicting local backend process if needed**

Run:

```powershell
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue |
  Select-Object LocalAddress,LocalPort,State,OwningProcess
```

Expected: if a process exists, confirm it belongs to this workspace before stopping it.

- [ ] **Step 2: Start backend server**

Run:

```powershell
$env:DEEPSEEK_API_KEY = '<runtime only>'
Start-Process -FilePath "backend\.venv\Scripts\python.exe" `
  -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8000" `
  -WorkingDirectory "backend" `
  -WindowStyle Hidden `
  -RedirectStandardOutput ".tmp\phase2-backend.stdout.log" `
  -RedirectStandardError ".tmp\phase2-backend.stderr.log"
```

Expected: server starts on `http://127.0.0.1:8000`.

- [ ] **Step 3: Health check**

Run:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

Expected: health response succeeds.

## Task 3: Create Or Select Dogfood Project

- [ ] **Step 1: Check whether project already exists**

Run:

```powershell
$projects = Invoke-RestMethod http://127.0.0.1:8000/api/v1/projects
$projects | Where-Object { $_.name -eq '雾港回声' } | Select-Object id,name,target_chapter_count,target_word_count,ai_model
```

Expected: either one reusable project or no output.

- [ ] **Step 2: Create project if missing**

Run:

```powershell
$body = @{
  name = '雾港回声'
  description = '长期狗粮项目：都市悬疑、轻科幻、群像成长。用于验证长记忆网文创作 Agent。'
  genre = '都市悬疑 / 轻科幻 / 群像成长'
  target_chapter_count = 600
  target_word_count = 1200000
  ai_model = 'deepseek-chat'
  style = '商业网文正文；强场景、强冲突、持续悬念；避免大纲式输出。'
  complexity = 5
} | ConvertTo-Json -Depth 10
$project = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/projects -ContentType 'application/json' -Body $body
$project | Select-Object id,name,target_chapter_count,target_word_count,ai_model
```

Expected: returns project id.

## Task 4: Generate Setup, Storyline, Outline, And Chapter 1

- [ ] **Step 1: Generate setup**

Run:

```powershell
$projectId = '<project id>'
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/projects/$projectId/setup/generate?command_args=请为《雾港回声》建立适合600章长篇展开的都市悬疑轻科幻设定，突出雾港、记忆异常、城市地下实验、群像关系和长期伏笔。"
```

Expected: setup status is `generated`.

- [ ] **Step 2: Generate storyline**

Run:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/projects/$projectId/storyline/generate?command_args=请生成可支撑600章的主线、支线和伏笔骨架，先保证前30章有清晰阶段目标。"
```

Expected: storyline status is `generated`.

- [ ] **Step 3: Generate outline**

Run:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/projects/$projectId/outline/generate?command_args=请生成前期章节规划，重点保证第1章具备完整正文场景目标、冲突、悬念和后续钩子。"
```

Expected: outline status is `generated`, and chapter 1 outline exists.

- [ ] **Step 4: Generate chapter 1**

Run:

```powershell
$chapter = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/projects/$projectId/chapters/1/generate"
$chapter | Select-Object chapter_index,title,word_count,status,last_generation_trace_id
```

Expected: status is `generated`, `word_count` is at least 2000, and `last_generation_trace_id` exists.

## Task 5: Inspect Generated Quality And Maintenance

- [ ] **Step 1: Fetch chapter 1**

Run:

```powershell
$chapter = Invoke-RestMethod "http://127.0.0.1:8000/api/v1/projects/$projectId/chapters/1"
($chapter.content).Substring(0, [Math]::Min(800, $chapter.content.Length))
$chapter.word_count
```

Expected: content begins as prose, not outline.

- [ ] **Step 2: Fetch generation trace**

Run:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/projects/$projectId/model-call-traces/$($chapter.last_generation_trace_id)"
```

Expected: trace includes context blocks and `chapter_prose_quality`.

- [ ] **Step 3: Inspect retrieval diagnostics**

Run:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/projects/$projectId/athena/retrieval/diagnostics"
```

Expected: diagnostics show at least chapter document/index presence or explain missing state.

- [ ] **Step 4: Inspect longform memory diagnostics**

Run:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/projects/$projectId/athena/longform/memory/diagnostics"
```

Expected: diagnostics respond successfully.

- [ ] **Step 5: Inspect Athena proposal state**

Run:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/projects/$projectId/athena/evolution/proposal-review-queue"
```

Expected: proposal review queue state is visible, or the lack of proposals is documented.

## Task 6: Write Phase 2 Report

- [ ] **Step 1: Create `2026-05-18-phase2-first-dogfood-chapter.md`**

The note must include:

```markdown
# Phase 2 First Dogfood Chapter

## Runtime

## Project

## Generated Artifacts

## Chapter 1 Metrics

## Quality Review

## Maintenance / Memory / World Model

## Issues Found

## Issues Fixed

## Verification

## Next Phase Recommendation
```

- [ ] **Step 2: Update this plan with completion notes**

Add:

```markdown
## Phase 2 Completion Notes

## Actual Completed Work

## Novel Progress

## Issues Found

## Issues Fixed

## Verification

## Next Phase Recommendation
```

## Task 7: Verify And Commit Phase 2 Docs

- [ ] **Step 1: Run docs check**

Run:

```powershell
git diff --check
```

Expected: exit code 0.

- [ ] **Step 2: Commit docs**

Run:

```powershell
git add docs/superpowers/plans/long-memory-agent/2026-05-18-phase2-first-dogfood-chapter.md docs/superpowers/notes/long-memory-agent/2026-05-18-phase2-first-dogfood-chapter.md
git commit -m "docs: record long memory agent phase 2"
```

Expected: commit succeeds.

## Phase 2 Completion Notes

Phase 2 executed on `http://127.0.0.1:8001` because port `8000` already had an unidentified listener. No API key was written to files.

The original plan also contained three execution assumptions that were corrected during execution:

- PowerShell `$PID` is a read-only automatic variable, so plan snippets now use `$projectId`.
- The trace endpoint is `model-call-traces`, not `model-traces`.
- The available Athena proposal review inspection endpoint is `athena/evolution/proposal-review-queue`; the earlier guessed `world/proposals` path is not the API route used for this phase.

## Actual Completed Work

- Created dogfood project `雾港回声` with id `25fa2b20-5b9f-473b-918b-f4ea491cbb60`.
- Generated setup `38532a88-bc20-4b13-8a0c-00ac0f006590`.
- Generated storyline `63694c94-7dd0-4e0b-be60-697bf87436be`.
- Generated 600-chapter outline `49229388-f2d6-4bdb-bfa0-f4e8b9aa0beb`.
- Generated chapter 1 `雾中回声`.
- Fixed outline structured scene normalization discovered during dogfood.
- Added regression coverage for structured `scenes` and `characters`.
- Wrote Phase 2 report: `docs/superpowers/notes/long-memory-agent/2026-05-18-phase2-first-dogfood-chapter.md`.

## Novel Progress

- Novel: `《雾港回声》`.
- Planned total: 600 chapters.
- Generated chapters: 1.
- Chapter 1 title: `雾中回声`.
- Chapter 1 word count: `3735`.
- Chapter 1 trace id: `febf0ad4-eadd-4b26-b97a-76f6d54468f9`.

## Issues Found

- Outline generation failed when the model returned structured scene dictionaries instead of strings.
- Chapter 1 exceeded target average/max length; longform generation needs an Agent-level length-control loop.
- Athena proposal review queue was empty after chapter generation, with `profile_version=null`.

## Issues Fixed

- Normalized structured outline `scenes` and `characters` before persistence and response serialization.
- Added defensive schema validation for outline chapter list fields.
- Added a targeted regression test for structured outline scene output.

## Verification

- T1 targeted regression: `.venv\Scripts\python.exe -m pytest tests\test_outlines.py::test_generate_outline_normalizes_structured_scene_items -q`.
- T1 outline test file: `.venv\Scripts\python.exe -m pytest tests\test_outlines.py -q`.
- T2 runtime dogfood: setup, storyline, outline, chapter generation, trace inspection, retrieval diagnostics, longform memory diagnostics, maintenance diagnostics, and Athena proposal queue inspection.

## Next Phase Recommendation

Phase 3 should implement the first thin Writing Agent run model and tool-orchestration trace:

- Record an Agent run goal, steps, selected tools, outputs, and trace links.
- Wrap existing generation APIs as Agent-callable tools.
- Add the first chapter-length control policy.
- Investigate missing Athena proposal queue output.
- Generate chapter 2 through the Agent run path.
