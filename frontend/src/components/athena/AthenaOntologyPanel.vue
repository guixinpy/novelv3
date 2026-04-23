<template>
  <div class="athena-panel">
    <div v-if="ontology" class="athena-panel__grid">
      <section class="athena-panel__card">
        <h4>角色实体</h4>
        <ul v-if="ontology.entities.characters?.length" class="athena-panel__list">
          <li v-for="c in ontology.entities.characters" :key="c.id">{{ c.name }}</li>
        </ul>
        <p v-else class="athena-panel__empty">无</p>
      </section>
      <section class="athena-panel__card">
        <h4>地点</h4>
        <ul v-if="ontology.entities.locations?.length" class="athena-panel__list">
          <li v-for="loc in ontology.entities.locations" :key="loc.id">{{ loc.name }}</li>
        </ul>
        <p v-else class="athena-panel__empty">无</p>
      </section>
      <section class="athena-panel__card">
        <h4>关系图谱</h4>
        <ul v-if="ontology.relations.length" class="athena-panel__list">
          <li v-for="r in ontology.relations" :key="r.id">
            {{ r.source_ref }} → {{ r.relation_type }} → {{ r.target_ref }}
          </li>
        </ul>
        <p v-else class="athena-panel__empty">无</p>
      </section>
      <section class="athena-panel__card">
        <h4>世界规则</h4>
        <ul v-if="ontology.rules.length" class="athena-panel__list">
          <li v-for="r in ontology.rules" :key="r.id">{{ r.description }}</li>
        </ul>
        <p v-else class="athena-panel__empty">无</p>
      </section>
      <template v-if="ontology.setup_summary">
        <section v-if="characters.length" class="athena-panel__card athena-panel__card--wide">
          <h4>角色详情（来自设定）</h4>
          <ul class="athena-panel__list">
            <li v-for="(c, i) in characters" :key="i">
              <strong>{{ c.name }}</strong>（{{ c.gender || '未知' }}，{{ c.age || '?' }}岁）— {{ c.personality || '' }}
            </li>
          </ul>
        </section>
        <section v-if="ontology.setup_summary.world_building" class="athena-panel__card athena-panel__card--wide">
          <h4>世界观（来自设定）</h4>
          <p class="athena-panel__text">{{ worldBackground }}</p>
        </section>
      </template>
    </div>
    <p v-else class="athena-panel__empty">加载中...</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { AthenaOntology } from '../../api/types'

const props = defineProps<{
  ontology: AthenaOntology | null
}>()

interface SetupCharacter {
  name?: string
  age?: number
  gender?: string
  personality?: string
}

const characters = computed<SetupCharacter[]>(() => {
  const raw = props.ontology?.setup_summary?.characters
  return Array.isArray(raw) ? raw : []
})

const worldBackground = computed(() => {
  const wb = props.ontology?.setup_summary?.world_building
  if (!wb || typeof wb !== 'object') return ''
  const obj = wb as Record<string, unknown>
  return String(obj.background || obj.atmosphere || '')
})
</script>

<style scoped>
.athena-panel__grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.8rem; }
.athena-panel__card { border: 1px solid rgba(111, 69, 31, 0.1); border-radius: 0.8rem; padding: 0.85rem; background: rgba(255, 252, 246, 0.92); }
.athena-panel__card--wide { grid-column: 1 / -1; }
.athena-panel__card h4 { margin: 0 0 0.5rem; color: var(--accent-strong); font-size: 0.82rem; }
.athena-panel__list { display: grid; gap: 0.3rem; margin: 0; padding: 0; list-style: none; }
.athena-panel__list li { color: var(--ink-strong); font-size: 0.76rem; line-height: 1.5; }
.athena-panel__list strong { color: var(--accent-strong); }
.athena-panel__empty { color: var(--ink-muted); font-size: 0.76rem; }
.athena-panel__meta { color: var(--ink-muted); font-size: 0.74rem; margin: 0; }
.athena-panel__text { color: var(--ink-strong); font-size: 0.76rem; line-height: 1.6; margin: 0; white-space: pre-wrap; }
</style>
