<template>
  <el-container class="layout-container">
    <!-- Sidebar -->
    <el-aside width="220px" class="sidebar">
      <div class="logo">
        <img v-if="siteConfig.logo_url" :src="siteConfig.logo_url" class="logo-img" alt="Logo" />
        <h2 v-if="!siteConfig.logo_url || siteConfig.site_name">{{ siteConfig.site_name }}</h2>
      </div>
      
      <el-menu
        :default-active="route.path"
        router
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
      >
        <el-menu-item index="/">
          <el-icon><DataBoard /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/instruments">
          <el-icon><Odometer /></el-icon>
          <span>仪表管理</span>
        </el-menu-item>
        <el-menu-item index="/devices">
          <el-icon><Monitor /></el-icon>
          <span>传感器管理</span>
        </el-menu-item>
        <el-menu-item index="/alarms">
          <el-icon><Bell /></el-icon>
          <span>报警记录</span>
        </el-menu-item>
        <el-menu-item index="/config">
          <el-icon><Setting /></el-icon>
          <span>系统配置</span>
        </el-menu-item>
        <el-divider />
        <el-sub-menu index="/screen-group">
          <template #title>
            <el-icon><FullScreen /></el-icon>
            <span>可视化大屏</span>
          </template>
          <el-menu-item index="/screen">
            <el-icon><Monitor /></el-icon>
            <span>大屏显示</span>
          </el-menu-item>
          <el-menu-item index="/screen/background">
            <el-icon><Picture /></el-icon>
            <span>背景设置</span>
          </el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-aside>
    
    <!-- Main Content -->
    <el-container>
      <!-- Header -->
      <el-header class="header">
        <div class="header-left">
          <div class="header-logo" v-if="siteConfig.logo_url">
             <img :src="siteConfig.logo_url" class="header-logo-img" alt="Logo" />
          </div>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item>{{ route.name }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        
        <div class="header-right">
          <el-dropdown>
            <span class="user-info">
              <el-avatar size="small" icon="User" />
              <span class="username">{{ authStore.user?.username || 'Admin' }}</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="handleLogout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      
      <!-- Page Content -->
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { configApi } from '../api'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const siteConfig = ref({
  site_name: "MCS-IoT",
  logo_url: "",
  browser_title: ""
})

async function loadSiteConfig() {
  try {
    const res = await configApi.getSite()
    if (res.data) {
      siteConfig.value = { ...siteConfig.value, ...res.data }
      if (siteConfig.value.browser_title) {
        document.title = siteConfig.value.browser_title
      }
      // Update favicon if logo_url is set
      if (siteConfig.value.logo_url) {
        updateFavicon(siteConfig.value.logo_url)
      }
    }
  } catch (error) {
    console.error("Failed to load site config")
  }
}

function updateFavicon(url: string) {
  let link = document.querySelector("link[rel~='icon']") as HTMLLinkElement
  if (!link) {
    link = document.createElement('link')
    link.rel = 'icon'
    document.head.appendChild(link)
  }
  link.href = url
}

onMounted(() => {
  loadSiteConfig()
})

function handleLogout() {
  authStore.logout()
  ElMessage.success('已退出登录')
  router.push('/login')
}
</script>

<style scoped>
.layout-container {
  min-height: 100vh;
}

.sidebar {
  background-color: #304156;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #263445;
  gap: 10px;
  padding: 0 10px;
}

.logo-img {
  height: 32px;
  width: auto;
}

.logo h2 {
  color: #fff;
  margin: 0;
  font-size: 18px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.header {
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.1);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-logo-img {
  height: 24px;
  width: auto;
}

.header-right {
  display: flex;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.username {
  color: #606266;
}

.main-content {
  background-color: #f5f7fa;
  padding: 20px;
}
</style>
