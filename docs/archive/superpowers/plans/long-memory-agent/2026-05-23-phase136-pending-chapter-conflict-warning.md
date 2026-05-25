# Phase136 Pending Chapter Conflict Warning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show explicit chapter target conflicts as a dedicated warning inside the pending action card before the user confirms execution.

**Architecture:** Keep backend conflict data unchanged. The frontend `ActionCard` reads `action.params.chapter_target_conflict`, renders a separate warning band, and removes the backend warning sentence from the normal action copy to avoid duplicate text.

**Tech Stack:** Vue 3, Vitest, Vue Test Utils, Vite build.

---

## Scope

This phase improves the visibility of the explicit chapter conflict warning added in Phase135. It does not change backend target selection, conflict detection, or action confirmation behavior.

## Files

- Modify: `frontend/src/components/chat/ActionCard.vue`
- Modify: `frontend/src/components/chat/ChatMessage.test.ts`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase136-pending-chapter-conflict-warning.md`

## Validation Level

T1:

- Targeted component test for conflict warning rendering.
- Frontend component test file regression.
- Frontend build to verify TypeScript and Vite.

Commands:

- Targeted RED/GREEN:
  - `npm run test:unit -- src/components/chat/ChatMessage.test.ts -t "renders pending chapter conflict as a warning before confirmation"`
- Regression subset:
  - `npm run test:unit -- src/components/chat/ChatMessage.test.ts`
- Build:
  - `npm run build`
- Hygiene:
  - `git diff --check`
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`

## Task 1: Failing Test

- [ ] **Step 1: Add component test**

Add this test to `frontend/src/components/chat/ChatMessage.test.ts`:

```ts
it('renders pending chapter conflict as a warning before confirmation', () => {
  const wrapper = mount(ChatMessage, {
    props: {
      msg: {
        role: 'assistant',
        message_type: 'plain',
        content: '准备生成章节。',
        pending_action: {
          id: 'pending-1',
          type: 'preview_chapter',
          description: '我可以生成第2章正文，完成后会进入 Calliope 和正文进度。 注意：第2章已有待确认或运行中的生成任务，请确认是否仍要继续。',
          params: {
            chapter_index: 2,
            chapter_target_conflict: {
              status: 'reserved',
              chapter_index: 2,
              reason: 'pending_or_running_generation',
            },
          },
        },
      },
      isLatest: true,
      loading: false,
    },
  })

  const warning = wrapper.get('[data-testid="chapter-target-conflict"]')
  expect(warning.text()).toContain('第2章已有待确认或运行中的生成任务')
  expect(warning.text()).toContain('确认前请检查是否要继续覆盖同一章节')
  expect(wrapper.get('.action-card__copy').text()).not.toContain('注意：')
})
```

- [ ] **Step 2: Run RED**

Expected: test fails because no warning element exists.

## Task 2: Minimal Implementation

- [ ] **Step 1: Add computed conflict helpers**

In `ActionCard.vue`, add:

```ts
const chapterTargetConflict = computed(() => {
  const conflict = props.action?.params?.chapter_target_conflict
  if (!conflict || typeof conflict !== 'object') return null
  if (conflict.status !== 'reserved') return null
  const chapterIndex = Number(conflict.chapter_index || props.action?.params?.chapter_index)
  if (!Number.isInteger(chapterIndex) || chapterIndex <= 0) return null
  return { chapterIndex }
})

const actionCopy = computed(() => {
  const copy = String(props.action?.description || '')
  if (!chapterTargetConflict.value) return copy
  return copy.replace(/\\s*注意：第\\d+章已有待确认或运行中的生成任务，请确认是否仍要继续。\\s*$/, '').trim()
})
```

- [ ] **Step 2: Render warning**

Replace `{{ action.description }}` with `{{ actionCopy }}` and add:

```vue
<div
  v-if="chapterTargetConflict"
  class="action-card__warning"
  data-testid="chapter-target-conflict"
>
  <strong>章节目标冲突</strong>
  <span>第{{ chapterTargetConflict.chapterIndex }}章已有待确认或运行中的生成任务，确认前请检查是否要继续覆盖同一章节。</span>
</div>
```

- [ ] **Step 3: Add scoped styles**

Use an inline warning band inside the existing action card:

```css
.action-card__warning {
  display: grid;
  gap: 0.2rem;
  margin-bottom: 0.8rem;
  border-left: 3px solid var(--color-warning, #b7791f);
  background: rgba(255, 247, 214, 0.78);
  color: var(--color-text-primary);
  padding: 0.65rem 0.75rem;
  border-radius: 0.55rem;
  font-size: 0.82rem;
  line-height: 1.45;
}

.action-card__warning strong {
  font-size: 0.78rem;
}
```

## Task 3: Verify, Document, Commit

- [ ] Run targeted test and confirm it passes.
- [ ] Run `ChatMessage.test.ts` regression.
- [ ] Run frontend build.
- [ ] Run hygiene checks.
- [ ] Write phase report with RED/GREEN evidence.
- [ ] Commit and push:

```powershell
git add frontend/src/components/chat/ActionCard.vue frontend/src/components/chat/ChatMessage.test.ts docs/superpowers/plans/long-memory-agent/2026-05-23-phase136-pending-chapter-conflict-warning.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase136-pending-chapter-conflict-warning.md
git commit -m "feat: show pending chapter conflict warning"
git push origin main
```
