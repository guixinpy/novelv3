<script setup lang="ts">
import BaseModal from '../base/BaseModal.vue'
import type { LocalAnnotation, LocalCorrection } from '../../stores/manuscript'

defineProps<{
  open: boolean
  annotations: LocalAnnotation[]
  corrections: LocalCorrection[]
  submitting: boolean
}>()

const emit = defineEmits<{
  close: []
  confirm: []
}>()
</script>

<template>
  <BaseModal :open="open" title="提交修订" width="560px" @close="emit('close')">
    <div class="revision-submit">
      <p class="revision-submit__hint">确认后将跳转回 Hermes，AI 会根据这些反馈重新生成本章。</p>
      <section class="revision-submit__section">
        <h4>批注（{{ annotations.length }}）</h4>
        <ul><li v-for="item in annotations" :key="item.id">第{{ item.paragraphIndex + 1 }}段：{{ item.comment }}</li></ul>
      </section>
      <section class="revision-submit__section">
        <h4>修正（{{ corrections.length }}）</h4>
        <ul><li v-for="item in corrections" :key="item.id">{{ item.originalText }} → {{ item.correctedText }}</li></ul>
      </section>
    </div>
    <template #footer>
      <button class="revision-submit__button" @click="emit('close')">取消</button>
      <button class="revision-submit__button revision-submit__button--primary" :disabled="submitting" @click="emit('confirm')">{{ submitting ? '提交中...' : '确认提交' }}</button>
    </template>
  </BaseModal>
</template>

<style scoped>
.revision-submit__hint { padding: var(--space-3); border-radius: var(--radius-md); background: var(--color-brand-light); color: var(--color-brand); font-size: var(--text-sm); }
.revision-submit__section { margin-top: var(--space-4); }
.revision-submit__section h4 { margin-bottom: var(--space-2); color: var(--color-text-primary); font-size: var(--text-sm); font-weight: var(--font-semibold); }
.revision-submit__section li { margin-bottom: var(--space-1); color: var(--color-text-secondary); font-size: var(--text-sm); }
.revision-submit__button { padding: var(--space-2) var(--space-4); border-radius: var(--radius-md); color: var(--color-text-secondary); }
.revision-submit__button--primary { background: var(--color-brand); color: var(--color-bg-white); }
.revision-submit__button:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
