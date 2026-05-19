# Phase36 Chapter 21 Dogfood Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Continue the real longform dogfood loop by expanding, generating, reviewing, and stabilizing Chapter 21 of `《雾港回声》`.

**Architecture:** Use the Writing Agent as the main orchestration path. Keep Chapter 21 bounded to the immediate second-door obstacle, creditor pressure, and memory/riddle escalation. Resolve world model proposals and refresh longform memory/retrieval before continuing.

**Tech Stack:** FastAPI TestClient for Writing Agent tool execution, Athena longform memory/retrieval, world proposal review flow, chapter quality/continuity review, targeted pytest verification.

**Length Policy:** Treat `2000+` as an elastic quality target, not an exact hard target. For this phase, the acceptable chapter band is `2000-3000` words; only under-floor chapters or clearly runaway chapters should block continuation.

---

## Context

Current dogfood state before Phase36:

- project: `25fa2b20-5b9f-473b-918b-f4ea491cbb60`
- latest chapter: `20`
- latest title: `三重门`
- Chapter 20 word count: `2293`
- pending world proposals: `0`
- longform maintenance: `current`
- ready for writing: `True`
- latest synced chapter index: `20`
- outline currently has 20 chapters, so Chapter 21 must be planned via `expand_outline_window`.

Chapter 20 ending state:

- The group opened only the first door.
- A级雾晶 is consumed and cannot solve later doors.
- The group is inside the first-door corridor and faces a second door requiring iris recognition.
- 顾衍's existing权限 is not enough.
- 苏晚晴 is unconscious or unstable, with grey-blue light still in her pupils.
- 赵猛 is alive, trapped with the group, and his creditor has arrived outside the first door.
- 叶知秋 is a plausible iris/key clue but her location and current state are unknown.
- N-07 remains unresolved and must not become a confirmed Su Wanqing identity reveal.

## Task 1: Preflight and Outline Chapter 21

- [x] **Step 1: Record baseline state**

Run a read-only script to record:

- latest generated chapter;
- pending proposal count;
- longform maintenance status;
- whether outline chapter 21 exists.

Expected:

- latest chapter index: `20`;
- pending world proposals: `0`;
- longform maintenance: `current`;
- outline chapter 21 does not exist yet.

Result:

- latest chapter index: `20`;
- latest word count: `2293`;
- pending world proposals: `0`;
- longform maintenance: `current`;
- ready for writing: `True`;
- outline count: `20`;
- outline chapter 21 existed: `False`;
- latest synced chapter index: `20`.

- [x] **Step 2: Expand outline window**

Use Writing Agent:

```json
[
  {
    "tool_name": "expand_outline_window",
    "params": {
      "start_chapter": 21,
      "end_chapter": 21,
      "command_args": "第21章承接第20章《三重门》：主角团困在第一道门后的狭窄走廊，第二道门需要虹膜识别，A级雾晶已碎裂不可再用。赵猛债主在第一道门外出现并造成逼迫，不能直接杀死赵猛，也不能让赵猛虹膜直接解决第二道门。叶知秋可以作为线索或权限关联被提及，但不能直接现身解决问题。苏晚晴仍虚弱/昏迷，可通过记忆纹路或雾感提供碎片线索，但不要确认她就是N-07，不要混入N-017，不要拿到完整配方或终局真相。第21章目标2000-3000字，应推进第二道门的阻碍、债务压力、叶知秋线索和新的代价。"
    }
  }
]
```

Result: Writing Agent run `b9df4484-3814-44bb-a1af-8e84a9fc2969`, status `success`, added chapter count `1`.

The first generated outline contained a stage-boundary problem: it tried to reuse the already shattered fog crystal and open the second door. This contradicted Chapter 20's accepted endpoint.

Correction: updated Chapter 21 outline through `PATCH /api/v1/projects/{project_id}/outline/chapters/21` to keep:

- second door locked;
- A级雾晶 unavailable as an effective key;
- Zhao Meng alive with creditor pressure active;
- Ye Zhiqiu only as a remote permission clue;
- Su Wanqing / N-07 unresolved.

- [x] **Step 3: Verify outline 21 exists**

Read the latest `Outline.chapters` and confirm chapter 21 has:

- title;
- summary;
- scenes;
- characters;
- purpose that keeps second-door access unresolved or only partially advanced.

Result: Chapter 21 exists with title `虹膜之锁`, 3 scenes, characters `林深` / `苏晚晴` / `顾衍` / `赵猛`, and purpose explicitly says not to reuse A级雾晶 or directly open the second door.

## Task 2: Generate and Review Chapter 21

- [x] **Step 1: Run Agent generation chain**

Use Writing Agent:

```json
[
  {"tool_name": "preflight_writing", "params": {"chapter_index": 21}},
  {
    "tool_name": "generate_chapter",
    "params": {"chapter_index": 21},
    "command_args": "生成第21章：保持2000-3000字；承接第20章第一道门后走廊、第二道虹膜门、赵猛债主在外敲门；A级雾晶已碎裂不可再用；赵猛必须继续存活且债务压力继续发挥作用；不能让赵猛虹膜直接通过第二道门；叶知秋可作为权限/虹膜/记忆线索被推进，但不能突然现身救场；苏晚晴与N-07保持未确认，不要写“我就是N-07”“苏晚晴是实验体”“N-07就是苏晚晴”；禁止混入N-017；禁止拿到完整配方、配方内容或终局真相。"
  },
  {"tool_name": "review_chapter_quality", "params": {"chapter_index": 21}},
  {"tool_name": "review_chapter_continuity", "params": {"chapter_index": 21, "lookback": 20}},
  {"tool_name": "analyze_chapter_world_model", "params": {"chapter_index": 21}}
]
```

Result: Writing Agent run `2604bbda-a5f5-4384-8c6f-d815b4ba976d`, status `success`.

- `preflight_writing`: `ready`.
- `generate_chapter`: produced Chapter 21 at `3485` words, over the `3000` soft cap.
- `review_chapter_quality`: warning only, no blockers; findings were over-target length, convenient key-item acquisition risk, and pending proposals.
- `review_chapter_continuity`: ready, 0 findings.
- `analyze_chapter_world_model`: skipped because generation already analyzed the chapter in the same run; 8 proposal items were created.

- [x] **Step 2: Inspect generated content**

Run read-only checks for:

- `word_count` inside `2000-3000`;
- no `我就是N-07`, `那是我`, `苏晚晴是实验体`, `N-017`, `完整配方到手`, `成功拿到完整配方`, `配方如下`;
- no direct second-door pass through 赵猛's iris;
- no Zhao Meng death;
- no sudden complete access to the core database.

Result:

- no hard Su Wanqing / N-07 identity reveal;
- no N-017 contamination;
- no complete formula acquisition;
- no second-door pass;
- no Zhao Meng death;
- chapter was too long (`3485`) and reused shattered fog-crystal residue too prominently, so compression was required.

- [x] **Step 3: Revise if needed**

If the chapter violates stage constraints, regenerate or revise before proposal handling.

Do not continue to the next chapter until:

- length is inside the elastic target range;
- automated reviews have no blockers;
- manual semantic checks confirm no premature reveal or shortcut.

Revision path:

1. Rejected the 8 proposals extracted from the superseded overlong draft.
2. Ran `compress_chapter_to_target` in Writing Agent run `999fa447-101e-4348-adcc-41b56bd2a7c7`.
3. Final Chapter 21 result:
   - title: `虹膜之锁`;
   - word count: `2996`;
   - target range: `2000-3000`;
   - remaining forbidden terms: `[]`;
   - quality review: `ready`, 0 findings;
   - continuity review: `ready`, 0 findings.
4. Manual semantic checks confirmed:
   - second door remains locked;
   - no core database access or formula acquisition;
   - Zhao Meng survives and debt pressure continues;
   - Ye Zhiqiu does not appear in person;
   - Su Wanqing / N-07 remains an unresolved inference, not a confirmed reveal;
   - fog-crystal fragments are only residual stimulus, not an effective key.

## Task 3: Resolve Proposals and Refresh Memory

- [x] **Step 1: Resolve Chapter 21 proposals**

Use `draft_world_model_proposal_resolution_decisions` and/or explicit `apply_world_model_proposal_resolution`.

Policy:

- `event_summary`: `mark_uncertain` only after final text is accepted.
- derived metadata such as `presence_count`: reject.
- textual mentions: reject unless they are genuine world facts.
- no approval of hard N-07/Su identity claims unless explicitly intended.
- no approval of second-door/full database access unless the final accepted text actually supports it.

Result:

- overlong-draft proposal items: 8 rejected before compression;
- post-compression analysis created 0 new items and updated 0 existing items because the deterministic summary stayed equivalent after compression;
- pending world proposals: `0`.

Process note:

- This exposed an operational issue, not a production-code defect: rejecting all overlong-draft proposals before compression also rejected an event summary that remained valid after compression. Existing code correctly avoids recreating identical rejected proposals, otherwise an explicitly rejected summary would reappear on every analysis rerun. Future phases should either avoid rejecting still-valid `event_summary` before compression, or introduce an explicit `superseded_by_revision` state/reason that can be safely refreshed.

- [x] **Step 2: Refresh memory and retrieval**

Expected:

- pending proposals: `0`;
- longform maintenance: `current`;
- latest synced chapter index: `21`.

Result:

- pending proposals: `0`;
- longform maintenance: `current`;
- ready for writing: `True`;
- issue count: `0`;
- latest synced chapter index: `21`.

## Task 4: Verification, Report, and Commit

- [x] **Step 1: Run targeted verification**

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "premature_mystery_reveal or review_chapter_quality or review_chapter_continuity"
```

Result: `21 passed, 90 deselected in 1.66s` using the expanded targeted selector `premature_mystery_reveal or review_chapter_quality or review_chapter_continuity or event_summary`.

- [x] **Step 2: Static checks**

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

Results:

- `git diff --check`: passed with no output.
- secret scan: no matches, `rg` exit code `1`.

- [x] **Step 3: Write report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-19-phase36-chapter21-loop.md` with:

- baseline;
- generated Chapter 21 result;
- revisions and proposal handling;
- maintenance state;
- verification evidence;
- next phase recommendation.

Result: report written to `docs/superpowers/notes/long-memory-agent/2026-05-19-phase36-chapter21-loop.md`.

- [ ] **Step 4: Commit and push**

Commit and push `main` after checks pass.
