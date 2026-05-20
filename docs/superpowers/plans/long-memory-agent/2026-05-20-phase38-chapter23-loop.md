# Phase38 Chapter 23 Dogfood Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Continue the real longform dogfood loop by expanding, generating, reviewing, and stabilizing Chapter 23 of `《雾港回声》`.

**Architecture:** Use the Writing Agent as the main orchestration path. Keep Chapter 23 focused on the left-fork escape, creditor pursuit pressure, Su Wanqing's unstable clue, and the Ye Zhiqiu evidence-item trail. Resolve world model proposals and refresh longform memory/retrieval before continuing.

**Tech Stack:** FastAPI TestClient for Writing Agent tool execution, Athena longform memory/retrieval, world proposal review flow, chapter quality/continuity review, targeted pytest verification.

**Length Policy:** Treat `2000+` as an elastic quality target, not an exact hard target. Aim around `2000-3000` words, but only obvious shrinkage or runaway length should block continuation.

---

## Context

Current dogfood state before Phase38:

- project: `25fa2b20-5b9f-473b-918b-f4ea491cbb60`
- latest chapter: `22`
- latest title: `碎片中的签名`
- Chapter 22 word count: `2798`
- pending world proposals: `0`
- longform maintenance: `current`
- ready for writing: `True`
- latest synced chapter index: `22`
- retrieval documents: `89`
- retrieval chunks: `162`
- outline currently has 22 chapters, so Chapter 23 must be planned via `expand_outline_window`.

Phase38 preflight correction:

- A follow-up scan found two residual `陆先生` honorifics in Chapter 22 after the Phase37 name correction.
- The current canonical setup and Chapters 1-22 use `林深`; residual `陆先生` was corrected to `林先生`.
- Longform memory/retrieval was repaired after the correction.
- Final Chapter 22 scan: `陆辞=0`, `陆先生=0`, `陆=0`, `林先生=2`, `林深=37`.

Chapter 22 ending state:

- Lin Shen, Chen Mo, Zhao Meng, and unconscious/weak Su Wanqing have fled into the left fork.
- Scarface Liu's people have breached the first door and are pursuing them.
- The second iris door remains unopened.
- The group has only a clue, not access: `EV-2045-0812-07`, last accessed by Ye Zhiqiu at `2045-08-12 23:47`, location `雾安局证物室，柜号G-07`.
- A级雾晶 fragments are weak residual stimulus only.
- Ye Zhiqiu remains absent and unresolved.
- Su Wanqing / N-07 remains unresolved.

## Task 1: Preflight and Outline Chapter 23

- [x] **Step 1: Record baseline state**

Run a read-only script to record:

- latest generated chapter;
- pending proposal count;
- longform maintenance status;
- whether outline chapter 23 exists.

Expected:

- latest chapter index: `22`;
- pending world proposals: `0`;
- longform maintenance: `current`;
- outline chapter 23 does not exist yet.

Result:

- latest chapter index: `22`;
- latest word count: `2798`;
- pending world proposals: `0`;
- outline count: `22`;
- outline chapter 23 did not exist;
- latest synced chapter index: `22`.

- [x] **Step 2: Expand outline window**

Use Writing Agent:

```json
[
  {
    "tool_name": "expand_outline_window",
    "params": {
      "start_chapter": 23,
      "end_chapter": 23
    },
    "command_args": "第23章承接第22章《碎片中的签名》：林深背着虚弱的苏晚晴，与陈默、赵猛从左侧岔道逃离，疤脸刘的人已经破门并在后方追击。第二道虹膜门仍未打开，本章不得进入核心数据库，不得拿到完整配方。第23章应推进逃亡压力、岔道中的新阻碍、EV-2045-0812-07/G-07证物线索，以及叶知秋意识签名残片的下一步方向；叶知秋不能本人现身救场。苏晚晴可出现短暂雾感反应或片段梦话，但不能确认她就是N-07，不要混入N-017。赵猛必须继续存活，债务线不能结清。第23章目标约2000-3000字，字数为弹性质量指标，优先保证场景完整和节奏。"
  }
]
```

- [x] **Step 3: Verify outline 23 exists**

Read the latest `Outline.chapters` and confirm chapter 23 has:

- title;
- summary;
- scenes;
- characters;
- purpose that keeps second-door/core-database access bounded and preserves long-form suspense.

Result:

- `expand_outline_window` succeeded.
- Initial outline title: `暗渠追兵`.
- The outline was tightened before generation:
  - changed `G-07样本` into `G-07证物/柜号` to avoid N-07-like identity confusion;
  - clarified four-person state instead of vague `三人`;
  - kept Ye Zhiqiu absent, second door unopened, Su Wanqing / N-07 unresolved, and Zhao Meng alive.
- Final outline characters: `林深`, `苏晚晴`, `陈默`, `赵猛`.

## Task 2: Generate and Review Chapter 23

- [x] **Step 1: Run Agent generation chain**

Use Writing Agent:

```json
[
  {"tool_name": "preflight_writing", "params": {"chapter_index": 23}},
  {
    "tool_name": "generate_chapter",
    "params": {"chapter_index": 23},
    "command_args": "生成第23章：目标约2000-3000字，字数是弹性指标，优先保证场景完整和节奏；承接左侧岔道逃亡、疤脸刘追击、苏晚晴虚弱、第二道虹膜门未打开、EV-2045-0812-07/G-07证物线索。第二道门本章不得完全打开，不得进入核心数据库；不得拿到完整配方、配方内容或终局真相；叶知秋可作为权限/虹膜/意识密码线索推进，但不能现身救场；苏晚晴与N-07保持未确认，禁止写“我就是N-07”“苏晚晴是实验体”“N-07就是苏晚晴”；禁止混入N-017；赵猛必须继续存活，债务压力继续。请使用既有主角林深。"
  },
  {"tool_name": "review_chapter_quality", "params": {"chapter_index": 23}},
  {"tool_name": "review_chapter_continuity", "params": {"chapter_index": 23, "lookback": 20}},
  {"tool_name": "analyze_chapter_world_model", "params": {"chapter_index": 23}}
]
```

- [x] **Step 2: Inspect generated content**

Run read-only checks for:

- `word_count` near the `2000-3000` target band, with quality and scene completeness taking priority;
- no `陆辞`, `陆先生`, `我就是N-07`, `那是我`, `苏晚晴是实验体`, `N-07就是苏晚晴`, `苏晚晴就是`, `N-017`, `完整配方到手`, `成功拿到完整配方`, `配方如下`;
- no complete second-door opening;
- no core database entry;
- no Zhao Meng death;
- no Ye Zhiqiu sudden appearance.

- [x] **Step 3: Revise if needed**

If the chapter violates stage constraints, regenerate or revise before proposal handling.

Do not continue to the next chapter until:

- length is not obviously shrunken or runaway;
- automated reviews have no blockers;
- manual semantic checks confirm no premature reveal or shortcut.

Result:

- Generated Chapter 23 `暗渠追兵`.
- Initial generated word count: `2931`.
- Targeted revision was required:
  - replaced one residual `陆辞` with `林深`;
  - removed one `核心数据库` mention;
  - softened an over-explicit E-0047 / Ye Zhiqiu relationship inference into an uncertain authorization-template similarity clue.
- Final word count: `2926`.
- Final hard-term scan had no hits for name pollution, hard N-07 reveal, N-017 confusion, second-door opening, core database access, complete formula, Ye Zhiqiu appearance, Zhao Meng death/debt closure, Su Wanqing full recovery, or G-07/EV evidence shortcut.
- Final review results: `review_chapter_quality=ready`, `review_chapter_continuity=ready`.

## Task 3: Resolve Proposals and Refresh Memory

- [x] **Step 1: Resolve Chapter 23 proposals**

Use `draft_world_model_proposal_resolution_decisions` and/or explicit `apply_world_model_proposal_resolution`.

Policy:

- `event_summary`: `mark_uncertain` only after final text is accepted.
- derived metadata such as `presence_count`: reject.
- textual mentions: reject unless they are genuine world facts.
- no approval of hard N-07/Su identity claims unless explicitly intended.
- no approval of second-door/core database access unless the final accepted text actually supports it.

- [x] **Step 2: Refresh memory and retrieval**

Expected:

- pending proposals: `0`;
- longform maintenance: `current`;
- latest synced chapter index: `23`.

Result:

- World proposal handling applied `6` decisions:
  - `5` derived count/mention proposals rejected;
  - Chapter 23 `event_summary` marked `uncertain` after final text acceptance.
- Pending actionable proposals: `0`.
- Longform maintenance repaired after final Chapter 23 revision: `current`, `ready_for_writing=True`, `latest_synced_chapter_index=23`.
- A subagent found stale retrieval chunks containing old name `陆辞` from Chapter 22. Full retrieval reindex was run after memory repair.
- Final retrieval diagnostics: `82` documents, `159` chunks, including `23` chapter documents, `54` longform memory documents, and `5` world fact documents.
- Final retrieval old-name scan: `陆辞=0`, `陆先生=0`.

## Task 4: Verification, Report, and Commit

- [x] **Step 1: Run targeted verification**

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "premature_mystery_reveal or review_chapter_quality or review_chapter_continuity or event_summary"
```

- [x] **Step 2: Static checks**

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

Result:

- `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "premature_mystery_reveal or review_chapter_quality or review_chapter_continuity or event_summary"` -> `21 passed, 90 deselected`.
- `git diff --check` -> passed.
- `rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"` -> no matches.

- [x] **Step 3: Write report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-20-phase38-chapter23-loop.md` with:

- baseline;
- Phase38 preflight correction;
- generated Chapter 23 result;
- revisions and proposal handling;
- maintenance state;
- verification evidence;
- next phase recommendation.

Result:

- Report written to `docs/superpowers/notes/long-memory-agent/2026-05-20-phase38-chapter23-loop.md`.

- [ ] **Step 4: Commit and push**

Commit and push `main` after checks pass. If GitHub network is unavailable, record the local commit and ahead count.
