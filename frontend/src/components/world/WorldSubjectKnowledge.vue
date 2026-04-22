<template>
  <div class="subject-knowledge" data-testid="world-subject-knowledge">
    <div class="subject-knowledge__selector">
      <span class="subject-knowledge__label">选择主体：</span>
      <select
        v-model="selected"
        class="subject-knowledge__select"
        @change="onSelect"
      >
        <option value="" disabled>请选择</option>
        <option v-for="ref in subjectRefs" :key="ref" :value="ref">{{ ref }}</option>
      </select>
    </div>
    <div v-if="projection" class="subject-knowledge__grid">
      <article class="subject-knowledge__block">
        <h4>作为主体的事实</h4>
        <ul v-if="asSubjectEntries.length" class="subject-knowledge__list">
          <li v-for="[pred, val] in asSubjectEntries" :key="pred">
            <strong>{{ selected }}.{{ pred }}</strong>
            <span>{{ String(val) }}</span>
          </li>
        </ul>
        <p v-else class="subject-knowledge__empty">无</p>
      </article>
      <article class="subject-knowledge__block">
        <h4>作为客体的事实</h4>
        <ul v-if="asObjectEntries.length" class="subject-knowledge__list">
          <li v-for="[subj, facts] in asObjectEntries" :key="subj">
            <strong>{{ subj }}</strong>
            <span>{{ formatFacts(facts) }}</span>
          </li>
        </ul>
        <p v-else class="subject-knowledge__empty">无</p>
      </article>
    </div>
    <p v-else-if="selected" class="subject-knowledge__empty">加载中...</p>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { WorldProjection } from '../../api/types'
const props = defineProps<{
  subjectRefs: string[]
  projection: WorldProjection | null
}>()

const emit = defineEmits<{
  select: [subjectRef: string]
}>()

const selected = ref('')

const asSubjectEntries = computed(() => {
  if (!props.projection || !selected.value) return []
  const facts = props.projection.facts[selected.value]
  return facts ? Object.entries(facts) : []
})

const asObjectEntries = computed(() => {
  if (!props.projection || !selected.value) return []
  return Object.entries(props.projection.facts).filter(([key]) => key !== selected.value)
})

function formatFacts(facts: Record<string, unknown>) {
  return Object.entries(facts).map(([k, v]) => `${k}: ${String(v)}`).join(' / ')
}

function onSelect() {
  if (selected.value) emit('select', selected.value)
}
</script>

<style scoped>
.subject-knowledge__selector {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-bottom: 0.8rem;
}
.subject-knowledge__label { color: var(--ink-muted); font-size: 0.8rem; }
.subject-knowledge__select {
  border: 1px solid rgba(111, 69, 31, 0.14);
  border-radius: 0.6rem;
  padding: 0.4rem 0.6rem;
  background: rgba(255, 252, 246, 0.92);
  color: var(--ink-strong);
  font-size: 0.8rem;
}
.subject-knowledge__grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.8rem; }
.subject-knowledge__block { display: grid; gap: 0.4rem; }
.subject-knowledge__block h4 { margin: 0; color: var(--ink-strong); font-size: 0.84rem; }
.subject-knowledge__list { display: grid; gap: 0.35rem; margin: 0; padding: 0; list-style: none; }
.subject-knowledge__list li { display: grid; gap: 0.1rem; }
.subject-knowledge__list strong { color: var(--ink-strong); font-size: 0.78rem; }
.subject-knowledge__list span,
.subject-knowledge__empty { color: var(--ink-muted); font-size: 0.78rem; }
</style>
