import { createRouter, createWebHistory } from 'vue-router'
import ProjectList from '../views/ProjectList.vue'
import ProjectDetail from '../views/ProjectDetail.vue'
import SettingsView from '../views/SettingsView.vue'

const routes = [
  { path: '/', component: ProjectList },
  { path: '/projects/:id', component: ProjectDetail },
  { path: '/settings', component: SettingsView },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
