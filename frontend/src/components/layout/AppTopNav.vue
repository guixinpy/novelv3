<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const pageMeta = computed(() => route.matched[route.matched.length - 1]?.meta ?? {})
const navSection = computed(() => (pageMeta.value.navSection === 'settings' ? 'settings' : 'projects'))

const projectId = computed(() => {
  const id = route.params.id
  return typeof id === 'string' ? id : null
})

const isAthenaRoute = computed(() => route.path.endsWith('/athena'))
const isManuscriptRoute = computed(() => route.path.endsWith('/manuscript'))
const isHermesRoute = computed(() => !!projectId.value && !isAthenaRoute.value && !isManuscriptRoute.value)
</script>

<template>
  <header class="app-top-nav">
    <div class="app-top-nav__inner">
      <router-link
        to="/"
        class="app-top-nav__brand"
      >
        <span class="app-top-nav__brand-mark">墨舟</span>
        <span class="app-top-nav__brand-text">创作中枢</span>
      </router-link>
      <nav
        class="app-top-nav__links"
        aria-label="主导航"
      >
        <router-link
          to="/"
          class="app-top-nav__link"
          :class="{ 'is-active': navSection === 'projects' && !projectId }"
        >
          项目
        </router-link>
        <template v-if="projectId">
          <router-link
            :to="`/projects/${projectId}`"
            class="app-top-nav__link app-top-nav__link--hermes"
            :class="{ 'is-active': isHermesRoute }"
          >
            ☿ Hermes
          </router-link>
          <router-link
            :to="`/projects/${projectId}/athena`"
            class="app-top-nav__link app-top-nav__link--athena"
            :class="{ 'is-active': isAthenaRoute }"
          >
            ⏣ Athena
          </router-link>
          <span
            class="app-top-nav__link app-top-nav__link--manuscript"
            title="即将推出"
          >
            📜 Manuscript
          </span>
        </template>
        <router-link
          to="/settings"
          class="app-top-nav__link"
          :class="{ 'is-active': navSection === 'settings' }"
        >
          设置
        </router-link>
      </nav>
    </div>
  </header>
</template>

<style scoped>
.app-top-nav__link--hermes.is-active {
  color: var(--hermes-accent);
  border-color: rgba(196, 85, 58, 0.24);
  background: rgba(196, 85, 58, 0.08);
}

.app-top-nav__link--athena.is-active {
  color: var(--athena-accent);
  border-color: rgba(212, 168, 83, 0.24);
  background: rgba(212, 168, 83, 0.08);
}

.app-top-nav__link--manuscript {
  opacity: 0.4;
  cursor: default;
  pointer-events: none;
  user-select: none;
}
</style>
