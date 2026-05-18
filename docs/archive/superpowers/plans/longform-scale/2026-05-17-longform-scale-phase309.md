# Longform Scale Phase 309 - Show Chapter Word Target Drift

## Goal

Help the user spot chapter pacing drift during long-form manuscript review.

## Finding

Project-level target chapter count and target word count were already available, but the manuscript chapter sidebar only showed raw word counts. For 1000-chapter writing, repeatedly short or long chapters can accumulate into large pacing drift without an immediate visual signal.

## TDD Evidence

RED:

```powershell
npm run test:unit -- --run src/views/ManuscriptView.test.ts
```

Observed failure:

```text
expected '第1章 700字' to contain '700字 偏短'
```

GREEN:

```powershell
npm run test:unit -- --run src/views/ManuscriptView.test.ts
```

Observed result:

```text
8 passed
```

## Change

- Manuscript sidebar derives a per-chapter target word range from `target_word_count / target_chapter_count`.
- Chapters below the range are labeled `偏短`; chapters above the range are labeled `偏长`.
- Chapter list styling distinguishes over-target and under-target counts without changing navigation behavior.

## Verification

Full phase gate:

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` -> `703 passed`
- `npm run build` -> passed
- `npm run test:unit -- --run` -> `443 passed`
- Browser check for manuscript sidebar word drift labels -> rendered `700字 偏短`, `1,000字`, `1,300字 偏长`
- `git diff --check` -> passed
- DeepSeek key scan -> `NO_MATCH`
