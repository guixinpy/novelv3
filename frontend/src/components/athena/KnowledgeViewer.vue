<script setup lang="ts">
import { computed } from 'vue'

interface KnowledgeItem {
  belief?: string
  content?: string
  ground_truth?: string
  discrepancy?: boolean
}

interface KnowledgeSubject {
  name?: string
  beliefs?: KnowledgeItem[]
  items?: KnowledgeItem[]
}

type KnowledgePayload = {
  subjects?: Record<string, KnowledgeSubject>
} & Record<string, KnowledgeSubject | Record<string, KnowledgeSubject> | undefined>

const props = defineProps<{
  knowledge: KnowledgePayload | null
}>()

const subjects = computed(() => {
  if (!props.knowledge) return []
  const rawSubjects = props.knowledge.subjects && typeof props.knowledge.subjects === 'object'
    ? props.knowledge.subjects
    : props.knowledge
  return Object.entries(rawSubjects)
    .filter((entry): entry is [string, KnowledgeSubject] => isKnowledgeSubject(entry[1]))
    .map(([key, subject]) => ({
      key,
      name: subject.name || key,
      items: subject.beliefs || subject.items || [],
    }))
})

function isKnowledgeSubject(value: unknown): value is KnowledgeSubject {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}
</script>

<template>
  <div class="knowledge-viewer">
    <div v-if="!knowledge" class="knowledge-viewer__empty">暂无主体认知数据</div>
    <template v-else>
      <div
        v-for="subject in subjects"
        :key="subject.key"
        class="knowledge-viewer__subject"
      >
        <h4 class="knowledge-viewer__name">{{ subject.name }}</h4>
        <div
          v-for="(item, i) in subject.items"
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
