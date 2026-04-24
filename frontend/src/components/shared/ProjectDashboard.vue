<script setup lang="ts">
defineProps<{
  setup: any
  storyline: any
  outline: any
  chapters: any[]
  totalWords: number
}>()

const emit = defineEmits<{
  action: [command: string]
}>()
</script>

<template>
  <div class="dashboard">
    <button
      class="dashboard__item"
      :class="{ 'dashboard__item--done': !!setup }"
      @click="emit('action', '/setup')"
    >
      <span class="dashboard__dot" :class="setup ? 'dashboard__dot--done' : 'dashboard__dot--empty'" />
      <span class="dashboard__label">设定</span>
      <span class="dashboard__detail">{{ setup ? '已生成' : '未创建' }}</span>
    </button>
    <button
      class="dashboard__item"
      :class="{ 'dashboard__item--done': !!storyline }"
      @click="emit('action', '/storyline')"
    >
      <span class="dashboard__dot" :class="storyline ? 'dashboard__dot--done' : 'dashboard__dot--empty'" />
      <span class="dashboard__label">故事线</span>
      <span class="dashboard__detail">{{ storyline ? '已生成' : '未创建' }}</span>
    </button>
    <button
      class="dashboard__item"
      :class="{ 'dashboard__item--done': !!outline }"
      @click="emit('action', '/outline')"
    >
      <span class="dashboard__dot" :class="outline ? 'dashboard__dot--done' : 'dashboard__dot--empty'" />
      <span class="dashboard__label">大纲</span>
      <span class="dashboard__detail">{{ outline ? `${outline.chapters?.length || 0} 章` : '未创建' }}</span>
    </button>
    <div class="dashboard__divider" />
    <div class="dashboard__stats">
      <div class="dashboard__stat">
        <span class="dashboard__stat-value">{{ chapters.length }}</span>
        <span class="dashboard__stat-label">章节</span>
      </div>
      <div class="dashboard__stat">
        <span class="dashboard__stat-value">{{ totalWords >= 10000 ? (totalWords / 10000).toFixed(1) + '万' : totalWords }}</span>
        <span class="dashboard__stat-label">字数</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dashboard {
  padding: var(--space-2) var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.dashboard__item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-2);
  border-radius: var(--radius-md);
  background: transparent;
  border: none;
  cursor: pointer;
  text-align: left;
  transition: background var(--transition-fast);
}

.dashboard__item:hover {
  background: var(--color-bg-secondary);
}

.dashboard__dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  flex-shrink: 0;
}

.dashboard__dot--done {
  background: var(--color-success);
}

.dashboard__dot--empty {
  background: transparent;
  border: 2px solid var(--color-border-strong);
}

.dashboard__label {
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  flex: 1;
}

.dashboard__detail {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.dashboard__divider {
  height: 1px;
  background: var(--color-border);
  margin: var(--space-1) 0;
}

.dashboard__stats {
  display: flex;
  gap: var(--space-4);
  padding: var(--space-2);
}

.dashboard__stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
}

.dashboard__stat-value {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  line-height: var(--leading-tight);
}

.dashboard__stat-label {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}
</style>
