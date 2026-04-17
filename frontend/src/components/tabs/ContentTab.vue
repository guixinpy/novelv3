<template>
  <div v-if="chapters.length" class="space-y-2">
    <div v-for="ch in chapters" :key="ch.id" class="bg-white rounded-lg shadow p-3">
      <div class="flex items-center justify-between cursor-pointer" @click="$emit('select-chapter', ch.chapter_index)">
        <h4 class="text-sm font-medium text-gray-900">{{ ch.title }}</h4>
        <div class="flex items-center gap-2">
          <span class="text-xs text-gray-500">{{ ch.word_count }} 字</span>
          <button @click.stop="deepCheck(ch.chapter_index)" :disabled="checking === ch.chapter_index"
            class="text-xs text-indigo-600 hover:text-indigo-800 disabled:opacity-50">
            {{ checking === ch.chapter_index ? '检查中...' : '深度检查' }}
          </button>
        </div>
      </div>
      <div v-if="issuesByChapter[ch.chapter_index]?.length" class="mt-2 space-y-1">
        <div v-for="issue in issuesByChapter[ch.chapter_index]" :key="issue.id || issue.subject"
          class="text-xs px-2 py-1 rounded"
          :class="issue.severity === 'fatal' ? 'bg-red-50 text-red-700' : issue.severity === 'warn' ? 'bg-yellow-50 text-yellow-700' : 'bg-gray-50 text-gray-600'">
          [{{ issue.checker_name }}] {{ issue.description }}
        </div>
      </div>
    </div>
    <div v-if="selectedChapter" class="bg-white rounded-lg shadow p-4 mt-4">
      <h3 class="text-base font-semibold text-gray-900 mb-2">{{ selectedChapter.title }}</h3>
      <div class="prose prose-sm max-w-none text-gray-800 whitespace-pre-wrap">{{ selectedChapter.content }}</div>
    </div>
  </div>
  <p v-else class="text-gray-500 text-sm p-4">暂无章节内容。</p>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { api } from '../../api/client'

const props = defineProps<{ chapters: any[]; selectedChapter: any; projectId: string }>()
defineEmits<{ 'select-chapter': [index: number] }>()

const checking = ref<number | null>(null)
const issuesByChapter = reactive<Record<number, any[]>>({})

async function deepCheck(chapterIndex: number) {
  checking.value = chapterIndex
  try {
    const res = await api.deepCheck(props.projectId, chapterIndex)
    if (res.task_id) {
      // Poll for result
      for (let i = 0; i < 20; i++) {
        await new Promise(r => setTimeout(r, 3000))
        const task = await api.getBackgroundTask(res.task_id)
        if (task.status === 'completed') {
          issuesByChapter[chapterIndex] = task.result?.issues || []
          break
        }
        if (task.status === 'failed') {
          issuesByChapter[chapterIndex] = [{ checker_name: 'Error', description: task.error || '检查失败', severity: 'warn' }]
          break
        }
      }
    } else if (res.issues) {
      issuesByChapter[chapterIndex] = res.issues
    }
  } catch (e: any) {
    issuesByChapter[chapterIndex] = [{ checker_name: 'Error', description: e.message, severity: 'warn' }]
  } finally {
    checking.value = null
  }
}
</script>
