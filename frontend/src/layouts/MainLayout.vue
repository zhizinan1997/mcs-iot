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
        <el-menu-item index="/ai-config">
          <el-icon><Cpu /></el-icon>
          <span>AI 接口</span>
        </el-menu-item>
        <el-menu-item index="/license">
          <el-icon><Key /></el-icon>
          <span>授权管理</span>
        </el-menu-item>
        <el-menu-item index="/config">
          <el-icon><Setting /></el-icon>
          <span>系统配置</span>
        </el-menu-item>
        <el-menu-item index="/health-check">
          <el-icon><FirstAidKit /></el-icon>
          <span>系统自检</span>
        </el-menu-item>
        <el-menu-item index="/archive">
          <el-icon><Folder /></el-icon>
          <span>数据归档</span>
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
          <el-menu-item index="/screen/config">
            <el-icon><Setting /></el-icon>
            <span>大屏配置</span>
          </el-menu-item>
          <el-menu-item index="/screen/display">
            <el-icon><Grid /></el-icon>
            <span>显示管理</span>
          </el-menu-item>
          <el-menu-item index="/screen/weather">
            <el-icon><Cloudy /></el-icon>
            <span>天气设置</span>
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
          <!-- License Status -->
          <el-tag 
            :type="licenseStatus.status === 'active' ? 'success' : licenseStatus.status === 'grace' ? 'warning' : 'danger'"
            class="license-tag"
            v-if="licenseStatus.status"
          >
            <template v-if="licenseStatus.status === 'active'">
              已授权 {{ licenseStatus.expires ? `(到期: ${licenseStatus.expires})` : '' }}
            </template>
            <template v-else-if="licenseStatus.status === 'grace'">
              宽限期 (剩余 {{ licenseStatus.grace_remaining_days || 0 }} 天)
            </template>
            <template v-else>
              未授权
            </template>
          </el-tag>

          <!-- Tampering Warning Badge -->
          <el-tag 
            type="danger"
            effect="dark"
            class="tamper-warning-tag"
            v-if="licenseStatus.tampered"
          >
            <el-icon><WarningFilled /></el-icon> 检测到代码篡改
          </el-tag>

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
import { WarningFilled } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const siteConfig = ref({
  site_name: "MCS-IoT",
  logo_url: "",
  browser_title: ""
})

const licenseStatus = ref<any>({
  status: '',
  expires: '',
  grace_remaining_days: 0,
  tampered: false
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
  loadLicenseStatus()
})

async function loadLicenseStatus() {
  try {
    const res = await configApi.getLicense()
    if (res.data) {
      licenseStatus.value = {
        status: res.data.status || 'unlicensed',
        expires: res.data.expires_at ? res.data.expires_at.split('T')[0] : '',
        grace_remaining_days: res.data.grace_remaining_days || 0
      }
    }
  } catch (error) {
    console.error("Failed to load license status")
  }
}

function handleLogout() {
  authStore.logout()
  ElMessage.success('已退出登录')
  router.push('/login')
}
</script>

<style scoped>
/* Global Font Stack for Apple Feel */
.layout-container {
  min-height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", Helvetica, Arial, sans-serif;
  background-color: #f5f5f7; /* Apple's standard light gray background */
}

/* Glassmorphism Sidebar - Darker for Contrast */
.sidebar {
  background-color: rgba(235, 235, 240, 0.85) !important; /* Darker gray frosted glass */
  backdrop-filter: blur(20px) saturate(180%);
  border-right: 1px solid rgba(0, 0, 0, 0.08); /* Stronger border */
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.logo {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: transparent;
  gap: 12px;
  padding: 0 16px;
  /* border-bottom: 1px solid rgba(0, 0, 0, 0.05); Remove border for cleaner look */
}

.logo-img {
  height: 32px;
  width: auto;
}

.logo h2 {
  color: #1d1d1f;
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  letter-spacing: -0.01em;
}

/* Apple-style Menu Items */
:deep(.el-menu) {
  border-right: none;
  background-color: transparent !important;
  padding: 12px;
}

:deep(.el-menu-item), :deep(.el-sub-menu__title) {
  height: 48px;
  line-height: 48px;
  margin: 4px 0;
  border-radius: 12px; /* Smoother rounding */
  color: #48484a; /* Darker gray text */
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
}

:deep(.el-menu-item:hover), :deep(.el-sub-menu__title:hover) {
  background-color: rgba(0, 0, 0, 0.05) !important;
  color: #1d1d1f;
}

:deep(.el-menu-item.is-active) {
  background-color: #0071e3 !important;
  color: #ffffff !important;
  box-shadow: 0 4px 12px rgba(0, 113, 227, 0.3); /* Stronger shadow */
  font-weight: 600;
}

:deep(.el-icon) {
  font-size: 20px;
  margin-right: 12px;
  vertical-align: middle;
}

/* Glassmorphism Header */
.header {
  background: rgba(255, 255, 255, 0.8); /* Whiter header for contrast against gray sidebar */
  backdrop-filter: blur(20px) saturate(180%);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  position: sticky;
  top: 0;
  z-index: 100;
  height: 64px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

/* Breadcrumb Styling */
:deep(.el-breadcrumb__inner) {
  color: #86868b !important;
  font-weight: 500;
}

:deep(.el-breadcrumb__inner.is-link:hover) {
  color: #0071e3 !important;
}

:deep(.el-breadcrumb__item:last-child .el-breadcrumb__inner) {
  color: #1d1d1f !important;
  font-weight: 600;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.license-tag {
  font-size: 13px;
  border-radius: 14px;
  padding: 4px 12px;
  border: none;
  font-weight: 600;
  height: 28px;
  line-height: 20px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding: 6px 12px;
  border-radius: 20px;
  transition: background 0.2s;
}

.user-info:hover {
  background: rgba(0, 0, 0, 0.05);
}

.username {
  color: #1d1d1f;
  font-size: 14px;
  font-weight: 500;
}

/* Main Content Area */
.main-content {
  background-color: transparent;
  padding: 32px; /* Increase padding */
  overflow-y: auto;
}

/* Global Card Override for "Rounded Corners" request */
:deep(.el-card) {
  border-radius: 16px !important; /* Force global rounding */
  border: none !important;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.04) !important;
}

/* Global Table Styling for Aesthetics */
:deep(.el-table) {
  border-radius: 12px;
  overflow: hidden;
  --el-table-header-bg-color: #f5f5f7;
}

:deep(.el-table th.el-table__cell) {
  background-color: #f5f5f7;
  color: #86868b;
  font-weight: 600;
  font-size: 13px;
  height: 48px;
}

:deep(.el-button--small) {
  border-radius: 14px;
  padding: 8px 16px;
}

</style>
