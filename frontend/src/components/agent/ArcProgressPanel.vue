<template>
  <div class="arc-progress-panel">
    <div v-if="loading" class="arc-loading">加载中...</div>
    <div v-else-if="error" class="arc-error">{{ error }}</div>
    <div v-else-if="!data.has_active_arc" class="arc-empty">
      <span class="arc-empty-icon">📋</span>
      <span>暂无活跃弧线 — 开始写作前请先规划弧线</span>
    </div>
    <template v-else>
      <!-- 当前活跃弧线进度条 -->
      <div class="arc-current">
        <div class="arc-header">
          <span class="arc-title">{{ data.arc_title }}</span>
          <span class="arc-chapters">{{ data.written }}/{{ data.total }} 章</span>
        </div>
        <div class="arc-bar-track">
          <div class="arc-bar-fill" :style="{ width: data.percent + '%' }" :class="barColor"></div>
        </div>
        <div class="arc-meta">
          <span class="arc-percent">{{ data.percent }}%</span>
          <span v-if="data.remaining > 0 && data.remaining <= 3" class="arc-warning">⚠ 还剩 {{ data.remaining }} 章 — 请规划下一弧线</span>
          <span v-else-if="data.remaining > 0" class="arc-hint">还剩 {{ data.remaining }} 章</span>
          <span v-else class="arc-done">✅ 弧线完成</span>
        </div>
      </div>

      <!-- 所有弧线时间轴 -->
      <div v-if="data.all_arcs.length > 1" class="arc-timeline">
        <div class="arc-timeline-title">弧线时间轴</div>
        <div
          v-for="arc in data.all_arcs"
          :key="arc.title"
          class="arc-timeline-item"
          :class="{ active: arc.status === 'active', completed: arc.status === 'completed' }"
        >
          <div class="arc-timeline-dot"></div>
          <div class="arc-timeline-content">
            <div class="arc-timeline-name">{{ arc.title }}</div>
            <div class="arc-timeline-meta">
              {{ arc.span }} · {{ arc.chapters }}/{{ arc.total }} 章
              <span v-if="arc.status === 'completed'">✅</span>
              <span v-else-if="arc.status === 'active'">●</span>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

interface ArcData {
  has_active_arc: boolean
  arc_title: string
  span: string
  written: number
  total: number
  remaining: number
  percent: number
  warning: string
  all_arcs: { title: string; span: string; status: string; chapters: number; total: number }[]
}

const props = defineProps<{ projectId: string }>()
const data = ref<ArcData>({ has_active_arc: false, arc_title: '', span: '', written: 0, total: 0, remaining: 0, percent: 0, warning: '', all_arcs: [] })
const loading = ref(true)
const error = ref('')

const barColor = computed(() => {
  if (data.value.percent >= 90) return 'bar-warning'
  if (data.value.percent >= 50) return 'bar-mid'
  return 'bar-early'
})

onMounted(async () => {
  try {
    const resp = await fetch(`/api/v2/projects/${props.projectId}/arc-progress`)
    data.value = await resp.json()
  } catch (e: any) {
    error.value = '无法加载弧线数据'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.arc-progress-panel {
  padding: 12px 16px;
  background: var(--color-surface-1, #1a1a2e);
  border-radius: 8px;
  font-size: 13px;
}
.arc-loading, .arc-error, .arc-empty {
  color: var(--color-text-muted, #888);
  display: flex; align-items: center; gap: 8px;
}
.arc-current { margin-bottom: 12px; }
.arc-header {
  display: flex; justify-content: space-between; align-items: baseline;
  margin-bottom: 6px;
}
.arc-title { font-weight: 600; color: var(--color-text, #eee); }
.arc-chapters { color: var(--color-text-muted, #888); font-size: 12px; }
.arc-bar-track {
  height: 6px; background: var(--color-surface-3, #333);
  border-radius: 3px; overflow: hidden; margin-bottom: 6px;
}
.arc-bar-fill {
  height: 100%; border-radius: 3px; transition: width 0.5s ease;
}
.bar-early { background: var(--color-primary, #4f8); }
.bar-mid { background: var(--color-warning, #fa0); }
.bar-warning { background: var(--color-danger, #f44); }
.arc-meta { display: flex; gap: 12px; font-size: 12px; }
.arc-percent { font-weight: 600; color: var(--color-text, #ddd); }
.arc-warning { color: var(--color-danger, #f44); }
.arc-hint { color: var(--color-text-muted, #888); }
.arc-done { color: var(--color-primary, #4f8); }
.arc-timeline { margin-top: 12px; border-top: 1px solid var(--color-border, #333); padding-top: 12px; }
.arc-timeline-title { font-size: 11px; text-transform: uppercase; color: var(--color-text-muted, #666); margin-bottom: 8px; }
.arc-timeline-item {
  display: flex; gap: 10px; padding: 4px 0; align-items: flex-start;
}
.arc-timeline-dot {
  width: 8px; height: 8px; border-radius: 50%; margin-top: 4px;
  flex-shrink: 0; background: var(--color-surface-3, #555);
}
.arc-timeline-item.active .arc-timeline-dot { background: var(--color-primary, #4f8); }
.arc-timeline-item.completed .arc-timeline-dot { background: var(--color-success, #4a4); }
.arc-timeline-name { font-size: 13px; color: var(--color-text, #ddd); }
.arc-timeline-meta { font-size: 11px; color: var(--color-text-muted, #777); }
</style>
