<template>
  <section class="world-profile-banner" data-testid="world-profile-banner">
    <div>
      <p class="world-profile-banner__eyebrow">世界模型</p>
      <h3 class="world-profile-banner__title">Profile v{{ profile.version }}</h3>
    </div>
    <dl class="world-profile-banner__meta">
      <div>
        <dt>合同</dt>
        <dd>{{ profile.contract_version }}</dd>
      </div>
      <div>
        <dt>题材</dt>
        <dd>{{ genreLabel }}</dd>
      </div>
    </dl>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ProjectProfileVersion } from '../../api/types'

const props = defineProps<{
  profile: ProjectProfileVersion
}>()

const genreLabel = computed(() => {
  const rawValue = props.profile.profile_payload.genre
  return typeof rawValue === 'string' && rawValue.trim() ? rawValue : '未标注'
})
</script>

<style scoped>
.world-profile-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  border: 1px solid rgba(111, 69, 31, 0.18);
  border-radius: 1rem;
  padding: 1rem 1.1rem;
  background:
    linear-gradient(180deg, rgba(252, 249, 241, 0.98) 0%, rgba(243, 233, 217, 0.94) 100%);
  box-shadow:
    0 12px 26px rgba(85, 58, 29, 0.08),
    inset 0 1px 0 rgba(255, 251, 242, 0.88);
}

.world-profile-banner__eyebrow {
  margin: 0;
  color: var(--ink-muted);
  font-size: 0.75rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.world-profile-banner__title {
  margin: 0.15rem 0 0;
  color: var(--accent-strong);
  font-size: 1.05rem;
  font-weight: 700;
}

.world-profile-banner__meta {
  display: grid;
  gap: 0.45rem;
  margin: 0;
  text-align: right;
}

.world-profile-banner__meta dt {
  color: var(--ink-muted);
  font-size: 0.74rem;
}

.world-profile-banner__meta dd {
  margin: 0.1rem 0 0;
  color: var(--ink-strong);
  font-size: 0.82rem;
  font-weight: 600;
}
</style>
