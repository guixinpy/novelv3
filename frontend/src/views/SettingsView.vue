<template>
  <div>
    <h2>设置</h2>
    <div style="margin-top: 1rem;">
      <label>DeepSeek API Key</label>
      <input v-model="apiKey" type="password" placeholder="sk-..." style="width: 300px;" />
      <button @click="save" style="margin-left: 0.5rem;">保存</button>
    </div>
    <p v-if="saved" style="color: green;">已保存</p>
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
