<template>
  <router-view />
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { configApi } from './api'

// Load site config and update favicon on app start
onMounted(async () => {
  try {
    const res = await configApi.getSite()
    if (res.data) {
      // Update document title
      if (res.data.browser_title) {
        document.title = res.data.browser_title
      }
      // Update favicon
      if (res.data.logo_url) {
        let link = document.querySelector("link[rel~='icon']") as HTMLLinkElement
        if (!link) {
          link = document.createElement('link')
          link.rel = 'icon'
          document.head.appendChild(link)
        }
        link.href = res.data.logo_url
      }
    }
  } catch (e) {
    console.log('Failed to load site config for favicon')
  }
})
</script>
