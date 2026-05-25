<script setup lang="ts">
import type { ChatCommandDefinition } from '../../components/workspace/chatCommands'

defineProps<{
  commands: ChatCommandDefinition[]
  activeIndex: number
}>()

const emit = defineEmits<{
  pick: [command: ChatCommandDefinition]
}>()

const categoryLabels: Record<string, string> = {
  agent_control: 'Agent 控制',
  session: '会话',
  legacy_alias: '兼容',
}

const projectionLabels: Record<string, string> = {
  continue_agent_control: '继续控制',
  agent_health_projection: '状态诊断',
}

function categoryLabel(command: ChatCommandDefinition) {
  return categoryLabels[command.category || ''] || ''
}

function projectionLabel(command: ChatCommandDefinition) {
  return projectionLabels[command.controlProjectionType || ''] || ''
}

function requiredToolCount(command: ChatCommandDefinition) {
  return command.requiredAgentTools?.length || 0
}
</script>

<template>
  <div class="command-menu" data-testid="command-menu">
    <button
      v-for="(command, index) in commands"
      :key="command.name"
      type="button"
      class="command-menu__item"
      :class="{ 'command-menu__item--active': index === activeIndex }"
      @click="emit('pick', command)"
    >
      <span class="command-menu__main">
        <span class="command-menu__name">{{ command.label }}</span>
        <span class="command-menu__desc">{{ command.description }}</span>
        <span class="command-menu__meta">
          <span v-if="categoryLabel(command)" class="command-menu__badge">{{ categoryLabel(command) }}</span>
          <span v-if="projectionLabel(command)" class="command-menu__badge command-menu__badge--result">
            {{ projectionLabel(command) }}
          </span>
          <span v-if="requiredToolCount(command)" class="command-menu__badge command-menu__badge--muted">
            {{ requiredToolCount(command) }} 项能力
          </span>
        </span>
      </span>
      <span class="command-menu__example">{{ command.example }}</span>
    </button>
  </div>
</template>

<style scoped>
.command-menu {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-white);
  box-shadow: var(--shadow-md);
  padding: var(--space-1);
}

.command-menu__item {
  width: 100%;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-3);
  text-align: left;
  padding: var(--space-2) var(--space-3);
  color: var(--color-text-primary);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.command-menu__item:hover,
.command-menu__item--active {
  background: var(--color-bg-secondary);
}

.command-menu__main {
  display: grid;
  gap: 2px;
}

.command-menu__name {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
}

.command-menu__desc {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
}

.command-menu__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 2px;
}

.command-menu__badge {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: 1px 5px;
  font-size: 11px;
  line-height: 1.5;
  color: var(--color-text-secondary);
  background: var(--color-bg-secondary);
}

.command-menu__badge--result {
  color: var(--color-brand);
  background: var(--color-brand-subtle);
  border-color: var(--color-brand-subtle);
}

.command-menu__badge--muted {
  color: var(--color-text-tertiary);
  background: var(--color-bg-white);
}

.command-menu__example {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  white-space: nowrap;
}
</style>
