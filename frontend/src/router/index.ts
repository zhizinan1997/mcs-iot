import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
    {
        path: '/login',
        name: 'Login',
        component: () => import('../views/login/index.vue'),
        meta: { requiresAuth: false }
    },
    {
        path: '/',
        component: () => import('../layouts/MainLayout.vue'),
        meta: { requiresAuth: true },
        children: [
            {
                path: '',
                name: 'Dashboard',
                component: () => import('../views/dashboard/index.vue')
            },
            {
                path: 'devices',
                name: 'Devices',
                component: () => import('../views/devices/index.vue')
            },
            {
                path: 'alarms',
                name: 'Alarms',
                component: () => import('../views/alarms/index.vue')
            },
            {
                path: 'config',
                name: 'Config',
                component: () => import('../views/config/index.vue')
            }
        ]
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

// Navigation guard
router.beforeEach((to, from, next) => {
    const token = localStorage.getItem('token')

    if (to.meta.requiresAuth !== false && !token) {
        next('/login')
    } else if (to.path === '/login' && token) {
        next('/')
    } else {
        next()
    }
})

export default router
