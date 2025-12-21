import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useThemeStore = defineStore('theme', () => {
  // Default to light mode, only switch to dark when manually toggled
  // Read from localStorage if previously saved
  const savedTheme = localStorage.getItem('theme-preference')
  const isDark = ref(savedTheme === 'dark')

  // Apply theme to document
  const applyTheme = () => {
    if (isDark.value) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }

  // Toggle theme action
  const toggleTheme = () => {
    isDark.value = !isDark.value
    localStorage.setItem('theme-preference', isDark.value ? 'dark' : 'light')
    applyTheme()
  }

  // Initialize immediately
  applyTheme()

  return {
    isDark,
    toggleTheme
  }
})
