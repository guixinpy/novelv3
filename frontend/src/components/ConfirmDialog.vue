<template>
  <Teleport to="body">
    <div
      v-if="show"
      class="confirm-dialog"
      role="dialog"
      aria-modal="true"
      :aria-labelledby="titleId"
      @click.self="handleClose"
    >
      <div class="confirm-dialog__panel">
        <div class="confirm-dialog__head">
          <div class="space-y-2">
            <p class="confirm-dialog__eyebrow">{{ eyebrow }}</p>
            <h2 :id="titleId" class="confirm-dialog__title">{{ title }}</h2>
          </div>

          <button
            type="button"
            class="confirm-dialog__close"
            :disabled="confirming"
            aria-label="关闭"
            @click="handleClose"
          >
            ×
          </button>
        </div>

        <p v-if="description" class="confirm-dialog__description">{{ description }}</p>
        <p v-if="errorMessage" class="confirm-dialog__error">{{ errorMessage }}</p>

        <div class="confirm-dialog__actions">
          <button
            type="button"
            class="confirm-dialog__button confirm-dialog__button--ghost"
            :disabled="confirming"
            @click="handleClose"
          >
            {{ cancelText }}
          </button>
          <button
            type="button"
            class="confirm-dialog__button confirm-dialog__button--danger"
            :disabled="confirming"
            @click="$emit('confirm')"
          >
            {{ confirming ? pendingText : confirmText }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
const props = withDefaults(defineProps<{
  show: boolean
  title: string
  description?: string
  eyebrow?: string
  confirmText?: string
  cancelText?: string
  pendingText?: string
  confirming?: boolean
  errorMessage?: string
}>(), {
  description: '',
  eyebrow: '危险操作',
  confirmText: '确认',
  cancelText: '取消',
  pendingText: '处理中...',
  confirming: false,
  errorMessage: '',
})

const emit = defineEmits<{
  close: []
  confirm: []
}>()

const titleId = `confirm-dialog-title-${Math.random().toString(36).slice(2, 9)}`

function handleClose() {
  if (props.confirming) return
  emit('close')
}
</script>

<style scoped>
.confirm-dialog {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.2rem;
  background: rgba(47, 36, 24, 0.4);
  backdrop-filter: blur(6px);
}

.confirm-dialog__panel {
  width: min(100%, 31rem);
  display: grid;
  gap: 1rem;
  border: 1px solid rgba(125, 79, 42, 0.24);
  border-radius: 1.7rem;
  padding: 1.35rem;
  background:
    linear-gradient(180deg, rgba(252, 248, 239, 0.98) 0%, rgba(244, 236, 222, 0.97) 100%);
  box-shadow:
    0 28px 48px rgba(43, 28, 15, 0.28),
    inset 0 1px 0 rgba(255, 251, 243, 0.82);
}

.confirm-dialog__head {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 1rem;
}

.confirm-dialog__eyebrow {
  color: #8d4c34;
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.confirm-dialog__title {
  color: var(--ink-strong);
  font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif;
  font-size: 1.55rem;
  line-height: 1.08;
}

.confirm-dialog__close {
  width: 2.3rem;
  height: 2.3rem;
  border: 1px solid rgba(111, 69, 31, 0.16);
  border-radius: 999px;
  background: rgba(255, 249, 238, 0.88);
  color: var(--ink-muted);
  font-size: 1.2rem;
  line-height: 1;
}

.confirm-dialog__description,
.confirm-dialog__error {
  font-size: 0.96rem;
  line-height: 1.7;
}

.confirm-dialog__description {
  color: var(--ink-muted);
}

.confirm-dialog__error {
  color: #8d3f31;
}

.confirm-dialog__actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding-top: 0.2rem;
}

.confirm-dialog__button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 1rem;
  padding: 0.82rem 1.05rem;
  font-size: 0.92rem;
  font-weight: 700;
  transition:
    transform 180ms ease,
    box-shadow 180ms ease,
    border-color 180ms ease;
}

.confirm-dialog__button:hover:not(:disabled),
.confirm-dialog__close:hover:not(:disabled) {
  transform: translateY(-1px);
}

.confirm-dialog__button--ghost {
  border: 1px solid rgba(111, 69, 31, 0.16);
  background: rgba(255, 249, 238, 0.86);
  color: var(--accent-strong);
}

.confirm-dialog__button--danger {
  border: 1px solid rgba(137, 65, 48, 0.24);
  background: linear-gradient(180deg, rgba(155, 78, 58, 0.97) 0%, rgba(128, 59, 38, 0.99) 100%);
  color: #fff7f2;
  box-shadow: 0 14px 28px rgba(101, 49, 34, 0.18);
}

.confirm-dialog__button:disabled,
.confirm-dialog__close:disabled {
  cursor: not-allowed;
  opacity: 0.58;
  transform: none;
  box-shadow: none;
}

@media (max-width: 640px) {
  .confirm-dialog__panel {
    padding: 1.1rem;
    border-radius: 1.35rem;
  }

  .confirm-dialog__title {
    font-size: 1.32rem;
  }

  .confirm-dialog__actions {
    flex-direction: column-reverse;
  }

  .confirm-dialog__button {
    width: 100%;
  }
}
</style>
