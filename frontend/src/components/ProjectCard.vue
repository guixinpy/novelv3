<template>
  <article :class="['project-card', `project-card--${insight.readinessTone}`]">
    <div class="project-card__head">
      <div class="space-y-3">
        <div class="project-card__topline">
          <span class="project-card__badge">{{ insight.phaseLabel }}</span>
          <span class="project-card__updated">{{ updatedLabel }}</span>
        </div>

        <div class="space-y-2">
          <h3 class="project-card__title">{{ project.name }}</h3>
          <p class="project-card__meta">
            {{ project.genre || '未分类题材' }}
            <span class="project-card__dot" />
            {{ insight.progressLabel }}
          </p>
        </div>
      </div>

      <div class="project-card__actions">
        <router-link :to="`/projects/${project.id}`" class="project-card__link">
          进入工作区
        </router-link>
        <button
          type="button"
          class="project-card__link project-card__link--danger"
          :disabled="deleting"
          @click="$emit('requestDelete', project.id)"
        >
          {{ deleting ? '删除中...' : '删除项目' }}
        </button>
      </div>
    </div>

    <p class="project-card__caption">{{ insight.phaseCaption }}</p>

    <div class="project-card__progress">
      <div class="project-card__progress-track">
        <span class="project-card__progress-fill" :style="{ width: `${insight.progressValue}%` }" />
      </div>
      <div class="project-card__progress-meta">
        <span>推进度</span>
        <span>{{ insight.progressValue }}%</span>
      </div>
    </div>

    <div class="project-card__next-step">
      <p class="project-card__next-eyebrow">建议下一步</p>
      <p class="project-card__next-label">{{ insight.nextStepLabel }}</p>
      <p class="project-card__next-copy">{{ insight.nextStepDetail }}</p>
    </div>

  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { buildProjectInsight, type ProjectListProject } from './list/projectListMeta'

const props = defineProps<{
  project: ProjectListProject
  deleting?: boolean
}>()

defineEmits<{
  requestDelete: [projectId: string]
}>()

const insight = computed(() => buildProjectInsight(props.project))

const updatedLabel = computed(() => {
  const raw = props.project.updated_at
  if (!raw) return '等待推进'
  const updatedAt = new Date(raw).getTime()
  if (Number.isNaN(updatedAt)) return '等待推进'

  const diffHours = Math.max(0, Math.floor((Date.now() - updatedAt) / (1000 * 60 * 60)))
  if (diffHours < 1) return '刚刚整理过'
  if (diffHours < 24) return `${diffHours} 小时前更新`
  const diffDays = Math.floor(diffHours / 24)
  if (diffDays < 7) return `${diffDays} 天前更新`
  return '久未推进'
})
</script>

<style scoped>
.project-card {
  display: grid;
  gap: 1rem;
  min-height: 100%;
  border: 1px solid rgba(111, 69, 31, 0.16);
  border-radius: 1.8rem;
  padding: 1.25rem;
  background:
    linear-gradient(180deg, rgba(255, 251, 244, 0.98) 0%, rgba(247, 241, 230, 0.96) 100%);
  box-shadow:
    0 20px 36px rgba(83, 57, 29, 0.11),
    inset 0 1px 0 rgba(255, 251, 242, 0.82);
  transition:
    transform 180ms ease,
    box-shadow 180ms ease,
    border-color 180ms ease;
}

.project-card:hover {
  transform: translateY(-2px);
  box-shadow:
    0 24px 42px rgba(83, 57, 29, 0.14),
    inset 0 1px 0 rgba(255, 251, 242, 0.82);
}

.project-card--warming {
  border-color: rgba(141, 93, 49, 0.14);
}

.project-card--ready {
  border-color: rgba(141, 93, 49, 0.2);
}

.project-card--urgent {
  border-color: rgba(111, 69, 31, 0.28);
}

.project-card__head {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.project-card__topline {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.65rem;
}

.project-card__badge {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 0.35rem 0.7rem;
  background: rgba(255, 247, 231, 0.9);
  color: var(--accent-strong);
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.project-card__updated,
.project-card__meta,
.project-card__caption,
.project-card__progress-meta,
.project-card__next-eyebrow,
.project-card__next-copy {
  color: var(--ink-muted);
  font-size: 0.9rem;
  line-height: 1.6;
}

.project-card__title {
  color: var(--ink-strong);
  font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif;
  font-size: 1.6rem;
  line-height: 1.08;
}

.project-card__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.45rem;
}

.project-card__dot {
  width: 0.28rem;
  height: 0.28rem;
  border-radius: 999px;
  background: rgba(111, 69, 31, 0.28);
}

.project-card__link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  align-self: flex-start;
  border: 1px solid rgba(111, 69, 31, 0.18);
  border-radius: 1rem;
  padding: 0.78rem 0.95rem;
  background: rgba(255, 248, 234, 0.8);
  color: var(--accent-strong);
  font-size: 0.92rem;
  font-weight: 700;
  text-decoration: none;
  cursor: pointer;
}

.project-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
}

.project-card__link--danger {
  border-color: rgba(137, 65, 48, 0.2);
  background: rgba(252, 241, 237, 0.92);
  color: #8d4c34;
}

.project-card__link:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.project-card__progress-track {
  overflow: hidden;
  height: 0.55rem;
  border-radius: 999px;
  background: rgba(111, 69, 31, 0.12);
}

.project-card__progress-fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, rgba(165, 110, 57, 0.94) 0%, rgba(111, 69, 31, 1) 100%);
}

.project-card__progress-meta {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  margin-top: 0.45rem;
}

.project-card__next-step {
  border: 1px solid rgba(111, 69, 31, 0.1);
  border-radius: 1.2rem;
  padding: 0.95rem 1rem;
  background: rgba(255, 250, 241, 0.76);
}

.project-card__next-eyebrow {
  font-size: 0.76rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.project-card__next-label {
  margin-top: 0.35rem;
  color: var(--ink-strong);
  font-size: 1.02rem;
  font-weight: 700;
  line-height: 1.45;
}

.project-card__next-copy {
  margin-top: 0.35rem;
}

@media (min-width: 768px) {
  .project-card__head {
    flex-direction: row;
    align-items: start;
    justify-content: space-between;
  }

  .project-card__link {
    align-self: stretch;
  }
}
</style>
