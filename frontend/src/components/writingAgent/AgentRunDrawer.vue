<script setup lang="ts">
import { computed } from 'vue'
import BaseModal from '../base/BaseModal.vue'
import type { WritingAgentRunDetail } from '../../api/types'

const props = defineProps<{
  open: boolean
  loading: boolean
  error: string
  run: WritingAgentRunDetail | null
}>()

const emit = defineEmits<{ close: [] }>()

const steps = computed(() => props.run?.steps || [])

function close() {
  emit('close')
}
</script>

<template>
  <BaseModal
    :open="open"
    title="Agent 运行详情"
    width="720px"
    test-id="agent-run-drawer"
    @close="close"
  >
    <div class="agent-run-drawer">
      <p v-if="loading" class="agent-run-drawer__state">正在加载 Agent 运行详情...</p>
      <p v-else-if="error" class="agent-run-drawer__state agent-run-drawer__state--error">{{ error }}</p>
      <p v-else-if="!run" class="agent-run-drawer__state">暂无运行详情。</p>
      <template v-else>
        <section class="agent-run-drawer__summary">
          <div>
            <span class="agent-run-drawer__eyebrow">目标</span>
            <h4>{{ run.goal }}</h4>
          </div>
          <dl>
            <div>
              <dt>状态</dt>
              <dd>{{ run.status }}</dd>
            </div>
            <div>
              <dt>入口</dt>
              <dd>{{ run.entrypoint }}</dd>
            </div>
            <div>
              <dt>运行 ID</dt>
              <dd>{{ run.id }}</dd>
            </div>
          </dl>
        </section>

        <section class="agent-run-drawer__steps" aria-label="Agent run steps">
          <h4>工具步骤</h4>
          <ol v-if="steps.length">
            <li
              v-for="step in steps"
              :key="step.id"
              class="agent-run-drawer__step"
            >
              <span class="agent-run-drawer__step-index">#{{ step.step_index }}</span>
              <span class="agent-run-drawer__step-tool">{{ step.tool_name }}</span>
              <span class="agent-run-drawer__step-status">{{ step.status }}</span>
            </li>
          </ol>
          <p v-else class="agent-run-drawer__state">暂无工具步骤。</p>
        </section>
      </template>
    </div>
  </BaseModal>
</template>

<style scoped>
.agent-run-drawer {
  display: grid;
  gap: var(--space-4);
}

.agent-run-drawer__state {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

.agent-run-drawer__state--error {
  color: var(--color-error);
}

.agent-run-drawer__summary {
  display: grid;
  gap: var(--space-3);
}

.agent-run-drawer__eyebrow {
  display: block;
  margin-bottom: var(--space-1);
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
}

.agent-run-drawer__summary h4,
.agent-run-drawer__steps h4 {
  margin: 0;
  color: var(--color-text-primary);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
}

.agent-run-drawer__summary dl {
  display: grid;
  gap: var(--space-2);
  margin: 0;
}

.agent-run-drawer__summary dl div {
  display: grid;
  grid-template-columns: 5rem minmax(0, 1fr);
  gap: var(--space-3);
}

.agent-run-drawer__summary dt {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.agent-run-drawer__summary dd {
  margin: 0;
  min-width: 0;
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.agent-run-drawer__steps {
  display: grid;
  gap: var(--space-2);
}

.agent-run-drawer__steps ol {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.agent-run-drawer__step {
  display: grid;
  grid-template-columns: 3rem minmax(0, 1fr) max-content;
  gap: var(--space-2);
  align-items: center;
  padding: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
  font-size: var(--text-xs);
}

.agent-run-drawer__step-index,
.agent-run-drawer__step-status {
  color: var(--color-text-tertiary);
}

.agent-run-drawer__step-tool {
  min-width: 0;
  color: var(--color-text-primary);
  font-weight: var(--font-medium);
  overflow-wrap: anywhere;
}
</style>
