<template>
  <Teleport to="body">
    <div
      v-if="show"
      class="inspector-detail-modal"
      role="dialog"
      aria-modal="true"
      :aria-labelledby="titleId"
      @click.self="emit('close')"
    >
      <div class="inspector-detail-modal__panel">
        <header class="inspector-detail-modal__header">
          <h2 :id="titleId" class="inspector-detail-modal__title">{{ title }}</h2>
          <button
            type="button"
            class="inspector-detail-modal__close"
            data-testid="inspector-detail-modal-close"
            aria-label="关闭详情弹窗"
            @click="emit('close')"
          >
            ×
          </button>
        </header>

        <div class="inspector-detail-modal__body">
          <slot />
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { onBeforeUnmount, watch } from 'vue'

const props = defineProps<{
  show: boolean
  title: string
}>()

const emit = defineEmits<{
  close: []
}>()

const titleId = `inspector-detail-modal-title-${Math.random().toString(36).slice(2, 9)}`

function handleKeydown(event: KeyboardEvent) {
  if (props.show && event.key === 'Escape') {
    emit('close')
  }
}

watch(
  () => props.show,
  (show) => {
    if (show) {
      document.addEventListener('keydown', handleKeydown)
      return
    }

    document.removeEventListener('keydown', handleKeydown)
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  document.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
.inspector-detail-modal {
  position: fixed;
  inset: 0;
  z-index: 90;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.2rem;
  background: rgba(47, 36, 24, 0.38);
  backdrop-filter: blur(8px);
}

.inspector-detail-modal__panel {
  width: min(100%, 70rem);
  max-height: calc(100vh - 2.4rem);
  overflow: auto;
  border: 1px solid rgba(125, 79, 42, 0.18);
  border-radius: 1.7rem;
  padding: 1.2rem;
  background:
    linear-gradient(180deg, rgba(252, 248, 239, 0.98) 0%, rgba(244, 236, 222, 0.97) 100%);
  box-shadow:
    0 28px 48px rgba(43, 28, 15, 0.24),
    inset 0 1px 0 rgba(255, 251, 243, 0.82);
}

.inspector-detail-modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.inspector-detail-modal__title {
  color: var(--ink-strong);
  font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif;
  font-size: 1.5rem;
  line-height: 1.1;
}

.inspector-detail-modal__close {
  width: 2.3rem;
  height: 2.3rem;
  flex: none;
  border: 1px solid rgba(111, 69, 31, 0.16);
  border-radius: 999px;
  background: rgba(255, 249, 238, 0.88);
  color: var(--ink-muted);
  font-size: 1.2rem;
  line-height: 1;
  transition:
    transform 180ms ease,
    border-color 180ms ease;
}

.inspector-detail-modal__close:hover {
  transform: translateY(-1px);
  border-color: rgba(111, 69, 31, 0.28);
}

.inspector-detail-modal__body {
  margin-top: 1rem;
}

@media (max-width: 720px) {
  .inspector-detail-modal {
    padding: 0.8rem;
  }

  .inspector-detail-modal__panel {
    max-height: calc(100vh - 1.6rem);
    border-radius: 1.35rem;
    padding: 1rem;
  }

  .inspector-detail-modal__title {
    font-size: 1.25rem;
  }
}
</style>
