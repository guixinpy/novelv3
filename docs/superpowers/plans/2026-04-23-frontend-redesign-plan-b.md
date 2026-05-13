# Frontend Redesign Plan B: Page Views

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace all page views with new implementations using the minimalist design system and layout shell from Plan A.

**Architecture:** Each view is rebuilt from scratch using base components and design tokens. Chat functionality is preserved by extracting and restyling existing logic. Athena uses master-detail pattern with sub-nav driven navigation. All old view-specific components are superseded but not yet deleted (Plan C).

**Tech Stack:** Vue 3, TypeScript, Pinia, CSS Custom Properties

---

### Task 1: Shared Components

**Files:**
- Create: `frontend/src/components/shared/PhaseProgress.vue`
- Create: `frontend/src/components/shared/ChapterList.vue`
- Create: `frontend/src/components/shared/ExportModal.vue`
- Create: `frontend/src/components/shared/VersionsModal.vue`

- [ ] **Step 1: Create `frontend/src/components/shared/PhaseProgress.vue`**

Create directory `frontend/src/components/shared/` then create the file:

```vue
<script setup lang="ts">
export interface PhaseItem {
  key: string
  label: string
  status: 'done' | 'current' | 'pending'
}

defineProps<{
  phases: PhaseItem[]
}>()
</script>

<template>
  <div class="phase-progress">
    <div
      v-for="(phase, index) in phases"
      :key="phase.key"
      class="phase-progress__item"
    >
      <div class="phase-progress__indicator">
        <span
          class="phase-progress__dot"
          :class="`phase-progress__dot--${phase.status}`"
        >
          <svg
            v-if="phase.status === 'done'"
            width="10"
            height="10"
            viewBox="0 0 10 10"
            fill="none"
          >
            <path
              d="M2 5L4.5 7.5L8 3"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
        </span>
        <div
          v-if="index < phases.length - 1"
          class="phase-progress__line"
          :class="{
            'phase-progress__line--done': phase.status === 'done',
          }"
        />
      </div>
      <span
        class="phase-progress__label"
        :class="`phase-progress__label--${phase.status}`"
      >
        {{ phase.label }}
      </span>
      <span v-if="phase.status === 'current'" class="phase-progress__arrow">→</span>
    </div>
  </div>
</template>

<style scoped>
.phase-progress {
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: var(--space-3);
}

.phase-progress__item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 32px;
}

.phase-progress__indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 16px;
  flex-shrink: 0;
}

.phase-progress__dot {
  width: 12px;
  height: 12px;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.phase-progress__dot--done {
  background: var(--color-success);
  color: var(--color-text-inverse);
}

.phase-progress__dot--current {
  background: var(--color-brand);
  box-shadow: 0 0 0 3px var(--color-brand-subtle);
  animation: pulse-dot 2s ease-in-out infinite;
}

.phase-progress__dot--pending {
  background: transparent;
  border: 2px solid var(--color-border-strong);
}

.phase-progress__line {
  width: 2px;
  height: 16px;
  background: var(--color-border);
}

.phase-progress__line--done {
  background: var(--color-success);
}

.phase-progress__label {
  font-size: var(--text-sm);
  flex: 1;
}

.phase-progress__label--done {
  color: var(--color-text-secondary);
}

.phase-progress__label--current {
  color: var(--color-brand);
  font-weight: var(--font-medium);
}

.phase-progress__label--pending {
  color: var(--color-text-tertiary);
}

.phase-progress__arrow {
  color: var(--color-brand);
  font-size: var(--text-sm);
}

@keyframes pulse-dot {
  0%, 100% { box-shadow: 0 0 0 3px var(--color-brand-subtle); }
  50% { box-shadow: 0 0 0 5px var(--color-brand-subtle); }
}
</style>
```

- [ ] **Step 2: Create `frontend/src/components/shared/ChapterList.vue`**

```vue
<script setup lang="ts">
export interface ChapterItem {
  index: number
  wordCount: number
}

defineProps<{
  chapters: ChapterItem[]
  activeIndex: number | null
}>()

const emit = defineEmits<{
  select: [index: number]
}>()
</script>

<template>
  <div class="chapter-list">
    <button
      v-for="ch in chapters"
      :key="ch.index"
      class="chapter-list__item"
      :class="{ 'chapter-list__item--active': activeIndex === ch.index }"
      @click="emit('select', ch.index)"
    >
      <span class="chapter-list__name">第{{ ch.index }}章</span>
      <span class="chapter-list__count">{{ ch.wordCount.toLocaleString() }}字</span>
    </button>
    <div v-if="chapters.length === 0" class="chapter-list__empty">
      暂无章节
    </div>
  </div>
</template>

<style scoped>
.chapter-list {
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.chapter-list__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  transition: background var(--transition-fast);
  border: none;
  background: transparent;
  text-align: left;
  width: 100%;
  cursor: pointer;
}

.chapter-list__item:hover {
  background: var(--color-bg-secondary);
}

.chapter-list__item--active {
  background: var(--color-brand-light);
  color: var(--color-brand);
  font-weight: var(--font-medium);
}

.chapter-list__item--active:hover {
  background: var(--color-brand-light);
}

.chapter-list__count {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.chapter-list__item--active .chapter-list__count {
  color: var(--color-brand);
  opacity: 0.7;
}

.chapter-list__empty {
  padding: var(--space-4) var(--space-3);
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
  text-align: center;
}
</style>
```

- [ ] **Step 3: Create `frontend/src/components/shared/ExportModal.vue`**

```vue
<script setup lang="ts">
import BaseModal from '../base/BaseModal.vue'
import BaseButton from '../base/BaseButton.vue'

defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  close: []
  export: [format: string]
}>()
</script>

<template>
  <BaseModal :open="open" title="导出" width="360px" @close="emit('close')">
    <div class="export-modal__actions">
      <BaseButton variant="secondary" size="md" @click="emit('export', 'markdown')">
        导出 Markdown
      </BaseButton>
      <BaseButton variant="secondary" size="md" @click="emit('export', 'txt')">
        导出 TXT
      </BaseButton>
    </div>
  </BaseModal>
</template>

<style scoped>
.export-modal__actions {
  display: flex;
  gap: var(--space-3);
}
</style>
```

- [ ] **Step 4: Create `frontend/src/components/shared/VersionsModal.vue`**

```vue
<script setup lang="ts">
import BaseModal from '../base/BaseModal.vue'
import BaseTable from '../base/BaseTable.vue'
import BaseButton from '../base/BaseButton.vue'
import BaseBadge from '../base/BaseBadge.vue'
import type { BaseTableColumn } from '../base/BaseTable.vue'

defineProps<{
  open: boolean
  versions: any[]
  projectId: string
}>()

const emit = defineEmits<{
  close: []
  filter: [type: string]
  rollback: [versionId: string]
  'delete-version': [versionId: string]
}>()

const columns: BaseTableColumn[] = [
  { key: 'node_type', label: '类型', width: '80px' },
  { key: 'label', label: '标签' },
  { key: 'created_at', label: '创建时间', width: '160px' },
  { key: 'actions', label: '操作', width: '120px', align: 'right' },
]

const typeLabels: Record<string, string> = {
  setup: '设定',
  storyline: '故事线',
  outline: '大纲',
  chapter: '章节',
}

const filterOptions = [
  { value: '', label: '全部' },
  { value: 'setup', label: '设定' },
  { value: 'storyline', label: '故事线' },
  { value: 'outline', label: '大纲' },
  { value: 'chapter', label: '章节' },
]
</script>

<template>
  <BaseModal :open="open" title="版本历史" width="640px" @close="emit('close')">
    <div class="versions-modal__filters">
      <BaseButton
        v-for="opt in filterOptions"
        :key="opt.value"
        variant="ghost"
        size="sm"
        @click="emit('filter', opt.value)"
      >
        {{ opt.label }}
      </BaseButton>
    </div>
    <BaseTable :columns="columns" :data="versions" row-key="id" empty-text="暂无版本记录">
      <template #cell-node_type="{ value }">
        <BaseBadge variant="neutral" size="sm">
          {{ typeLabels[String(value)] || value }}
        </BaseBadge>
      </template>
      <template #cell-actions="{ row }">
        <div class="versions-modal__row-actions">
          <BaseButton variant="ghost" size="sm" @click.stop="emit('rollback', String(row.id))">
            回滚
          </BaseButton>
          <BaseButton variant="ghost" size="sm" @click.stop="emit('delete-version', String(row.id))">
            删除
          </BaseButton>
        </div>
      </template>
    </BaseTable>
  </BaseModal>
</template>

<style scoped>
.versions-modal__filters {
  display: flex;
  gap: var(--space-1);
  margin-bottom: var(--space-4);
  flex-wrap: wrap;
}

.versions-modal__row-actions {
  display: flex;
  gap: var(--space-1);
  justify-content: flex-end;
}
</style>
```

- [ ] **Step 5: Commit**

```bash
cd /home/guixin/project_workspace/novelv3 && git add frontend/src/components/shared/ && git commit -m "feat: add shared components (PhaseProgress, ChapterList, ExportModal, VersionsModal)"
```

---

### Task 2: Chat Components

**Files:**
- Create: `frontend/src/components/chat/ChatMessage.vue`
- Create: `frontend/src/components/chat/ChatInput.vue`
- Create: `frontend/src/components/chat/ChatMessageList.vue`
- Create: `frontend/src/components/chat/CommandMenu.vue`

- [ ] **Step 1: Create `frontend/src/components/chat/ChatMessage.vue`**

Create directory `frontend/src/components/chat/` then create the file. This restyled version preserves all existing ChatMessage logic (action cards, summary cards, action results, decide emit) but uses design tokens:

```vue
<script setup lang="ts">
import { computed } from 'vue'
import ActionCard from '../ActionCard.vue'
import ChatSummaryCard from '../ChatSummaryCard.vue'

const props = defineProps<{
  msg: any
  isLatest: boolean
  loading: boolean
}>()

const emit = defineEmits<{
  decide: [decision: string, comment?: string]
}>()

const roleName = computed(() => {
  if (props.msg.role === 'user') return '我'
  if (props.msg.role === 'system') return '系统'
  return '墨舟'
})

const TYPE_LABELS: Record<string, string> = {
  generate_setup: '生成设定',
  generate_storyline: '生成故事线',
  generate_outline: '生成大纲',
  preview_setup: '生成设定',
  preview_storyline: '生成故事线',
  preview_outline: '生成大纲',
}

const resultText = computed(() => {
  const r = props.msg.action_result
  if (!r) return ''
  const label = TYPE_LABELS[r.type] || r.type
  if (r.status === 'success') return `✓ ${label}执行成功`
  if (r.status === 'cancelled') return `✗ 操作已取消`
  if (r.status === 'generating') return `⏳ ${label}生成中...`
  if (r.status === 'failed') return `✗ ${label}失败`
  return `${label}: ${r.status}`
})

const resultVariant = computed(() => {
  const status = props.msg.action_result?.status
  if (status === 'success') return 'success'
  if (status === 'failed') return 'error'
  return 'neutral'
})

const summaryTitle = computed(() => {
  const title = props.msg.meta?.title
  return typeof title === 'string' && title.trim() ? title : '会话摘要'
})

const summaryCompactedCount = computed(() => {
  const compactedCount = props.msg.meta?.compacted_count
  return typeof compactedCount === 'number' ? compactedCount : 0
})

function onDecide(decision: string, comment?: string) {
  emit('decide', decision, comment)
}
</script>

<template>
  <div
    class="chat-msg"
    :class="msg.role === 'user' ? 'chat-msg--right' : 'chat-msg--left'"
  >
    <ChatSummaryCard
      v-if="msg.message_type === 'summary'"
      :content="msg.content"
      :title="summaryTitle"
      :compacted-count="summaryCompactedCount"
    />
    <div
      v-else
      class="chat-msg__bubble"
      :class="`chat-msg__bubble--${msg.role}`"
    >
      <div class="chat-msg__role">{{ roleName }}</div>
      <div class="chat-msg__content">{{ msg.content }}</div>
      <ActionCard
        v-if="msg.pending_action && isLatest"
        :action="msg.pending_action"
        :disabled="loading"
        @decide="onDecide"
      />
      <div
        v-if="msg.action_result"
        class="chat-msg__result"
        :class="`chat-msg__result--${resultVariant}`"
      >
        {{ resultText }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-msg {
  display: flex;
}

.chat-msg--left {
  justify-content: flex-start;
}

.chat-msg--right {
  justify-content: flex-end;
}

.chat-msg__bubble {
  max-width: 85%;
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
}

.chat-msg__bubble--assistant {
  background: var(--color-bg-white);
  border-left: 3px solid var(--color-brand);
}

.chat-msg__bubble--system {
  background: var(--color-bg-secondary);
  border-left: 3px solid var(--color-border-strong);
}

.chat-msg__bubble--user {
  background: var(--color-brand-light);
  max-width: 80%;
}

.chat-msg__role {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: var(--space-1);
}

.chat-msg__content {
  white-space: pre-wrap;
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
  color: var(--color-text-primary);
}

.chat-msg__result {
  margin-top: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
}

.chat-msg__result--success {
  background: var(--color-success-light);
  color: var(--color-success);
}

.chat-msg__result--error {
  background: var(--color-error-light);
  color: var(--color-error);
}

.chat-msg__result--neutral {
  background: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
}
</style>
```

- [ ] **Step 2: Create `frontend/src/components/chat/ChatInput.vue`**

Extracts the input bar logic from `ChatWorkspace.vue`. Preserves slash command detection, IME handling, keyboard navigation, and submit gating:

```vue
<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import BaseButton from '../base/BaseButton.vue'
import CommandMenu from './CommandMenu.vue'
import {
  filterChatCommands,
  parseSlashCommand,
  type ChatCommandDefinition,
} from '../../components/workspace/chatCommands'

const props = defineProps<{
  loading: boolean
  disabled: boolean
  hasPendingAction: boolean
}>()

const emit = defineEmits<{
  send: [text: string]
}>()

const input = ref('')
const inputEl = ref<HTMLInputElement | null>(null)
const activeCommandIndex = ref(0)
const commandMenuDismissed = ref(false)

const commandCandidates = computed(() => {
  const candidates = filterChatCommands(input.value)
  if (!props.hasPendingAction) return candidates
  return candidates.filter((c) => c.name === 'clear')
})

const showCommandMenu = computed(() => {
  if (commandMenuDismissed.value) return false
  if (!input.value.startsWith('/')) return false
  return commandCandidates.value.length > 0
})

const canSubmit = computed(() => {
  const text = input.value.trim()
  if (!text || props.loading) return false
  if (!props.hasPendingAction) return true
  const parsed = parseSlashCommand(text)
  return parsed.kind === 'command' && parsed.name === 'clear'
})

function submit() {
  const text = input.value.trim()
  if (!text || !canSubmit.value) return
  emit('send', text)
  input.value = ''
  activeCommandIndex.value = 0
  commandMenuDismissed.value = false
}

function pickCommand(command: ChatCommandDefinition) {
  input.value = `/${command.name} `
  activeCommandIndex.value = 0
  commandMenuDismissed.value = true
  nextTick(() => inputEl.value?.focus())
}

function isImeComposing(event: KeyboardEvent) {
  return event.isComposing || event.keyCode === 229
}

function onInputKeydown(event: KeyboardEvent) {
  if (isImeComposing(event)) return

  if (event.key === 'Escape' && showCommandMenu.value) {
    commandMenuDismissed.value = true
    return
  }

  if (!showCommandMenu.value) {
    if (event.key === 'Enter') {
      event.preventDefault()
      submit()
    }
    return
  }

  if (event.key === 'ArrowDown') {
    event.preventDefault()
    activeCommandIndex.value = (activeCommandIndex.value + 1) % commandCandidates.value.length
    return
  }

  if (event.key === 'ArrowUp') {
    event.preventDefault()
    const total = commandCandidates.value.length
    activeCommandIndex.value = (activeCommandIndex.value - 1 + total) % total
    return
  }

  if (event.key === 'Enter') {
    event.preventDefault()
    if (props.hasPendingAction && canSubmit.value) {
      submit()
      return
    }
    const command = commandCandidates.value[activeCommandIndex.value]
    if (command) pickCommand(command)
  }
}

watch(input, () => { commandMenuDismissed.value = false })
watch(commandCandidates, (next) => {
  if (!next.length || activeCommandIndex.value >= next.length) {
    activeCommandIndex.value = 0
  }
})
</script>

<template>
  <footer class="chat-input">
    <CommandMenu
      v-if="showCommandMenu"
      :commands="commandCandidates"
      :active-index="activeCommandIndex"
      class="chat-input__menu"
      @pick="pickCommand"
    />
    <div class="chat-input__bar">
      <input
        ref="inputEl"
        v-model="input"
        :disabled="loading || disabled"
        class="chat-input__field"
        placeholder="输入消息，或键入 / 查看命令"
        @keydown="onInputKeydown"
      />
      <BaseButton
        variant="primary"
        size="sm"
        :disabled="!canSubmit"
        @click="submit"
      >
        ➤
      </BaseButton>
    </div>
  </footer>
</template>

<style scoped>
.chat-input {
  border-top: 1px solid var(--color-border);
  padding: var(--space-3);
  background: var(--color-bg-white);
  flex-shrink: 0;
}

.chat-input__menu {
  margin-bottom: var(--space-2);
}

.chat-input__bar {
  display: flex;
  gap: var(--space-2);
}

.chat-input__field {
  flex: 1;
  min-width: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  background: var(--color-bg-white);
  outline: none;
  transition: border-color var(--transition-fast);
}

.chat-input__field:focus {
  border-color: var(--color-brand);
  box-shadow: 0 0 0 2px var(--color-brand-subtle);
}

.chat-input__field:disabled {
  background: var(--color-bg-secondary);
  cursor: not-allowed;
}
</style>
```

- [ ] **Step 3: Create `frontend/src/components/chat/ChatMessageList.vue`**

```vue
<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import ChatMessage from './ChatMessage.vue'

const props = defineProps<{
  messages: any[]
  loading: boolean
}>()

const emit = defineEmits<{
  decide: [decision: string, comment?: string]
}>()

const container = ref<HTMLElement | null>(null)

function scrollToBottom() {
  nextTick(() => {
    if (!container.value) return
    container.value.scrollTop = container.value.scrollHeight
  })
}

watch(() => props.messages.length, scrollToBottom)
watch(() => props.loading, scrollToBottom)
</script>

<template>
  <div ref="container" class="chat-message-list">
    <ChatMessage
      v-for="(message, index) in messages"
      :key="`${index}-${message.role}`"
      :msg="message"
      :is-latest="index === messages.length - 1"
      :loading="loading"
      @decide="(d, c) => emit('decide', d, c)"
    />
    <div v-if="loading" class="chat-message-list__loading">
      <span class="chat-message-list__dots">
        <span /><span /><span />
      </span>
    </div>
  </div>
</template>

<style scoped>
.chat-message-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.chat-message-list__loading {
  display: flex;
  justify-content: flex-start;
}

.chat-message-list__dots {
  display: flex;
  gap: 4px;
  padding: var(--space-3) var(--space-4);
  background: var(--color-bg-white);
  border-left: 3px solid var(--color-brand);
  border-radius: var(--radius-md);
}

.chat-message-list__dots span {
  width: 6px;
  height: 6px;
  border-radius: var(--radius-full);
  background: var(--color-text-tertiary);
  animation: dot-pulse 1.5s ease-in-out infinite;
}

.chat-message-list__dots span:nth-child(2) { animation-delay: 0.2s; }
.chat-message-list__dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes dot-pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1; }
}
</style>
```

- [ ] **Step 4: Create `frontend/src/components/chat/CommandMenu.vue`**

Restyled version of `ChatCommandMenu.vue` using design tokens:

```vue
<script setup lang="ts">
import type { ChatCommandDefinition } from '../../components/workspace/chatCommands'

defineProps<{
  commands: ChatCommandDefinition[]
  activeIndex: number
}>()

const emit = defineEmits<{
  pick: [command: ChatCommandDefinition]
}>()
</script>

<template>
  <div class="command-menu" data-testid="command-menu">
    <button
      v-for="(command, index) in commands"
      :key="command.name"
      type="button"
      class="command-menu__item"
      :class="{ 'command-menu__item--active': index === activeIndex }"
      @click="emit('pick', command)"
    >
      <span class="command-menu__main">
        <span class="command-menu__name">{{ command.label }}</span>
        <span class="command-menu__desc">{{ command.description }}</span>
      </span>
      <span class="command-menu__example">{{ command.example }}</span>
    </button>
  </div>
</template>

<style scoped>
.command-menu {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-white);
  box-shadow: var(--shadow-md);
  padding: var(--space-1);
}

.command-menu__item {
  width: 100%;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-3);
  text-align: left;
  padding: var(--space-2) var(--space-3);
  color: var(--color-text-primary);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.command-menu__item:hover,
.command-menu__item--active {
  background: var(--color-bg-secondary);
}

.command-menu__main {
  display: grid;
  gap: 2px;
}

.command-menu__name {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
}

.command-menu__desc {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
}

.command-menu__example {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  white-space: nowrap;
}
</style>
```

- [ ] **Step 5: Commit**

```bash
cd /home/guixin/project_workspace/novelv3 && git add frontend/src/components/chat/ && git commit -m "feat: add chat components (ChatMessage, ChatInput, ChatMessageList, CommandMenu)"
```

---

### Task 3: ProjectListView

**Files:**
- Create: `frontend/src/views/ProjectListView.vue`
- Modify: `frontend/src/router/index.ts`

- [ ] **Step 1: Create `frontend/src/views/ProjectListView.vue`**

This replaces `ProjectList.vue`. Uses `BaseTable`, `BaseButton`, `BaseModal`, `BaseInput`, `BaseBadge`, `ConfirmDialog`. Preserves all existing project store interactions (loadProjects, createProject, deleteProject):

```vue
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import BaseButton from '../components/base/BaseButton.vue'
import BaseInput from '../components/base/BaseInput.vue'
import BaseModal from '../components/base/BaseModal.vue'
import BaseBadge from '../components/base/BaseBadge.vue'
import BaseTable from '../components/base/BaseTable.vue'
import ConfirmDialog from '../components/base/ConfirmDialog.vue'
import type { BaseTableColumn } from '../components/base/BaseTable.vue'
import { useProjectStore } from '../stores/project'

const router = useRouter()
const store = useProjectStore()

const showCreateDialog = ref(false)
const creating = ref(false)
const newProject = ref({ name: '', genre: '', targetChapters: '', targetWords: '' })

const deleteTarget = ref<any>(null)
const deleting = ref(false)

const columns: BaseTableColumn[] = [
  { key: 'name', label: '项目名称' },
  { key: 'genre', label: '类型', width: '100px' },
  { key: 'current_word_count', label: '字数', width: '100px', align: 'right' },
  { key: 'status', label: '状态', width: '100px' },
  { key: 'updated_at', label: '最后修改', width: '140px' },
  { key: 'actions', label: '操作', width: '60px', align: 'center' },
]

const projects = computed(() => store.projects)

const statusMap: Record<string, { label: string; variant: 'success' | 'warning' | 'neutral' }> = {
  writing: { label: '写作中', variant: 'success' },
  outline_generated: { label: '大纲完成', variant: 'success' },
  storyline_generated: { label: '故事线完成', variant: 'warning' },
  draft: { label: '草稿', variant: 'neutral' },
}

function getStatusInfo(status: string) {
  return statusMap[status] || { label: '进行中', variant: 'neutral' as const }
}

function formatRelativeTime(dateStr: string) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin}分钟前`
  const diffHr = Math.floor(diffMin / 60)
  if (diffHr < 24) return `${diffHr}小时前`
  const diffDay = Math.floor(diffHr / 24)
  return `${diffDay}天前`
}

onMounted(() => store.loadProjects())

function onRowClick(row: Record<string, unknown>) {
  router.push(`/projects/${row.id}/hermes`)
}

function requestDelete(project: any, event: Event) {
  event.stopPropagation()
  deleteTarget.value = project
}

async function confirmDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await store.deleteProject(deleteTarget.value.id)
  } finally {
    deleting.value = false
    deleteTarget.value = null
  }
}

async function createProject() {
  const name = newProject.value.name.trim()
  if (!name) return
  creating.value = true
  try {
    await store.createProject({
      name,
      genre: newProject.value.genre.trim() || undefined,
    })
    showCreateDialog.value = false
    newProject.value = { name: '', genre: '', targetChapters: '', targetWords: '' }
  } finally {
    creating.value = false
  }
}
</script>

<template>
  <div class="project-list-view">
    <div class="project-list-view__header">
      <h1 class="project-list-view__title">项目</h1>
      <BaseButton variant="primary" size="sm" @click="showCreateDialog = true">
        新建项目
      </BaseButton>
    </div>

    <div v-if="projects.length === 0" class="project-list-view__empty">
      <p class="project-list-view__empty-text">还没有项目</p>
      <BaseButton variant="primary" size="sm" @click="showCreateDialog = true">
        新建项目
      </BaseButton>
    </div>

    <BaseTable
      v-else
      :columns="columns"
      :data="projects"
      row-key="id"
      clickable
      @row-click="onRowClick"
    >
      <template #cell-name="{ value }">
        <span class="project-list-view__name">{{ value }}</span>
      </template>
      <template #cell-current_word_count="{ value }">
        {{ Number(value || 0).toLocaleString() }}
      </template>
      <template #cell-status="{ value }">
        <BaseBadge :variant="getStatusInfo(String(value)).variant" size="sm">
          {{ getStatusInfo(String(value)).label }}
        </BaseBadge>
      </template>
      <template #cell-updated_at="{ value }">
        {{ formatRelativeTime(String(value || '')) }}
      </template>
      <template #cell-actions="{ row }">
        <button
          class="project-list-view__delete"
          title="删除"
          @click="requestDelete(row, $event)"
        >
          🗑
        </button>
      </template>
    </BaseTable>

    <!-- Create dialog -->
    <BaseModal
      :open="showCreateDialog"
      title="新建项目"
      width="420px"
      @close="showCreateDialog = false"
    >
      <div class="project-list-view__form">
        <BaseInput
          v-model="newProject.name"
          label="项目名称"
          placeholder="输入项目名称"
        />
        <BaseInput
          v-model="newProject.genre"
          label="题材类型"
          placeholder="如：科幻、悬疑、言情"
        />
        <BaseInput
          v-model="newProject.targetChapters"
          label="目标章节数"
          placeholder="如：20"
        />
        <BaseInput
          v-model="newProject.targetWords"
          label="目标字数"
          placeholder="如：200000"
        />
      </div>
      <template #footer>
        <BaseButton variant="ghost" size="sm" @click="showCreateDialog = false">
          取消
        </BaseButton>
        <BaseButton
          variant="primary"
          size="sm"
          :loading="creating"
          :disabled="!newProject.name.trim()"
          @click="createProject"
        >
          创建
        </BaseButton>
      </template>
    </BaseModal>

    <!-- Delete confirm -->
    <ConfirmDialog
      :open="!!deleteTarget"
      :title="`删除「${deleteTarget?.name || ''}」？`"
      message="删除后所有数据将永久丢失，无法恢复。"
      confirm-text="确认删除"
      cancel-text="取消"
      variant="danger"
      @confirm="confirmDelete"
      @cancel="deleteTarget = null"
    />
  </div>
</template>

<style scoped>
.project-list-view {
  max-width: 960px;
  margin: 0 auto;
}

.project-list-view__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-6);
}

.project-list-view__title {
  font-size: var(--text-xl);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.project-list-view__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-12) 0;
  gap: var(--space-4);
}

.project-list-view__empty-text {
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

.project-list-view__name {
  font-weight: var(--font-medium);
}

.project-list-view__delete {
  opacity: 0.5;
  transition: opacity var(--transition-fast);
  font-size: var(--text-sm);
}

.project-list-view__delete:hover {
  opacity: 1;
}

.project-list-view__form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
</style>
```

- [ ] **Step 2: Update router to point `/` to ProjectListView**

In `frontend/src/router/index.ts`, change the import and route:

```typescript
// Replace:
import ProjectList from '../views/ProjectList.vue'
// With:
import ProjectListView from '../views/ProjectListView.vue'

// Replace in routes array:
// component: ProjectList,
// With:
// component: ProjectListView,
```

The full diff for the router file — change only the import and the `/` route component:

```diff
-import ProjectList from '../views/ProjectList.vue'
+import ProjectListView from '../views/ProjectListView.vue'

   {
     path: '/',
-    component: ProjectList,
+    component: ProjectListView,
     meta: { showSidebar: false, workspace: null } satisfies AppRouteMeta,
   },
```

- [ ] **Step 3: Commit**

```bash
cd /home/guixin/project_workspace/novelv3 && git add frontend/src/views/ProjectListView.vue frontend/src/router/index.ts && git commit -m "feat: add ProjectListView with table layout, replace ProjectList route"
```

---

### Task 4: HermesView

**Files:**
- Create: `frontend/src/views/HermesView.vue`
- Modify: `frontend/src/router/index.ts`

This is the most complex task. HermesView replaces ProjectDetail.vue and must preserve ALL chat functionality: hydration tracking, action polling, slash commands, decide flow, panel data loading, export, and version history.

- [ ] **Step 1: Create `frontend/src/views/HermesView.vue`**

This view integrates the new layout shell (sub-nav content via PhaseProgress + ChapterList + action buttons) with the chat interface (ChatMessageList + ChatInput). All business logic from ProjectDetail.vue is carried over:

```vue
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api/client'
import type { ChatResponse, RefreshTarget, ResolveActionResponse, WorkspacePanel } from '../api/types'
import PhaseProgress from '../components/shared/PhaseProgress.vue'
import type { PhaseItem } from '../components/shared/PhaseProgress.vue'
import ChapterList from '../components/shared/ChapterList.vue'
import ExportModal from '../components/shared/ExportModal.vue'
import VersionsModal from '../components/shared/VersionsModal.vue'
import ChatMessageList from '../components/chat/ChatMessageList.vue'
import ChatInput from '../components/chat/ChatInput.vue'
import BaseButton from '../components/base/BaseButton.vue'
import { parseSlashCommand } from '../components/workspace/chatCommands'
import {
  getActionLabel,
  getActionPanel,
  getActionRefreshTargets,
  getPanelRefreshTargets,
  getVersionRefreshTarget,
  getVersionTypeLabel,
  isFinishedActionStatus,
  normalizeActionStatus,
} from '../components/workspace/workspaceMeta'
import {
  beginHydration,
  createHydrationTracker,
  isActiveHydrationSnapshot,
  markHydratedTarget,
  markHydratedTargets,
  type HydrationSnapshot,
} from './projectDetailHydration'
import { useChatStore } from '../stores/chat'
import { useProjectStore } from '../stores/project'
import { useWorkspaceStore } from '../stores/workspace'

type UiAwareResponse =
  | Pick<ChatResponse, 'ui_hint' | 'refresh_targets'>
  | Pick<ResolveActionResponse, 'ui_hint' | 'refresh_targets'>

const route = useRoute()
const project = useProjectStore()
const chat = useChatStore()
const workspace = useWorkspaceStore()
const pid = computed(() => route.params.id as string)
const ready = ref(false)
const hydrationTracker = createHydrationTracker()
const hydratedTargets = hydrationTracker.targets

// Modal state
const showExportModal = ref(false)
const showVersionsModal = ref(false)

// Phase progress
const currentPhase = computed(() => {
  const p = project.currentProject
  if (!p) return 'setup'
  if (p.status === 'writing') return 'writing'
  if (p.status === 'outline_generated') return 'writing'
  if (p.status === 'storyline_generated') return 'outline'
  const phase = String(p.current_phase || '')
  if (phase === 'outline') return 'outline'
  if (phase === 'storyline') return 'storyline'
  return 'setup'
})

const phases = computed<PhaseItem[]>(() => {
  const phase = currentPhase.value
  const phaseOrder = ['setup', 'storyline', 'outline', 'writing']
  const currentIdx = phaseOrder.indexOf(phase)
  return [
    { key: 'setup', label: '设定', status: currentIdx > 0 ? 'done' : currentIdx === 0 ? 'current' : 'pending' },
    { key: 'storyline', label: '故事线', status: currentIdx > 1 ? 'done' : currentIdx === 1 ? 'current' : 'pending' },
    { key: 'outline', label: '大纲', status: currentIdx > 2 ? 'done' : currentIdx === 2 ? 'current' : 'pending' },
    { key: 'writing', label: '正文', status: currentIdx >= 3 ? 'current' : 'pending' },
  ] as PhaseItem[]
})

// Chapters
const chapterItems = computed(() =>
  (project.chapters || []).map((c: any) => ({
    index: c.chapter_index,
    wordCount: c.word_count || 0,
  })),
)

const activeChapterIndex = computed(() => project.chapter?.chapter_index ?? null)

// Action fingerprint watcher (from ProjectDetail.vue)
const latestActionFingerprint = computed(() => {
  const latest = chat.messages[chat.messages.length - 1]?.action_result as
    | { type?: unknown; status?: unknown }
    | undefined
  if (!latest) return ''
  return `${chat.messages.length}:${String(latest.type)}:${String(latest.status)}`
})

onMounted(async () => {
  await initialize(pid.value)
})

watch(pid, (nextPid, prevPid) => {
  if (!nextPid || nextPid === prevPid) return
  void initialize(nextPid)
})

watch(
  () => workspace.panel,
  (panel, previousPanel) => {
    if (!ready.value || panel === previousPanel) return
    void ensurePanelData(panel)
  },
)

watch(latestActionFingerprint, async (fingerprint) => {
  if (!fingerprint) return
  const latest = chat.messages[chat.messages.length - 1]?.action_result as
    | { type?: unknown; status?: unknown }
    | undefined
  const status = normalizeActionStatus(latest?.status)
  const actionType = typeof latest?.type === 'string' ? latest.type : ''
  if (!isFinishedActionStatus(status)) return
  workspace.settleUiAction(status)
  await refreshProjectTargets(getActionRefreshTargets(actionType, status))
})

async function initialize(projectId: string) {
  ready.value = false
  const snapshot = beginHydration(hydrationTracker, projectId)
  project.resetProjectScopedState(projectId)
  workspace.reset()
  await Promise.all([
    chat.init(projectId),
    project.loadProject(projectId),
  ])
  if (!markHydratedTarget(hydrationTracker, snapshot, 'project')) return
  await ensurePanelData(workspace.panel, projectId, false, snapshot)
  if (!isActiveHydrationSnapshot(hydrationTracker, snapshot)) return
  ready.value = true
}

function currentHydrationSnapshot(projectId = pid.value): HydrationSnapshot {
  return { projectId, version: hydrationTracker.version }
}

function shouldIgnoreMissingTarget(target: RefreshTarget, error: unknown) {
  if (target === 'project') return false
  const message = error instanceof Error ? error.message : String(error || '')
  return /not found/i.test(message)
}

async function loadTarget(projectId: string, target: RefreshTarget) {
  try {
    switch (target) {
      case 'project': await project.loadProject(projectId); break
      case 'setup': await project.loadSetup(projectId); break
      case 'storyline': await project.loadStoryline(projectId); break
      case 'outline': await project.loadOutline(projectId); break
      case 'content': await project.loadChapters(projectId); break
      case 'topology': await project.loadTopology(projectId); break
      case 'versions': await project.loadVersions(projectId, project.versionsNodeType); break
      case 'preferences': await project.loadPreferences(projectId); break
    }
  } catch (error) {
    if (shouldIgnoreMissingTarget(target, error)) return
    throw error
  }
}

async function ensurePanelData(
  panel: WorkspacePanel,
  projectId = pid.value,
  force = false,
  snapshot = currentHydrationSnapshot(projectId),
) {
  for (const target of getPanelRefreshTargets(panel)) {
    if (!isActiveHydrationSnapshot(hydrationTracker, snapshot)) return
    if (!force && hydratedTargets.has(target)) continue
    await loadTarget(projectId, target)
    markHydratedTarget(hydrationTracker, snapshot, target)
  }
}

async function refreshProjectTargets(targets: RefreshTarget[], snapshot = currentHydrationSnapshot()) {
  if (!targets.length) return []
  const successTargets = await project.refreshTargets(pid.value, targets)
  if (!isActiveHydrationSnapshot(hydrationTracker, snapshot)) return []
  markHydratedTargets(hydrationTracker, snapshot, successTargets)
  if (successTargets.includes('content') && project.chapter?.chapter_index != null) {
    await project.loadChapter(pid.value, project.chapter.chapter_index)
  }
  return successTargets
}

async function handleResponse(res: UiAwareResponse | null) {
  if (!res) return
  workspace.applyUiHint(res.ui_hint)
  await refreshProjectTargets(res.refresh_targets)
}

async function onSend(text: string) {
  const parsed = parseSlashCommand(text)
  if (chat.pendingAction && !(parsed.kind === 'command' && parsed.name === 'clear')) return
  workspace.applyUserPanel(workspace.panel, '你发送了一条消息')
  const res = parsed.kind === 'command'
    ? await chat.sendCommand(parsed.name, parsed.args, parsed.rawInput)
    : await chat.sendText(parsed.text)
  await handleResponse(res)
}

async function onDecide(decision: string, comment?: string) {
  const reason = decision === 'confirm'
    ? '你确认执行当前动作'
    : decision === 'cancel'
      ? '你取消了当前动作'
      : `你提交了修改意见${comment?.trim() ? `：${comment.trim()}` : ''}`
  const decisionPanel = workspace.mode === 'locked' && workspace.lockedPanel
    ? workspace.lockedPanel
    : workspace.panel
  workspace.applyUserPanel(decisionPanel, reason)
  const res = await chat.resolveAction(decision as 'confirm' | 'cancel' | 'revise', comment)
  await handleResponse(res)
}

async function loadChapter(index: number) {
  const snapshot = currentHydrationSnapshot()
  workspace.applyUserPanel('content', `你刚点了第 ${index} 章`)
  await project.loadChapter(pid.value, index)
  markHydratedTarget(hydrationTracker, snapshot, 'content')
}

async function onExport(format: string) {
  showExportModal.value = false
  await project.exportProject(pid.value, format)
}

async function onFilterVersions(type: string) {
  const snapshot = currentHydrationSnapshot()
  const reason = type
    ? `你筛选了${getVersionTypeLabel(type)}版本`
    : '你查看全部版本记录'
  workspace.applyUserPanel('versions', reason)
  await project.loadVersions(pid.value, type || undefined)
  markHydratedTarget(hydrationTracker, snapshot, 'versions')
}

async function onRollback(versionId: string) {
  workspace.applyUserPanel('versions', '你发起了版本回滚')
  const version = project.versions.find((item: any) => item.id === versionId)
  await project.rollbackVersion(pid.value, versionId)
  const targets: RefreshTarget[] = ['versions']
  const relatedTarget = getVersionRefreshTarget(version?.node_type)
  if (relatedTarget) targets.push(relatedTarget)
  await refreshProjectTargets(targets)
}

async function onDeleteVersion(versionId: string) {
  workspace.applyUserPanel('versions', '你删除了一条版本记录')
  await api.deleteVersion(pid.value, versionId)
  await refreshProjectTargets(['versions'])
}

function openVersionsModal() {
  showVersionsModal.value = true
  void refreshProjectTargets(['versions'])
}
</script>

<template>
  <div v-if="project.currentProject && ready" class="hermes-view">
    <!-- Sub-nav content: rendered into AppShell SubNav slot via provide/inject or teleport -->
    <Teleport to=".subnav__content">
      <div class="hermes-subnav">
        <div class="hermes-subnav__section-label">创作阶段</div>
        <PhaseProgress :phases="phases" />
        <div class="hermes-subnav__divider" />
        <div class="hermes-subnav__section-label">章节</div>
        <ChapterList
          :chapters="chapterItems"
          :active-index="activeChapterIndex"
          @select="loadChapter"
        />
        <div class="hermes-subnav__divider" />
        <div class="hermes-subnav__actions">
          <BaseButton variant="ghost" size="sm" @click="showExportModal = true">
            📤 导出
          </BaseButton>
          <BaseButton variant="ghost" size="sm" @click="openVersionsModal">
            🕐 版本历史
          </BaseButton>
        </div>
      </div>
    </Teleport>

    <!-- Main content: Chat interface -->
    <div class="hermes-view__chat">
      <ChatMessageList
        :messages="chat.messages"
        :loading="chat.loading"
        @decide="onDecide"
      />
      <ChatInput
        :loading="chat.loading"
        :disabled="false"
        :has-pending-action="!!chat.pendingAction"
        @send="onSend"
      />
    </div>

    <!-- Modals -->
    <ExportModal
      :open="showExportModal"
      @close="showExportModal = false"
      @export="onExport"
    />
    <VersionsModal
      :open="showVersionsModal"
      :versions="project.versions"
      :project-id="pid"
      @close="showVersionsModal = false"
      @filter="onFilterVersions"
      @rollback="onRollback"
      @delete-version="onDeleteVersion"
    />
  </div>
  <div v-else class="hermes-view__loading">
    加载项目工作区...
  </div>
</template>

<style scoped>
.hermes-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  /* Override content-area padding for full-bleed chat */
  margin: calc(-1 * var(--content-padding));
}

.hermes-view__chat {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

.hermes-view__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}

/* Sub-nav styles */
.hermes-subnav {
  display: flex;
  flex-direction: column;
}

.hermes-subnav__section-label {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-tertiary);
  padding: var(--space-3) var(--space-3) var(--space-1);
}

.hermes-subnav__divider {
  height: 1px;
  background: var(--color-border);
  margin: var(--space-2) 0;
}

.hermes-subnav__actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-3);
}
</style>
```

**Important implementation note:** The `<Teleport to=".subnav__content">` targets the SubNav's content div. For this to work, the SubNav component's content wrapper must have the class `subnav__content`. This is already the case in Plan A's SubNav.vue (Step 3 of Task 4). If the class is scoped, add a `data-subnav-content` attribute to SubNav's content div and teleport to `[data-subnav-content]` instead. Alternatively, use provide/inject or a named slot from AppShell — see Step 2 below.

- [ ] **Step 2: Update AppShell.vue to pass sub-nav content via slot**

A cleaner approach than Teleport: modify AppShell to expose a `subnav` slot that the router-view child can fill. Update `frontend/src/components/layout/AppShell.vue`:

Replace the SubNav section in the template:

```diff
      <SubNav
        :collapsed="ui.subNavCollapsed"
        @toggle-collapse="ui.toggleSubNav()"
      >
-       <!-- Plan B will fill sub-nav content per workspace -->
+       <slot name="subnav" />
      </SubNav>
```

Then update `frontend/src/App.vue` to pass the slot through:

```vue
<script setup lang="ts">
import AppShell from './components/layout/AppShell.vue'
</script>

<template>
  <AppShell>
    <template #default>
      <router-view v-slot="{ Component }">
        <component :is="Component" />
      </router-view>
    </template>
  </AppShell>
</template>
```

Since router-view children can't directly fill parent slots, the recommended pattern is to use provide/inject. Add to AppShell:

```typescript
// In AppShell.vue <script setup>
import { provide, shallowRef, type Component as VueComponent } from 'vue'

const subNavContent = shallowRef<VueComponent | null>(null)
provide('subnav-content', subNavContent)
```

And in SubNav template, render the dynamic component:

```vue
<!-- In SubNav.vue, inside .subnav__content -->
<component :is="subNavContent" v-if="subNavContent" />
```

However, the simplest working approach is to keep the Teleport pattern from Step 1. To make it work with scoped CSS, add `data-subnav-content` to SubNav.vue:

In `frontend/src/components/layout/SubNav.vue`, change:
```diff
-   <div class="subnav__content">
+   <div class="subnav__content" data-subnav-content>
```

And in HermesView.vue, change the Teleport target:
```diff
-   <Teleport to=".subnav__content">
+   <Teleport to="[data-subnav-content]">
```

- [ ] **Step 3: Update router to point `/projects/:id/hermes` to HermesView**

In `frontend/src/router/index.ts`:

```diff
+import HermesView from '../views/HermesView.vue'

   {
     path: '/projects/:id/hermes',
-    component: ProjectDetail,
+    component: HermesView,
     meta: { showSidebar: true, workspace: 'hermes' } satisfies AppRouteMeta,
   },
```

Remove the `ProjectDetail` import if no other route uses it.

- [ ] **Step 4: Commit**

```bash
cd /home/guixin/project_workspace/novelv3 && git add frontend/src/views/HermesView.vue frontend/src/router/index.ts frontend/src/components/layout/SubNav.vue && git commit -m "feat: add HermesView with chat interface and sub-nav, replace ProjectDetail route"
```

---

### Task 5: Athena Components

**Files:**
- Create: `frontend/src/components/athena/EntityTable.vue`
- Create: `frontend/src/components/athena/RelationTable.vue`
- Create: `frontend/src/components/athena/RuleList.vue`
- Create: `frontend/src/components/athena/TimelineView.vue`
- Create: `frontend/src/components/athena/ProjectionViewer.vue`
- Create: `frontend/src/components/athena/KnowledgeViewer.vue`
- Create: `frontend/src/components/athena/ProposalList.vue`
- Create: `frontend/src/components/athena/ConsistencyList.vue`
- Create: `frontend/src/components/athena/AthenaChatPanel.vue`

- [ ] **Step 1: Create `frontend/src/components/athena/EntityTable.vue`**

```vue
<script setup lang="ts">
import BaseTable from '../base/BaseTable.vue'
import type { BaseTableColumn } from '../base/BaseTable.vue'

defineProps<{
  entities: any[]
  entityType?: string
}>()

const columns: BaseTableColumn[] = [
  { key: 'name', label: '名称', width: '160px' },
  { key: 'type', label: '类型', width: '100px' },
  { key: 'description', label: '描述' },
]
</script>

<template>
  <BaseTable
    :columns="columns"
    :data="entities"
    row-key="id"
    :empty-text="`暂无${entityType || ''}数据`"
  />
</template>
```

- [ ] **Step 2: Create `frontend/src/components/athena/RelationTable.vue`**

```vue
<script setup lang="ts">
import BaseTable from '../base/BaseTable.vue'
import type { BaseTableColumn } from '../base/BaseTable.vue'

defineProps<{
  relations: any[]
}>()

const columns: BaseTableColumn[] = [
  { key: 'source', label: '源实体', width: '160px' },
  { key: 'arrow', label: '', width: '40px', align: 'center' },
  { key: 'relation_type', label: '关系类型', width: '120px' },
  { key: 'target', label: '目标实体', width: '160px' },
]
</script>

<template>
  <BaseTable :columns="columns" :data="relations" row-key="id" empty-text="暂无关系数据">
    <template #cell-arrow>
      <span class="relation-arrow">→</span>
    </template>
  </BaseTable>
</template>

<style scoped>
.relation-arrow {
  color: var(--color-text-tertiary);
}
</style>
```

- [ ] **Step 3: Create `frontend/src/components/athena/RuleList.vue`**

```vue
<script setup lang="ts">
defineProps<{
  rules: any[]
}>()
</script>

<template>
  <div class="rule-list">
    <div v-if="rules.length === 0" class="rule-list__empty">暂无规则</div>
    <div
      v-for="(rule, index) in rules"
      :key="index"
      class="rule-list__item"
    >
      <span class="rule-list__number">{{ index + 1 }}</span>
      <span class="rule-list__text">{{ typeof rule === 'string' ? rule : rule.content || rule.description || '' }}</span>
    </div>
  </div>
</template>

<style scoped>
.rule-list__item {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--color-border);
  font-size: var(--text-sm);
}

.rule-list__number {
  color: var(--color-text-tertiary);
  font-weight: var(--font-medium);
  min-width: 24px;
}

.rule-list__text {
  color: var(--color-text-primary);
  line-height: var(--leading-normal);
}

.rule-list__empty {
  padding: var(--space-8) 0;
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}
</style>
```

- [ ] **Step 4: Create `frontend/src/components/athena/TimelineView.vue`**

```vue
<script setup lang="ts">
defineProps<{
  events: any[]
  anchors?: any[]
}>()
</script>

<template>
  <div class="timeline-view">
    <div v-if="events.length === 0" class="timeline-view__empty">暂无时间线数据</div>
    <div
      v-for="(event, index) in events"
      :key="index"
      class="timeline-view__item"
    >
      <div class="timeline-view__track">
        <span
          class="timeline-view__dot"
          :class="{ 'timeline-view__dot--current': index === events.length - 1 }"
        />
        <div v-if="index < events.length - 1" class="timeline-view__line" />
      </div>
      <div class="timeline-view__content">
        <div class="timeline-view__desc">{{ event.description || event.event || '' }}</div>
        <div v-if="event.chapter_ref || event.timestamp" class="timeline-view__meta">
          <span v-if="event.chapter_ref">第{{ event.chapter_ref }}章</span>
          <span v-if="event.timestamp">{{ event.timestamp }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.timeline-view {
  padding: var(--space-2) 0;
}

.timeline-view__item {
  display: flex;
  gap: var(--space-4);
  min-height: 48px;
}

.timeline-view__track {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 16px;
  flex-shrink: 0;
}

.timeline-view__dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  background: var(--color-border);
  flex-shrink: 0;
  margin-top: 6px;
}

.timeline-view__dot--current {
  background: var(--color-brand);
}

.timeline-view__line {
  width: 2px;
  flex: 1;
  background: var(--color-border);
  margin-top: 4px;
}

.timeline-view__content {
  padding-bottom: var(--space-4);
}

.timeline-view__desc {
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  line-height: var(--leading-normal);
}

.timeline-view__meta {
  display: flex;
  gap: var(--space-2);
  margin-top: var(--space-1);
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.timeline-view__empty {
  padding: var(--space-8) 0;
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}
</style>
```

- [ ] **Step 5: Create `frontend/src/components/athena/ProjectionViewer.vue`**

```vue
<script setup lang="ts">
import { computed, ref } from 'vue'

const props = defineProps<{
  projection: any
}>()

const expandedEntities = ref<Set<string>>(new Set())

const groups = computed(() => {
  if (!props.projection) return []
  const facts = props.projection.facts || props.projection.entries || []
  const grouped: Record<string, any[]> = {}
  for (const fact of facts) {
    const entity = fact.subject || fact.entity || '未知'
    if (!grouped[entity]) grouped[entity] = []
    grouped[entity].push(fact)
  }
  return Object.entries(grouped).map(([entity, items]) => ({ entity, items }))
})

function toggle(entity: string) {
  if (expandedEntities.value.has(entity)) {
    expandedEntities.value.delete(entity)
  } else {
    expandedEntities.value.add(entity)
  }
}
</script>

<template>
  <div class="projection-viewer">
    <div v-if="groups.length === 0" class="projection-viewer__empty">暂无投影数据</div>
    <div v-for="group in groups" :key="group.entity" class="projection-viewer__group">
      <button class="projection-viewer__header" @click="toggle(group.entity)">
        <span class="projection-viewer__entity">{{ group.entity }}</span>
        <span class="projection-viewer__count">{{ group.items.length }}</span>
        <span class="projection-viewer__chevron">{{ expandedEntities.has(group.entity) ? '▾' : '▸' }}</span>
      </button>
      <div v-if="expandedEntities.has(group.entity)" class="projection-viewer__facts">
        <div v-for="(fact, i) in group.items" :key="i" class="projection-viewer__fact">
          <span class="projection-viewer__predicate">{{ fact.predicate || fact.key || '' }}</span>
          <span class="projection-viewer__value">{{ fact.value || fact.object || '' }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.projection-viewer__group {
  border-bottom: 1px solid var(--color-border);
}

.projection-viewer__header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
  padding: var(--space-3) 0;
  background: transparent;
  border: none;
  cursor: pointer;
  text-align: left;
}

.projection-viewer__entity {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-primary);
}

.projection-viewer__count {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  background: var(--color-bg-tertiary);
  padding: 1px 6px;
  border-radius: var(--radius-full);
}

.projection-viewer__chevron {
  margin-left: auto;
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.projection-viewer__facts {
  padding: 0 0 var(--space-3) var(--space-4);
}

.projection-viewer__fact {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-1) 0;
  font-size: var(--text-sm);
}

.projection-viewer__predicate {
  color: var(--color-text-secondary);
  min-width: 100px;
}

.projection-viewer__value {
  color: var(--color-text-primary);
}

.projection-viewer__empty {
  padding: var(--space-8) 0;
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}
</style>
```

- [ ] **Step 6: Create `frontend/src/components/athena/KnowledgeViewer.vue`**

```vue
<script setup lang="ts">
defineProps<{
  knowledge: any
}>()
</script>

<template>
  <div class="knowledge-viewer">
    <div v-if="!knowledge" class="knowledge-viewer__empty">暂无主体认知数据</div>
    <template v-else>
      <div
        v-for="(subject, key) in (knowledge.subjects || knowledge)"
        :key="String(key)"
        class="knowledge-viewer__subject"
      >
        <h4 class="knowledge-viewer__name">{{ typeof key === 'string' ? key : subject.name || '' }}</h4>
        <div
          v-for="(item, i) in (subject.beliefs || subject.items || [])"
          :key="i"
          class="knowledge-viewer__item"
          :class="{ 'knowledge-viewer__item--discrepancy': item.discrepancy }"
        >
          <span class="knowledge-viewer__belief">{{ item.belief || item.content || '' }}</span>
          <span v-if="item.ground_truth" class="knowledge-viewer__truth">真相: {{ item.ground_truth }}</span>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.knowledge-viewer__subject {
  margin-bottom: var(--space-4);
}

.knowledge-viewer__name {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-2);
}

.knowledge-viewer__item {
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  border-bottom: 1px solid var(--color-border);
}

.knowledge-viewer__item--discrepancy {
  background: var(--color-warning-light);
}

.knowledge-viewer__belief {
  color: var(--color-text-primary);
}

.knowledge-viewer__truth {
  display: block;
  margin-top: var(--space-1);
  font-size: var(--text-xs);
  color: var(--color-warning);
}

.knowledge-viewer__empty {
  padding: var(--space-8) 0;
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}
</style>
```

- [ ] **Step 7: Create `frontend/src/components/athena/ProposalList.vue`**

```vue
<script setup lang="ts">
import { ref } from 'vue'
import BaseBadge from '../base/BaseBadge.vue'

defineProps<{
  proposals: any
}>()

const expandedId = ref<string | null>(null)

function toggle(id: string) {
  expandedId.value = expandedId.value === id ? null : id
}

const statusVariant: Record<string, 'success' | 'warning' | 'error' | 'neutral'> = {
  draft: 'neutral',
  pending: 'warning',
  approved: 'success',
  rejected: 'error',
}
</script>

<template>
  <div class="proposal-list">
    <div v-if="!proposals?.bundles?.length" class="proposal-list__empty">暂无提案</div>
    <div
      v-for="bundle in (proposals?.bundles || [])"
      :key="bundle.id"
      class="proposal-list__item"
    >
      <button class="proposal-list__header" @click="toggle(bundle.id)">
        <span class="proposal-list__title">{{ bundle.title || bundle.id }}</span>
        <BaseBadge :variant="statusVariant[bundle.status] || 'neutral'" size="sm">
          {{ bundle.status }}
        </BaseBadge>
        <span class="proposal-list__meta">{{ bundle.items?.length || 0 }} 项</span>
        <span class="proposal-list__chevron">{{ expandedId === bundle.id ? '▾' : '▸' }}</span>
      </button>
      <div v-if="expandedId === bundle.id" class="proposal-list__detail">
        <div v-for="(item, i) in (bundle.items || [])" :key="i" class="proposal-list__detail-item">
          {{ item.description || item.content || JSON.stringify(item) }}
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.proposal-list__item {
  border-bottom: 1px solid var(--color-border);
}

.proposal-list__header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  width: 100%;
  padding: var(--space-3) 0;
  background: transparent;
  border: none;
  cursor: pointer;
  text-align: left;
}

.proposal-list__title {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-primary);
  flex: 1;
}

.proposal-list__meta {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.proposal-list__chevron {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.proposal-list__detail {
  padding: 0 0 var(--space-3) var(--space-4);
}

.proposal-list__detail-item {
  padding: var(--space-2) 0;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  border-bottom: 1px solid var(--color-border);
}

.proposal-list__detail-item:last-child {
  border-bottom: none;
}

.proposal-list__empty {
  padding: var(--space-8) 0;
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}
</style>
```

- [ ] **Step 8: Create `frontend/src/components/athena/ConsistencyList.vue`**

```vue
<script setup lang="ts">
import { ref } from 'vue'
import BaseBadge from '../base/BaseBadge.vue'

defineProps<{
  issues: any[]
}>()

const expandedIdx = ref<number | null>(null)

function toggle(idx: number) {
  expandedIdx.value = expandedIdx.value === idx ? null : idx
}

const severityVariant: Record<string, 'success' | 'warning' | 'error' | 'neutral'> = {
  pass: 'success',
  warning: 'warning',
  error: 'error',
  info: 'neutral',
}
</script>

<template>
  <div class="consistency-list">
    <div v-if="issues.length === 0" class="consistency-list__empty">暂无一致性检查结果</div>
    <div
      v-for="(issue, idx) in issues"
      :key="idx"
      class="consistency-list__item"
    >
      <button class="consistency-list__header" @click="toggle(idx)">
        <BaseBadge :variant="severityVariant[issue.severity || issue.status] || 'neutral'" size="sm">
          {{ issue.severity || issue.status || 'info' }}
        </BaseBadge>
        <span class="consistency-list__type">{{ issue.check_type || issue.type || '' }}</span>
        <span class="consistency-list__desc">{{ issue.description || issue.message || '' }}</span>
        <span class="consistency-list__chevron">{{ expandedIdx === idx ? '▾' : '▸' }}</span>
      </button>
      <div v-if="expandedIdx === idx && issue.evidence" class="consistency-list__evidence">
        {{ typeof issue.evidence === 'string' ? issue.evidence : JSON.stringify(issue.evidence) }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.consistency-list__item {
  border-bottom: 1px solid var(--color-border);
}

.consistency-list__header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
  padding: var(--space-3) 0;
  background: transparent;
  border: none;
  cursor: pointer;
  text-align: left;
}

.consistency-list__type {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  min-width: 80px;
}

.consistency-list__desc {
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  flex: 1;
}

.consistency-list__chevron {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.consistency-list__evidence {
  padding: var(--space-2) var(--space-4) var(--space-3);
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-sm);
  margin-bottom: var(--space-2);
}

.consistency-list__empty {
  padding: var(--space-8) 0;
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}
</style>
```

- [ ] **Step 9: Create `frontend/src/components/athena/AthenaChatPanel.vue`**

Slide-over panel from right, 400px wide, uses ChatMessageList + ChatInput pattern for Athena dialog:

```vue
<script setup lang="ts">
import { computed } from 'vue'
import ChatMessageList from '../chat/ChatMessageList.vue'
import ChatInput from '../chat/ChatInput.vue'
import { useAthenaStore } from '../../stores/athena'

const props = defineProps<{
  open: boolean
  projectId: string
}>()

const emit = defineEmits<{
  close: []
}>()

const athena = useAthenaStore()

const messages = computed(() =>
  (athena.messages || []).map((m: any) => ({
    role: m.role,
    content: m.content,
    message_type: m.message_type || null,
    meta: m.meta || null,
    pending_action: null,
    action_result: null,
  })),
)

async function onSend(text: string) {
  await athena.sendChat(props.projectId, text)
}
</script>

<template>
  <Teleport to="body">
    <Transition name="slide">
      <div v-if="open" class="athena-chat-panel">
        <header class="athena-chat-panel__header">
          <h3 class="athena-chat-panel__title">Athena</h3>
          <button class="athena-chat-panel__close" @click="emit('close')">&times;</button>
        </header>
        <ChatMessageList
          :messages="messages"
          :loading="athena.chatLoading"
        />
        <ChatInput
          :loading="athena.chatLoading"
          :disabled="false"
          :has-pending-action="false"
          @send="onSend"
        />
      </div>
    </Transition>
    <Transition name="fade">
      <div v-if="open" class="athena-chat-panel__backdrop" @click="emit('close')" />
    </Transition>
  </Teleport>
</template>

<style scoped>
.athena-chat-panel {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  width: var(--athena-chat-width, 400px);
  background: var(--color-bg-white);
  border-left: 1px solid var(--color-border);
  box-shadow: var(--shadow-md);
  z-index: 30;
  display: flex;
  flex-direction: column;
}

.athena-chat-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
}

.athena-chat-panel__title {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.athena-chat-panel__close {
  font-size: var(--text-xl);
  color: var(--color-text-tertiary);
  padding: var(--space-1);
  line-height: 1;
}

.athena-chat-panel__close:hover {
  color: var(--color-text-primary);
}

.athena-chat-panel__backdrop {
  position: fixed;
  inset: 0;
  z-index: 29;
}

/* Transitions */
.slide-enter-active,
.slide-leave-active {
  transition: transform var(--transition-normal);
}

.slide-enter-from,
.slide-leave-to {
  transform: translateX(100%);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--transition-normal);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
```

- [ ] **Step 10: Commit**

```bash
cd /home/guixin/project_workspace/novelv3 && git add frontend/src/components/athena/EntityTable.vue frontend/src/components/athena/RelationTable.vue frontend/src/components/athena/RuleList.vue frontend/src/components/athena/TimelineView.vue frontend/src/components/athena/ProjectionViewer.vue frontend/src/components/athena/KnowledgeViewer.vue frontend/src/components/athena/ProposalList.vue frontend/src/components/athena/ConsistencyList.vue frontend/src/components/athena/AthenaChatPanel.vue && git commit -m "feat: add Athena detail components and chat slide-over panel"
```

---

### Task 6: AthenaView

**Files:**
- Create: `frontend/src/views/AthenaView.vue` (replace existing)
- Modify: `frontend/src/router/index.ts`

- [ ] **Step 1: Create new `frontend/src/views/AthenaView.vue`**

Replace the entire file. The new AthenaView uses sub-nav for section navigation and renders the appropriate detail component in the main content area. Preserves all existing athena store interactions:

```vue
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectStore } from '../stores/project'
import { useAthenaStore } from '../stores/athena'
import { useUiStore, type AthenaSection } from '../stores/ui'
import BaseButton from '../components/base/BaseButton.vue'
import EntityTable from '../components/athena/EntityTable.vue'
import RelationTable from '../components/athena/RelationTable.vue'
import RuleList from '../components/athena/RuleList.vue'
import TimelineView from '../components/athena/TimelineView.vue'
import ProjectionViewer from '../components/athena/ProjectionViewer.vue'
import KnowledgeViewer from '../components/athena/KnowledgeViewer.vue'
import ProposalList from '../components/athena/ProposalList.vue'
import ConsistencyList from '../components/athena/ConsistencyList.vue'
import AthenaChatPanel from '../components/athena/AthenaChatPanel.vue'

interface NavSection {
  label: string
  items: { key: AthenaSection; label: string }[]
}

const sections: NavSection[] = [
  {
    label: '本体',
    items: [
      { key: 'characters', label: '角色' },
      { key: 'locations', label: '地点' },
      { key: 'factions', label: '势力' },
      { key: 'items', label: '物品' },
      { key: 'relations', label: '关系' },
      { key: 'rules', label: '规则' },
    ],
  },
  {
    label: '状态',
    items: [
      { key: 'projection', label: '真相投影' },
      { key: 'timeline', label: '时间线' },
      { key: 'knowledge', label: '主体认知' },
    ],
  },
  {
    label: '演化',
    items: [
      { key: 'outline', label: '大纲' },
      { key: 'storyline', label: '故事线' },
      { key: 'proposals', label: '提案' },
      { key: 'consistency', label: '一致性检查' },
    ],
  },
]

const route = useRoute()
const router = useRouter()
const project = useProjectStore()
const athena = useAthenaStore()
const ui = useUiStore()
const pid = computed(() => route.params.id as string)
const chatOpen = ref(false)

const activeSection = computed<AthenaSection>(() => {
  const routeSection = route.params.section as string | undefined
  if (routeSection && isValidSection(routeSection)) return routeSection as AthenaSection
  return ui.activeAthenaSection
})

function isValidSection(s: string): boolean {
  return sections.some((sec) => sec.items.some((item) => item.key === s))
}

// Entity type mapping for ontology sections
const entityTypeMap: Record<string, string> = {
  characters: 'character',
  locations: 'location',
  factions: 'faction',
  items: 'item',
}

const entitySections = new Set(['characters', 'locations', 'factions', 'items'])

const entities = computed(() => {
  if (!entitySections.has(activeSection.value)) return []
  const type = entityTypeMap[activeSection.value]
  const allEntities = athena.ontology?.entities || []
  return allEntities.filter((e: any) => !type || e.type === type || e.entity_type === type)
})

const relations = computed(() => athena.ontology?.relations || [])
const rules = computed(() => athena.ontology?.rules || [])
const timelineEvents = computed(() => athena.timeline?.events || athena.timeline?.entries || [])
const timelineAnchors = computed(() => athena.timeline?.anchors || [])
const consistencyIssues = computed<any[]>(() => [])

onMounted(() => void initialize(pid.value))

watch(pid, (next, prev) => {
  if (next && next !== prev) void initialize(next)
})

watch(activeSection, (section) => {
  ui.setAthenaSection(section)
  void loadSectionData(section)
})

async function initialize(projectId: string) {
  athena.reset()
  await project.loadProject(projectId)
  await Promise.all([
    athena.loadOntology(projectId),
    athena.loadMessages(projectId),
  ])
  await loadSectionData(activeSection.value)
}

async function loadSectionData(section: AthenaSection) {
  const id = pid.value
  if (entitySections.has(section) || section === 'relations' || section === 'rules') {
    if (!athena.ontology) await athena.loadOntology(id)
  }
  if (section === 'projection') {
    if (!athena.projection) await athena.loadState(id)
  }
  if (section === 'timeline') {
    if (!athena.timeline) await athena.loadTimeline(id)
  }
  if (section === 'knowledge') {
    if (!athena.projection) await athena.loadState(id)
  }
  if (section === 'proposals') {
    if (!athena.proposals) await athena.loadProposals(id)
  }
  if (section === 'outline' || section === 'storyline') {
    if (!athena.evolutionPlan) await athena.loadEvolutionPlan(id)
  }
}

function navigateSection(section: AthenaSection) {
  router.push(`/projects/${pid.value}/athena/${section}`)
}
</script>

<template>
  <div v-if="project.currentProject" class="athena-view">
    <!-- Sub-nav content -->
    <Teleport to="[data-subnav-content]">
      <div class="athena-subnav">
        <div v-for="sec in sections" :key="sec.label" class="athena-subnav__section">
          <div class="athena-subnav__section-label">{{ sec.label }}</div>
          <button
            v-for="item in sec.items"
            :key="item.key"
            class="athena-subnav__item"
            :class="{ 'athena-subnav__item--active': activeSection === item.key }"
            @click="navigateSection(item.key)"
          >
            {{ item.label }}
          </button>
        </div>
        <div class="athena-subnav__divider" />
        <div class="athena-subnav__actions">
          <BaseButton variant="ghost" size="sm" @click="chatOpen = true">
            💬 Athena 对话
          </BaseButton>
        </div>
      </div>
    </Teleport>

    <!-- Main content: detail view based on active section -->
    <div class="athena-view__content">
      <EntityTable
        v-if="entitySections.has(activeSection)"
        :entities="entities"
        :entity-type="entityTypeMap[activeSection]"
      />
      <RelationTable v-else-if="activeSection === 'relations'" :relations="relations" />
      <RuleList v-else-if="activeSection === 'rules'" :rules="rules" />
      <ProjectionViewer v-else-if="activeSection === 'projection'" :projection="athena.projection" />
      <TimelineView
        v-else-if="activeSection === 'timeline'"
        :events="timelineEvents"
        :anchors="timelineAnchors"
      />
      <KnowledgeViewer v-else-if="activeSection === 'knowledge'" :knowledge="athena.projection" />
      <ProposalList v-else-if="activeSection === 'proposals'" :proposals="athena.proposals" />
      <ConsistencyList v-else-if="activeSection === 'consistency'" :issues="consistencyIssues" />
      <div v-else-if="activeSection === 'outline' || activeSection === 'storyline'" class="athena-view__placeholder">
        {{ activeSection === 'outline' ? '大纲' : '故事线' }}数据加载中...
      </div>
    </div>

    <!-- Chat slide-over -->
    <AthenaChatPanel
      :open="chatOpen"
      :project-id="pid"
      @close="chatOpen = false"
    />
  </div>
  <div v-else class="athena-view__loading">加载中...</div>
</template>

<style scoped>
.athena-view {
  height: 100%;
}

.athena-view__content {
  height: 100%;
}

.athena-view__loading,
.athena-view__placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}

/* Sub-nav styles */
.athena-subnav {
  display: flex;
  flex-direction: column;
}

.athena-subnav__section {
  margin-bottom: var(--space-1);
}

.athena-subnav__section-label {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-tertiary);
  padding: var(--space-3) var(--space-3) var(--space-1);
}

.athena-subnav__item {
  display: block;
  width: 100%;
  text-align: left;
  font-size: var(--text-sm);
  padding: var(--space-1) var(--space-3) var(--space-1) var(--space-5);
  color: var(--color-text-secondary);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.athena-subnav__item:hover {
  color: var(--color-text-primary);
  background: var(--color-bg-secondary);
}

.athena-subnav__item--active {
  color: var(--color-brand);
  font-weight: var(--font-medium);
  background: var(--color-brand-light);
}

.athena-subnav__divider {
  height: 1px;
  background: var(--color-border);
  margin: var(--space-2) 0;
}

.athena-subnav__actions {
  padding: var(--space-2) var(--space-3);
}
</style>
```

- [ ] **Step 2: Router already has AthenaView routes from Plan A**

Verify that the router imports point to the correct file. Since we're replacing the existing `AthenaView.vue` in-place, the import `import AthenaView from '../views/AthenaView.vue'` in the router already works. No change needed.

- [ ] **Step 3: Commit**

```bash
cd /home/guixin/project_workspace/novelv3 && git add frontend/src/views/AthenaView.vue && git commit -m "feat: rebuild AthenaView with master-detail pattern and sub-nav navigation"
```

---

### Task 7: ManuscriptView + SettingsView

**Files:**
- Create: `frontend/src/views/ManuscriptView.vue`
- Rewrite: `frontend/src/views/SettingsView.vue`
- Modify: `frontend/src/router/index.ts`

- [ ] **Step 1: Create `frontend/src/views/ManuscriptView.vue`**

```vue
<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useProjectStore } from '../stores/project'
import ChapterList from '../components/shared/ChapterList.vue'

const route = useRoute()
const project = useProjectStore()
const pid = computed(() => route.params.id as string)

const chapterItems = computed(() =>
  (project.chapters || []).map((c: any) => ({
    index: c.chapter_index,
    wordCount: c.word_count || 0,
  })),
)

function onSelectChapter(_index: number) {
  // Placeholder — manuscript editor not yet implemented
}
</script>

<template>
  <div class="manuscript-view">
    <!-- Sub-nav content -->
    <Teleport to="[data-subnav-content]">
      <div class="manuscript-subnav">
        <div class="manuscript-subnav__label">章节</div>
        <ChapterList
          :chapters="chapterItems"
          :active-index="null"
          @select="onSelectChapter"
        />
      </div>
    </Teleport>

    <!-- Main content: placeholder -->
    <div class="manuscript-view__placeholder">
      正文编辑器即将推出
    </div>
  </div>
</template>

<style scoped>
.manuscript-view {
  height: 100%;
}

.manuscript-view__placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--color-text-tertiary);
  font-size: var(--text-lg);
}

.manuscript-subnav__label {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-tertiary);
  padding: var(--space-3) var(--space-3) var(--space-1);
}
</style>
```

- [ ] **Step 2: Rewrite `frontend/src/views/SettingsView.vue`**

Replace the entire file. Preserves the existing API key save logic but uses new base components:

```vue
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api/client'
import BaseButton from '../components/base/BaseButton.vue'
import BaseInput from '../components/base/BaseInput.vue'

const apiKey = ref('')
const saved = ref(false)
const hasStoredKey = ref(false)

onMounted(async () => {
  const cfg = await api.getConfig()
  hasStoredKey.value = cfg.has_api_key
})

async function save() {
  const nextKey = apiKey.value.trim()
  if (!nextKey) {
    saved.value = true
    setTimeout(() => { saved.value = false }, 2000)
    return
  }
  await api.updateConfig(nextKey)
  hasStoredKey.value = true
  apiKey.value = ''
  saved.value = true
  setTimeout(() => { saved.value = false }, 2000)
}
</script>

<template>
  <div class="settings-view">
    <h1 class="settings-view__title">设置</h1>

    <section class="settings-view__section">
      <h2 class="settings-view__section-title">API 配置</h2>
      <div class="settings-view__row">
        <BaseInput
          v-model="apiKey"
          label="API Key"
          type="password"
          placeholder="sk-..."
        />
      </div>
      <div class="settings-view__row settings-view__row--actions">
        <BaseButton variant="primary" size="sm" @click="save">
          保存配置
        </BaseButton>
        <span v-if="hasStoredKey" class="settings-view__status">已配置</span>
        <span v-if="saved" class="settings-view__saved">已保存</span>
      </div>
    </section>

    <section class="settings-view__section">
      <h2 class="settings-view__section-title">偏好设置</h2>
      <p class="settings-view__placeholder">更多设置项即将推出</p>
    </section>
  </div>
</template>

<style scoped>
.settings-view {
  max-width: 720px;
  margin: 0 auto;
}

.settings-view__title {
  font-size: var(--text-xl);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-8);
}

.settings-view__section {
  margin-bottom: var(--space-8);
}

.settings-view__section-title {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--color-border);
}

.settings-view__row {
  margin-bottom: var(--space-4);
}

.settings-view__row--actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.settings-view__status {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  font-weight: var(--font-medium);
}

.settings-view__saved {
  font-size: var(--text-sm);
  color: var(--color-success);
  font-weight: var(--font-medium);
}

.settings-view__placeholder {
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}
</style>
```

- [ ] **Step 3: Update router for ManuscriptView**

In `frontend/src/router/index.ts`:

```diff
-import ManuscriptPlaceholder from '../views/ManuscriptPlaceholder.vue'
+import ManuscriptView from '../views/ManuscriptView.vue'

   {
     path: '/projects/:id/manuscript',
-    component: ManuscriptPlaceholder,
+    component: ManuscriptView,
     meta: { showSidebar: true, workspace: 'manuscript' } satisfies AppRouteMeta,
   },
```

The SettingsView import stays the same since we're replacing the file in-place.

- [ ] **Step 4: Commit**

```bash
cd /home/guixin/project_workspace/novelv3 && git add frontend/src/views/ManuscriptView.vue frontend/src/views/SettingsView.vue frontend/src/router/index.ts && git commit -m "feat: add ManuscriptView placeholder and rebuild SettingsView with base components"
```

---

### Task 8: Verification

**Files:** None (verification only)

- [ ] **Step 1: TypeScript type check**

```bash
cd /home/guixin/project_workspace/novelv3/frontend && npx vue-tsc --noEmit
```

Common issues to fix:
- Missing type imports for `AthenaSection` in ui store
- `BaseTableColumn` export from BaseTable.vue may need to be a separate type export
- `entitySections` used in template needs to be a reactive computed or exposed — use `entitySections.has()` in a method instead if template access fails
- Any `any` type warnings from strict mode — add explicit types where needed

- [ ] **Step 2: Build check**

```bash
cd /home/guixin/project_workspace/novelv3/frontend && npm run build
```

- [ ] **Step 3: Run tests**

```bash
cd /home/guixin/project_workspace/novelv3/frontend && npx vitest run
```

Common test fixes:
- Tests importing from old `ProjectList.vue` or `ProjectDetail.vue` — update imports to new view files
- Tests that mount `ChatWorkspace` with old props — update to use new chat components
- Tests referencing old CSS classes — update selectors
- The `projectListDeleteDialog.test.ts` should still pass since the dialog logic file is unchanged

- [ ] **Step 4: Fix any issues found in Steps 1-3, then commit**

```bash
cd /home/guixin/project_workspace/novelv3 && git add -A && git commit -m "fix: resolve type/build/test issues from Plan B page views"
```

- [ ] **Step 5: Visual verification in browser**

```bash
cd /home/guixin/project_workspace/novelv3/frontend && npm run dev
```

Check in browser:
1. `/` — Project list table renders, create/delete works
2. `/projects/:id/hermes` — Chat loads, messages display, slash commands work, action polling works
3. `/projects/:id/athena` — Sub-nav sections render, detail views switch, chat panel slides in
4. `/projects/:id/manuscript` — Placeholder shows, chapter list in sub-nav
5. `/settings` — API key form works, save persists

---

### Summary of What Plan B Delivers

After completing all 8 tasks:

1. Four shared components (`PhaseProgress`, `ChapterList`, `ExportModal`, `VersionsModal`) reused across views
2. Four chat components (`ChatMessage`, `ChatInput`, `ChatMessageList`, `CommandMenu`) extracted and restyled
3. `ProjectListView` — table-based project list replacing card grid
4. `HermesView` — full chat interface with sub-nav phases/chapters, preserving all ProjectDetail.vue logic
5. Nine Athena detail components + `AthenaChatPanel` slide-over
6. `AthenaView` — master-detail with sub-nav section navigation
7. `ManuscriptView` — placeholder with chapter list sub-nav
8. `SettingsView` — clean form layout with base components

Old view components (`ProjectList.vue`, `ProjectDetail.vue`, `ManuscriptPlaceholder.vue`) and their dependencies are superseded but not deleted. Plan C will handle cleanup.
