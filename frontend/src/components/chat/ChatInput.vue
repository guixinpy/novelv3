<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import BaseButton from '../base/BaseButton.vue'
import CommandMenu from './CommandMenu.vue'
import {
  filterChatCommands,
  parseSlashCommand,
  type ChatCommandDefinition,
} from '../../components/workspace/chatCommands'

const props = defineProps<{
  loading: boolean
  disabled: boolean
  hasPendingAction: boolean
}>()

const emit = defineEmits<{
  send: [text: string]
}>()

const input = ref('')
const inputEl = ref<HTMLInputElement | null>(null)
const activeCommandIndex = ref(0)
const commandMenuDismissed = ref(false)

const commandCandidates = computed(() => {
  const candidates = filterChatCommands(input.value)
  if (!props.hasPendingAction) return candidates
  return candidates.filter((c) => c.name === 'clear')
})

const showCommandMenu = computed(() => {
  if (commandMenuDismissed.value) return false
  if (!input.value.startsWith('/')) return false
  return commandCandidates.value.length > 0
})

const canSubmit = computed(() => {
  const text = input.value.trim()
  if (!text || props.loading) return false
  if (!props.hasPendingAction) return true
  const parsed = parseSlashCommand(text)
  return parsed.kind === 'command' && parsed.name === 'clear'
})

function submit() {
  const text = input.value.trim()
  if (!text || !canSubmit.value) return
  emit('send', text)
  input.value = ''
  activeCommandIndex.value = 0
  commandMenuDismissed.value = false
}

function pickCommand(command: ChatCommandDefinition) {
  input.value = `/${command.name} `
  activeCommandIndex.value = 0
  commandMenuDismissed.value = true
  nextTick(() => inputEl.value?.focus())
}

function isImeComposing(event: KeyboardEvent) {
  return event.isComposing || event.keyCode === 229
}

function onInputKeydown(event: KeyboardEvent) {
  if (isImeComposing(event)) return

  if (event.key === 'Escape' && showCommandMenu.value) {
    commandMenuDismissed.value = true
    return
  }

  if (!showCommandMenu.value) {
    if (event.key === 'Enter') {
      event.preventDefault()
      submit()
    }
    return
  }

  if (event.key === 'ArrowDown') {
    event.preventDefault()
    activeCommandIndex.value = (activeCommandIndex.value + 1) % commandCandidates.value.length
    return
  }

  if (event.key === 'ArrowUp') {
    event.preventDefault()
    const total = commandCandidates.value.length
    activeCommandIndex.value = (activeCommandIndex.value - 1 + total) % total
    return
  }

  if (event.key === 'Enter') {
    event.preventDefault()
    if (props.hasPendingAction && canSubmit.value) {
      submit()
      return
    }
    const command = commandCandidates.value[activeCommandIndex.value]
    if (command) pickCommand(command)
  }
}

watch(input, () => { commandMenuDismissed.value = false })
watch(commandCandidates, (next) => {
  if (!next.length || activeCommandIndex.value >= next.length) {
    activeCommandIndex.value = 0
  }
})
</script>

<template>
  <footer class="chat-input">
    <CommandMenu
      v-if="showCommandMenu"
      :commands="commandCandidates"
      :active-index="activeCommandIndex"
      class="chat-input__menu"
      @pick="pickCommand"
    />
    <div class="chat-input__bar">
      <input
        ref="inputEl"
        v-model="input"
        :disabled="loading || disabled"
        class="chat-input__field"
        placeholder="输入消息，或键入 / 查看命令"
        @keydown="onInputKeydown"
      />
      <BaseButton
        variant="primary"
        size="sm"
        :disabled="!canSubmit"
        @click="submit"
      >
        ➤
      </BaseButton>
    </div>
  </footer>
</template>

<style scoped>
.chat-input {
  border-top: 1px solid var(--color-border);
  padding: var(--space-3);
  background: var(--color-bg-white);
  flex-shrink: 0;
}

.chat-input__menu {
  margin-bottom: var(--space-2);
}

.chat-input__bar {
  display: flex;
  gap: var(--space-2);
}

.chat-input__field {
  flex: 1;
  min-width: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  background: var(--color-bg-white);
  outline: none;
  transition: border-color var(--transition-fast);
}

.chat-input__field:focus {
  border-color: var(--color-brand);
  box-shadow: 0 0 0 2px var(--color-brand-subtle);
}

.chat-input__field:disabled {
  background: var(--color-bg-secondary);
  cursor: not-allowed;
}
</style>
