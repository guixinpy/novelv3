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
            :class="{ 'is-active': !!projectId && !isAthenaRoute }"
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
  color: var(--accent-strong);
}

.app-top-nav__link--athena.is-active {
  color: var(--accent-strong);
}
</style>
