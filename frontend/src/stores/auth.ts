import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '../api'

export interface UserPermissions {
    dashboard: boolean
    devices: boolean
    instruments: boolean
    alarms: boolean
    logs: boolean
    ai: boolean
    license: boolean
    archive: boolean
    health: boolean
    config: boolean
    screen: boolean
}

export interface UserInfo {
    username: string
    role: string
    permissions: UserPermissions
}

export const useAuthStore = defineStore('auth', () => {
    const token = ref<string | null>(localStorage.getItem('token'))
    const user = ref<UserInfo | null>(null)

    const isLoggedIn = computed(() => !!token.value)
    const isAdmin = computed(() => user.value?.role === 'admin')

    // 检查是否有某个权限
    function hasPermission(key: string): boolean {
        if (!user.value) return false
        // 管理员拥有所有权限
        if (user.value.role === 'admin') return true
        // 特殊处理 admin 权限 - 只有管理员可以
        if (key === 'admin') return false
        // 其他权限根据 permissions 判断
        return user.value.permissions?.[key as keyof UserPermissions] === true
    }

    async function login(username: string, password: string) {
        const res = await authApi.login(username, password)
        token.value = res.data.access_token
        localStorage.setItem('token', res.data.access_token)
        await fetchUser()
        return res.data
    }

    async function fetchUser() {
        if (!token.value) return
        try {
            const res = await authApi.getMe()
            user.value = {
                username: res.data.username,
                role: res.data.role,
                permissions: res.data.permissions || {}
            }
        } catch {
            logout()
        }
    }

    function logout() {
        token.value = null
        user.value = null
        localStorage.removeItem('token')
    }

    return { token, user, isLoggedIn, isAdmin, hasPermission, login, fetchUser, logout }
})
