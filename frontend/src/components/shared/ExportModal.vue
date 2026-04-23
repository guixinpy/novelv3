<script setup lang="ts">
import BaseModal from '../base/BaseModal.vue'
import BaseButton from '../base/BaseButton.vue'

defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  close: []
  export: [format: string]
}>()
</script>

<template>
  <BaseModal :open="open" title="导出" width="360px" @close="emit('close')">
    <div class="export-modal__actions">
      <BaseButton variant="secondary" size="md" @click="emit('export', 'markdown')">
        导出 Markdown
      </BaseButton>
      <BaseButton variant="secondary" size="md" @click="emit('export', 'txt')">
        导出 TXT
      </BaseButton>
    </div>
  </BaseModal>
</template>

<style scoped>
.export-modal__actions {
  display: flex;
  gap: var(--space-3);
}
</style>
