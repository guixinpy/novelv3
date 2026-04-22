<template>
  <div class="chapter-snapshot" data-testid="world-chapter-snapshot">
    <div class="chapter-snapshot__selector">
      <span class="chapter-snapshot__label">截至章节：</span>
      <button class="chapter-snapshot__nav" :disabled="!canPrev" @click="prev">◀</button>
      <span class="chapter-snapshot__current">第 {{ selectedChapter }} 章</span>
      <button class="chapter-snapshot__nav" :disabled="!canNext" @click="next">▶</button>
      <span class="chapter-snapshot__total">/ 共 {{ maxChapter }} 章</span>
      <span class="chapter-snapshot__badge">只读快照</span>
    </div>
    <div v-if="projection" class="chapter-snapshot__grid">
      <article class="chapter-snapshot__block">
        <h4>实体状态</h4>
        <ul v-if="entityEntries.length" class="chapter-snapshot__list">
          <li v-for="[ref, entity] in entityEntries" :key="ref">
            <strong>{{ ref }}</strong>
            <span>{{ formatAttrs(entity.attributes) }}</span>
          </li>
        </ul>
        <p v-else class="chapter-snapshot__empty">无</p>
      </article>
      <article class="chapter-snapshot__block">
        <h4>关键事实</h4>
        <ul v-if="factEntries.length" class="chapter-snapshot__list">
          <li v-for="[subj, facts] in factEntries" :key="subj">
            <strong>{{ subj }}</strong>
            <span>{{ formatAttrs(facts) }}</span>
          </li>
        </ul>
        <p v-else class="chapter-snapshot__empty">无</p>
      </article>
      <article class="chapter-snapshot__block">
        <h4>在场信息</h4>
        <ul v-if="presenceEntries.length" class="chapter-snapshot__list">
          <li v-for="[ref, p] in presenceEntries" :key="ref">
            <strong>{{ ref }}</strong>
            <span>{{ p.location_ref || '未知' }} / {{ p.presence_status || '未标注' }}</span>
          </li>
        </ul>
        <p v-else class="chapter-snapshot__empty">无</p>
      </article>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { WorldProjection } from '../../api/types'

const props = defineProps<{
  projection: WorldProjection | null
  selectedChapter: number
  maxChapter: number
}>()

const emit = defineEmits<{
  'update:selectedChapter': [chapter: number]
}>()

const canPrev = computed(() => props.selectedChapter > 1)
const canNext = computed(() => props.selectedChapter < props.maxChapter)

const entityEntries = computed(() => props.projection ? Object.entries(props.projection.entities).slice(0, 6) : [])
const factEntries = computed(() => props.projection ? Object.entries(props.projection.facts).slice(0, 6) : [])
const presenceEntries = computed(() => props.projection ? Object.entries(props.projection.presence).slice(0, 6) : [])

function formatAttrs(val: Record<string, unknown>) {
  return Object.entries(val).map(([k, v]) => `${k}: ${String(v)}`).join(' / ')
}
function prev() { if (canPrev.value) emit('update:selectedChapter', props.selectedChapter - 1) }
function next() { if (canNext.value) emit('update:selectedChapter', props.selectedChapter + 1) }
</script>

<style scoped>
.chapter-snapshot__selector {
  display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.8rem;
}
.chapter-snapshot__label { color: var(--ink-muted); font-size: 0.8rem; }
.chapter-snapshot__nav {
  border: 1px solid rgba(111, 69, 31, 0.14); border-radius: 0.4rem;
  padding: 0.2rem 0.5rem; background: rgba(255, 252, 246, 0.92);
  color: var(--ink-muted); font-size: 0.78rem; cursor: pointer;
}
.chapter-snapshot__nav:disabled { opacity: 0.4; cursor: default; }
.chapter-snapshot__current {
  font-weight: 700; color: var(--accent-strong); font-size: 0.88rem;
  min-width: 4rem; text-align: center;
}
.chapter-snapshot__total { color: var(--ink-muted); font-size: 0.76rem; }
.chapter-snapshot__badge {
  margin-left: auto; border-radius: 999px; padding: 0.2rem 0.6rem;
  background: rgba(245, 158, 11, 0.12); color: #d97706; font-size: 0.7rem; font-weight: 700;
}
.chapter-snapshot__grid { display: grid; gap: 0.8rem; }
.chapter-snapshot__block { display: grid; gap: 0.4rem; border: 1px dashed rgba(111, 69, 31, 0.14); border-radius: 0.8rem; padding: 0.8rem; }
.chapter-snapshot__block h4 { margin: 0; color: var(--ink-strong); font-size: 0.84rem; }
.chapter-snapshot__list { display: grid; gap: 0.35rem; margin: 0; padding: 0; list-style: none; }
.chapter-snapshot__list li { display: grid; gap: 0.1rem; }
.chapter-snapshot__list strong { color: var(--ink-strong); font-size: 0.78rem; }
.chapter-snapshot__list span,
.chapter-snapshot__empty { color: var(--ink-muted); font-size: 0.78rem; }
</style>
