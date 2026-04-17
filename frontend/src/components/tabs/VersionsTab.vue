<template>
  <div class="space-y-2">
    <div class="flex gap-2 mb-3">
      <select v-model="filter" class="border border-gray-300 rounded-md px-2 py-1 text-sm" @change="$emit('filter', filter)">
        <option value="">全部类型</option>
        <option value="setup">设定</option>
        <option value="storyline">故事线</option>
        <option value="outline">大纲</option>
        <option value="chapter">章节</option>
      </select>
      <button v-if="selected.length === 2" @click="showDiff = true"
        class="rounded-md bg-indigo-600 px-3 py-1 text-xs font-medium text-white hover:bg-indigo-700">
        对比选中 ({{ selected.length }})
      </button>
    </div>
    <div v-if="versions.length" class="space-y-2">
      <div v-for="v in versions" :key="v.id" class="bg-white rounded-lg shadow p-3"
        :class="selected.includes(v.id) ? 'ring-2 ring-indigo-300' : ''">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <input type="checkbox" :value="v.id" v-model="selected" :disabled="selected.length >= 2 && !selected.includes(v.id)" class="rounded" />
            <span class="text-sm font-medium text-gray-900">v{{ v.version_number }}</span>
            <span class="text-xs text-gray-500">{{ labels[v.node_type] || v.node_type }}</span>
            <span class="text-xs text-gray-400">{{ v.author === 'ai_system' ? 'AI' : '用户' }}</span>
          </div>
          <div class="flex gap-1">
            <button @click="$emit('rollback', v.id)" class="text-xs text-indigo-600 hover:text-indigo-800">回滚</button>
            <button @click="$emit('delete-version', v.id)" class="text-xs text-red-500 hover:text-red-700">删除</button>
          </div>
        </div>
        <p v-if="v.description" class="text-xs text-gray-600 mt-1">{{ v.description }}</p>
      </div>
    </div>
    <p v-else class="text-gray-500 text-sm">暂无版本记录。</p>

    <VersionDiff :show="showDiff" :version-a="diffVersionA" :version-b="diffVersionB" @close="showDiff = false" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { api } from '../../api/client'
import VersionDiff from './VersionDiff.vue'

const props = defineProps<{ versions: any[]; projectId: string }>()
defineEmits<{ filter: [type: string]; rollback: [id: string]; 'delete-version': [id: string] }>()

const filter = ref('')
const selected = ref<string[]>([])
const showDiff = ref(false)
const diffVersionA = ref<any>(null)
const diffVersionB = ref<any>(null)
const labels: Record<string, string> = { setup: '设定', storyline: '故事线', outline: '大纲', chapter: '章节' }

watch(showDiff, async (val) => {
  if (val && selected.value.length === 2) {
    const [idA, idB] = selected.value
    diffVersionA.value = await api.getVersion(props.projectId, idA)
    diffVersionB.value = await api.getVersion(props.projectId, idB)
  }
})
</script>
