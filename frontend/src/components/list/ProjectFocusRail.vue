<template>
  <aside class="focus-rail">
    <section class="focus-rail__panel">
      <div class="focus-rail__panel-head">
        <p class="focus-rail__eyebrow">创作概况</p>
        <h2 class="focus-rail__title">先推进最接近成形的项目。</h2>
      </div>

      <div class="focus-rail__stats">
        <article class="focus-rail__stat">
          <span class="focus-rail__stat-value">{{ summary.totalProjects }}</span>
          <span class="focus-rail__stat-label">项目总数</span>
        </article>
        <article class="focus-rail__stat">
          <span class="focus-rail__stat-value">{{ summary.writingProjects }}</span>
          <span class="focus-rail__stat-label">正文推进中</span>
        </article>
        <article class="focus-rail__stat">
          <span class="focus-rail__stat-value">{{ summary.totalWords.toLocaleString('zh-CN') }}</span>
          <span class="focus-rail__stat-label">累计字数</span>
        </article>
      </div>

      <p class="focus-rail__summary">{{ summary.pendingLabel }}</p>
    </section>

    <section class="focus-rail__panel focus-rail__panel--focus">
      <div class="focus-rail__panel-head">
        <p class="focus-rail__eyebrow">下一步推荐</p>
        <h2 class="focus-rail__title">
          {{ focusProject ? `继续 ${focusProject.name}` : '先创建一个项目' }}
        </h2>
      </div>

      <template v-if="focusProject && focusInsight">
        <p class="focus-rail__focus-meta">
          {{ focusProject.genre || '未分类题材' }} · {{ focusInsight.phaseLabel }}
        </p>
        <p class="focus-rail__focus-next">{{ focusInsight.nextStepLabel }}</p>
        <p class="focus-rail__focus-copy">{{ focusInsight.nextStepDetail }}</p>

        <div class="focus-rail__progress">
          <div class="focus-rail__progress-track">
            <span class="focus-rail__progress-fill" :style="{ width: `${focusInsight.progressValue}%` }" />
          </div>
          <div class="focus-rail__progress-meta">
            <span>{{ focusInsight.progressLabel }}</span>
            <span>{{ focusInsight.progressValue }}%</span>
          </div>
        </div>

        <router-link :to="`/projects/${focusProject.id}`" class="focus-rail__cta">
          进入工作区
        </router-link>
      </template>

      <template v-else>
        <p class="focus-rail__focus-copy">
          矩阵为空。先创建一个项目，把设定、故事线和大纲拉进同一套工作流里。
        </p>
      </template>
    </section>
  </aside>
</template>

<script setup lang="ts">
import type { ProjectInsight, ProjectListProject, ProjectPortfolioSummary } from './projectListMeta'

defineProps<{
  summary: ProjectPortfolioSummary
  focusProject?: ProjectListProject
  focusInsight?: ProjectInsight
}>()
</script>

<style scoped>
.focus-rail {
  display: grid;
  gap: 1rem;
}

.focus-rail__panel {
  border: 1px solid rgba(111, 69, 31, 0.15);
  border-radius: 1.7rem;
  padding: 1.2rem;
  background:
    linear-gradient(180deg, rgba(252, 248, 239, 0.96) 0%, rgba(246, 240, 228, 0.96) 100%);
  box-shadow:
    0 18px 32px rgba(83, 57, 29, 0.1),
    inset 0 1px 0 rgba(255, 250, 239, 0.8);
}

.focus-rail__panel--focus {
  background:
    linear-gradient(180deg, rgba(255, 250, 240, 0.98) 0%, rgba(241, 232, 215, 0.94) 100%);
}

.focus-rail__panel-head {
  display: grid;
  gap: 0.45rem;
}

.focus-rail__eyebrow {
  color: var(--accent-strong);
  font-size: 0.73rem;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.focus-rail__title {
  color: var(--ink-strong);
  font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif;
  font-size: 1.55rem;
  line-height: 1.1;
}

.focus-rail__stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
  margin-top: 1rem;
}

.focus-rail__stat {
  display: grid;
  gap: 0.25rem;
  border-radius: 1.2rem;
  padding: 0.85rem 0.9rem;
  background: rgba(255, 249, 237, 0.76);
}

.focus-rail__stat-value {
  color: var(--ink-strong);
  font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif;
  font-size: 1.4rem;
}

.focus-rail__stat-label,
.focus-rail__summary,
.focus-rail__focus-meta,
.focus-rail__focus-copy,
.focus-rail__progress-meta {
  color: var(--ink-muted);
  font-size: 0.88rem;
  line-height: 1.55;
}

.focus-rail__summary {
  margin-top: 1rem;
}

.focus-rail__focus-meta {
  margin-top: 0.9rem;
}

.focus-rail__focus-next {
  margin-top: 0.5rem;
  color: var(--ink-strong);
  font-size: 1.15rem;
  font-weight: 700;
  line-height: 1.35;
}

.focus-rail__focus-copy {
  margin-top: 0.55rem;
}

.focus-rail__progress {
  margin-top: 1rem;
}

.focus-rail__progress-track {
  overflow: hidden;
  height: 0.55rem;
  border-radius: 999px;
  background: rgba(111, 69, 31, 0.12);
}

.focus-rail__progress-fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, rgba(150, 101, 55, 0.96) 0%, rgba(112, 72, 34, 1) 100%);
}

.focus-rail__progress-meta {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  margin-top: 0.5rem;
}

.focus-rail__cta {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-top: 1rem;
  border: 1px solid rgba(111, 69, 31, 0.18);
  border-radius: 1rem;
  padding: 0.8rem 1rem;
  background: rgba(255, 248, 232, 0.86);
  color: var(--accent-strong);
  font-size: 0.95rem;
  font-weight: 700;
  text-decoration: none;
  transition:
    transform 180ms ease,
    box-shadow 180ms ease;
}

.focus-rail__cta:hover {
  transform: translateY(-1px);
  box-shadow: 0 14px 22px rgba(82, 55, 27, 0.12);
}

@media (min-width: 1280px) {
  .focus-rail {
    position: sticky;
    top: 5.5rem;
  }
}

@media (min-width: 640px) {
  .focus-rail__stats {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
</style>
