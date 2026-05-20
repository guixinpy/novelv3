# Phase38 Chapter 23 Dogfood Loop Report

## Summary

Phase38 continued the real longform dogfood loop for `《雾港回声》` by expanding, generating, reviewing, and stabilizing Chapter 23.

Final result:

- Chapter 23 title: `暗渠追兵`
- Final word count: `2926`
- Final chapter status: `generated`
- Pending world proposals: `0`
- Longform maintenance: `current`
- Latest synced chapter index: `23`
- Retrieval diagnostics: `82` documents, `159` chunks

## Baseline

Before Phase38:

- latest generated chapter: `22`
- latest title: `碎片中的签名`
- Chapter 22 word count: `2798`
- pending world proposals: `0`
- outline count: `22`
- outline chapter 23 existed: `false`
- longform maintenance: `current`
- latest synced chapter index: `22`

## Phase38 Preflight Correction

A baseline scan found that Chapter 22 still had two residual `陆先生` honorifics after the Phase37 `陆辞 -> 林深` correction.

Correction:

- `陆先生` -> `林先生`
- refreshed Chapter 22 longform memory
- repaired retrieval after the correction

Immediate post-correction scan:

- `陆辞=0`
- `陆先生=0`
- `陆=0`
- `林先生=2`
- `林深=37`

This exposed a process issue: name canonicalization needs to scan honorifics and retrieval chunks, not only exact full names.

## Subagent Review

A read-only subagent reviewed Chapter 23 constraints and flagged a high-risk retrieval issue:

- `chapter_contents` for Chapter 22 was clean after correction.
- Retrieval chunks still contained stale `陆辞` text from Chapter 22.
- This stale retrieval could pollute future generation if not reindexed.

The issue was confirmed and fixed in this phase by running a full retrieval reindex after final memory refresh.

Final retrieval old-name scan:

- `陆辞` chunks: `0`
- `陆先生` chunks: `0`

## Outline Work

`expand_outline_window` successfully created Chapter 23.

Initial outline:

- title: `暗渠追兵`
- main movement: left-fork escape into drainage channels
- pressure: Scarface Liu's pursuit
- clue: G-07 / Ye Zhiqiu signature residue

The outline was tightened before generation:

- changed `G-07样本` into `G-07证物/柜号`
- clarified the four-person state: `林深`, `苏晚晴`, `陈默`, `赵猛`
- kept second-door access bounded
- kept Ye Zhiqiu absent
- kept Su Wanqing / N-07 unresolved
- kept Zhao Meng alive and under creditor pressure

## Chapter Result

The Writing Agent generated Chapter 23 at `2931` words.

Targeted revisions were needed:

- replaced one residual `陆辞` with `林深`
- removed one `核心数据库` mention
- softened a too-explicit E-0047 / Ye Zhiqiu relationship inference into an uncertain authorization-template similarity clue

Final Chapter 23:

- title: `暗渠追兵`
- word count: `2926`
- protagonist name clean: no `陆辞`, `陆先生`, or standalone `陆`
- no hard N-07 reveal
- no N-017 confusion
- no complete formula
- no second-door opening shortcut
- no core database access
- no Zhao Meng death or debt closure
- no Ye Zhiqiu appearance
- no G-07/EV evidence shortcut

Semantic checks:

- second door remains unopened
- the group is still in pursuit pressure
- Su Wanqing remains weak and unresolved
- G-07 is only a next-step evidence direction
- E-0047 remains an uncertain clue, not an identity conclusion
- Zhao Meng remains alive

## Proposal Handling

After final text acceptance, Chapter 23 world proposals were handled with guarded apply:

- `5` derived count/mention proposals rejected
- Chapter 23 `event_summary` marked `uncertain`
- actionable pending proposals after apply: `0`

## Memory And Retrieval

Longform repair after final Chapter 23 revision:

- repaired memory count: `1`
- repaired retrieval count: `4`
- synced scope keys:
  - `chapter:23`
  - `arc:21-23`
  - `volume:1-23`
  - `global`

Full retrieval reindex:

- indexed documents: `16`
- indexed chunks: `45`
- indexed terms: `23164`
- indexed embeddings: `45`
- preserved documents: `66`
- removed stale documents: `27`

Final maintenance:

- status: `current`
- ready_for_writing: `true`
- issue_count: `0`
- latest_synced_chapter_index: `23`

Final retrieval:

- total documents: `82`
- total chunks: `159`
- chapter documents: `23`
- longform memory documents: `54`
- world fact documents: `5`

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

The main system issue found in this phase is retrieval freshness after direct data correction.

Current behavior:

- chapter content can be corrected;
- longform memory can be repaired;
- but chapter-source retrieval chunks may remain stale unless reindexing is explicitly run.

Operational rule going forward:

- after manual or revision-based chapter text corrections, run both longform repair and retrieval reindex or a targeted chapter retrieval reindex before continuing generation.

Potential future product improvement:

- add a Writing Agent maintenance tool that performs `repair_longform_maintenance + reindex stale chapter retrieval` as one safe post-revision step.

## Next Phase

Phase39 should expand Chapter 24 before writing because final `preflight_writing` for Chapter 24 correctly blocks on missing outline.

Recommended Chapter 24 direction:

- continue from Chapter 23 ending after the group emerges into the foggy street
- find temporary shelter before pursuing the G-07 evidence route
- keep Scarface Liu pursuit and Zhao Meng debt pressure alive
- keep Su Wanqing weak and unresolved
- avoid opening the second iris door or reaching the evidence item too quickly
