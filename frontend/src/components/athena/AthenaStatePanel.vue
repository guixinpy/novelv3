<template>
  <div class="athena-panel">
    <div v-if="projection" class="athena-panel__grid">
      <section class="athena-panel__card">
        <h4>实体状态</h4>
        <ul v-if="entityEntries.length" class="athena-panel__list">
          <li v-for="[ref, entity] in entityEntries" :key="ref">
            <strong>{{ ref }}</strong> — {{ formatAttrs(entity.attributes) }}
          </li>
        </ul>
        <p v-else class="athena-panel__empty">无</p>
      </section>
      <section class="athena-panel__card">
        <h4>关键事实</h4>
        <ul v-if="factEntries.length" class="athena-panel__list">
          <li v-for="[subj, facts] in factEntries" :key="subj">
            <strong>{{ subj }}</strong> — {{ formatAttrs(facts) }}
          </li>
        </ul>
        <p v-else class="athena-panel__empty">无</p>
      </section>
      <section v-if="timeline" class="athena-panel__card">
        <h4>时间线 ({{ timeline.events.length }} 事件)</h4>
        <ul v-if="timeline.events.length" class="athena-panel__list">
          <li v-for="e in timeline.events.slice(0, 15)" :key="e.id">
            第{{ e.chapter_index }}章 — {{ e.description }}
          </li>
        </ul>
      </section>
    </div>
    <p v-else class="athena-panel__empty">加载中...</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { AthenaTimeline, WorldProjection } from '../../api/types'

const props = defineProps<{
  projection: WorldProjection | null
  timeline: AthenaTimeline | null
}>()

const entityEntries = computed(() => props.projection ? Object.entries(props.projection.entities).slice(0, 10) : [])
const factEntries = computed(() => props.projection ? Object.entries(props.projection.facts).slice(0, 10) : [])

function formatAttrs(val: Record<string, unknown>) {
  return Object.entries(val).map(([k, v]) => `${k}: ${String(v)}`).join(' / ')
}
</script>

<style scoped>
.athena-panel__grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.8rem; }
.athena-panel__card { border: 1px solid rgba(111, 69, 31, 0.1); border-radius: 0.8rem; padding: 0.85rem; background: rgba(255, 252, 246, 0.92); }
.athena-panel__card h4 { margin: 0 0 0.5rem; color: var(--accent-strong); font-size: 0.82rem; }
.athena-panel__list { display: grid; gap: 0.3rem; margin: 0; padding: 0; list-style: none; }
.athena-panel__list li { color: var(--ink-strong); font-size: 0.76rem; line-height: 1.5; }
.athena-panel__list strong { color: var(--accent-strong); }
.athena-panel__empty { color: var(--ink-muted); font-size: 0.76rem; }
.athena-panel__meta { color: var(--ink-muted); font-size: 0.74rem; margin: 0; }
</style>
