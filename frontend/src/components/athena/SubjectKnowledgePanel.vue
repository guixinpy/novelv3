<script setup lang="ts">
import { computed } from 'vue'
import type { WorldProjection } from '../../api/types'

const props = defineProps<{
  projection: WorldProjection | null
  subjectKnowledge: WorldProjection | null
  selectedSubjectRef: string | null
}>()

const emit = defineEmits<{
  selectSubject: [subjectRef: string]
}>()

const subjectRefs = computed(() => {
  const refs = new Set<string>()
  const entities = props.projection?.entities || {}
  for (const [ref, entity] of Object.entries(entities)) {
    if (entity.entity_type === 'character') refs.add(ref)
  }
  for (const ref of Object.keys(props.projection?.facts || {})) {
    if (!entities[ref] && ref.startsWith('char.')) refs.add(ref)
  }
  return [...refs].sort()
})
const selectedFacts = computed(() => {
  const subjectRef = props.selectedSubjectRef
  if (!subjectRef || !props.subjectKnowledge) return []
  return Object.entries(props.subjectKnowledge.facts?.[subjectRef] || {})
})
const visibleFactGroups = computed(() => Object.entries(props.subjectKnowledge?.facts || {}))

function formatValue(value: unknown) {
  if (value == null) return ''
  if (typeof value === 'string') return value
  return JSON.stringify(value)
}
</script>

<template>
  <div class="subject-panel">
    <div v-if="!projection" class="subject-panel__empty">尚未建立正式 world-model 投影</div>
    <template v-else>
      <div class="subject-panel__toolbar">
        <label class="subject-panel__label" for="athena-subject-select">主体</label>
        <select
          id="athena-subject-select"
          class="subject-panel__select"
          :value="selectedSubjectRef || ''"
          @change="emit('selectSubject', ($event.target as HTMLSelectElement).value)"
        >
          <option value="" disabled>选择主体</option>
          <option v-for="subjectRef in subjectRefs" :key="subjectRef" :value="subjectRef">
            {{ subjectRef }}
          </option>
        </select>
      </div>

      <div v-if="selectedSubjectRef && !subjectKnowledge" class="subject-panel__empty">加载主体认知...</div>
      <div v-else-if="selectedSubjectRef" class="subject-panel__content">
        <section class="subject-panel__section">
          <h3 class="subject-panel__title">作为主体</h3>
          <div v-if="selectedFacts.length === 0" class="subject-panel__empty">暂无主体事实</div>
          <div v-for="[predicate, value] in selectedFacts" :key="predicate" class="subject-panel__fact">
            <span>{{ predicate }}</span>
            <strong>{{ formatValue(value) }}</strong>
          </div>
        </section>

        <section class="subject-panel__section">
          <h3 class="subject-panel__title">可见事实组</h3>
          <div v-if="visibleFactGroups.length === 0" class="subject-panel__empty">暂无可见事实</div>
          <div v-for="[subjectRef, facts] in visibleFactGroups" :key="subjectRef" class="subject-panel__group">
            <strong>{{ subjectRef }}</strong>
            <span>{{ Object.entries(facts).map(([k, v]) => `${k}: ${formatValue(v)}`).join(' / ') }}</span>
          </div>
        </section>
      </div>
      <div v-else class="subject-panel__empty">选择一个主体查看它知道的世界。</div>
    </template>
  </div>
</template>

<style scoped>
.subject-panel {
  height: 100%;
  overflow: auto;
  padding: var(--space-4);
}

.subject-panel__toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}

.subject-panel__label {
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

.subject-panel__select {
  min-width: 220px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: var(--space-2) var(--space-3);
  color: var(--color-text-primary);
  background: var(--color-bg-primary);
  font-size: var(--text-sm);
}

.subject-panel__content {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: var(--space-4);
}

.subject-panel__section {
  display: grid;
  align-content: start;
  gap: var(--space-2);
}

.subject-panel__title {
  color: var(--color-text-primary);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}

.subject-panel__fact,
.subject-panel__group {
  display: grid;
  gap: var(--space-1);
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--color-border);
  font-size: var(--text-sm);
}

.subject-panel__fact span,
.subject-panel__group span {
  color: var(--color-text-secondary);
  overflow-wrap: anywhere;
}

.subject-panel__fact strong,
.subject-panel__group strong {
  color: var(--color-text-primary);
  font-weight: var(--font-medium);
  overflow-wrap: anywhere;
}

.subject-panel__empty {
  padding: var(--space-8) 0;
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}

@media (max-width: 860px) {
  .subject-panel__content {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
