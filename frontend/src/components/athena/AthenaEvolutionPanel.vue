<template>
  <div class="athena-panel">
    <div class="athena-panel__grid">
      <section class="athena-panel__card">
        <h4>大纲</h4>
        <div v-if="evolutionPlan?.outline">
          <p class="athena-panel__meta">状态：{{ evolutionPlan.outline.status }} · {{ evolutionPlan.outline.total_chapters }} 章</p>
        </div>
        <p v-else class="athena-panel__empty">未生成</p>
      </section>
      <section class="athena-panel__card">
        <h4>故事线</h4>
        <div v-if="evolutionPlan?.storyline">
          <p class="athena-panel__meta">状态：{{ evolutionPlan.storyline.status }}</p>
        </div>
        <p v-else class="athena-panel__empty">未生成</p>
      </section>
      <section class="athena-panel__card">
        <h4>待审提案</h4>
        <div v-if="proposals">
          <p class="athena-panel__meta">共 {{ proposals.total }} 个 bundle</p>
          <ul v-if="proposals.items.length" class="athena-panel__list">
            <li v-for="b in proposals.items" :key="b.id">
              {{ b.title }} — {{ b.bundle_status }}
            </li>
          </ul>
        </div>
        <p v-else class="athena-panel__empty">加载中...</p>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { AthenaEvolutionPlan, PaginatedProposalBundles } from '../../api/types'

defineProps<{
  evolutionPlan: AthenaEvolutionPlan | null
  proposals: PaginatedProposalBundles | null
}>()
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
