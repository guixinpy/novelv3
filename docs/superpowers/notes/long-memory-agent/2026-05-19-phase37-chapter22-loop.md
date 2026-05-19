# Phase37 Chapter 22 Dogfood Loop Report

## Summary

Phase37 continued the real longform dogfood loop for `《雾港回声》` by expanding, generating, reviewing, and stabilizing Chapter 22.

Final result:

- Chapter 22 title: `碎片中的签名`
- Final word count: `2798`
- Final chapter status: `generated`
- Pending world proposals: `0`
- Longform maintenance: `current`
- Latest synced chapter index: `22`
- Retrieval diagnostics: `89` documents, `162` chunks

## User Constraint Update

The long-term goal document was updated to treat `2000+` as an elastic writing-quality target, not as a mechanical hard constraint.

Current policy:

- Aim around `2000-3000` words for this project.
- Do not force the model to land exactly on 2000.
- Block or revise only when a chapter is obviously shrunken or runaway.
- Prioritize scene completeness, rhythm, and narrative quality over exact word count.

## Baseline

Before Phase37:

- latest generated chapter: `21`
- latest title: `虹膜之锁`
- Chapter 21 word count: `2996`
- pending world proposals: `0`
- outline count: `21`
- outline chapter 22 existed: `false`

Chapter 21 ending constraints:

- The group was still under pressure around the second iris door.
- The second door was still locked.
- Zhao Meng's creditor was cutting through the first door.
- Su Wanqing had just said `我看到了`.
- A级雾晶 fragments could only provide weak residual stimulus.
- Ye Zhiqiu remained a remote permission / iris clue.
- Su Wanqing / N-07 remained unresolved.

## Outline Work

`expand_outline_window` successfully created Chapter 22.

The first outline draft had one continuity problem: it drifted into the wrong protagonist name. After checking the canonical setup and Chapters 1-21, the accepted project protagonist is `林深`, not `陆辞`. Chapter 22 outline was therefore surgically corrected to keep continuity with the existing generated novel.

Final outline:

- title: `碎片中的签名`
- characters: `林深`, `苏晚晴`, `赵猛`, `陈默`
- keeps the second iris door locked
- keeps A级雾晶 fragments as weak residual stimulus only
- preserves Zhao Meng's creditor pressure
- keeps Su Wanqing / N-07 unresolved

## Chapter Result

The Writing Agent generated Chapter 22 at `2798` words.

The generated draft inherited the temporary name drift from the corrected outline command and used `陆辞`. Since the authoritative setup and all existing generated chapters use `林深`, the final accepted Chapter 22 content was mechanically corrected from `陆辞` to `林深`.

Final name scan:

- `林深`: `37`
- `陆辞`: `0`

Final hard-term scan had no hits for:

- hard N-07 reveal
- N-017 confusion
- complete formula
- second-door opening shortcut
- core database entry
- Zhao Meng death
- Ye Zhiqiu sudden appearance

Semantic checks:

- second door remains unopened
- no core database access
- A级雾晶 fragments only provide weak residual stimulus
- Zhao Meng remains alive
- creditor pressure continues
- Ye Zhiqiu remains a remote clue
- Su Wanqing / N-07 remains unresolved

## Proposal Handling

After final text acceptance, Chapter 22 world proposals were handled with guarded apply:

- `6` derived count/mention proposals rejected
- Chapter 22 `event_summary` marked `uncertain`
- actionable pending proposals after apply: `0`

The event summary was refreshed after the name correction before being marked uncertain, so longform memory now points at the final `林深` version.

## Memory And Retrieval

After the final name correction, longform maintenance detected Chapter 22 memory as stale.

Repair result:

- repaired memory count: `1`
- repaired retrieval count: `4`
- synced scope keys:
  - `chapter:22`
  - `arc:21-22`
  - `volume:1-22`
  - `global`

Final maintenance:

- status: `current`
- ready_for_writing: `true`
- issue_count: `0`
- latest_synced_chapter_index: `22`

Final retrieval:

- total documents: `89`
- total chunks: `162`
- chapter documents: `22`
- longform memory documents: `67`

## Verification

Targeted verification:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "premature_mystery_reveal or review_chapter_quality or review_chapter_continuity or event_summary"
```

Result:

```text
21 passed, 90 deselected
```

Static checks:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

Result:

- `git diff --check` passed.
- secret scan found no matches.

## Observations

The phase exposed a useful process issue: context from prior user discussions contained an old protagonist name, while the actual current project data uses `林深`. For dogfood generation, the DB/setup/current manuscript must override memory or older summaries.

This reinforces a workflow rule:

- before injecting concrete names into generation prompts, check the current setup and latest chapters when there is any risk of stale context.

## Next Phase

Phase38 should expand Chapter 23 before writing because the final `preflight_writing` check for Chapter 23 correctly blocks on missing outline.

Recommended Chapter 23 direction:

- continue from Chapter 22 ending in the unknown left fork
- keep pursuit pressure from Zhao Meng's creditor
- preserve the clue that Ye Zhiqiu's authorization residue may be tied to a sealed evidence item
- avoid opening the second door too early
- avoid confirming Su Wanqing / N-07
