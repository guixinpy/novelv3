<template>
  <div class="chat-command-menu" data-testid="chat-command-menu">
    <button
      v-for="(command, index) in commands"
      :key="command.name"
      type="button"
      class="chat-command-menu__item"
      :class="{ 'chat-command-menu__item--active': index === activeIndex }"
      @click="emit('pick', command)"
    >
      <span class="chat-command-menu__main">
        <span class="chat-command-menu__name">{{ command.label }}</span>
        <span class="chat-command-menu__description">{{ command.description }}</span>
      </span>
      <span class="chat-command-menu__example">{{ command.example }}</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import type { ChatCommandDefinition } from './chatCommands'

defineProps<{
  commands: ChatCommandDefinition[]
  activeIndex: number
}>()

const emit = defineEmits<{
  pick: [command: ChatCommandDefinition]
}>()
</script>

<style scoped>
.chat-command-menu {
  border: 1px solid rgba(111, 69, 31, 0.16);
  border-radius: 0.9rem;
  background: rgba(255, 251, 242, 0.98);
  box-shadow: 0 10px 24px rgba(78, 53, 26, 0.12);
  padding: 0.35rem;
}

.chat-command-menu__item {
  width: 100%;
  border: 0;
  border-radius: 0.7rem;
  background: transparent;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 0.75rem;
  text-align: left;
  padding: 0.58rem 0.68rem;
  color: var(--ink-strong);
}

.chat-command-menu__item--active {
  background: rgba(111, 69, 31, 0.1);
}

.chat-command-menu__main {
  display: grid;
  gap: 0.14rem;
}

.chat-command-menu__name {
  font-size: 0.84rem;
  font-weight: 700;
  color: var(--ink-strong);
}

.chat-command-menu__description {
  font-size: 0.75rem;
  color: var(--ink-muted);
}

.chat-command-menu__example {
  font-size: 0.73rem;
  color: rgba(111, 69, 31, 0.72);
  white-space: nowrap;
}

@media (max-width: 720px) {
  .chat-command-menu__item {
    grid-template-columns: 1fr;
  }

  .chat-command-menu__example {
    white-space: normal;
  }
}
</style>
