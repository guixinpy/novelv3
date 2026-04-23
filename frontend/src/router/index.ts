import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import ProjectListView from '../views/ProjectListView.vue'
import HermesView from '../views/HermesView.vue'
import AthenaView from '../views/AthenaView.vue'
import ManuscriptView from '../views/ManuscriptView.vue'
import SettingsView from '../views/SettingsView.vue'

export interface AppRouteMeta {
  showSidebar: boolean
  workspace: 'hermes' | 'athena' | 'manuscript' | null
}

declare module 'vue-router' {
  interface RouteMeta extends Partial<AppRouteMeta> {}
}

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: ProjectListView,
    meta: { showSidebar: false, workspace: null } satisfies AppRouteMeta,
  },
  {
    path: '/projects/:id',
    redirect: (to) => `/projects/${to.params.id}/hermes`,
  },
  {
    path: '/projects/:id/hermes',
    component: HermesView,
    meta: { showSidebar: true, workspace: 'hermes' } satisfies AppRouteMeta,
  },
  {
    path: '/projects/:id/athena',
    component: AthenaView,
    meta: { showSidebar: true, workspace: 'athena' } satisfies AppRouteMeta,
  },
  {
    path: '/projects/:id/athena/:section',
    component: AthenaView,
    meta: { showSidebar: true, workspace: 'athena' } satisfies AppRouteMeta,
  },
  {
    path: '/projects/:id/manuscript',
    component: ManuscriptView,
    meta: { showSidebar: true, workspace: 'manuscript' } satisfies AppRouteMeta,
  },
  {
    path: '/settings',
    component: SettingsView,
    meta: { showSidebar: false, workspace: null } satisfies AppRouteMeta,
  },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
