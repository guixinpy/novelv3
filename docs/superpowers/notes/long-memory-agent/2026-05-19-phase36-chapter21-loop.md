# Phase36 Chapter 21 Dogfood Loop Report

## Summary

Phase36 continued the `《雾港回声》` dogfood loop through Chapter 21 and exposed two useful system/process issues:

- the rolling outline expansion can still over-advance a local obstacle unless corrected before generation;
- rejecting every overlong-draft proposal before compression can discard an event summary that remains valid after compression.

Final accepted Chapter 21 is `《虹膜之锁》`, `2996` words, within the elastic `2000-3000` range.

## Baseline

- project: `25fa2b20-5b9f-473b-918b-f4ea491cbb60`
- latest chapter before phase: Chapter 20, `《三重门》`
- Chapter 20 word count: `2293`
- pending world proposals before phase: `0`
- longform maintenance before phase: `current`
- ready for writing: `True`
- outline count before phase: `20`
- Chapter 21 outline existed before phase: `false`
- latest synced chapter index before phase: `20`

## Outline Expansion

Writing Agent run `b9df4484-3814-44bb-a1af-8e84a9fc2969` expanded the rolling outline to Chapter 21.

The first generated outline had a stage-boundary problem:

- it reused the shattered A-level fog crystal as a cracking tool;
- it opened the second door in Chapter 21.

This contradicted the accepted Chapter 20 endpoint. The outline was corrected through the existing outline chapter PATCH API.

Final outline anchor:

- title: `虹膜之锁`
- second door remains locked;
- A-level fog crystal is unavailable as an effective key;
- Zhao Meng remains alive with creditor pressure active;
- Ye Zhiqiu is a remote permission clue, not a rescuer;
- Su Wanqing / N-07 remains unresolved.

## Generation

Writing Agent run `2604bbda-a5f5-4384-8c6f-d815b4ba976d` generated the first Chapter 21 draft.

Result:

- generated word count: `3485`
- length decision: `over`, accepted with warning
- quality review: warning only, no blockers
- continuity review: ready, 0 findings
- world proposals created: `8`

Manual review found no hard lore break:

- no confirmed Su Wanqing / N-07 identity reveal;
- no N-017 contamination;
- no complete formula acquisition;
- no second-door pass;
- no Zhao Meng death.

But the draft exceeded the soft cap and leaned too heavily on shattered fog-crystal residue, so it required compression.

## Compression

Writing Agent run `999fa447-101e-4348-adcc-41b56bd2a7c7` handled the correction path.

Step 1 rejected the 8 proposals extracted from the superseded overlong draft.

Step 2 compressed Chapter 21:

- previous word count: `3485`
- final word count: `2996`
- target range: `2000-3000`
- remaining forbidden terms: `[]`
- compression attempts: `3`

Compression summary from the tool:

> 压缩至约2500字，保留走廊困局、第二道虹膜门、赵猛债主切门逼近、叶知秋权限线索和苏晚晴雾感碎片。删减重复解释和冗长推理，如顾衍背景说明、林深内心独白；保留关键动作链（检查门框、读取刻痕、切割门）和对话；第二道门未开启，赵猛存活，叶知秋未现身，苏晚晴与N-07未确认；A级雾晶碎片仅作为微弱刺激，未作为有效钥匙。

Post-compression reviews:

- `review_chapter_quality`: `ready`, 0 findings
- `review_chapter_continuity`: `ready`, 0 findings

Manual semantic checks confirmed:

- second door remains locked;
- no core database access or formula acquisition;
- Zhao Meng survives and debt pressure continues;
- Ye Zhiqiu does not appear in person;
- Su Wanqing / N-07 remains an unresolved inference, not a confirmed reveal;
- fog-crystal fragments are only residual stimulus, not an effective key.

## World Model And Memory

Final state:

- pending world proposals: `0`
- longform maintenance: `current`
- ready for writing: `True`
- issue count: `0`
- latest synced chapter index: `21`

Operational issue recorded:

- The overlong draft's event summary was rejected before compression.
- After compression, analysis created 0 new proposal items because the deterministic summary remained equivalent.
- This is not a production-code defect: recreating identical rejected proposals would cause user-rejected summaries to keep reappearing.
- Future phases should avoid blanket-rejecting event summaries before compression, or add an explicit `superseded_by_revision` semantics that allows safe refreshed event-summary candidates after chapter revision.

## Verification

Targeted verification:

- `backend/.venv/Scripts/python.exe -m pytest tests/test_writing_agent_runs.py -q -k "premature_mystery_reveal or review_chapter_quality or review_chapter_continuity or event_summary"`: `21 passed, 90 deselected in 1.66s`.
- `git diff --check`: passed with no output.
- `rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"`: no matches, exit code `1`.

## Next Phase Recommendation

Phase37 should continue from the Chapter 21 endpoint:

- the group is still trapped between the first and second doors;
- the second door is still locked;
- the creditor is actively cutting into the first door;
- Su Wanqing has just faintly said `我看到了`;
- A-level fog crystal fragments cannot serve as an effective key;
- Ye Zhiqiu remains a remote permission/iris clue;
- avoid turning Su Wanqing's readable memory code into a confirmed N-07 identity reveal.
