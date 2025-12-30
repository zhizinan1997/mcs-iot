<!--
  MCS-IOT 后台管理主布局 (Main Layout Container)

  该文件是应用内部页面的公共壳容器，采用了响应式的左右布局结构。
  主要职责：
  1. 侧边导航栏 (Sidebar)：基于权限系统 (RBAC) 动态渲染功能菜单，涵盖设备管理、系统管理及大屏配置入口。
  2. 顶部工具栏 (Header)：展示当前页面标题、商业授权状态、异常篡改预警、用户信息及系统退出逻辑。
  3. 全局状态监听：实时同步站点配置 (Logo/名称) 并监听授权更新事件以刷新 UI。
  4. 视觉风格调优：集成了 macOS 风格的毛玻璃效果与响应式侧边栏。

  技术栈：Vue 3 (setup), Vue Router, Pinia (Auth/Theme), Element Plus.
-->
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
        <el-menu-item index="/" v-if="hasPermission('dashboard')">
          <el-icon><DataBoard /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        
        <div class="menu-group-title" v-if="hasPermission('instruments') || hasPermission('devices') || hasPermission('alarms')">设备管理</div>
        <el-menu-item index="/instruments" v-if="hasPermission('instruments')">
          <el-icon><Odometer /></el-icon>
          <span>仪表管理</span>
        </el-menu-item>
        <el-menu-item index="/devices" v-if="hasPermission('devices')">
          <el-icon><Monitor /></el-icon>
          <span>传感器管理</span>
        </el-menu-item>
        <el-menu-item index="/alarms" v-if="hasPermission('alarms')">
          <el-icon><Bell /></el-icon>
          <span>报警记录</span>
        </el-menu-item>

        <div class="menu-group-title" v-if="hasAnySystemPermission">系统管理</div>
        <el-menu-item index="/logs" v-if="hasPermission('logs')">
          <el-icon><Document /></el-icon>
          <span>服务器日志</span>
        </el-menu-item>
        <el-menu-item index="/ai-config" v-if="hasPermission('ai')">
          <el-icon><Cpu /></el-icon>
          <span>AI 接口</span>
        </el-menu-item>
        <el-menu-item index="/license" v-if="hasPermission('license')">
          <el-icon><Key /></el-icon>
          <span>授权管理</span>
        </el-menu-item>
        <el-menu-item index="/archive" v-if="hasPermission('archive')">
          <el-icon><Folder /></el-icon>
          <span>数据归档</span>
        </el-menu-item>
        <el-menu-item index="/health-check" v-if="hasPermission('health')">
          <el-icon><FirstAidKit /></el-icon>
          <span>系统自检</span>
        </el-menu-item>
        <!-- 子账号管理 (仅管理员) -->
        <el-menu-item index="/users" v-if="isAdmin">
          <el-icon><User /></el-icon>
          <span>子账号管理</span>
        </el-menu-item>
        <el-menu-item index="/config" v-if="hasPermission('config')">
          <el-icon><Setting /></el-icon>
          <span>系统配置</span>
        </el-menu-item>
        
        <el-divider class="mac-divider" v-if="hasPermission('screen')" />
        
        <el-sub-menu index="/screen-group" v-if="hasPermission('screen')">
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
          <!-- Theme Toggle -->
          <el-button circle @click="themeStore.toggleTheme" class="theme-toggle-btn">
             <el-icon v-if="themeStore.isDark"><Moon /></el-icon>
             <el-icon v-else><Sunny /></el-icon>
          </el-button>

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
            <span class="tamper-content">
              <el-icon class="tamper-icon"><WarningFilled /></el-icon>
              <span>代码篡改</span>
            </span>
          </el-tag>

          <!-- User Info -->
          <el-tag type="info" class="user-tag" v-if="authStore.user">
            {{ authStore.user.username }}
            <span v-if="isAdmin">(管理员)</span>
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
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useThemeStore } from '../stores/theme'
import { configApi } from '../api'
import { Moon, Sunny, WarningFilled, User } from '@element-plus/icons-vue'
import { onLicenseUpdate } from '../utils/licenseEvent'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const themeStore = useThemeStore()

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

// 权限检查
const isAdmin = computed(() => authStore.isAdmin)

function hasPermission(key: string): boolean {
  return authStore.hasPermission(key)
}

// 检查是否有任意系统管理相关权限
const hasAnySystemPermission = computed(() => {
  return hasPermission('logs') || hasPermission('ai') || hasPermission('license') || 
         hasPermission('archive') || hasPermission('health') || hasPermission('config') ||
         isAdmin.value
})

// 用于取消订阅
let unsubscribeLicenseEvent: (() => void) | null = null

onMounted(() => {
  loadSiteConfig()
  loadLicenseStatus()
  // 加载用户信息以获取权限
  authStore.fetchUser()
  
  // 监听授权验证成功事件，刷新右上角状态
  unsubscribeLicenseEvent = onLicenseUpdate(() => {
    loadLicenseStatus()
  })
})

onUnmounted(() => {
  // 清理事件订阅
  if (unsubscribeLicenseEvent) {
    unsubscribeLicenseEvent()
  }
})

async function loadLicenseStatus() {
  try {
    const res = await configApi.getLicense()
    if (res.data) {
      licenseStatus.value = {
        status: res.data.status || 'unlicensed',
        expires: res.data.expires_at ? res.data.expires_at.split('T')[0] : '',
        grace_remaining_days: res.data.grace_remaining_days || 0,
        tampered: res.data.tampered || false
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

.user-tag {
  border-radius: 12px;
  font-weight: 500;
}

.tamper-warning-tag {
  border-radius: 12px;
  font-weight: 500;
  white-space: nowrap;
  padding: 0 10px !important;
  height: 28px !important;
  line-height: 26px !important;
  display: inline-flex !important;
  align-items: center !important;
  box-sizing: border-box !important;
}

.tamper-content {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  line-height: 1;
}

.tamper-icon {
  font-size: 14px;
  vertical-align: middle;
}

.page-title { font-size: 18px; font-weight: 600; margin: 0; color: #1d1d1f; }

.main-content {
  padding: 20px;
  background: transparent;
  overflow-y: auto;
}

.theme-toggle-btn {
  border: none;
  background: transparent;
  width: 32px;
  height: 32px;
}

.theme-toggle-btn:hover {
  background: rgba(0,0,0,0.05);
}

html.dark .theme-toggle-btn {
  color: #fff;
}

html.dark .theme-toggle-btn:hover {
  background: rgba(255,255,255,0.1);
}
</style>
