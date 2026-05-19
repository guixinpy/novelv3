# Phase35 Chapter 20 Dogfood Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Continue the real longform dogfood loop by expanding, generating, reviewing, and stabilizing Chapter 20 of `《雾港回声》`.

**Architecture:** Use the Writing Agent as the main orchestration path. Apply Phase34 `forbidden_terms` postconditions if the generated chapter requires compression or revision, then resolve world model proposals and refresh longform memory/retrieval before continuing.

**Tech Stack:** FastAPI TestClient for Writing Agent tool execution, Athena longform memory/retrieval, world proposal review flow, chapter quality/continuity review, pytest targeted verification.

**Length Policy:** Treat `2000+` as an elastic quality target, not an exact hard target. For this phase, the acceptable chapter band is `2000-3000` words; only under-floor chapters or clearly runaway chapters should block continuation.

---

## Context

Current dogfood state before Phase35:

- project: `25fa2b20-5b9f-473b-918b-f4ea491cbb60`
- latest chapter: `19`
- latest title: `暗网迷途`
- Chapter 19 word count: `2322`
- pending world proposals: `0`
- longform maintenance: `current`
- outline currently has 19 chapters, so Chapter 20 must be planned via `expand_outline_window`.

Chapter 19 ending state:

- 林深、顾衍、赵猛、苏晚晴 are in/near the dark web passage.
- A级雾晶 can open or activate the next obstacle but should not solve everything.
- N-07 is a suspicious unresolved line, not confirmed as 苏晚晴.
- N-017 must remain distinct from N-07.
- 顾衍军牌留痕/损坏/被识别 can become a risk vector, but Chapter 19 text did not establish an actual loss event.
- 赵猛 debt and 雾安局 internal creditor remain pressure.

## Task 1: Preflight and Outline Chapter 20

- [x] **Step 1: Record baseline state**

Run a read-only script to record:

- latest generated chapter;
- pending proposal count;
- longform maintenance status;
- whether outline chapter 20 exists.

Result:

- latest chapter index: `19`;
- latest word count: `2322`;
- pending world proposals: `0`;
- longform maintenance: `current`;
- outline count: `19`;
- outline chapter 20 existed: `False`.

- [x] **Step 2: Expand outline window**

Use Writing Agent:

```json
[
  {
    "tool_name": "expand_outline_window",
    "params": {
      "start_chapter": 20,
      "end_chapter": 20,
      "command_args": "第20章承接第19章《暗网迷途》：主角团抵达第三研究所核心数据库入口附近。A级雾晶只能打开第一道门或激活入口，不等于拿到完整配方。继续保留苏晚晴与N-07的关系为未确认线索；不要把N-07写成顾衍军牌，不要混入N-017。顾衍军牌遗失、赵猛债务和雾安局追踪必须造成压力。第20章目标2000-3000字，应推进入口试探、权限阻碍、追兵压力和新的代价，不要直接拿到完整配方或终局真相。"
    }
  }
]
```

Result: Writing Agent run `32cd95d0-062c-4e1d-82c2-3263ce258b79`, status `success`, added chapter count `1`.

- [x] **Step 3: Verify outline 20 exists**

Read the latest `Outline.chapters` and confirm chapter 20 has a title, summary, scenes, and characters.

Result: Chapter 20 exists with title `三重门`, summary, 2 scenes, characters `林深` / `苏晚晴` / `顾衍`, and purpose focused on entrance exploration, permissions, pursuit pressure, and A级雾晶 cost.

## Task 2: Generate and Review Chapter 20

- [x] **Step 1: Run Agent generation chain**

Use Writing Agent:

```json
[
  {"tool_name": "preflight_writing", "params": {"chapter_index": 20}},
  {"tool_name": "generate_chapter", "params": {"chapter_index": 20}},
  {"tool_name": "review_chapter_quality", "params": {"chapter_index": 20}},
  {"tool_name": "review_chapter_continuity", "params": {"chapter_index": 20, "lookback": 20}},
  {"tool_name": "analyze_chapter_world_model", "params": {"chapter_index": 20}}
]
```

Result: Writing Agent run `c1982aff-4460-448a-9a9d-3acce194be93`, status `success`.

- `preflight_writing`: `ready`.
- `generate_chapter`: produced Chapter 20 at `2577` words, accepted inside `2000-3000`.
- `review_chapter_quality`: `warning`, no blocker, only pending world proposals.
- `review_chapter_continuity`: `ready`, 0 findings.
- `analyze_chapter_world_model`: skipped because the generation step already analyzed the chapter in the same run; 8 proposal items were created.

- [x] **Step 2: Inspect generated content**

Run read-only checks for:

- `word_count` inside `2000-3000`;
- no `我就是N-07`, `那是我`, `苏晚晴是实验体`, `N-017` misuse, `完整配方到手`, `成功拿到完整配方`;
- Chapter 20 continues Chapter 19 instead of skipping to final reveal.

Result: The first generated version passed the raw length check but failed semantic stage constraints:

- it opened the second door via 赵猛's iris, while the phase target required the second door to remain an obstacle;
- it killed 赵猛, prematurely cutting off the debt/inner-creditor pressure line;
- it therefore needed regeneration rather than simple compression.

- [x] **Step 3: Revise if needed**

If length is over target or forbidden terms remain, use:

```json
{
  "tool_name": "compress_chapter_to_target",
  "params": {
    "chapter_index": 20,
    "forbidden_terms": ["我就是N-07", "那是我", "苏晚晴是实验体", "N-017", "完整配方到手", "成功拿到完整配方"],
    "extra_instruction": "修订第20章：保持2000-3000字；不要确认苏晚晴就是N-07；不要混入N-017；A级雾晶只能推进入口第一层阻碍；不要拿到完整配方或终局真相；保留追兵、军牌遗失和赵猛债务压力。"
  }
}
```

Then rerun quality and continuity review.

Actual revision path:

1. Rejected the 8 stale proposal items extracted from the first Chapter 20 draft via Writing Agent run `7ef66959-0eca-4975-8ad2-e85fdcf445fd` step 1.
2. Regenerated Chapter 20 in the same run with explicit constraints:
   - keep `2000-3000` words;
   - only open the first door;
   - keep the second-door iris scan unresolved;
   - keep 赵猛 alive and keep his debt pressure active;
   - keep 苏晚晴 / N-07 unresolved;
   - do not reveal complete formula or terminal truth.
3. Final Chapter 20 result:
   - title: `三重门`;
   - word count: `2293`;
   - length decision: `within`, accepted;
   - world proposal creation: 2 new items;
   - quality review: warning only, 0 blockers;
   - continuity review: ready, 0 findings.
4. Manual semantic checks confirmed:
   - no hard `我就是N-07` / `苏晚晴是实验体` reveal;
   - no `N-017` contamination;
   - no complete formula acquisition;
   - A级雾晶 only opens the first door and is consumed;
   - second-door iris recognition remains the next obstacle;
   - 赵猛 survives and debt pressure remains active.

## Task 3: Resolve Proposals and Refresh Memory

- [x] **Step 1: Resolve Chapter 20 proposals**

Use `draft_world_model_proposal_resolution_decisions` and `apply_world_model_proposal_resolution`.

Policy:

- `event_summary`: `mark_uncertain` only after final revision is accepted.
- derived metadata such as `presence_count`: reject.
- textual mentions: reject unless they are genuine world facts.
- no approval of hard N-07/Su identity claims unless explicitly supported and intended.

Result:

- First-draft stale proposals: 8 rejected before regeneration.
- Final-draft proposals: 2 processed via Writing Agent run `d8642381-5855-442e-9443-d9e0dad58c49`.
- `event_summary`: marked uncertain.
- `presence_count` for `char.叶知秋`: rejected as derived metadata.
- pending proposal count after apply: `0`.

- [x] **Step 2: Refresh memory and retrieval**

Run maintenance repair or direct refresh/sync for Chapter 20 as needed.

Expected:

- pending proposals: `0`;
- longform maintenance: `current`;
- latest synced chapter index: `20`.

Result:

- pending proposals: `0`;
- longform maintenance: `current`;
- ready for writing: `True`;
- issue count: `0`;
- latest synced chapter index: `20`.

## Task 4: Verification, Report, and Commit

- [x] **Step 1: Run targeted verification**

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "compress_chapter_to_target or premature_mystery_reveal or review_chapter_quality or review_chapter_continuity"
```

Result: `33 passed, 78 deselected in 2.80s`.

- [x] **Step 2: Static checks**

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

Results:

- `git diff --check`: passed with no output.
- secret scan: no matches, `rg` exit code `1`.

- [x] **Step 3: Write report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-19-phase35-chapter20-loop.md` with:

- baseline;
- generated Chapter 20 result;
- revisions and proposal handling;
- maintenance state;
- verification evidence;
- next phase recommendation.

Result: report written to `docs/superpowers/notes/long-memory-agent/2026-05-19-phase35-chapter20-loop.md`.

- [x] **Step 4: Commit and push**

Commit and push `main` after checks pass.

Result: committed and pushed `17d6520 phase35: document chapter 20 loop` to `origin/main`.
