<template>
  <div class="bg-white rounded-lg shadow p-4 max-w-xl">
    <h2 class="text-xl font-semibold text-gray-900 mb-4">设置</h2>
    <div class="flex flex-col sm:flex-row sm:items-center gap-3">
      <label class="text-sm font-medium text-gray-700 sm:w-32">DeepSeek API Key</label>
      <input
        v-model="apiKey"
        type="password"
        placeholder="sk-..."
        class="flex-1 border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
      />
      <button
        @click="save"
        class="inline-flex items-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
      >
        保存
      </button>
    </div>
    <p v-if="saved" class="mt-3 text-sm text-green-600">已保存</p>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../api/client'

const apiKey = ref('')
const saved = ref(false)

onMounted(async () => {
  const cfg = await api.getConfig()
  if (cfg.has_api_key) apiKey.value = '********'
})

async function save() {
  await api.updateConfig(apiKey.value)
  saved.value = true
  setTimeout(() => saved.value = false, 2000)
}
</script>
