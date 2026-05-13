# Athena 20-Chapter Dogfood Log

Date: 2026-04-30

Project: `霜灯档案：20章Dogfood`

Goal: Use the app as a real creator, with emphasis on Athena / world-model workflows, to create and inspect a 20-chapter novel project. Fix reproducible blocking issues when appropriate; record non-blocking UI, UX, and logic issues here.

## Running Notes

- Created a 20-chapter project from the UI with genre `近未来悬疑群像` and target word count `60000`.
- Generated setup through Hermes `/setup`; setup completed and the production overview updated.
- Generated storyline through Hermes `/storyline`; storyline completed and the production overview updated.
- Started outline generation through Hermes `/outline`; the background task failed after roughly 58 seconds with `无法解析模型返回的 JSON`.
- After fixing outline token budgeting, retried `/outline` successfully and generated a 20-chapter outline.
- Generated chapters 1-20. Final total: `78127` words, 20 Athena proposal bundles, 21 retrieval documents, 0 consistency issues from the summary endpoint. Only the first chapter proposal has one approved item from manual review; the remaining 19 bundles are pending review.
- Browser-checked Calliope after full generation: sidebar renders 20 chapter buttons and chapter 20 opens in the editor.

## Issues And Improvements

### DFD-001: Create-project modal remains in DOM after successful creation

Severity: Low

Status: fixed in working tree, regression test added

Observation: After creating the project, the project list showed the new project, but the DOM snapshot still included the `新建项目` dialog with all filled fields and a disabled `创建` button.

Impact: It may be visually hidden, but it can confuse accessibility tooling and may leave stale form state in the DOM. Needs visual and focus verification before deciding whether this is only a DOM artifact or a real UX/accessibility defect.

Evidence: Browser DOM snapshot after creating `霜灯档案：20章Dogfood`.

Fix applied: Confirmed the create dialog is closed and form state reset after a successful create. Added a regression test that creates a project through the modal and asserts `[data-testid="project-create-modal"]` is removed from the DOM.

### DFD-002: AI task progress wording duplicates the action verb

Severity: Low

Status: fixed in working tree, regression test added

Observation: During generation, Hermes displayed status strings such as `生成设定生成中...` and `生成故事线生成中...`.

Impact: The wording feels machine-composed and less polished for creator-facing UX. A cleaner pattern would be `设定生成中...`, `故事线生成中...`, or `正在生成设定...`.

Evidence: Hermes chat stream during `/setup` and `/storyline`.

Root cause: The chat message result renderer reused action labels such as `生成设定` for the `generating` state and then appended `生成中...`, producing duplicated verbs.

Fix applied: Added progress-specific action labels, so generating states render as `设定生成中...`, `故事线生成中...`, `大纲生成中...`, and `正文生成中...`. Added a component regression test.

### DFD-003: Storyline command messages appear duplicated in the chat transcript

Severity: Medium

Status: fixed in working tree, regression test added

Observation: After confirming `/storyline`, the chat transcript showed the user command, assistant recommendation, confirmation message, and `生成故事线生成中...` block twice before the final success message.

Impact: This makes users doubt whether the action ran twice and clutters the main writing conversation. Needs root-cause investigation: possible frontend optimistic update duplication, repeated workspace bootstrap merge, or backend message persistence duplication.

Evidence: Browser DOM snapshot after `/storyline` completion.

Root cause: Hermes optimistically appended command/assistant/confirmation messages without backend message IDs, but later task polling still used the previously loaded `after_id` anchor. The API then returned the persisted copies of those same messages, and the store appended them again.

Fix applied: Chat polling now invalidates the stale history anchor after local optimistic appends and falls back to a full-history cursor slice before resuming incremental polling. Added a store regression test for `/storyline` + confirm with an existing history message ID.

### DFD-004: 20-chapter outline generation can fail on model JSON parsing

Severity: High

Status: fixed in working tree, end-to-end recheck passed

Observation: Hermes `/outline` for a 20-chapter plan failed after roughly 58 seconds. Backend stderr logged `Task exception was never retrieved`, and stdout logged `event=task_failed ... error="无法解析模型返回的 JSON"`.

Impact: This blocks the normal creator flow from setup/storyline into outline and therefore blocks generating the requested 20-chapter novel through the UI.

Evidence: `.tmp/backend-server.stderr.log` and `.tmp/backend-server.stdout.log` after the `/outline` attempt for project `b9d50481-6f5c-4f54-9b60-984c43e40808`.

Root cause: 20-chapter outline generation still used the generic `max_tokens=4000`, which is too small for a structured 20-chapter JSON outline and can cause truncated or otherwise invalid model output.

Fix applied: Added dynamic outline token budgeting: 10 chapters remains at 4000 tokens, 20 chapters gets 8000 tokens, capped at 12000. Added a regression test proving 20-chapter outline generation requests at least 8000 max tokens.

End-to-end recheck: Passed. Retried `/outline`; the new trace used `max_tokens=8000`, the background task completed, and the saved outline has `total_chapters=20` with 20 chapter entries.

### DFD-005: Chapter generation can proceed before Athena world model is initialized

Severity: Medium

Status: fixed in working tree, backend regression tests added

Observation: Generated chapter 1 successfully before importing Setup into Athena. The chapter was saved and retrieval indexed one document, but no world-model proposal bundle was created. Opening Athena overview afterwards showed `未导入 world-model` and a CTA to import Setup.

Impact: A creator can start writing chapters while assuming Athena is tracking world changes, but Athena has not yet been initialized. The automatic chapter analysis is silently ineffective from the user's perspective.

Evidence: After chapter 1 generation, database showed chapter word count `4157`, retrieval documents `1`, and proposal bundles `0`; Athena overview then showed `未导入 world-model`.

Potential improvement: Before chapter generation, Hermes or the production overview should recommend/import Athena setup when world-model tracking is expected, or chapter analysis should surface a warning when it skips because the world model is not initialized.

Root cause: `analyze_chapter_to_world_proposals()` already returned a structured `skipped` result when no project profile existed, but chapter generation discarded that result, so Hermes only showed a successful chapter-generation message.

Fix applied: Chapter generation now carries the Athena analysis result into the background action result. When the skip reason is `missing_world_model_profile`, the Hermes completion message explicitly says `Athena 世界模型尚未导入，已跳过本章世界事实分析`. Added backend regression coverage for both the action result data and the user-facing completion message.

### DFD-006: Athena proposal risk copy is internally inconsistent

Severity: Low

Status: fixed in working tree, browser recheck passed

Observation: After importing Setup and analyzing chapter 1, Athena created one proposal bundle. The bundle description said `自动抽取 5 条低风险世界事实候选`, but the impact snapshot section displayed `高风险变更`.

Impact: Reviewers may not know whether these generated facts are routine low-risk extractions or risky world-model changes requiring deeper review.

Evidence: Athena `待审变更` view for chapter 1 proposal bundle.

Potential improvement: Align bundle summary risk and impact snapshot risk labeling, or explain why a low-risk extraction bundle has a high-risk aggregate impact.

Root cause: The frontend impact badge inferred `高风险变更` from candidate volume as well as existing-truth overlap, so a routine extraction batch could be labeled as high risk without explaining why.

Fix applied: Replaced the generic high-risk badge with cause-specific labels: `批量候选` for large candidate batches and `覆盖既有真相` when a proposal touches confirmed truth. Added component regression tests for both cases.

Browser recheck: Passed. In the proposal view, the impact snapshot now shows `覆盖既有真相` and no longer shows `高风险变更`.

### DFD-007: Calliope manuscript view shows no chapters despite generated chapters

Severity: High

Status: fixed in working tree, browser recheck passed

Observation: After generating chapters 1-5, the database contained five `ChapterContent` rows and the chapter-generation API had returned success. Opening `/projects/{project_id}/manuscript` showed the Calliope sidebar text `暂无章节` and the main area `请选择章节`.

Impact: This blocks users from reading/editing generated manuscript content through the primary manuscript UI, even though generation succeeded.

Evidence: Database showed chapters 1-5 with word counts; Calliope DOM snapshot showed no chapter list.

Root cause: The frontend project store marked `project:{id}:chapters` as fresh after workspace bootstrap, even when the bootstrap chapter list was empty. `loadChapters()` then returned early while the cache was still fresh, so Manuscript could keep rendering the old empty list after chapters were generated.

Fix applied: Added a `force` option to `loadChapters()`. `refreshTargets(['content'])` now forces a chapter-list refresh after generation tasks, and `ManuscriptView` forces a refresh when entering the manuscript route. Added regression tests for both stale-cache paths.

Browser recheck: Passed. Reloaded Calliope and confirmed the sidebar lists chapters 1-5 with word counts, and chapter 1 opens in the manuscript editor.

### DFD-008: Setup import creates phrase-like location/faction nodes

Severity: Medium

Status: fixed in working tree, regression test added

Observation: Athena `设定库` contains imported nodes such as `loc.海雾时常笼罩灯塔`, `loc.澜城分为旧城`, `loc.以一座废弃的百年灯塔`, and `faction.政府设立记忆管理局`. These read like extracted prose fragments rather than stable world entities.

Impact: The world model becomes harder to search, review, and reason about. Later chapter facts can attach to awkward subject refs, making truth review and retrieval less trustworthy.

Evidence: Athena `设定库` after importing Setup and generating 20 chapters.

Potential improvement: Tighten Setup import entity normalization, prefer noun-phrase canonical IDs, and add review/merge affordances for imported nodes before they become the project profile baseline.

Root cause: The unquoted Setup term extractor matched the longest Chinese fragment ending with location/faction suffixes, so prose clauses like `海雾时常笼罩灯塔` and `政府设立记忆管理局` survived as entity names.

Fix applied: Setup term extraction now splits on additional world-building verbs such as `分为`, `设立`, and `笼罩`, then strips leading descriptive phrases like `以一座废弃的百年`. Added a regression test expecting stable nouns such as `澜城`, `旧城`, `新港`, `灯塔`, `记忆管理局`, and `守夜人联盟`.

### DFD-009: Narrative timeline defaults to empty despite available 20-chapter plan

Severity: Low

Status: fixed in working tree, browser recheck passed

Observation: Athena `叙事脉络` opens on `时间线`, which displays `暂无时间线数据` even though the `章节` tab has a complete 20-chapter plan, 4 storylines, and 10 foreshadowing items.

Impact: Users may think Athena failed to understand the story after generation. The useful narrative data is one tab away, but the default empty state undersells the module.

Evidence: Athena `叙事脉络` after generating all 20 chapters.

Potential improvement: Use the chapter plan as a fallback timeline source, change the default tab to `章节` when no timeline facts exist, or explain that timeline requires approved world facts.

Root cause: The timeline route loaded only timeline facts and rendered a generic empty state, so it had no way to acknowledge the already generated chapter plan, storylines, or foreshadowing data.

Fix applied: Timeline route loading now also ensures the evolution plan is available. `TimelineView` accepts a fallback summary and shows the available chapter/storyline/foreshadowing counts when timeline facts are empty. Added component and route-loader regression coverage.

Browser recheck: Passed. Opened Athena `叙事脉络 -> 时间线` and confirmed it shows `已生成 20 章规划、4 条故事线、10 条伏笔`.

### DFD-010: Truth projection renders raw JSON fact values

Severity: Medium

Status: fixed in working tree, browser recheck passed

Observation: Athena `真相认知 -> 真相投影` displays an approved `presence_count` fact as a raw JSON object string, including fields like `source`, `matched_names`, `evidence_span`, and `quality`.

Impact: This is technically complete but not creator-readable. Users need a concise fact such as `陆辞在第1章出现 51 次`, with expandable metadata for evidence and quality.

Evidence: Athena truth projection after approving one chapter-1 proposal item.

Potential improvement: Add display formatters for structured fact values by predicate, with raw JSON hidden behind a details/debug affordance.

Root cause: Projection rendering treated every structured fact value with the generic JSON formatter, so predicate-specific creator-facing values were never translated into readable text.

Fix applied: Added a predicate-aware display formatter for `presence_count`, preserving the generic formatter for unknown structured values. Added a component regression test that expects `第1章出现 51 次` and rejects raw metadata such as `matched_names`.

Browser recheck: Passed. Reloaded Athena `真相认知` and confirmed the projection shows `第1章出现 51 次` without raw JSON metadata.

### DFD-011: Consistency check has no success feedback when no issues are found

Severity: Low

Status: fixed in working tree, browser recheck passed

Observation: In Athena `待审变更 -> 一致性`, clicking `检查最新章节` for chapter 20 produced no visible change; the UI still displayed `暂无一致性检查结果`. Direct API verification returned `issues: []`.

Impact: Users cannot tell whether the check ran successfully, failed silently, or did nothing. This weakens trust in the consistency workflow.

Evidence: Athena consistency view after full 20-chapter generation and a latest-chapter check.

Potential improvement: Show a success state such as `最近检查：第20章，未发现一致性问题`, with timestamp and depth.

Root cause: The frontend only rendered the issue list itself. A successful empty result and an unchecked empty state were both represented by `issues.length === 0`.

Fix applied: Athena store now records the latest consistency-check result, including chapter index and issue count. `ConsistencyList` accepts the last checked chapter and renders a clean success state when the latest check returns no issues. Added store and component regression tests.

Browser recheck: Passed. Clicked `检查最新章节` on chapter 20 and confirmed the UI shows `最近检查：第20章，未发现一致性问题`.

### DFD-012: Athena Chat is unaware of the generated 20-chapter manuscript

Severity: High

Status: fixed in working tree, browser/API recheck passed

Observation: After all 20 chapters were generated and retrieval showed 20 chapter documents, Athena Chat was asked: `请根据当前世界模型和20章正文，指出陆辞、苏晚晴、陈默三人的核心秘密是否已经在结尾闭环。` It replied that the current project only has chapter 1 and that it cannot judge the 20-chapter ending.

Impact: This is a major trust break for the Athena assistant. Users expect Athena Chat to reason over the same manuscript and retrieval corpus visible in Athena, especially after full generation.

Evidence: Athena Chat panel after generating 20 chapters; retrieval diagnostics at the same time showed 20 chapter documents and 130 chunks.

Partial fix applied: Chapter generation now advances `project.current_phase` to `content`, and this dogfood project's stored phase was corrected from `outline` to `content`. Retest improved the phase signal, but Athena Chat still said the world model only records chapter 1 and cannot see actual chapter count/word count, so DFD-012 remains open.

Potential improvement: Feed Athena Chat the latest project chapter summary/retrieval diagnostics, allow it to retrieve from chapter text, and avoid stale statements like `仅有第1章` when the chapter API has 20 generated chapters.

Root cause: Athena Chat injected only the world-model context into the prompt. Confirmed world facts contained a chapter-1 `presence_count`, while generated manuscript progress and chapter summaries were absent from the model-visible `world_context`. The prompt also told Athena to say `当前世界模型中没有这个信息` when world-model facts were missing, so older wrong chat history reinforced the false `仅有第1章` answer.

Fix applied: Added an Athena manuscript summary context block and injected it into the model-visible world context. The block includes generated chapter count, target chapter count, current total words, chapter range, chapter list, and recent chapter excerpts. Updated the Athena prompt to treat `正文进度` as the authoritative source for chapter count, total words, and recent chapters. Added a backend regression test that asserts the 20-chapter/word-count manuscript context reaches the Athena Chat model input.

API recheck: Passed. Asked Athena Chat `这个项目现在已经生成了多少章正文？当前总字数是多少？`; it answered `20章正文` and `78,127字`.

Browser recheck: Passed. Reopened Athena Chat and confirmed the latest answer says it can see chapter range `第1章至第20章` and total words `78,127字`. The old incorrect answers remain in chat history as historical messages, but current responses no longer repeat the `仅有第1章` claim.

Residual improvement: The current fix gives Athena reliable manuscript progress plus recent chapter excerpts. A deeper follow-up should add query-aware retrieval snippets from the full chapter corpus for thematic questions such as long-range secret/arc closure, so Athena can cite more than the latest excerpts.

### DFD-013: Analyze-latest-chapter action has no feedback when the chapter was already analyzed

Severity: Low

Status: fixed in working tree, browser recheck passed

Observation: Clicking Athena sidebar `分析最新章节` after chapter 20 had already been auto-analyzed did not create a duplicate bundle, which is good. However, the UI did not show any status, toast, or explanation.

Impact: Users may think the button failed or did nothing. The non-duplication behavior is correct but invisible.

Evidence: Proposal total stayed at 20, and chapter 20 still had one proposal bundle after clicking `分析最新章节`.

Potential improvement: Show a completion message such as `第20章已有待审提案，未重复创建`, or navigate/highlight the existing bundle.

Root cause: The API returned enough information to distinguish created proposals from duplicate skips, but the Athena store discarded the result and the view had no status surface for the action.

Fix applied: Athena store now keeps the latest analyze-chapter result. `AthenaView` renders a small action notice for created proposals, duplicate skips, and no-new-fact completions. Added a store regression test for duplicate-skip results.

Browser recheck: Passed. Clicked `分析最新章节` after chapter 20 had already been analyzed and confirmed the UI shows `第20章已有待审提案，未重复创建`.

## Later Verification Targets

- Confirm outline generation produced exactly 20 chapters.
- Generate chapters 1-20 and verify manuscript navigation, word counts, and chapter retrieval.
- Use Athena overview, truth/projection, review/proposals, catalog/retrieval, and consistency workflows against generated chapters.
- Inspect browser console errors and backend logs during long generation.
- Export or otherwise verify the final 20-chapter manuscript artifact if the app supports it.
