<template>
  <section class="world-panel" data-testid="world-projection-viewer">
    <header class="world-panel__header">
      <div class="world-panel__tabs">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          type="button"
          class="world-panel__tab"
          :class="{ 'is-active': activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
        </button>
      </div>
      <span class="world-panel__pill">{{ entityEntries.length }} 个实体</span>
    </header>

    <div v-if="activeTab === 'current'" class="world-panel__grid">
      <article class="world-panel__block">
        <h4>实体状态</h4>
        <ul v-if="entityEntries.length" class="world-panel__list">
          <li v-for="[entityRef, entity] in entityEntries" :key="entityRef">
            <strong>{{ entityRef }}</strong>
            <span>{{ formatAttributes(entity.attributes) }}</span>
          </li>
        </ul>
        <p v-else class="world-panel__empty">当前没有结构化实体。</p>
      </article>
      <article class="world-panel__block">
        <h4>关键事实</h4>
        <ul v-if="factEntries.length" class="world-panel__list">
          <li v-for="[subjectRef, facts] in factEntries" :key="subjectRef">
            <strong>{{ subjectRef }}</strong>
            <span>{{ formatAttributes(facts) }}</span>
          </li>
        </ul>
        <p v-else class="world-panel__empty">当前没有确认事实。</p>
      </article>
      <article class="world-panel__block">
        <h4>在场信息</h4>
        <ul v-if="presenceEntries.length" class="world-panel__list">
          <li v-for="[entityRef, presence] in presenceEntries" :key="entityRef">
            <strong>{{ entityRef }}</strong>
            <span>{{ presence.location_ref || '未知位置' }} / {{ presence.presence_status || '未标注' }}</span>
          </li>
        </ul>
        <p v-else class="world-panel__empty">当前没有在场投影。</p>
      </article>
    </div>

    <WorldSubjectKnowledge
      v-else-if="activeTab === 'subject'"
      :subject-refs="subjectRefs"
      :projection="subjectKnowledge"
      @select="$emit('loadSubjectKnowledge', $event)"
    />

    <WorldChapterSnapshot
      v-else-if="activeTab === 'snapshot'"
      :projection="chapterSnapshot"
      :selected-chapter="selectedChapter"
      :max-chapter="maxChapter"
      @update:selected-chapter="$emit('loadChapterSnapshot', $event)"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { WorldProjection } from '../../api/types'
import WorldSubjectKnowledge from './WorldSubjectKnowledge.vue'
import WorldChapterSnapshot from './WorldChapterSnapshot.vue'

const props = defineProps<{
  projection: WorldProjection
  subjectKnowledge: WorldProjection | null
  chapterSnapshot: WorldProjection | null
  selectedChapter: number
  maxChapter: number
}>()

defineEmits<{
  loadSubjectKnowledge: [subjectRef: string]
  loadChapterSnapshot: [chapterIndex: number]
}>()

const tabs = [
  { key: 'current', label: '当前真相' },
  { key: 'subject', label: '主体认知' },
  { key: 'snapshot', label: '章节快照' },
] as const

const activeTab = ref<'current' | 'subject' | 'snapshot'>('current')

const entityEntries = computed(() => Object.entries(props.projection.entities).slice(0, 6))
const factEntries = computed(() => Object.entries(props.projection.facts).slice(0, 6))
const presenceEntries = computed(() => Object.entries(props.projection.presence).slice(0, 6))
const subjectRefs = computed(() => Object.keys(props.projection.entities))

function formatAttributes(value: Record<string, unknown>) {
  return Object.entries(value).map(([key, entry]) => `${key}: ${String(entry)}`).join(' / ')
}
</script>

<style scoped>
.world-panel {
  display: grid;
  gap: 0.95rem;
  border: 1px solid rgba(111, 69, 31, 0.14);
  border-radius: 1rem;
  padding: 1rem;
  background:
    linear-gradient(180deg, rgba(251, 247, 239, 0.98) 0%, rgba(244, 236, 222, 0.92) 100%);
}

.world-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.8rem;
}

.world-panel__eyebrow {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: 0.74rem;
}

.world-panel__title {
  margin: 0.1rem 0 0;
  color: var(--accent-strong);
  font-size: 1rem;
}

.world-panel__pill {
  border-radius: 999px;
  padding: 0.28rem 0.72rem;
  background: rgba(118, 74, 27, 0.08);
  color: var(--accent-strong);
  font-size: 0.74rem;
  font-weight: 700;
}

.world-panel__grid {
  display: grid;
  gap: 0.8rem;
}

.world-panel__block {
  display: grid;
  gap: 0.45rem;
}

.world-panel__block h4 {
  margin: 0;
  color: var(--color-text-primary);
  font-size: 0.86rem;
}

.world-panel__list {
  display: grid;
  gap: 0.45rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.world-panel__list li {
  display: grid;
  gap: 0.15rem;
}

.world-panel__list strong {
  color: var(--color-text-primary);
  font-size: 0.8rem;
}

.world-panel__list span,
.world-panel__empty {
  color: var(--color-text-secondary);
  font-size: 0.8rem;
  line-height: 1.5;
}

.world-panel__tabs {
  display: flex;
  gap: 0;
}

.world-panel__tab {
  padding: 0.45rem 0.85rem;
  border: none;
  background: none;
  color: var(--color-text-secondary);
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  border-bottom: 2px solid transparent;
}

.world-panel__tab.is-active {
  color: var(--accent-strong);
  border-bottom-color: var(--accent-strong);
}
</style>
