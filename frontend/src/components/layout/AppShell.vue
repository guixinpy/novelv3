<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUiStore } from '../../stores/ui'
import { useProjectStore } from '../../stores/project'
import TopBar from './TopBar.vue'
import ActivityBar from './ActivityBar.vue'
import SubNav from './SubNav.vue'
import ContentArea from './ContentArea.vue'

const route = useRoute()
const router = useRouter()
const ui = useUiStore()
const projectStore = useProjectStore()

const showSidebar = computed(() => route.meta.showSidebar === true)
const workspace = computed(() => (route.meta.workspace as string | null) ?? null)

const projectId = computed(() => {
  const id = route.params.id
  return typeof id === 'string' ? id : null
})

const projectName = computed(() => projectStore.currentProject?.name)

const projectList = computed(() =>
  projectStore.projects.map((p: any) => ({ id: String(p.id), title: p.name })),
)

function onSelectProject(id: string) {
  router.push(`/projects/${id}/hermes`)
}

function onNavigateSettings() {
  router.push('/settings')
}

function onActivityNavigate(target: string) {
  router.push(target)
}
</script>

<template>
  <div
    class="app-shell"
    :class="{
      'app-shell--no-sidebar': !showSidebar,
      'app-shell--subnav-collapsed': showSidebar && ui.subNavCollapsed,
    }"
  >
    <TopBar
      :project-name="showSidebar ? projectName : undefined"
      :projects="projectList"
      @select-project="onSelectProject"
      @navigate-settings="onNavigateSettings"
    />
    <template v-if="showSidebar && projectId">
      <ActivityBar
        :active-workspace="(workspace as any)"
        :project-id="projectId"
        @navigate="onActivityNavigate"
      />
      <SubNav
        :collapsed="ui.subNavCollapsed"
        @toggle-collapse="ui.toggleSubNav()"
      >
      </SubNav>
    </template>
    <ContentArea>
      <slot />
    </ContentArea>
  </div>
</template>

<style scoped>
.app-shell {
  display: grid;
  grid-template-rows: var(--topbar-height) 1fr;
  grid-template-columns: var(--activity-bar-width) var(--subnav-width) 1fr;
  grid-template-areas:
    "topbar   topbar   topbar"
    "activity subnav   content";
  height: 100vh;
  overflow: hidden;
}

.app-shell--subnav-collapsed {
  grid-template-columns: var(--activity-bar-width) 0px 1fr;
}

.app-shell--no-sidebar {
  grid-template-columns: 1fr;
  grid-template-areas:
    "topbar"
    "content";
}
</style>
