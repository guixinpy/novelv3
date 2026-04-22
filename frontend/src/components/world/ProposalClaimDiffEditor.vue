<template>
  <div class="diff-editor" data-testid="proposal-claim-diff-editor">
    <header class="diff-editor__header">
      <span class="diff-editor__title">编辑 Proposal Item</span>
      <span class="diff-editor__claim">{{ item.subject_ref }}.{{ item.predicate }}</span>
      <span v-if="changedCount > 0" class="diff-editor__badge">{{ changedCount }} 处变更</span>
    </header>

    <div class="diff-editor__fields">
      <div
        v-for="field in fields"
        :key="field.key"
        class="diff-editor__row"
        :class="{ 'is-changed': isChanged(field.key) }"
      >
        <span class="diff-editor__field-name">{{ field.key }}</span>
        <div class="diff-editor__field-value">
          <template v-if="field.type === 'number'">
            <span v-if="isChanged(field.key)" class="diff-editor__original">{{ field.original }}</span>
            <span v-if="isChanged(field.key)" class="diff-editor__arrow">→</span>
            <input
              type="number"
              :value="editedValues[field.key] ?? field.original"
              class="diff-editor__input"
              @input="onInput(field.key, ($event.target as HTMLInputElement).value, 'number')"
            >
          </template>
          <template v-else-if="field.type === 'select'">
            <span v-if="isChanged(field.key)" class="diff-editor__original">{{ field.original || '—' }}</span>
            <span v-if="isChanged(field.key)" class="diff-editor__arrow">→</span>
            <select
              :value="editedValues[field.key] ?? field.original ?? ''"
              class="diff-editor__input"
              @change="onInput(field.key, ($event.target as HTMLSelectElement).value, 'string')"
            >
              <option value="">—</option>
              <option v-for="opt in field.options" :key="opt" :value="opt">{{ opt }}</option>
            </select>
          </template>
          <template v-else-if="field.type === 'textarea'">
            <div v-if="isChanged(field.key)" class="diff-editor__original">{{ field.original }}</div>
            <textarea
              :value="editedValues[field.key] ?? field.original ?? ''"
              class="diff-editor__textarea"
              rows="2"
              @input="onInput(field.key, ($event.target as HTMLTextAreaElement).value, 'string')"
            />
          </template>
          <template v-else>
            <span v-if="isChanged(field.key)" class="diff-editor__original">{{ field.original || '—' }}</span>
            <span v-if="isChanged(field.key)" class="diff-editor__arrow">→</span>
            <input
              type="text"
              :value="editedValues[field.key] ?? field.original ?? ''"
              class="diff-editor__input"
              @input="onInput(field.key, ($event.target as HTMLInputElement).value, 'string')"
            >
          </template>
        </div>
        <button
          v-if="isChanged(field.key)"
          type="button"
          class="diff-editor__reset"
          @click="resetField(field.key)"
        >
          重置
        </button>
      </div>
    </div>

    <footer class="diff-editor__footer">
      <span class="diff-editor__hint">只有修改过的字段会提交</span>
      <div class="diff-editor__actions">
        <button type="button" class="diff-editor__btn" @click="$emit('cancel')">取消</button>
        <button type="button" class="diff-editor__btn diff-editor__btn--primary" @click="submit">确认编辑并通过</button>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue'
import type { ProposalItem } from '../../api/types'

const props = defineProps<{
  item: ProposalItem
  anchorOptions: string[]
}>()

const emit = defineEmits<{
  submit: [editedFields: Record<string, unknown>]
  cancel: []
}>()

interface FieldDef {
  key: string
  type: 'number' | 'text' | 'select' | 'textarea'
  original: unknown
  options?: string[]
}

const fields = computed<FieldDef[]>(() => [
  { key: 'chapter_index', type: 'number', original: (props.item as any).chapter_index ?? null },
  { key: 'intra_chapter_seq', type: 'number', original: (props.item as any).intra_chapter_seq ?? 0 },
  { key: 'valid_from_anchor_id', type: 'select', original: (props.item as any).valid_from_anchor_id ?? null, options: props.anchorOptions },
  { key: 'valid_to_anchor_id', type: 'select', original: (props.item as any).valid_to_anchor_id ?? null, options: props.anchorOptions },
  { key: 'source_event_ref', type: 'text', original: (props.item as any).source_event_ref ?? null },
  { key: 'evidence_refs', type: 'text', original: (props.item.evidence_refs ?? []).join(', ') },
  { key: 'notes', type: 'textarea', original: (props.item as any).notes ?? '' },
])

const editedValues = reactive<Record<string, unknown>>({})

const changedCount = computed(() =>
  fields.value.filter((f) => isChanged(f.key)).length,
)

function isChanged(key: string): boolean {
  if (!(key in editedValues)) return false
  const field = fields.value.find((f) => f.key === key)
  return field ? editedValues[key] !== field.original : false
}

function onInput(key: string, value: string, type: 'number' | 'string') {
  editedValues[key] = type === 'number' ? (value === '' ? null : Number(value)) : value
}

function resetField(key: string) {
  delete editedValues[key]
}

function submit() {
  const result: Record<string, unknown> = {}
  for (const field of fields.value) {
    if (isChanged(field.key)) {
      let val = editedValues[field.key]
      if (field.key === 'evidence_refs' && typeof val === 'string') {
        val = val.split(',').map((s: string) => s.trim()).filter(Boolean)
      }
      result[field.key] = val
    }
  }
  emit('submit', result)
}
</script>

<style scoped>
.diff-editor { display: grid; gap: 0; border: 1px solid rgba(111, 69, 31, 0.14); border-radius: 0.8rem; overflow: hidden; }
.diff-editor__header { display: flex; align-items: center; gap: 0.6rem; padding: 0.7rem 0.85rem; border-bottom: 1px solid rgba(111, 69, 31, 0.1); }
.diff-editor__title { color: var(--ink-strong); font-size: 0.84rem; font-weight: 700; }
.diff-editor__claim { color: var(--ink-muted); font-size: 0.76rem; }
.diff-editor__badge { margin-left: auto; border-radius: 0.4rem; padding: 0.15rem 0.5rem; background: rgba(245, 158, 11, 0.12); color: #d97706; font-size: 0.7rem; font-weight: 700; }
.diff-editor__fields { display: grid; }
.diff-editor__row { display: flex; align-items: center; gap: 0.6rem; padding: 0.55rem 0.85rem; border-bottom: 1px solid rgba(111, 69, 31, 0.06); }
.diff-editor__row.is-changed { background: rgba(245, 158, 11, 0.06); }
.diff-editor__field-name { width: 10rem; color: var(--ink-muted); font-size: 0.76rem; flex-shrink: 0; }
.diff-editor__row.is-changed .diff-editor__field-name { color: #d97706; font-weight: 700; }
.diff-editor__field-value { flex: 1; display: flex; align-items: center; gap: 0.5rem; }
.diff-editor__original { color: var(--ink-muted); font-size: 0.76rem; text-decoration: line-through; opacity: 0.7; }
.diff-editor__arrow { color: var(--ink-muted); font-size: 0.76rem; }
.diff-editor__input, .diff-editor__textarea {
  border: 1px solid rgba(111, 69, 31, 0.14); border-radius: 0.4rem;
  padding: 0.3rem 0.5rem; background: rgba(255, 252, 246, 0.92);
  color: var(--ink-strong); font-size: 0.78rem; flex: 1;
}
.diff-editor__textarea { resize: vertical; width: 100%; }
.diff-editor__reset { background: none; border: none; color: var(--ink-muted); font-size: 0.7rem; cursor: pointer; }
.diff-editor__footer { display: flex; align-items: center; justify-content: space-between; padding: 0.65rem 0.85rem; border-top: 1px solid rgba(111, 69, 31, 0.1); }
.diff-editor__hint { color: var(--ink-muted); font-size: 0.72rem; }
.diff-editor__actions { display: flex; gap: 0.45rem; }
.diff-editor__btn { border: 1px solid rgba(111, 69, 31, 0.18); border-radius: 999px; padding: 0.35rem 0.7rem; background: rgba(255, 252, 246, 0.92); color: var(--ink-muted); font-size: 0.76rem; cursor: pointer; }
.diff-editor__btn--primary { background: var(--accent-strong); color: #fff; border-color: var(--accent-strong); font-weight: 700; }
</style>
