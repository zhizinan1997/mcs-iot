/**
 * MCS-IOT API 客户端 (Axios API Client)
 * 
 * 该文件封装了前端与后端 RESTful API 的所有通信逻辑。
 * 主要职责：
 * 1. Axios 实例配置：设置基础 URL (/api) 及请求超时时间。
 * 2. 拦截器实现：
 *    - 请求拦截：自动在 Header 中注入 JWT Token 进行身份识别。
 *    - 响应拦截：统一处理 401 错误（Token 过期/无效），自动清理本地缓存并跳转至登录页。
 * 3. 模块化 API 封装：将业务接口按功能领域（Auth, Devices, Alarms, Config 等）进行对象化组织，提供 TS 类型支持。
 */
import axios from 'axios'

// Use relative URL to go through nginx proxy in production
// In dev, this still works because Vite proxy or direct access
const api = axios.create({
    baseURL: '/api',
    timeout: 10000
})

// Request interceptor
api.interceptors.request.use(
    config => {
        const token = localStorage.getItem('token')
        if (token) {
            config.headers.Authorization = `Bearer ${token}`
        }
        return config
    },
    error => Promise.reject(error)
)

// Response interceptor
api.interceptors.response.use(
    response => response,
    error => {
        if (error.response?.status === 401) {
            localStorage.removeItem('token')
            window.location.href = '/login'
        }
        return Promise.reject(error)
    }
)

export default api

// Auth API
export const authApi = {
    login: (username: string, password: string) =>
        api.post('/auth/login', new URLSearchParams({ username, password })),
    getMe: () => api.get('/auth/me')
}

// Devices API
export const devicesApi = {
    list: (page = 1, size = 20) => api.get('/devices', { params: { page, size } }),
    get: (sn: string) => api.get(`/devices/${sn}`),
    create: (data: any) => api.post('/devices', data),
    update: (sn: string, data: any) => api.put(`/devices/${sn}`, data),
    delete: (sn: string) => api.delete(`/devices/${sn}`),
    history: (sn: string, params: any) => api.get(`/devices/${sn}/history`, { params })
}

// Alarms API
export const alarmsApi = {
    list: (params: any) => api.get('/alarms', { params }),
    get: (id: number) => api.get(`/alarms/${id}`),
    ack: (id: number) => api.post(`/alarms/${id}/ack`),
    ackAll: () => api.post('/alarms/ack-all'),
    stats: () => api.get('/alarms/stats/summary')
}

// Config API
export const configApi = {
    getEmail: () => api.get('/config/alarm/email'),
    updateEmail: (data: any) => api.put('/config/alarm/email', data),
    getWebhook: () => api.get('/config/alarm/webhook'),
    updateWebhook: (data: any) => api.put('/config/alarm/webhook', data),
    getDashboard: () => api.get('/config/dashboard'),
    updateDashboard: (data: any) => api.put('/config/dashboard', data),
    testNotification: (channel: string) => api.post('/config/alarm/test', null, { params: { channel } }),
    // MQTT 账号管理
    getMqtt: () => api.get('/config/mqtt'),
    updateMqtt: (data: any) => api.put('/config/mqtt', data),
    reloadMqtt: () => api.post('/config/mqtt/reload'),
    // R2 归档配置
    getArchive: () => api.get('/config/archive'),
    updateArchive: (data: any) => api.put('/config/archive', data),
    testArchive: () => api.post('/config/archive/test'),
    getArchiveStats: () => api.get('/config/archive/stats'),
    listArchiveFiles: () => api.get('/config/archive/files'),
    backupArchive: () => api.post('/config/archive/backup', null, { timeout: 60000 }),
    cleanupData: (days: number) => api.post('/config/archive/cleanup', { days }, { timeout: 60000 }),
    deleteArchiveFile: (key: string) => api.post('/config/archive/delete', { key }),
    // 站点品牌配置
    getSite: () => api.get('/config/site'),
    updateSite: (data: any) => api.put('/config/site', data),
    // 大屏背景配置
    getScreenBg: () => api.get('/config/screen_bg'),
    updateScreenBg: (data: any) => api.put('/config/screen_bg', data),
    // 天气配置
    getWeather: () => api.get('/config/weather'),
    updateWeather: (data: any) => api.put('/config/weather', data),
    // AI 配置
    getAI: () => api.get('/config/ai'),
    updateAI: (data: any) => api.put('/config/ai', data),
    testAI: (data: any) => api.post('/config/ai/test', data),
    getAIHistory: (page = 1, size = 20) => api.get('/config/ai/history', { params: { page, size } }),
    clearAIHistory: () => api.delete('/config/ai/history'),
    // 报警通用配置（消抖时间+报警时段）
    getAlarmGeneral: () => api.get('/config/alarm/general'),
    updateAlarmGeneral: (data: any) => api.put('/config/alarm/general', data),
    // 授权管理
    getLicense: () => api.get('/config/license'),
    verifyLicense: () => api.post('/config/license/verify'),
    // 大屏面板布局配置
    getScreenLayout: () => api.get('/config/screen-layout'),
    updateScreenLayout: (data: any) => api.put('/config/screen-layout', data)
}

// Upload API
export const uploadApi = {
    uploadImage: (file: File) => {
        const formData = new FormData()
        formData.append('file', file)
        return api.post('/uploads', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        })
    }
}

// Dashboard API
export const dashboardApi = {
    stats: () => api.get('/dashboard/stats'),
    realtime: () => api.get('/dashboard/realtime'),
    getAISummary: () => api.get('/ai/summary')
}



// Instruments API
export const instrumentsApi = {
    list: () => api.get('/instruments'),
    get: (id: number) => api.get(`/instruments/${id}`),
    create: (data: any) => api.post('/instruments', data),
    update: (id: number, data: any) => api.put(`/instruments/${id}`, data),
    delete: (id: number) => api.delete(`/instruments/${id}`),
    updatePosition: (id: number, pos_x: number, pos_y: number) =>
        api.patch(`/instruments/${id}/position`, { pos_x, pos_y }),
    history: (id: number, hours = 1) => api.get(`/instruments/${id}/history`, { params: { hours } })
}

// Users API (子账号管理)
export const usersApi = {
    list: () => api.get('/users'),
    get: (id: number) => api.get(`/users/${id}`),
    create: (data: any) => api.post('/users', data),
    update: (id: number, data: any) => api.put(`/users/${id}`, data),
    delete: (id: number) => api.delete(`/users/${id}`),
    changePassword: (id: number, new_password: string) =>
        api.put(`/users/${id}/password`, { new_password }),
    getPermissions: () => api.get('/users/permissions')
}

