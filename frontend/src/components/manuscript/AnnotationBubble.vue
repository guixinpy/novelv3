<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
  open: boolean
  selectedText: string
  initialComment?: string
}>()

const emit = defineEmits<{
  save: [comment: string]
  cancel: []
}>()

const comment = ref('')

watch(() => props.open, (open) => {
  if (open) comment.value = props.initialComment || ''
})
</script>

<template>
  <div v-if="open" class="annotation-bubble">
    <div class="annotation-bubble__selected">{{ selectedText }}</div>
    <textarea v-model="comment" class="annotation-bubble__input" rows="3" placeholder="写下批注..." />
    <div class="annotation-bubble__actions">
      <button class="annotation-bubble__button" @click="emit('cancel')">取消</button>
      <button class="annotation-bubble__button annotation-bubble__button--primary" :disabled="!comment.trim()" @click="emit('save', comment.trim())">保存</button>
    </div>
  </div>
</template>

<style scoped>
.annotation-bubble { position: sticky; top: var(--space-3); z-index: var(--z-panel); margin-bottom: var(--space-4); padding: var(--space-3); border: 1px solid var(--color-border); border-radius: var(--radius-lg); background: var(--color-bg-white); box-shadow: var(--shadow-md); }
.annotation-bubble__selected { margin-bottom: var(--space-2); color: var(--color-text-secondary); font-size: var(--text-sm); }
.annotation-bubble__input { width: 100%; border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: var(--space-2); color: var(--color-text-primary); resize: vertical; }
.annotation-bubble__actions { display: flex; justify-content: flex-end; gap: var(--space-2); margin-top: var(--space-2); }
.annotation-bubble__button { padding: var(--space-1) var(--space-3); border-radius: var(--radius-md); color: var(--color-text-secondary); }
.annotation-bubble__button--primary { background: var(--color-brand); color: var(--color-bg-white); }
.annotation-bubble__button:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
