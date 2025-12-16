import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '../api'

export const useAuthStore = defineStore('auth', () => {
    const token = ref<string | null>(localStorage.getItem('token'))
    const user = ref<{ username: string; role: string } | null>(null)

    const isLoggedIn = computed(() => !!token.value)

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
            user.value = res.data
        } catch {
            logout()
        }
    }

    function logout() {
        token.value = null
        user.value = null
        localStorage.removeItem('token')
    }

    return { token, user, isLoggedIn, login, fetchUser, logout }
})
