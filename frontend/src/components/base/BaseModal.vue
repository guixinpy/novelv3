<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    open: boolean
    title?: string
    width?: string
  }>(),
  { width: '480px' },
)

const emit = defineEmits<{ close: [] }>()
const panelRef = ref<HTMLElement | null>(null)

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
  if (e.key === 'Tab' && panelRef.value) {
    const focusable = panelRef.value.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    )
    if (!focusable.length) return
    const first = focusable[0]
    const last = focusable[focusable.length - 1]
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault()
      last.focus()
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault()
      first.focus()
    }
  }
}

function onBackdropClick(e: MouseEvent) {
  if (e.target === e.currentTarget) emit('close')
}

watch(() => props.open, async (val) => {
  document.body.style.overflow = val ? 'hidden' : ''
  if (val) {
    await nextTick()
    panelRef.value?.focus()
  }
})

onMounted(() => { document.addEventListener('keydown', onKeydown) })
onUnmounted(() => { document.removeEventListener('keydown', onKeydown); document.body.style.overflow = '' })
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="open" class="base-modal__backdrop" @click="onBackdropClick">
        <div ref="panelRef" class="base-modal__panel" :style="{ width }" role="dialog" aria-modal="true" tabindex="-1">
          <header v-if="title || $slots.header" class="base-modal__header">
            <slot name="header">
              <h3 class="base-modal__title">{{ title }}</h3>
            </slot>
            <button class="base-modal__close" aria-label="关闭" @click="emit('close')">&times;</button>
          </header>
          <div class="base-modal__body"><slot /></div>
          <footer v-if="$slots.footer" class="base-modal__footer"><slot name="footer" /></footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.base-modal__backdrop { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.3); z-index: var(--z-modal); display: flex; align-items: center; justify-content: center; }
.base-modal__panel { background: var(--color-bg-white); border-radius: var(--radius-lg); box-shadow: var(--shadow-md); max-height: 85vh; overflow-y: auto; display: flex; flex-direction: column; outline: none; }
.base-modal__header { padding: var(--space-4); border-bottom: 1px solid var(--color-border); display: flex; justify-content: space-between; align-items: center; flex-shrink: 0; }
.base-modal__title { font-size: var(--text-lg); font-weight: var(--font-semibold); color: var(--color-text-primary); }
.base-modal__close { font-size: var(--text-xl); color: var(--color-text-tertiary); line-height: 1; padding: var(--space-1); }
.base-modal__close:hover { color: var(--color-text-primary); }
.base-modal__body { padding: var(--space-4); flex: 1; overflow-y: auto; }
.base-modal__footer { padding: var(--space-3) var(--space-4); border-top: 1px solid var(--color-border); display: flex; justify-content: flex-end; gap: var(--space-2); flex-shrink: 0; }
.modal-enter-active, .modal-leave-active { transition: opacity var(--transition-normal); }
.modal-enter-active .base-modal__panel, .modal-leave-active .base-modal__panel { transition: transform var(--transition-normal); }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from .base-modal__panel, .modal-leave-to .base-modal__panel { transform: scale(0.95); }
</style>
