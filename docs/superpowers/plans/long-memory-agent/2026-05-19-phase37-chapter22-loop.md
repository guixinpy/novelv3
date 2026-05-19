# Phase37 Chapter 22 Dogfood Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Continue the real longform dogfood loop by expanding, generating, reviewing, and stabilizing Chapter 22 of `《雾港回声》`.

**Architecture:** Use the Writing Agent as the main orchestration path. Keep Chapter 22 focused on Su Wanqing's faint vision, second-door verification clues, Zhao Meng's creditor pressure, and Ye Zhiqiu's remote permission trail. Resolve world model proposals and refresh longform memory/retrieval before continuing.

**Tech Stack:** FastAPI TestClient for Writing Agent tool execution, Athena longform memory/retrieval, world proposal review flow, chapter quality/continuity review, targeted pytest verification.

**Length Policy:** Treat `2000+` as an elastic quality target, not an exact hard target. For this phase, aim for `2000-3000` words, but only obvious shrinkage or runaway length should block continuation.

---

## Context

Current dogfood state before Phase37:

- project: `25fa2b20-5b9f-473b-918b-f4ea491cbb60`
- latest chapter: `21`
- latest title: `虹膜之锁`
- Chapter 21 word count: `2996`
- pending world proposals: `0`
- longform maintenance: `current`
- ready for writing: `True`
- latest synced chapter index: `21`
- outline currently has 21 chapters, so Chapter 22 must be planned via `expand_outline_window`.

Chapter 21 ending state:

- The group remains trapped between the first and second doors.
- The second door is still locked.
- Zhao Meng's creditor is cutting through the first door.
- Su Wanqing has just faintly said: `我看到了`.
- A级雾晶 is shattered; fragments can only provide weak residual stimulus, not an effective key.
- Ye Zhiqiu remains a remote permission / iris clue.
- Su Wanqing / N-07 remains unresolved.

## Task 1: Preflight and Outline Chapter 22

- [x] **Step 1: Record baseline state**

Run a read-only script to record:

- latest generated chapter;
- pending proposal count;
- longform maintenance status;
- whether outline chapter 22 exists.

Expected:

- latest chapter index: `21`;
- pending world proposals: `0`;
- longform maintenance: `current`;
- outline chapter 22 does not exist yet.

Result:

- latest chapter index: `21`;
- latest word count: `2996`;
- pending world proposals: `0`;
- outline count: `21`;
- outline chapter 22 did not exist.

- [x] **Step 2: Expand outline window**

Use Writing Agent:

```json
[
  {
    "tool_name": "expand_outline_window",
    "params": {
      "start_chapter": 22,
      "end_chapter": 22,
      "command_args": "第22章承接第21章《虹膜之锁》：苏晚晴在碎裂雾晶残留刺激下微弱苏醒并说“我看到了”，但碎裂A级雾晶不能作为有效钥匙或稳定能量源。第二道虹膜门仍锁定，最多允许获得替代验证线索或短暂显示下一步验证条件，不能直接进入核心数据库。赵猛债主正在切割第一道门并形成倒计时压力，赵猛必须继续存活，债务线不能结清。叶知秋可以作为虹膜模板、权限签名或意识密码来源被推进，但不能本人现身救场。苏晚晴与N-07仍是疑云，禁止确认身份，不要混入N-017，不要拿到完整配方或终局真相。第22章目标2000-3000字。"
    }
  }
]
```

- [x] **Step 3: Verify outline 22 exists**

Read the latest `Outline.chapters` and confirm chapter 22 has:

- title;
- summary;
- scenes;
- characters;
- purpose that keeps second-door access bounded and avoids terminal reveal.

Result:

- `expand_outline_window` succeeded.
- Initial outline drifted to the wrong protagonist name; the canonical setup and Chapters 1-21 use `林深`, so Chapter 22 outline was surgically corrected back to `林深`.
- Final outline title: `碎片中的签名`.
- Final outline characters: `林深`, `苏晚晴`, `赵猛`, `陈默`.
- Final outline keeps the second iris door locked, treats A级雾晶 fragments as weak residual stimulus only, preserves Zhao Meng's creditor pressure, and leaves Su Wanqing / N-07 unresolved.

## Task 2: Generate and Review Chapter 22

- [x] **Step 1: Run Agent generation chain**

Use Writing Agent:

```json
[
  {"tool_name": "preflight_writing", "params": {"chapter_index": 22}},
  {
    "tool_name": "generate_chapter",
    "params": {"chapter_index": 22},
    "command_args": "生成第22章：保持2000-3000字；承接苏晚晴说“我看到了”、债主切门、第二道虹膜门锁定；碎裂A级雾晶只能作为微弱残留刺激，不能作为有效钥匙；第二道门本章不得完全打开，不得进入核心数据库；赵猛必须继续存活，债务压力继续；叶知秋可作为权限/虹膜/意识密码线索推进，但不能现身救场；苏晚晴与N-07保持未确认，禁止写“我就是N-07”“苏晚晴是实验体”“N-07就是苏晚晴”；禁止混入N-017；禁止拿到完整配方、配方内容或终局真相。"
  },
  {"tool_name": "review_chapter_quality", "params": {"chapter_index": 22}},
  {"tool_name": "review_chapter_continuity", "params": {"chapter_index": 22, "lookback": 20}},
  {"tool_name": "analyze_chapter_world_model", "params": {"chapter_index": 22}}
]
```

- [x] **Step 2: Inspect generated content**

Run read-only checks for:

- `word_count` near the `2000-3000` target band, with quality and scene completeness taking priority;
- no `我就是N-07`, `那是我`, `苏晚晴是实验体`, `N-07就是苏晚晴`, `苏晚晴就是`, `N-017`, `完整配方到手`, `成功拿到完整配方`, `配方如下`;
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

- Generated Chapter 22 `碎片中的签名` at `2798` words.
- The generated draft initially used `陆辞`; this was a local correction error because the current canonical project setup and all existing generated chapters use `林深`. The final accepted Chapter 22 content was mechanically corrected from `陆辞` to `林深`.
- Final hard-term scan had no hits for hard N-07 reveal, N-017 confusion, complete formula, second-door opening, core database entry, Zhao Meng death, Ye Zhiqiu sudden appearance, or `陆辞`.
- Final review results: `review_chapter_quality=ready`, `review_chapter_continuity=ready`.
- Final semantic checks: second door remains unopened, no core database access, fragments only provide weak stimulus, Zhao Meng remains alive under creditor pressure, Ye Zhiqiu stays remote, Su Wanqing / N-07 remains unresolved.

## Task 3: Resolve Proposals and Refresh Memory

- [x] **Step 1: Resolve Chapter 22 proposals**

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
- latest synced chapter index: `22`.

Result:

- World proposal handling applied `7` decisions:
  - `6` derived count/mention proposals rejected;
  - Chapter 22 `event_summary` marked `uncertain` after final text acceptance.
- Pending actionable proposals: `0`.
- Longform maintenance repaired after final name correction: `current`, `ready_for_writing=True`, `latest_synced_chapter_index=22`.
- Retrieval diagnostics: `89` documents, `162` chunks, including `22` chapter documents and `67` longform memory documents.

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

Create `docs/superpowers/notes/long-memory-agent/2026-05-19-phase37-chapter22-loop.md` with:

- baseline;
- generated Chapter 22 result;
- revisions and proposal handling;
- maintenance state;
- verification evidence;
- next phase recommendation.

Result:

- Report written to `docs/superpowers/notes/long-memory-agent/2026-05-19-phase37-chapter22-loop.md`.

- [ ] **Step 4: Commit and push**

Commit and push `main` after checks pass. If GitHub network is unavailable, record the local commit and ahead count.
