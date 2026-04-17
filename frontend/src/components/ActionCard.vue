<template>
  <div class="border border-indigo-200 bg-indigo-50 rounded-lg p-4 mt-2">
    <p class="text-sm text-gray-800 mb-3">{{ action.description }}</p>
    <div class="flex gap-2">
      <button
        @click="$emit('decide', 'confirm')"
        :disabled="disabled"
        class="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
      >
        同意执行
      </button>
      <button
        @click="$emit('decide', 'cancel')"
        :disabled="disabled"
        class="rounded-md bg-white border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
      >
        取消
      </button>
      <button
        @click="showRevise = !showRevise"
        :disabled="disabled"
        class="rounded-md bg-white border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
      >
        修改后再执行
      </button>
    </div>
    <div v-if="showRevise" class="mt-2 flex gap-2">
      <input
        v-model="reviseComment"
        class="flex-1 border border-gray-300 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        placeholder="补充修改说明..."
        @keyup.enter="submitRevise"
      />
      <button
        @click="submitRevise"
        :disabled="disabled || !reviseComment.trim()"
        class="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
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
