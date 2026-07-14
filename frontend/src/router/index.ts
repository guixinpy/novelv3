import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

export interface AppRouteMeta {
  showSidebar: boolean
  workspace: 'agent' | 'athena' | 'manuscript' | null
}

declare module 'vue-router' {
  interface RouteMeta extends Partial<AppRouteMeta> {}
}

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('../views/ProjectListView.vue'),
    meta: { showSidebar: false, workspace: null } satisfies AppRouteMeta,
  },
  {
    path: '/projects/:id',
    redirect: (to) => `/projects/${to.params.id}/agent`,
  },
  {
    path: '/projects/:id/agent',
    component: () => import('../views/AgentV2View.vue'),
    meta: { showSidebar: true, workspace: 'agent' } satisfies AppRouteMeta,
  },
  {
    path: '/projects/:id/athena',
    component: () => import('../views/AthenaView.vue'),
    meta: { showSidebar: true, workspace: 'athena' } satisfies AppRouteMeta,
  },
  {
    path: '/projects/:id/athena/:section',
    component: () => import('../views/AthenaView.vue'),
    meta: { showSidebar: true, workspace: 'athena' } satisfies AppRouteMeta,
  },
  {
    path: '/projects/:id/manuscript',
    component: () => import('../views/ManuscriptView.vue'),
    meta: { showSidebar: true, workspace: 'manuscript' } satisfies AppRouteMeta,
  },
  {
    path: '/settings',
    component: () => import('../views/SettingsView.vue'),
    meta: { showSidebar: false, workspace: null } satisfies AppRouteMeta,
  },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
