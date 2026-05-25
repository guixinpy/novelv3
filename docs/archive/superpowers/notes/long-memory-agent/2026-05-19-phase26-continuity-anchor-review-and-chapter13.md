# Phase26 Continuity Anchor Review and Chapter 13 Report

## Scope

Phase26 added a deterministic continuity-anchor review tool and used it in the dogfood longform writing loop before continuing to Chapter 13.

This phase targeted the concrete failure from Phase25: high-salience facts such as dates, identifiers, and relationship names could drift between chapters without being caught by the automated review chain.

## Implementation

Added `review_chapter_continuity` as a Writing Agent internal tool.

- New backend module: `backend/app/core/chapter_continuity_review.py`.
- Tool registration in `backend/app/services/writing_agent/run_service.py`.
- Review target type is `review`.
- Added the tool to `NON_BLOCKING_REPORT_TOOLS`, so a blocked review report does not make the whole agent run fail.

The initial deterministic checker covers three anchor classes:

- timeline anchor: conflicting dates for the same explicit event phrase, currently including `fog_disaster_minus_3_days`;
- identifier anchor: conflicting values for `顾衍:military_tag_number`;
- relationship-name anchor: conflicting values for `林深:father_name`.

Also added a quality-review blocker for unclosed Chinese dialogue quotes, because Chapter 13 exposed a real compression tail defect.

## TDD Evidence

RED/GREEN checks were run before implementation was accepted.

- Date anchor conflict initially failed because `review_chapter_continuity` was unsupported, then passed after tool registration and date-window extraction.
- Identifier conflict initially failed because no identifier anchors existed, then passed after military-tag extraction.
- Experiment-code distinction initially failed because `N-07` was treated as another military tag, then passed after local context filtering for `暗纹`, `不是军牌编号`, and `实验代号`.
- Report semantics initially failed because blocked continuity reports blocked the entire run, then passed after adding the tool to `NON_BLOCKING_REPORT_TOOLS`.
- Relationship-name conflict initially failed because father-name anchors did not exist, then passed after adding apposition/signature extraction.
- Unclosed quote detection initially failed, then passed after adding the structural-tail quality finding.

Targeted final command:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_review_chapter_quality_flags_unclosed_quote_tail tests\test_writing_agent_runs.py::test_agent_review_chapter_continuity_flags_relationship_name_conflict tests\test_writing_agent_runs.py::test_agent_review_chapter_continuity_flags_event_date_conflict tests\test_writing_agent_runs.py::test_agent_review_chapter_continuity_flags_identifier_kind_conflict tests\test_writing_agent_runs.py::test_agent_review_chapter_continuity_allows_experiment_code_distinction -q
```

Result:

```text
5 passed in 0.42s
```

## Dogfood Chapter 13 Evidence

Project: `25fa2b20-5b9f-473b-918b-f4ea491cbb60`.

Key agent runs:

- Chapter 12 continuity review: `f705a2b8-c50f-4d6b-8347-445ddfc91859`, ready, 0 findings.
- Chapter 13 preflight: `5e6a673b-9b81-41e6-a7b3-deeb118e4b3f`, blocked only because outline was missing.
- Chapter 13 outline expansion: `5db1793e-3bd6-45b2-ae3a-055a44aa0a39`, trace `714df19a-39da-4b32-a3c7-3c30201605c0`.
- Chapter 13 generation/review/continuity/analyze: `ba7b86fc-2f97-42b5-81e2-820305b14e4f`.
- Chapter 13 compression/review/continuity: `8acb192f-07a0-4955-aeaf-420db0de9196`, revision `617e6cc8-2826-4649-87e3-087d8f6f4812`, trace `c300a92e-e1e5-4d5a-805e-31c5bd479457`.
- Post-repair quality review: `b2f0f973-1ed9-4a44-b433-690d0d658bfa`, ready, 0 findings.
- Post-repair continuity review: `9dec6893-3af3-44cf-86e5-30433581c4b5`, ready, 0 findings.

Chapter 13 was generated at 3449 words, then compressed and manually repaired after subagent review found real content defects. Final Chapter 13 state:

- title: `信任裂缝`;
- word count: 2021;
- project word count: 31914;
- generated chapters: 13;
- pending world-model proposals: 0;
- longform maintenance: `current`, issue count 0.

Manual repair fixed:

- broken unclosed ending quote;
- `林远山` drifting from the established father name `林建国`;
- confusing wording that made `N-07` look like a replacement military-tag number rather than an experiment code.

Final Chapter 13 tail now closes cleanly:

```text
那个人影慢慢走近，走到光束的边缘，停下，然后开口说话——“林深，好久不见。”

声音很熟悉。林深愣住了，因为他认出了那个声音。

那是他父亲的声音。

但林建国，已经死了十年。
```

## Verification

T2 backend verification:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_world_proposals.py -q
```

Result:

```text
151 passed in 10.71s
```

Dogfood state check:

```text
{'project_word_count': 31914, 'generated_chapters': 13, 'chapter13_word_count': 2021, 'pending_world_proposals': 0, 'maintenance_status': 'current', 'maintenance_issue_count': 0, 'chapter13_title': '信任裂缝'}
```

Hygiene:

- `git diff --check`: no whitespace errors; only an existing CRLF-to-LF warning for `backend/tests/test_writing_agent_runs.py`.
- `rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"`: no matches.

## Decisions and Limits

The continuity checker is intentionally narrow. It catches explicit anchor conflicts rather than trying to infer broad natural-language contradictions. That keeps false positives manageable and makes it suitable as a deterministic Agent gate.

Current limits:

- date extraction only covers known event phrases;
- identifier extraction only covers the observed `顾衍` military-tag pattern;
- relationship-name extraction only covers the observed `林深:father_name` pattern;
- world-model accepted facts are still sparse for dogfood chapters, so some high-salience truths remain outside durable structured memory.

## Phase27 Recommendation

Phase27 should convert high-salience dogfood truths into durable world-model facts before continuing generation:

- seed or approve critical identity/date/code anchors into the world model;
- let `review_chapter_continuity` consult those truth anchors, not only recent generated text;
- improve compression so it preserves endings and does not create dangling dialogue;
- continue with Chapter 14 only after the high-salience truth path is clean.
