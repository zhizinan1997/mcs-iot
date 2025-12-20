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


<style>
/* Global overrides for ElMessage to look like macOS */
.el-message {
  background: rgba(255, 255, 255, 0.85) !important;
  backdrop-filter: blur(24px) saturate(180%) !important;
  border: 1px solid rgba(255, 255, 255, 0.6) !important;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.1), 0 4px 12px rgba(0, 0, 0, 0.05) !important;
  border-radius: 16px !important;
  padding: 14px 28px !important;
  min-width: 320px !important;
  top: 32px !important; /* Move it down a bit */
  transform: translateX(-50%) translateY(0) !important;
}

.el-message--success {
  --el-message-bg-color: transparent;
  --el-message-border-color: transparent;
}
.el-message--warning {
  --el-message-bg-color: transparent;
  --el-message-border-color: transparent;
}
.el-message--error {
  --el-message-bg-color: transparent;
  --el-message-border-color: transparent;
}

.el-message .el-message__content {
  color: #1d1d1f !important;
  font-weight: 500 !important;
  font-size: 14px !important;
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, sans-serif !important;
}

.el-message .el-icon {
  font-size: 20px !important;
  margin-right: 12px !important;
}

/* Specific icon colors */
.el-message--success .el-icon { color: #28cd41 !important; }
.el-message--warning .el-icon { color: #ff9f0a !important; }
.el-message--error .el-icon { color: #ff3b30 !important; }
.el-message--info .el-icon { color: #0071e3 !important; }
</style>
