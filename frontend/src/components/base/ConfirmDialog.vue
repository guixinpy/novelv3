<script setup lang="ts">
import BaseModal from './BaseModal.vue'
import BaseButton from './BaseButton.vue'

withDefaults(
  defineProps<{
    open: boolean
    title: string
    message: string
    confirmText?: string
    cancelText?: string
    variant?: 'danger' | 'default'
  }>(),
  { confirmText: '确认', cancelText: '取消', variant: 'default' },
)

const emit = defineEmits<{ confirm: []; cancel: [] }>()
</script>

<template>
  <BaseModal :open="open" :title="title" width="400px" @close="emit('cancel')">
    <p class="confirm-dialog__message">{{ message }}</p>
    <template #footer>
      <BaseButton variant="ghost" size="sm" @click="emit('cancel')">{{ cancelText }}</BaseButton>
      <BaseButton :variant="variant === 'danger' ? 'danger' : 'primary'" size="sm" @click="emit('confirm')">{{ confirmText }}</BaseButton>
    </template>
  </BaseModal>
</template>

<style scoped>
.confirm-dialog__message { font-size: var(--text-sm); color: var(--color-text-secondary); line-height: var(--leading-normal); }
</style>
