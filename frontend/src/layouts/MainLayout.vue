<template>
  <el-container class="layout-container">
    <!-- Sidebar -->
    <el-aside width="240px" class="sidebar">
      <div class="sidebar-header">
        <img 
          v-if="siteConfig.logo_url" 
          :src="siteConfig.logo_url" 
          alt="Logo" 
          class="site-logo"
        />
        <span class="site-title">{{ siteConfig.site_name }}</span>
      </div>
      
      <el-menu
        :default-active="route.path"
        router
        class="mac-menu"
      >
        <!-- Dashboard -->
        <el-menu-item index="/">
          <el-icon><DataBoard /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        
        <div class="menu-group-title">设备管理</div>
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

        <div class="menu-group-title">系统管理</div>
        <el-menu-item index="/logs">
          <el-icon><Document /></el-icon>
          <span>服务器日志</span>
        </el-menu-item>
        <el-menu-item index="/ai-config">
          <el-icon><Cpu /></el-icon>
          <span>AI 接口</span>
        </el-menu-item>
        <el-menu-item index="/license">
          <el-icon><Key /></el-icon>
          <span>授权管理</span>
        </el-menu-item>
        <el-menu-item index="/archive">
          <el-icon><Folder /></el-icon>
          <span>数据归档</span>
        </el-menu-item>
        <el-menu-item index="/health-check">
          <el-icon><FirstAidKit /></el-icon>
          <span>系统自检</span>
        </el-menu-item>
        <el-menu-item index="/config">
          <el-icon><Setting /></el-icon>
          <span>系统配置</span>
        </el-menu-item>
        
        <el-divider class="mac-divider" />
        
        <el-sub-menu index="/screen-group">
          <template #title>
            <el-icon><FullScreen /></el-icon>
            <span>可视化大屏</span>
          </template>
          <el-menu-item index="/screen">
            <el-icon><Monitor /></el-icon>
            <span>大屏展示</span>
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
      <el-header class="header">
        <div class="header-left">
          <h1 class="page-title">{{ route.meta.title || route.name }}</h1>
        </div>
        <div class="header-right">
          <!-- License Status -->
          <el-tag 
            :type="licenseStatus.status === 'active' ? 'success' : licenseStatus.status === 'grace' ? 'warning' : 'danger'"
            class="license-tag"
            v-if="licenseStatus.status"
          >
            <template v-if="licenseStatus.status === 'active'">
              已授权
            </template>
            <template v-else-if="licenseStatus.status === 'grace'">
              宽限期 (剩余 {{ licenseStatus.grace_remaining_days }} 天)
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
            <el-icon><WarningFilled /></el-icon> 代码篡改
          </el-tag>

          <el-button @click="handleLogout" size="small" type="danger" plain round>
            退出登录
          </el-button>
        </div>
      </el-header>
      
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

// Import icons explicitly? No, used globally in main.ts, but let's test safely.
// Assuming global registration in main.ts is correct.

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

async function loadSiteConfig() {
  try {
    const res = await configApi.getSite()
    if (res.data) siteConfig.value = { ...siteConfig.value, ...res.data }
  } catch (error) {
    console.error("Failed to load site config")
  }
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.layout-container {
  width: 100vw;
  height: 100vh;
  margin: 0;
  padding: 0;
  background: #f5f5f7; /* macOS default background grey */
  background-image: linear-gradient(135deg, #f5f5f7 0%, #e4e4e7 100%);
}

.sidebar {
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(20px);
  border-right: 1px solid rgba(255, 255, 255, 0.4);
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  height: 60px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 24px;
}

.site-logo {
  height: 32px;
  width: 32px;
  object-fit: contain;
  border-radius: 6px;
}

.site-title { font-weight: 600; color: #1d1d1f; font-size: 18px; }

.mac-menu { border-right: none; background: transparent; }
.menu-group-title { padding: 10px 20px 5px; font-size: 11px; color: #6e6e73; font-weight: 600; }

.header {
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.4);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.license-tag {
  border-radius: 12px;
  font-weight: 500;
}

.page-title { font-size: 18px; font-weight: 600; margin: 0; color: #1d1d1f; }

.main-content {
  padding: 20px;
  background: transparent;
  overflow-y: auto;
}
</style>
