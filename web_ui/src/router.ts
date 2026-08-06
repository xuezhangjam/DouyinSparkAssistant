import { createRouter, createWebHashHistory } from 'vue-router'
import Dashboard from './components/Dashboard.vue'

const routes = [
  { path: '/', component: Dashboard },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

export default router
