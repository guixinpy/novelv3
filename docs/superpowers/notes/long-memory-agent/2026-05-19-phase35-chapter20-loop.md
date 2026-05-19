# Phase35 Chapter 20 Dogfood Loop Report

## Summary

Phase35 continued the real `《雾港回声》` dogfood loop through Chapter 20 and used the generation result to test the Writing Agent's outline expansion, generation, review, proposal handling, and longform maintenance path.

The final accepted Chapter 20 is `《三重门》`, `2293` words. It follows the elastic chapter-length policy: `2000+` is treated as a `2000-3000` quality band rather than an exact target.

## Baseline

- project: `25fa2b20-5b9f-473b-918b-f4ea491cbb60`
- latest chapter before phase: Chapter 19, `《暗网迷途》`
- Chapter 19 word count: `2322`
- pending world proposals before phase: `0`
- longform maintenance before phase: `current`
- outline count before phase: `19`
- Chapter 20 outline existed before phase: `false`

## Outline Expansion

Writing Agent run `32cd95d0-062c-4e1d-82c2-3263ce258b79` expanded the rolling outline to Chapter 20.

Final outline anchor:

- title: `三重门`
- purpose: push the core database entrance attempt, introduce three permissions, consume the A-level fog crystal, keep Su Wanqing / N-07 unresolved, and avoid complete formula acquisition.
- scenes: A-level fog crystal activation, memory-text backlash, pursuit pressure, first-door progress only.

## First Generation

Writing Agent run `c1982aff-4460-448a-9a9d-3acce194be93` produced the first Chapter 20 version.

Result:

- generated word count: `2577`
- length decision: `within`, accepted under `2000-3000`
- quality review: warning only, no blockers
- continuity review: ready, 0 findings
- world proposals created: `8`

Manual semantic review rejected this version despite passing automated gates:

- it opened the second door through Zhao Meng's iris;
- it killed Zhao Meng and prematurely cut off the debt pressure line;
- it exceeded the phase narrative boundary, where the second door should remain an unresolved obstacle.

## Revision

Writing Agent run `7ef66959-0eca-4975-8ad2-e85fdcf445fd` handled the correction path.

Step 1 rejected the 8 stale world proposals from the superseded first draft.

Step 2 regenerated Chapter 20 with stricter constraints:

- keep `2000-3000` words;
- only open the first door;
- keep the second-door iris scan unresolved;
- keep Zhao Meng alive and preserve debt pressure;
- keep Su Wanqing / N-07 unresolved;
- do not mix N-017 into the N-07 line;
- do not acquire the complete formula or terminal truth.

Final Chapter 20:

- title: `三重门`
- word count: `2293`
- length decision: `within`, accepted
- quality review: warning only, 0 blockers
- continuity review: ready, 0 findings
- new world proposals created: `2`

Manual semantic checks confirmed:

- no `我就是N-07`;
- no `苏晚晴是实验体`;
- no `N-017`;
- no complete formula acquisition;
- A-level fog crystal only opens the first door and is consumed;
- second-door iris recognition remains the next obstacle;
- Zhao Meng survives and his debt pressure remains active.

The remaining quality warning was `convenient_key_item_acquisition`, but the final text already includes cost and risk: the fog crystal shatters, the group is trapped between the first and second doors, and Zhao Meng's creditor arrives. This is acceptable for continuation.

## World Model And Memory

Writing Agent run `d8642381-5855-442e-9443-d9e0dad58c49` processed the final Chapter 20 proposals:

- `event_summary`: `mark_uncertain`
- `presence_count` for `char.叶知秋`: `reject`

Final state:

- pending world proposals: `0`
- longform maintenance: `current`
- ready for writing: `True`
- issue count: `0`
- latest synced chapter index: `20`

## Verification

Targeted verification:

- `backend/.venv/Scripts/python.exe -m pytest tests/test_writing_agent_runs.py -q -k "compress_chapter_to_target or premature_mystery_reveal or review_chapter_quality or review_chapter_continuity"`: `33 passed, 78 deselected in 2.80s`.
- `git diff --check`: passed with no output.
- `rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"`: no matches, exit code `1`.

## Next Phase Recommendation

Phase36 should continue from the Chapter 20 endpoint:

- the group has opened only the first door;
- A-level fog crystal is consumed;
- the second door requires iris recognition;
- Su Wanqing is unconscious/unstable and may be relevant to memory-text or N-07 but remains unconfirmed;
- Zhao Meng is alive, trapped with the group, and his creditor has arrived outside;
- avoid using Zhao Meng's iris as a convenient solution unless a later phase intentionally establishes why he has A-level authorization.
