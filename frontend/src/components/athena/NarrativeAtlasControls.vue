<script setup lang="ts">
type AtlasLayer = 'trunk' | 'branches' | 'foreshadowing' | 'events'

interface AtlasMetrics {
  chapters: number
  plotlines: number
  foreshadowing: number
  events: number
}

defineProps<{
  layers: Record<AtlasLayer, boolean>
  metrics: AtlasMetrics
}>()

const emit = defineEmits<{
  updateLayer: [layer: AtlasLayer, value: boolean]
}>()

const layerOptions: { key: AtlasLayer; label: string; description: string }[] = [
  { key: 'trunk', label: '章节主干', description: '章节节点与顺序连接' },
  { key: 'branches', label: '故事线枝干', description: '故事线与里程碑' },
  { key: 'foreshadowing', label: '伏笔埋收', description: '伏笔埋设与回收链路' },
  { key: 'events', label: '事件锚点', description: '时间线事件与章节关联' },
]

const metricItems = [
  { key: 'chapters', label: '章节' },
  { key: 'plotlines', label: '故事线' },
  { key: 'foreshadowing', label: '伏笔' },
  { key: 'events', label: '事件' },
] as const

function updateLayer(layer: AtlasLayer, event: Event) {
  emit('updateLayer', layer, Boolean((event.target as HTMLInputElement | null)?.checked))
}
</script>

<template>
  <aside class="narrative-atlas-controls" aria-label="叙事图谱控制">
    <section class="narrative-atlas-controls__section">
      <h2>图层</h2>
      <label
        v-for="option in layerOptions"
        :key="option.key"
        class="narrative-atlas-controls__layer"
      >
        <input
          type="checkbox"
          :checked="layers[option.key]"
          :data-testid="`atlas-layer-${option.key}`"
          @change="updateLayer(option.key, $event)"
        >
        <span>
          <strong>{{ option.label }}</strong>
          <small>{{ option.description }}</small>
        </span>
      </label>
    </section>

    <section class="narrative-atlas-controls__section">
      <h2>指标</h2>
      <div class="narrative-atlas-controls__metrics">
        <div
          v-for="item in metricItems"
          :key="item.key"
          class="narrative-atlas-controls__metric"
          :data-testid="`atlas-metric-${item.key}`"
        >
          <span>{{ item.label }}</span>
          <strong>{{ metrics[item.key] }}</strong>
        </div>
      </div>
    </section>
  </aside>
</template>

<style scoped>
.narrative-atlas-controls {
  min-width: 0;
  overflow: auto;
  padding: var(--space-4);
  border-right: 1px solid var(--color-border);
  background: var(--color-bg-white);
}

.narrative-atlas-controls__section {
  display: grid;
  gap: var(--space-3);
  padding-bottom: var(--space-4);
  margin-bottom: var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.narrative-atlas-controls__section:last-child {
  margin-bottom: 0;
  border-bottom: 0;
}

.narrative-atlas-controls__section h2 {
  color: var(--color-text-primary);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}

.narrative-atlas-controls__layer {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: var(--space-2);
  align-items: start;
  color: var(--color-text-primary);
  cursor: pointer;
}

.narrative-atlas-controls__layer input {
  width: 16px;
  height: 16px;
  margin-top: 2px;
  accent-color: var(--color-brand);
}

.narrative-atlas-controls__layer span {
  display: grid;
  gap: var(--space-1);
}

.narrative-atlas-controls__layer strong {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
}

.narrative-atlas-controls__layer small {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
  line-height: var(--leading-normal);
}

.narrative-atlas-controls__metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
}

.narrative-atlas-controls__metric {
  min-width: 0;
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--color-border);
}

.narrative-atlas-controls__metric span {
  display: block;
  margin-bottom: var(--space-1);
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.narrative-atlas-controls__metric strong {
  color: var(--color-text-primary);
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
}
</style>
