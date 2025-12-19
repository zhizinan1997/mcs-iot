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
                path: 'instruments',
                name: 'Instruments',
                component: () => import('../views/instruments/index.vue')
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
                path: 'ai-config',
                name: 'AIConfig',
                component: () => import('../views/config/AIConfig.vue')
            },
            {
                path: 'config',
                name: 'Config',
                component: () => import('../views/config/index.vue')
            },
            {
                path: 'screen/background',
                name: 'ScreenBackground',
                component: () => import('../views/screen/background.vue')
            },
            {
                path: 'license',
                name: 'License',
                component: () => import('../views/license/index.vue')
            }
        ]
    },
    {
        path: '/screen',
        name: 'Screen',
        component: () => import('../views/screen/index.vue'),
        meta: { requiresAuth: true }
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

// Navigation guard
router.beforeEach((to, _from, next) => {
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
