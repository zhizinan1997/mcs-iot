/**
 * MCS-IOT 路由配置管理 (Vue Router Configuration)
 * 
 * 该文件定义了前端应用的所有导航路径及其关联的视图组件。
 * 主要职责：
 * 1. 结构化路由映射：采用嵌套路由设计，将普通管理页面挂载在 MainLayout 下，并将大屏展示页独立出来。
 * 2. 权限元数据定义：通过 meta 属性标记每个页面所需的认证状态 (requiresAuth) 及业务权限标识 (permission)。
 * 3. 路由导航守卫：实现全局登录拦截逻辑，确保未授权用户无法访问受保护的内容。
 * 4. 动态导入：采用懒加载技术（import()），减小首屏资源体积。
 */
import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
    {
        path: '/login',
        name: 'Login',
        component: () => import('../views/login/index.vue'),
        meta: { requiresAuth: false, title: '登录' }
    },
    {
        path: '/',
        component: () => import('../layouts/MainLayout.vue'),
        meta: { requiresAuth: true },
        children: [
            {
                path: '',
                name: 'Dashboard',
                component: () => import('../views/dashboard/index.vue'),
                meta: { title: '仪表盘', permission: 'dashboard' }
            },
            {
                path: 'instruments',
                name: 'Instruments',
                component: () => import('../views/instruments/index.vue'),
                meta: { title: '仪表管理', permission: 'instruments' }
            },
            {
                path: 'devices',
                name: 'Devices',
                component: () => import('../views/devices/index.vue'),
                meta: { title: '传感器管理', permission: 'devices' }
            },
            {
                path: 'alarms',
                name: 'Alarms',
                component: () => import('../views/alarms/index.vue'),
                meta: { title: '报警记录', permission: 'alarms' }
            },
            {
                path: 'ai-config',
                name: 'AIConfig',
                component: () => import('../views/config/AIConfig.vue'),
                meta: { title: 'AI 接口', permission: 'ai' }
            },
            {
                path: 'screen/background',
                name: 'ScreenBackground',
                component: () => import('../views/screen/background.vue'),
                meta: { title: '大屏背景', permission: 'screen' }
            },
            {
                path: 'screen/config',
                name: 'ScreenConfig',
                component: () => import('../views/screen/ScreenConfig.vue'),
                meta: { title: '大屏配置', permission: 'screen' }
            },
            {
                path: 'screen/display',
                name: 'ScreenDisplay',
                component: () => import('../views/screen/ScreenDisplay.vue'),
                meta: { title: '大屏显示管理', permission: 'screen' }
            },
            {
                path: 'screen/weather',
                name: 'ScreenWeather',
                component: () => import('../views/screen/ScreenWeather.vue'),
                meta: { title: '天气设置', permission: 'screen' }
            },
            {
                path: 'logs',
                name: 'ServerLogs',
                component: () => import('../views/serverlogs/index.vue'),
                meta: { title: '服务器日志', permission: 'logs' }
            },
            {
                path: 'license',
                name: 'License',
                component: () => import('../views/license/index.vue'),
                meta: { title: '授权管理', permission: 'license' }
            },
            {
                path: 'archive',
                name: 'Archive',
                component: () => import('../views/archive/index.vue'),
                meta: { title: '数据归档', permission: 'archive' }
            },
            {
                path: 'health-check',
                name: 'HealthCheck',
                component: () => import('../views/health/index.vue'),
                meta: { title: '系统自检', permission: 'health' }
            },
            {
                path: 'users',
                name: 'Users',
                component: () => import('../views/users/index.vue'),
                meta: { title: '子账号管理', permission: 'admin' }
            },
            {
                path: 'config',
                name: 'Config',
                component: () => import('../views/config/index.vue'),
                meta: { title: '系统配置', permission: 'config' }
            }
        ]
    },
    {
        path: '/screen',
        name: 'Screen',
        component: () => import('../views/screen/index.vue'),
        meta: { requiresAuth: true, title: '可视化大屏', permission: 'screen' }
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
