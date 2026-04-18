<template>
  <div class="space-y-4">
    <div class="flex gap-2 mb-2">
      <button @click="mode = 'graph'" :class="mode === 'graph' ? 'bg-indigo-100 text-indigo-700' : 'text-gray-600'" class="rounded-md px-3 py-1 text-sm">角色关系图</button>
      <button @click="mode = 'timeline'" :class="mode === 'timeline' ? 'bg-indigo-100 text-indigo-700' : 'text-gray-600'" class="rounded-md px-3 py-1 text-sm">情节时间线</button>
    </div>
    <div v-if="topology" ref="chartRef" class="bg-white rounded-lg shadow" style="width:100%;height:500px;"></div>
    <p v-else class="text-gray-500 text-sm p-4">暂无拓扑数据，请先生成设定和大纲。</p>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, nextTick } from 'vue'
import { init, use, type EChartsType } from 'echarts/core'
import { GraphChart, ScatterChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([GraphChart, ScatterChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

const props = defineProps<{ topology: any }>()
const chartRef = ref<HTMLElement>()
const mode = ref('graph')
let chart: EChartsType | null = null

function renderGraph() {
  if (!chartRef.value || !props.topology) return
  if (!chart) chart = init(chartRef.value)

  const nodes = (props.topology.nodes || []).map((n: any) => ({
    id: n.id,
    name: n.label,
    symbolSize: n.type === 'CHARACTER' ? 40 : 20,
    category: n.type === 'CHARACTER' ? 0 : 1,
    itemStyle: { color: n.type === 'CHARACTER' ? '#6366f1' : '#f59e0b' },
  }))

  const edges = (props.topology.edges || []).map((e: any) => ({
    source: e.source,
    target: e.target,
    lineStyle: { color: e.type === 'appearance' ? '#d1d5db' : '#6366f1', width: 1 },
  }))

  chart.setOption({
    tooltip: { trigger: 'item' },
    legend: { data: ['角色', '事件'], top: 10 },
    series: [{
      type: 'graph',
      layout: 'force',
      roam: true,
      draggable: true,
      categories: [{ name: '角色' }, { name: '事件' }],
      data: nodes,
      links: edges,
      force: { repulsion: 200, edgeLength: 120 },
      label: { show: true, fontSize: 11 },
    }],
  }, true)
}

function renderTimeline() {
  if (!chartRef.value || !props.topology) return
  if (!chart) chart = init(chartRef.value)

  const events = (props.topology.nodes || [])
    .filter((n: any) => n.type === 'EVENT')
    .sort((a: any, b: any) => (a.meta?.chapter_index || 0) - (b.meta?.chapter_index || 0))

  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: events.map((e: any) => `第${e.meta?.chapter_index || '?'}章`), axisLabel: { rotate: 30, fontSize: 10 } },
    yAxis: { type: 'value', show: false },
    series: [{
      type: 'scatter',
      symbolSize: 20,
      data: events.map((_: any, i: number) => i + 1),
      label: { show: true, formatter: (p: any) => events[p.dataIndex]?.label || '', position: 'top', fontSize: 10 },
      itemStyle: { color: '#f59e0b' },
    }],
  }, true)
}

watch([mode, () => props.topology], () => {
  nextTick(() => {
    if (mode.value === 'graph') renderGraph()
    else renderTimeline()
  })
})

onMounted(() => {
  nextTick(() => {
    if (props.topology) renderGraph()
  })
})
</script>
