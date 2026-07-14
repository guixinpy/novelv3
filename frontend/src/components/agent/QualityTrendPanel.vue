<template>
  <div class="quality-trend-panel">
    <div v-if="loading" class="qt-loading">加载中...</div>
    <div v-else-if="error" class="qt-error">{{ error }}</div>
    <div v-else-if="data.trend === 'no_data' || data.trend === 'insufficient_data'" class="qt-empty">
      <span>{{ data.advice }}</span>
    </div>
    <template v-else>
      <!-- 趋势指示器 -->
      <div class="qt-header">
        <span class="qt-label">质量趋势</span>
        <span class="qt-trend-badge" :class="'trend-' + data.trend">{{ trendLabel }}</span>
      </div>

      <!-- SVG 折线图 -->
      <svg class="qt-chart" :viewBox="`0 0 ${chartWidth} ${chartHeight}`" preserveAspectRatio="none">
        <!-- 网格线 -->
        <line v-for="y in gridLines" :key="'g'+y"
          :x1="0" :y1="y" :x2="chartWidth" :y2="y"
          stroke="var(--color-border, #333)" stroke-width="0.5"
        />
        <!-- 折线 -->
        <polyline
          :points="linePoints"
          fill="none"
          :stroke="trendColor"
          stroke-width="2"
          stroke-linejoin="round"
        />
        <!-- 数据点 -->
        <circle
          v-for="(pt, i) in points"
          :key="i"
          :cx="pt.x" :cy="pt.y" r="3"
          :fill="trendColor"
          :opacity="i === points.length - 1 ? 1 : 0.5"
        />
        <!-- X 轴标签 -->
        <text
          v-for="(pt, i) in xLabels"
          :key="'xl'+i"
          :x="pt.x" :y="chartHeight + 12"
          text-anchor="middle" font-size="9" fill="var(--color-text-muted, #666)"
        >{{ pt.label }}</text>
      </svg>

      <!-- 统计 -->
      <div class="qt-stats">
        <div class="qt-stat">
          <span class="qt-stat-val">{{ Math.round(data.first_half_avg) }}</span>
          <span class="qt-stat-label">前半均字</span>
        </div>
        <div class="qt-stat">
          <span class="qt-stat-val">{{ Math.round(data.second_half_avg) }}</span>
          <span class="qt-stat-label">后半均字</span>
        </div>
        <div class="qt-stat">
          <span class="qt-stat-val">{{ Math.round(data.ratio * 100) }}%</span>
          <span class="qt-stat-label">比率</span>
        </div>
      </div>
      <div v-if="data.advice" class="qt-advice" :class="'advice-' + data.trend">{{ data.advice }}</div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

interface TrendData {
  chapters: { chapter_index: number; title: string; word_count: number }[]
  trend: string
  first_half_avg: number
  second_half_avg: number
  ratio: number
  advice: string
}

const props = defineProps<{ projectId: string }>()
const data = ref<TrendData>({ chapters: [], trend: 'no_data', first_half_avg: 0, second_half_avg: 0, ratio: 0, advice: '' })
const loading = ref(true)
const error = ref('')

const CHART_W = 280
const CHART_H = 100
const PAD_L = 4
const PAD_R = 4
const PAD_T = 8
const PAD_B = 18

const chartWidth = computed(() => CHART_W)
const chartHeight = computed(() => CHART_H + PAD_B)

const points = computed(() => {
  const chs = data.value.chapters
  if (chs.length < 2) return []
  const maxW = Math.max(...chs.map(c => c.word_count), 1)
  const w = CHART_W - PAD_L - PAD_R
  const h = CHART_H - PAD_T
  return chs.map((c, i) => ({
    x: PAD_L + (i / Math.max(1, chs.length - 1)) * w,
    y: PAD_T + h - (c.word_count / maxW) * h,
    ...c,
  }))
})

const linePoints = computed(() => points.value.map(p => `${p.x},${p.y}`).join(' '))

const xLabels = computed(() => {
  const pts = points.value
  if (pts.length <= 5) return pts.map(p => ({ x: p.x, label: String(p.chapter_index) }))
  const step = Math.floor(pts.length / 4)
  return [pts[0], ...pts.filter((_, i) => i % step === 0).slice(1), pts[pts.length - 1]]
    .filter((p, i, arr) => arr.indexOf(p) === i)
    .map(p => ({ x: p.x, label: String(p.chapter_index) }))
})

const gridLines = computed(() => {
  const h = CHART_H - PAD_T
  return [PAD_T + h * 0, PAD_T + h * 0.25, PAD_T + h * 0.5, PAD_T + h * 0.75, PAD_T + h * 1]
})

const trendLabel = computed(() => {
  const m: Record<string, string> = { stable: '稳定', growing: '增长', declining: '下滑', severe_decline: '严重下滑' }
  return m[data.value.trend] || data.value.trend
})

const trendColor = computed(() => {
  const m: Record<string, string> = { stable: '#4f8', growing: '#48f', declining: '#fa0', severe_decline: '#f44' }
  return m[data.value.trend] || '#888'
})

onMounted(async () => {
  try {
    const resp = await fetch(`/api/v2/projects/${props.projectId}/quality-trend?window=10`)
    data.value = await resp.json()
  } catch (e: any) {
    error.value = '无法加载趋势数据'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.quality-trend-panel {
  padding: 12px 16px;
  background: var(--color-surface-1, #1a1a2e);
  border-radius: 8px;
  font-size: 13px;
}
.qt-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.qt-label { font-weight: 600; color: var(--color-text, #eee); }
.qt-trend-badge {
  font-size: 11px; padding: 2px 8px; border-radius: 10px; font-weight: 600;
}
.trend-stable { background: #4f82; color: #4f8; }
.trend-growing { background: #48f2; color: #48f; }
.trend-declining { background: #fa02; color: #fa0; }
.trend-severe_decline { background: #f442; color: #f44; }
.qt-chart { width: 100%; height: auto; }
.qt-stats { display: flex; gap: 16px; margin-top: 4px; }
.qt-stat { display: flex; flex-direction: column; align-items: center; }
.qt-stat-val { font-weight: 700; font-size: 16px; color: var(--color-text, #eee); }
.qt-stat-label { font-size: 10px; color: var(--color-text-muted, #666); }
.qt-advice { font-size: 11px; margin-top: 8px; padding: 6px 10px; border-radius: 4px; }
.advice-stable { background: #4f81a; color: #4f8; }
.advice-growing { background: #48f1a; color: #48f; }
.advice-declining { background: #fa01a; color: #fa0; }
.advice-severe_decline { background: #f441a; color: #f44; }
.qt-loading, .qt-error, .qt-empty { color: var(--color-text-muted, #888); }
</style>
