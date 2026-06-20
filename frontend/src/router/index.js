import { createRouter, createWebHistory } from 'vue-router'
import HelloWorldView from '../views/HelloWorldView.vue'

const routes = [
  { path: '/', name: 'home', component: HelloWorldView },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// A global navigation guard lives here in the full template (reads useAuth()
// to enforce meta.requiresAuth / guestOnly / permission). This sample has only
// a public route, so the guard is omitted.

export default router
