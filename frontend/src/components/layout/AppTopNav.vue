<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const pageMeta = computed(() => route.matched[route.matched.length - 1]?.meta ?? {})
const navSection = computed(() => (pageMeta.value.navSection === 'settings' ? 'settings' : 'projects'))
</script>

<template>
  <header class="app-top-nav">
    <div class="app-top-nav__inner">
      <router-link to="/" class="app-top-nav__brand">
        <span class="app-top-nav__brand-mark">墨舟</span>
        <span class="app-top-nav__brand-text">创作中枢</span>
      </router-link>
      <nav class="app-top-nav__links" aria-label="主导航">
        <router-link to="/" class="app-top-nav__link" :class="{ 'is-active': navSection === 'projects' }">
          项目
        </router-link>
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
