<template>
  <div class="action-card">
    <p class="action-card__copy">
      {{ action.description }}
    </p>
    <div class="action-card__actions">
      <button
        :disabled="disabled"
        class="action-card__button action-card__button--primary"
        @click="$emit('decide', 'confirm')"
      >
        同意执行
      </button>
      <button
        :disabled="disabled"
        class="action-card__button"
        @click="$emit('decide', 'cancel')"
      >
        取消
      </button>
      <button
        :disabled="disabled"
        class="action-card__button"
        @click="showRevise = !showRevise"
      >
        修改后再执行
      </button>
    </div>
    <div
      v-if="showRevise"
      class="action-card__revise"
    >
      <input
        v-model="reviseComment"
        class="action-card__input"
        placeholder="补充修改说明..."
        @keyup.enter="submitRevise"
      >
      <button
        :disabled="disabled || !reviseComment.trim()"
        class="action-card__button action-card__button--primary"
        @click="submitRevise"
      >
        提交
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{ action: any; disabled: boolean }>()
const emit = defineEmits<{ decide: [decision: string, comment?: string] }>()

const showRevise = ref(false)
const reviseComment = ref('')

function submitRevise() {
  if (!reviseComment.value.trim()) return
  emit('decide', 'revise', reviseComment.value)
  reviseComment.value = ''
  showRevise.value = false
}
</script>

<style scoped>
.action-card {
  margin-top: 0.85rem;
  border: 1px solid rgba(111, 69, 31, 0.16);
  background:
    linear-gradient(180deg, rgba(248, 239, 221, 0.96) 0%, rgba(241, 230, 209, 0.94) 100%);
  border-radius: 1rem;
  padding: 1rem;
}

.action-card__copy {
  margin-bottom: 0.8rem;
  color: var(--color-text-primary);
  font-size: 0.92rem;
  line-height: 1.55;
}

.action-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}

.action-card__button {
  border: 1px solid rgba(111, 69, 31, 0.16);
  background: rgba(255, 251, 242, 0.92);
  color: var(--color-text-secondary);
  border-radius: 0.85rem;
  padding: 0.55rem 0.9rem;
  font-size: 0.86rem;
  font-weight: 700;
  transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
}

.action-card__button--primary {
  background: linear-gradient(180deg, #8d5d31 0%, #6f451f 100%);
  color: #fff8ef;
}

.action-card__button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 10px 18px rgba(79, 55, 27, 0.12);
}

.action-card__button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.action-card__revise {
  display: flex;
  gap: 0.65rem;
  margin-top: 0.8rem;
}

.action-card__input {
  flex: 1;
  min-width: 0;
  border: 1px solid rgba(111, 69, 31, 0.16);
  background: rgba(255, 251, 242, 0.96);
  color: var(--color-text-primary);
  border-radius: 0.85rem;
  padding: 0.65rem 0.85rem;
  font-size: 0.88rem;
  outline: none;
}

.action-card__input:focus {
  border-color: rgba(111, 69, 31, 0.34);
  box-shadow: 0 0 0 3px rgba(141, 93, 49, 0.12);
}
</style>
