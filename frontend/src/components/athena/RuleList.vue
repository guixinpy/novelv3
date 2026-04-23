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
