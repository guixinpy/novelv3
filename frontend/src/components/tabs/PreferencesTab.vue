<template>
  <div class="space-y-4">
    <div class="bg-white rounded-lg shadow p-4">
      <h4 class="text-sm font-semibold text-gray-700 mb-3">写作偏好</h4>
      <div class="space-y-4">
        <div>
          <label class="text-xs text-gray-600 block mb-1">描写密度 ({{ config.description_density }})</label>
          <input type="range" min="1" max="5" v-model.number="config.description_density" class="w-full" />
          <div class="flex justify-between text-xs text-gray-400"><span>极简</span><span>极繁</span></div>
        </div>
        <div>
          <label class="text-xs text-gray-600 block mb-1">对话比例 ({{ config.dialogue_ratio }})</label>
          <input type="range" min="1" max="5" v-model.number="config.dialogue_ratio" class="w-full" />
          <div class="flex justify-between text-xs text-gray-400"><span>叙述为主</span><span>对话为主</span></div>
        </div>
        <div>
          <label class="text-xs text-gray-600 block mb-1">节奏快慢 ({{ config.pacing_speed }})</label>
          <input type="range" min="1" max="5" v-model.number="config.pacing_speed" class="w-full" />
          <div class="flex justify-between text-xs text-gray-400"><span>慢热铺垫</span><span>快节奏</span></div>
        </div>
        <div>
          <label class="text-xs text-gray-600 block mb-1">基调偏好</label>
          <div class="flex flex-wrap gap-2">
            <label v-for="t in toneOptions" :key="t.value" class="flex items-center gap-1 text-xs">
              <input type="checkbox" :value="t.value" v-model="config.tone_preferences" class="rounded" />
              {{ t.label }}
            </label>
          </div>
        </div>
      </div>
      <div class="flex gap-2 mt-4">
        <button @click="save" :disabled="saving" class="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">保存</button>
        <button @click="reset" class="rounded-md bg-white border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50">重置默认</button>
      </div>
      <p v-if="saved" class="text-xs text-green-600 mt-2">已保存</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { api } from '../../api/client'

const props = defineProps<{ projectId: string }>()
const config = reactive({ description_density: 3, dialogue_ratio: 3, pacing_speed: 3, tone_preferences: [] as string[] })
const saving = ref(false)
const saved = ref(false)

const toneOptions = [
  { value: 'dark', label: '压抑沉重' },
  { value: 'realistic', label: '写实' },
  { value: 'light', label: '轻松明快' },
  { value: 'suspense', label: '悬疑' },
]

onMounted(async () => {
  const res = await api.getPreferences(props.projectId)
  Object.assign(config, res.config)
})

async function save() {
  saving.value = true
  saved.value = false
  await api.updatePreferences(props.projectId, { ...config })
  saving.value = false
  saved.value = true
  setTimeout(() => saved.value = false, 2000)
}

async function reset() {
  const res = await api.resetPreferences(props.projectId)
  Object.assign(config, res.config)
}
</script>
