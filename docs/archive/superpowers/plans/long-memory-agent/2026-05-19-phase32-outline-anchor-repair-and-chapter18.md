# Phase32 Outline Anchor Repair and Chapter 18 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair the stale Chapter 17 outline anchor, then continue the Dogfood writing loop through Chapter 18 with the elastic `2000-3000` policy.

**Architecture:** Treat the outline as writing memory that can steer future generation. Before expanding Chapter 18, reconcile the Chapter 17 outline with the reviewed Chapter 17 content so it preserves uncertainty around N-07 instead of hard-confirming 苏晚晴 as the experimental subject. Then use the existing Writing Agent tools for outline expansion, preflight, generation, review, proposal resolution, and memory sync.

**Tech Stack:** FastAPI backend, SQLAlchemy SQLite dogfood data, Writing Agent run service, Athena world proposals, longform memory/retrieval, pytest.

---

## Context

Phase31 ended with:

```text
project_id: 25fa2b20-5b9f-473b-918b-f4ea491cbb60
latest_chapter: 17
latest_title: 废弃医院
latest_word_count: 2580
length_policy: 2000-3000
pending_world_model_proposals: 0
longform_maintenance: current
latest_synced_chapter_index: 17
```

Current-state inspection before Phase32 found a mismatch:

- Chapter 17正文 only keeps 苏晚晴 and N-07 as a suspicious relation.
- The stored Chapter 17 outline still contains over-confirming wording such as `怀疑苏晚晴就是实验体7号` and `埋下苏晚晴实验体身份的伏笔`.

This is a real dogfood issue: future outline expansion can inherit stale certainty from outline memory even after chapter content has been corrected.

## Scope

In scope:

- Repair the stored Chapter 17 outline fields so they align with the reviewed content.
- Expand Chapter 18 outline from the actual Chapter 17 ending: the group needs more high-purity fog crystal and is heading to the lower-city black market.
- Preflight Chapter 18.
- Generate and review Chapter 18 using the elastic `2000-3000` chapter-length policy.
- Resolve world-model proposals and refresh longform memory/retrieval.
- Run a read-only subagent review for continuity, N-07/N-017 separation, and proposal/memory state.
- Record the phase report and targeted verification.

Out of scope:

- New frontend UI.
- New database schema.
- General knowledge-base implementation.
- A broad outline-drift detector unless Chapter 18 exposes a repeatable failure requiring code.
- Full frontend build, unless backend/API contract changes are introduced.

## Files

- Create: `docs/superpowers/notes/long-memory-agent/2026-05-19-phase32-outline-anchor-repair-and-chapter18.md`
- Update: this plan file as steps complete.
- Optional code/test files only if this phase exposes a deterministic backend bug.

## Task 1: Repair Chapter 17 Outline Anchor

- [x] **Step 1: Patch Chapter 17 outline wording**

Use the existing chapter-outline update behavior to replace only the stale certainty in Chapter 17:

```text
summary: 林深和顾衍将昏迷的苏晚晴带到废弃医院，试图寻找医疗设备稳定她的状况。医院内弥漫着稀薄的雾气，回声频现，林深触发一段与父母和N-07实验有关的记忆碎片；顾衍在地下室发现秘密实验室、N系列意识同步实验日志，以及回声稳定剂线索。苏晚晴在昏迷中重复数字“7”，但她与N-07的关系仍未确认。章节结尾确认稳定剂需要至少三块高纯度雾晶，三人转向下城黑市寻找更多雾晶。
purpose: 揭示医院与暗网实验的联系，保留苏晚晴与7号实验有关但未确认身份的伏笔；推进林深父母记忆碎片；让顾衍发现N-07实验记录并继续保持其N-017军牌事实独立；把下一步目标转向下城黑市雾晶交易。
```

Also update the final scene to avoid `苏晚晴就是实验体7号`:

```text
苏晚晴开始抽搐，喃喃说着“7号…不要…”。林深握住她的手，意识到她与7号实验存在联系，但仍不能确认她就是N-07。顾衍发现回声稳定剂需要至少三块高纯度雾晶，三人决定前往下城黑市寻找赵猛。
```

- [x] **Step 2: Verify repaired anchor**

Read Chapter 17 outline and assert it no longer contains:

```text
就是实验体7号
实验体身份
```

Expected: both strings absent. The outline should still contain `N-07` and `未确认`.

## Task 2: Expand and Preflight Chapter 18

- [x] **Step 1: Expand Chapter 18 outline**

Use `expand_outline_window` for Chapter 18 with guidance:

```text
第18章承接第17章《废弃医院》结尾：林深、顾衍带着昏迷的苏晚晴离开废弃医院，目标是去下城黑市寻找赵猛和更多高纯度雾晶，以合成回声稳定剂。保持N-07只是苏晚晴相关线索，不能确认苏晚晴就是N-07；保持顾衍军牌事实为N-017，不要与N-07混淆。章节目标为2000+，允许自然上浮到约3000字。第18章应推进黑市接触、交易风险、追捕压力和雾晶线索，不要直接解决稳定剂。
```

- [x] **Step 2: Preflight Chapter 18**

Run `preflight_writing` for Chapter 18.

Expected:

- status is `ready`;
- previous chapter state card references Chapter 17;
- length policy is `2000-3000`;
- no pending world-model proposal blocks generation.

## Task 3: Generate, Review, and Resolve Chapter 18

- [x] **Step 1: Generate and review Chapter 18**

Run an Agent tool chain:

```json
[
  {"tool_name": "generate_chapter", "params": {"chapter_index": 18}},
  {"tool_name": "review_chapter_quality", "params": {"chapter_index": 18}},
  {"tool_name": "review_chapter_continuity", "params": {"chapter_index": 18, "lookback": 20}},
  {"tool_name": "analyze_chapter_world_model", "params": {"chapter_index": 18}}
]
```

Expected:

- generated chapter is real prose, not outline;
- word count is at least 2000 and ideally no more than 3000;
- no hard confirmation that 苏晚晴就是N-07;
- no confusion between N-07 and N-017.

- [x] **Step 2: Fix actionable writing issues**

If review finds concrete quality/continuity issues:

- use planner revision or manual narrow correction for deterministic anchor wording;
- reindex the chapter;
- refresh longform memory;
- re-run quality and continuity review.

Only compress if the chapter clearly exceeds the elastic soft upper bound or review flags pacing/length as a real problem.

- [x] **Step 3: Resolve world-model proposals**

If pending proposals exist:

1. Run `draft_world_model_proposal_resolution_decisions`.
2. Inspect draft decisions.
3. Apply with `confirm_apply=true` if decisions match the reviewed chapter state.
4. Refresh Chapter 18 longform memory and retrieval.

Expected: pending proposal count returns to `0`.

## Task 4: Independent Review, Verification, and Report

- [x] **Step 1: Dispatch read-only subagent review**

Ask the subagent to check:

- Chapter 18 continues Chapter 17's black-market fog-crystal objective;
- N-07 and N-017 remain distinct;
- 苏晚晴 identity remains uncertain;
- Chapter 18 has no outline-like prose issue;
- pending proposals are clear;
- longform memory is current through Chapter 18.

- [x] **Step 2: Run targeted verification**

Because Phase32 is primarily dogfood data plus no planned code change, use T0/T1 verification:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "review_chapter_quality or review_chapter_continuity or length_decision"
```

If code changes are introduced, add the exact relevant test(s) before committing.

- [x] **Step 3: Write phase report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-19-phase32-outline-anchor-repair-and-chapter18.md` with:

- outline repair evidence;
- Chapter 18 outline/preflight/generation/review run IDs;
- word count and length decision;
- world-model proposal decisions;
- longform memory/retrieval state;
- subagent review result;
- verification commands;
- next phase recommendation.

- [x] **Step 4: Commit and push**

Commit docs and any code changes. Push `main`; if normal Git HTTPS push fails again, use the GitHub API fallback only after confirming the remote parent matches local `HEAD^`.
