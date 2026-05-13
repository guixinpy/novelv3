<script setup lang="ts">
import { ref } from 'vue'
import type { ContextBlock, PromptBudget } from '../../api/types'
import ContextSourceList from './ContextSourceList.vue'

const props = defineProps<{
  blocks: ContextBlock[]
  budget?: PromptBudget | null
}>()

const expanded = ref<Record<string, boolean>>({})
const previewLimit = 1000

function blockKey(block: ContextBlock, index: number) {
  return `${block.key || 'block'}-${index}`
}

function formatUnknownContent(value: unknown) {
  if (typeof value === 'string') return value
  if (value === null || value === undefined) return ''
  try {
    const serialized = JSON.stringify(value, null, 2)
    return typeof serialized === 'string' ? serialized : ''
  } catch {
    return String(value)
  }
}

function blockContent(block: ContextBlock) {
  return formatUnknownContent(block.content)
}

function isLong(block: ContextBlock) {
  return blockContent(block).length > previewLimit
}

function displayedContent(block: ContextBlock, index: number) {
  const content = blockContent(block)
  if (!isLong(block) || expanded.value[blockKey(block, index)]) return content
  return `${content.slice(0, previewLimit)}...`
}

function toggleBlock(block: ContextBlock, index: number) {
  const key = blockKey(block, index)
  expanded.value = {
    ...expanded.value,
    [key]: !expanded.value[key],
  }
}

function formatOriginalCount(block: ContextBlock) {
  if (block.original_char_count === null || block.original_char_count === undefined) return ''
  return ` / 原始 ${block.original_char_count}`
}

function formatKeyList(keys: string[] | undefined) {
  return keys?.length ? keys.join(', ') : '-'
}

function formatBudgetUsage(budget: PromptBudget) {
  const used = budget.used_context_chars ?? 0
  const max = budget.max_context_chars ?? 0
  return `已注入 ${used} / 上限 ${max} 字`
}
</script>

<template>
  <div class="context-blocks">
    <section v-if="props.budget" class="context-blocks__budget" aria-label="Prompt budget">
      <div class="context-blocks__budget-metrics">
        <span>{{ formatBudgetUsage(props.budget) }}</span>
        <span>剩余 {{ props.budget.remaining_context_chars ?? 0 }} 字</span>
        <span>保留块 {{ props.budget.included_blocks }}</span>
        <span>省略块 {{ props.budget.omitted_blocks }}</span>
      </div>
      <div class="context-blocks__budget-details">
        <div>
          <span>省略块 key</span>
          <strong>{{ formatKeyList(props.budget.omitted_block_keys) }}</strong>
        </div>
        <div>
          <span>截断块</span>
          <strong>{{ formatKeyList(props.budget.truncated_blocks) }}</strong>
        </div>
      </div>
    </section>

    <p v-if="!props.blocks.length" class="context-blocks__empty">无上下文块</p>
    <template v-else>
      <section v-for="(block, index) in props.blocks" :key="blockKey(block, index)" class="context-blocks__item">
        <header class="context-blocks__header">
          <div class="context-blocks__heading">
            <span class="context-blocks__kind">{{ block.kind }}</span>
            <h5>{{ block.title || block.key }}</h5>
          </div>
          <div class="context-blocks__metrics">
            <span>{{ block.char_count }} 字符{{ formatOriginalCount(block) }}</span>
            <span>{{ block.token_estimate }} tokens</span>
            <span v-if="block.truncated" class="context-blocks__truncated">已截断</span>
          </div>
        </header>

        <pre class="context-blocks__content">{{ displayedContent(block, index) }}</pre>
        <button v-if="isLong(block)" type="button" class="context-blocks__toggle" @click="toggleBlock(block, index)">
          {{ expanded[blockKey(block, index)] ? '收起' : '展开全文' }}
        </button>

        <div class="context-blocks__sources">
          <div class="context-blocks__source-title">来源</div>
          <ContextSourceList :sources="block.sources || []" />
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.context-blocks {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.context-blocks__budget {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
  min-width: 0;
  padding: var(--space-3);
}

.context-blocks__budget-metrics {
  color: var(--color-text-primary);
  display: flex;
  flex-wrap: wrap;
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  gap: var(--space-2);
}

.context-blocks__budget-metrics span {
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: var(--space-1) var(--space-2);
}

.context-blocks__budget-details {
  display: grid;
  gap: var(--space-2);
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.context-blocks__budget-details div {
  min-width: 0;
}

.context-blocks__budget-details span {
  color: var(--color-text-tertiary);
  display: block;
  font-size: var(--text-xs);
  margin-bottom: var(--space-1);
}

.context-blocks__budget-details strong {
  color: var(--color-text-primary);
  display: block;
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  overflow-wrap: anywhere;
}

.context-blocks__empty {
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
  margin: 0;
}

.context-blocks__item {
  border-top: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  min-width: 0;
  padding: var(--space-4) 0;
}

.context-blocks__item:first-of-type {
  border-top: 0;
  padding-top: 0;
}

.context-blocks__header {
  display: flex;
  gap: var(--space-3);
  justify-content: space-between;
  min-width: 0;
}

.context-blocks__heading {
  min-width: 0;
}

.context-blocks__kind {
  color: var(--color-brand);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
}

.context-blocks__heading h5 {
  color: var(--color-text-primary);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  line-height: var(--leading-tight);
  margin: var(--space-1) 0 0;
  overflow-wrap: anywhere;
}

.context-blocks__metrics {
  align-items: flex-end;
  color: var(--color-text-secondary);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  font-size: var(--text-xs);
  gap: var(--space-1);
  text-align: right;
}

.context-blocks__truncated {
  color: var(--color-warning);
  font-weight: var(--font-medium);
}

.context-blocks__content {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-primary);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: var(--leading-relaxed);
  margin: 0;
  max-height: 360px;
  overflow: auto;
  padding: var(--space-3);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.context-blocks__toggle {
  align-self: flex-start;
  color: var(--color-brand);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  padding: 0;
}

.context-blocks__toggle:hover {
  color: var(--color-brand-hover);
}

.context-blocks__sources {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  min-width: 0;
}

.context-blocks__source-title {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
}

@media (max-width: 640px) {
  .context-blocks__header {
    flex-direction: column;
  }

  .context-blocks__metrics {
    align-items: flex-start;
    text-align: left;
  }

  .context-blocks__budget-details {
    grid-template-columns: 1fr;
  }
}
</style>
