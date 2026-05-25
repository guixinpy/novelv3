# Phase32 Outline Anchor Repair and Chapter 18

## Goal

Phase32 continued the real Dogfood writing loop while fixing a newly exposed writing-memory issue: Chapter 17正文 had already kept 苏晚晴 and N-07 as an uncertain relation, but the stored Chapter 17 outline still contained over-confirming wording. The phase repaired that outline anchor before expanding and generating Chapter 18.

## Starting State

Project:

- `25fa2b20-5b9f-473b-918b-f4ea491cbb60`
- Title: `雾港回声`

Before Phase32:

- latest generated chapter: `17`
- Chapter 17 title: `废弃医院`
- Chapter 17 word count: `2580`
- length policy: `2000-3000`
- pending world-model proposals: `0`
- longform maintenance: `current`
- latest synced chapter index: `17`

## Issue Found

Current-state inspection found a mismatch:

- Chapter 17正文 only implied that 苏晚晴 is related to N-07.
- Chapter 17 outline still contained stale hard-confirming wording such as `怀疑苏晚晴就是实验体7号` and `埋下苏晚晴实验体身份的伏笔`.

This mattered because Chapter 18 outline expansion uses the stored outline as writing memory.

## Outline Anchor Repair

Updated Chapter 17 outline summary, purpose, and final scene to preserve uncertainty:

- N-07 remains a key clue.
- 苏晚晴与7号实验有关 remains possible.
- Her identity is not confirmed.
- The next objective points to lower-city black market fog-crystal acquisition.

Verification result:

```text
contains_hard_confirm: False
contains_uncertain: True
contains_n07: True
```

## Chapter 18 Outline and Preflight

Agent run:

- run: `b5ee8309-81d2-430f-86e8-9741ef3e4777`
- status: `success`

Steps:

- `expand_outline_window`
  - status: `completed`
  - trace: `16802b82-0e58-423e-8fcd-dc0b7be780e2`
  - added chapter count: `1`
- `preflight_writing`
  - status: `ready`
  - previous chapter: ready, Chapter 17
  - longform maintenance: ready
  - retrieval: ready, `69` documents / `125` chunks
  - length policy: ready

Chapter 18 outline:

- title: `黑市暗流`
- core objective: 林深 and 顾衍 take unconscious 苏晚晴 to the lower-city black market, contact 赵猛, face 雾安局 pressure, and discover further 回声计划 / 稳定剂 clues.

## Initial Chapter 18 Generation

Agent run:

- run: `22b1c3d8-9bf2-4737-8b61-1fb73a0ed202`
- status: `success`
- generation trace: `6572f92a-c274-48e7-9bbe-7e59d37b844d`

Initial generated chapter:

- title: `黑市暗流`
- word count: `3470`
- length decision: `over`
- target range: `2000-3000`
- pending proposals after analysis: `10`

Initial review findings:

- `chapter_over_target`: 3470 words exceeded the 3000 soft upper bound.
- `convenient_key_item_acquisition`: fog crystal acquisition looked too smooth.
- `pending_world_model_proposals`: 10 pending items.

Manual inspection also found a hard-confirming sentence:

```text
N-07——苏晚晴的实验代号。
```

This contradicted the active uncertainty anchor and required revision.

## Proposal Handling Before Revision

Compression was correctly blocked while proposals were pending:

```text
status: blocked
reason: pending_world_model_proposals
pending_world_model_proposal_count: 10
```

Draft/apply runs:

- draft run: `2f000eca-4730-4589-99d8-aba5594ab2fd`
- apply run: `a707ee1f-08fa-460b-8ecd-ef73e2d7a728`
- applied decisions: `10`
- pending after apply: `0`

Important decision:

- The pre-revision `event_summary` proposal was rejected because Chapter 18 required revision before memory refresh. This prevented a stale event summary from entering chapter-level longform memory.

## Chapter 18 Compression and Revision

Agent run:

- run: `6266cec1-3cc1-4995-8a60-1fb38a7d22b8`
- status: `success`
- compression trace: `6c1e3d08-873d-405e-aa63-2a90e379c649`

Revision instruction:

- compress Chapter 18 to under 3000 words;
- preserve black-market contact, 赵猛 debt/risk, 雾安局 pursuit, B-12 room, and 第三研究所 core database clue;
- keep N-07 as a suspicious 苏晚晴-related clue, not a confirmed identity;
- preserve transaction cost by making the fog crystal a debt/favor owed to 赵猛.

Final Chapter 18:

- title: `黑市暗流`
- word count after compression: `2071`
- status: `generated`
- quality review: ready, `finding_count=0`
- continuity review: ready, `finding_count=0`

Anchor checks after revision:

- `就是N-07`: absent
- `就是实验体7号`: absent
- `苏晚晴就是`: absent
- `苏晚晴的实验代号`: absent
- `N-017`: absent from Chapter 18
- `军牌`: present only as 顾衍 using it as a tool to open a lock
- transaction debt: present (`先欠着`, `我会还的`)

The phrase `实验对象编号N-07` remains only as text inside an old experiment record. It is followed by uncertain framing (`N-07是苏晚晴相关编号`) rather than identity confirmation.

Independent review suggested the phrase `N-07是苏晚晴相关编号` could still be misread. A narrow wording correction changed it to:

```text
这个编号与苏晚晴有关，但还不能说明她就是N-07。
```

Post-correction state:

- word count: `2082`
- base version: `Phase32 base before N-07 clarification wording`
- result version: `Phase32 result after N-07 clarification wording`
- `N-07是苏晚晴相关编号`: absent
- `苏晚晴的实验代号`: absent
- `就是实验体7号`: absent
- `苏晚晴就是`: absent

## Final Review and Maintenance

Final review run:

- run: `3a7bd95a-2c89-4fa6-ad42-179b2ea68bfb`
- status: `success`

Steps:

- `review_chapter_quality`: ready, `finding_count=0`
- `review_chapter_continuity`: ready, `finding_count=0`
- `analyze_chapter_world_model`: completed, created `0`, updated `0`, skipped duplicates `9`

Final review after wording correction:

- run: `64526eac-82bf-498d-8288-846be93ed103`
- status: `success`
- `review_chapter_quality`: ready, `finding_count=0`
- `review_chapter_continuity`: ready, `finding_count=0`
- `analyze_chapter_world_model`: completed, created `0`, updated `0`, skipped duplicates `9`

World-model queue:

- pending proposals: `0`
- proposal statuses: `approved=5`, `rejected=94`, `uncertain=29`

Longform maintenance:

- status: `current`
- ready for writing: `true`
- issue count: `0`
- latest synced chapter index: `18`
- word target:
  - min `2000`
  - max `3000`
  - under-target chapters: `[4]`
  - over-target chapters: `[1, 2, 3]`
- within-target count: `14`

After the final wording correction, maintenance briefly reported one stale retrieval index for `chapter:18`. Running the existing maintenance repair synced that scope:

- repaired retrieval count: `1`
- synced scope keys: `chapter:18`
- remaining issue count: `0`
- final status: `current`
- ready for writing: `true`

Chapter 18 memory:

- source: `chapter_content`
- word count: `2071`
- reason: the pre-revision event summary was rejected to avoid stale memory after revision.

## Issue Recorded

Phase32 exposed a repeatable design weakness:

- If an `event_summary` proposal is created before chapter revision, it can become stale.
- The current duplicate candidate logic prevents a clean post-revision replacement after the earlier proposal has already been reviewed into a non-actionable status.
- Phase32 avoided stale memory by rejecting the pre-revision event summary and allowing Chapter 18 memory to fall back to content preview.

Recommended future improvement:

- Add a post-revision event-summary refresh path that can create or update a chapter writing-memory summary without polluting world truth.

## Verification

Commands:

```powershell
git diff --check
```

Result: exit 0.

```powershell
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

Result: no matches.

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "review_chapter_quality or review_chapter_continuity or length_decision"
```

Result before final wording report update:

- `18 passed, 88 deselected in 1.38s`

Final wording correction was followed by a live Writing Agent review run:

- run: `64526eac-82bf-498d-8288-846be93ed103`
- quality ready, 0 findings
- continuity ready, 0 findings

## Next Phase Recommendation

Phase33 should continue from Chapter 19:

- start from Chapter 18 ending: 林深、顾衍、苏晚晴, and 赵猛 flee through the dark-net tunnels with fog crystal debt and the 第三研究所 core database clue;
- avoid directly solving the stable-agent formula too quickly;
- consider implementing the post-revision event-summary refresh path before or during Chapter 19 if stale summary handling becomes a recurring bottleneck.
