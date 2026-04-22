import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import ProjectList from '../views/ProjectList.vue'
import ProjectDetail from '../views/ProjectDetail.vue'
import AthenaView from '../views/AthenaView.vue'
import SettingsView from '../views/SettingsView.vue'

type ShellMode = 'default' | 'workspace'
type ShellSurface = 'panel' | 'none'
type NavSection = 'projects' | 'settings'

type AppRouteMeta = {
  shellMode: ShellMode
  shellSurface: ShellSurface
  navSection: NavSection
}

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: ProjectList,
    meta: {
      shellMode: 'default',
      shellSurface: 'panel',
      navSection: 'projects',
    } satisfies AppRouteMeta,
  },
  {
    path: '/projects/:id',
    component: ProjectDetail,
    meta: {
      shellMode: 'workspace',
      shellSurface: 'none',
      navSection: 'projects',
    } satisfies AppRouteMeta,
  },
  {
    path: '/projects/:id/athena',
    component: AthenaView,
    meta: {
      shellMode: 'default',
      shellSurface: 'none',
      navSection: 'projects',
    } satisfies AppRouteMeta,
  },
  {
    path: '/settings',
    component: SettingsView,
    meta: {
      shellMode: 'default',
      shellSurface: 'panel',
      navSection: 'settings',
    } satisfies AppRouteMeta,
  },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
