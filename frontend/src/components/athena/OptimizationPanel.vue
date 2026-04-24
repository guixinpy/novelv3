<script setup lang="ts">
import type { AthenaOptimization } from '../../api/types'

defineProps<{
  optimization: AthenaOptimization | null
}>()

function formatConfigKey(key: string) {
  const labels: Record<string, string> = {
    description_density: '描写密度',
    dialogue_ratio: '对话比例',
    pacing_speed: '节奏速度',
    emotional_intensity: '情绪强度',
    tone_preferences: '语气偏好',
  }
  return labels[key] || key
}

function formatConfigValue(value: unknown) {
  if (Array.isArray(value)) return value.join('、') || '无'
  if (value && typeof value === 'object') return JSON.stringify(value)
  return String(value ?? '未设置')
}
</script>

<template>
  <div class="optimization-panel">
    <section class="optimization-panel__section">
      <header class="optimization-panel__header">
        <h3 class="optimization-panel__title">学到的写作规则</h3>
        <span class="optimization-panel__count">{{ optimization?.rules.length || 0 }}</span>
      </header>
      <div v-if="!optimization || optimization.rules.length === 0" class="optimization-panel__empty">
        暂无自优化规则。提交 Manuscript 修订后会在这里看到学习结果。
      </div>
      <article v-for="rule in optimization?.rules || []" :key="rule.id" class="optimization-panel__rule">
        <div class="optimization-panel__rule-condition">{{ rule.condition }}</div>
        <div class="optimization-panel__rule-action">{{ rule.action }}</div>
        <div class="optimization-panel__rule-meta">优先级 {{ rule.priority }} · 命中 {{ rule.hit_count }}</div>
      </article>
    </section>

    <section class="optimization-panel__section">
      <header class="optimization-panel__header">
        <h3 class="optimization-panel__title">当前偏好参数</h3>
      </header>
      <div v-if="!optimization || Object.keys(optimization.style_config).length === 0" class="optimization-panel__empty">
        暂无偏好参数。
      </div>
      <dl v-else class="optimization-panel__config">
        <template v-for="(value, key) in optimization.style_config" :key="key">
          <dt>{{ formatConfigKey(String(key)) }}</dt>
          <dd>{{ formatConfigValue(value) }}</dd>
        </template>
      </dl>
    </section>

    <section class="optimization-panel__section">
      <header class="optimization-panel__header">
        <h3 class="optimization-panel__title">学习日志</h3>
      </header>
      <div v-if="!optimization || optimization.learning_logs.length === 0" class="optimization-panel__empty">
        暂无学习日志。
      </div>
      <ol v-else class="optimization-panel__logs">
        <li v-for="log in optimization.learning_logs" :key="`${log.rule_id}-${log.created_at}`" class="optimization-panel__log">
          <span class="optimization-panel__log-summary">{{ log.summary }}</span>
          <span class="optimization-panel__log-time">{{ log.created_at }}</span>
        </li>
      </ol>
    </section>
  </div>
</template>

<style scoped>
.optimization-panel {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 280px;
  gap: var(--space-4);
}

.optimization-panel__section {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-bg-white);
  overflow: hidden;
}

.optimization-panel__section:first-child {
  grid-row: span 2;
}

.optimization-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-primary);
}

.optimization-panel__title {
  color: var(--color-text-primary);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
}

.optimization-panel__count {
  color: var(--color-brand);
  font-size: var(--text-sm);
}

.optimization-panel__empty {
  padding: var(--space-6);
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
  text-align: center;
}

.optimization-panel__rule {
  padding: var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.optimization-panel__rule:last-child {
  border-bottom: none;
}

.optimization-panel__rule-condition {
  color: var(--color-text-primary);
  font-weight: var(--font-semibold);
}

.optimization-panel__rule-action {
  margin-top: var(--space-2);
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

.optimization-panel__rule-meta {
  margin-top: var(--space-2);
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.optimization-panel__config {
  padding: var(--space-4);
}

.optimization-panel__config dt {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.optimization-panel__config dd {
  margin-bottom: var(--space-3);
  color: var(--color-text-primary);
  font-size: var(--text-sm);
}

.optimization-panel__logs {
  padding: var(--space-4);
}

.optimization-panel__log {
  margin-bottom: var(--space-3);
}

.optimization-panel__log-summary,
.optimization-panel__log-time {
  display: block;
}

.optimization-panel__log-summary {
  color: var(--color-text-primary);
  font-size: var(--text-sm);
}

.optimization-panel__log-time {
  margin-top: var(--space-1);
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}
</style>
