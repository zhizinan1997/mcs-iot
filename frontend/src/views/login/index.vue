<template>
  <div class="login-container" :class="{ 'light-mode': !themeStore.isDark }">
    <!-- Theme Toggle -->
    <div class="theme-toggle">
      <el-button circle size="large" @click="toggleTheme">
        <el-icon v-if="themeStore.isDark" :size="20"><Moon /></el-icon>
        <el-icon v-else :size="20"><Sunny /></el-icon>
      </el-button>
    </div>
    
    <!-- Particles Background -->
    <div id="tsparticles"></div>
    
    <!-- Animated Background Orbs (Optional: Keep or Remove? Keeping for now as layer) -->
    <div class="bg-orb orb-1"></div>
    <div class="bg-orb orb-2"></div>
    <div class="bg-orb orb-3"></div>
    
    <div class="login-card">
      <!-- Logo & Header -->
      <div class="login-header">
        <div class="logo-wrapper">
          <img 
            v-if="siteConfig.logo_url" 
            :src="siteConfig.logo_url" 
            alt="Logo" 
            class="logo-img"
          />
          <div v-else class="logo-placeholder">
            <el-icon :size="48"><Monitor /></el-icon>
          </div>
        </div>
        <h1>{{ siteConfig.site_name || 'MCS-IoT' }}</h1>
        <p class="subtitle">工业气体监测管理平台</p>
      </div>
      
      <!-- Login Form -->
      <el-form :model="form" :rules="rules" ref="formRef" @submit.prevent="handleLogin">
        <el-form-item prop="username">
          <el-input 
            v-model="form.username" 
            placeholder="用户名"
            prefix-icon="User"
            size="large"
          />
        </el-form-item>
        
        <el-form-item prop="password">
          <el-input 
            v-model="form.password" 
            type="password" 
            placeholder="密码"
            prefix-icon="Lock"
            size="large"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button 
            type="primary" 
            native-type="submit" 
            :loading="loading"
            size="large"
            class="login-btn"
          >
            <span v-if="!loading">登 录</span>
            <span v-else>验证中...</span>
          </el-button>
        </el-form-item>
      </el-form>
    </div>
    <!-- Footer Credits -->
    <div class="login-credits">
      <div class="credits-content">
        <p class="developer">Developed by <strong>Ryan Zhi</strong></p>
        <p class="contact">
          Bug 反馈: 
          <a href="mailto:zinanzhi@gmail.com">zinanzhi@gmail.com</a>
          <span class="separator">|</span>
          <a href="https://github.com/zhizinan1997/mcs-iot" target="_blank">
            <el-icon><Link /></el-icon>
            GitHub PR
          </a>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Monitor, Link, Moon, Sunny } from '@element-plus/icons-vue'
import { useAuthStore } from '../../stores/auth'
import { useThemeStore } from '../../stores/theme'
import { configApi } from '../../api'

const router = useRouter()
const authStore = useAuthStore()
const themeStore = useThemeStore()
const formRef = ref()
const loading = ref(false)

const toggleTheme = () => {
  themeStore.toggleTheme()
  initParticles() // Reload particles when theme changes
}

// Load tsparticles params
const loadParticlesParams = {
  src: "https://cdn.jsdelivr.net/npm/tsparticles@2.11.1/tsparticles.bundle.min.js",
  id: "tsparticles-js"
}

// Initialize particles with theme-aware colors
const initParticles = () => {
  const tsParticles = (window as any).tsParticles
  if (tsParticles) {
    // Light grey for dark mode, subtle white for light mode
    const color = themeStore.isDark ? "#888888" : "#ffffff"
    const linkColor = themeStore.isDark ? "#aaaaaa" : "#ffffff"
    
    tsParticles.load("tsparticles", {
      fullScreen: { enable: false, zIndex: 0 },
      background: { color: { value: "transparent" } },
      fpsLimit: 120,
      interactivity: {
        events: {
          onHover: { enable: true, mode: "grab" },
          onClick: { enable: true, mode: "push" },
          resize: true
        },
        modes: {
          grab: { distance: 140, links: { opacity: 0.5 } },
          push: { quantity: 4 }
        }
      },
      particles: {
        color: { value: color },
        links: {
          color: linkColor,
          distance: 150,
          enable: true,
          opacity: 0.3, // Slightly higher opacity for visibility
          width: 1
        },
        move: {
          direction: "none",
          enable: true,
          outModes: { default: "bounce" },
          random: false,
          speed: 1, // Slow movement
          straight: false
        },
        number: {
          density: { enable: true, area: 800 },
          value: 80
        },
        opacity: { value: 0.5 },
        shape: { type: "circle" },
        size: { value: { min: 1, max: 3 } }
      },
      detectRetina: true
    })
  }
}

const form = reactive({
  username: '',
  password: ''
})

const siteConfig = reactive({
  site_name: 'MCS-IoT',
  logo_url: ''
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

async function handleLogin() {
  await formRef.value?.validate()
  loading.value = true
  try {
    await authStore.login(form.username, form.password)
    ElMessage.success('登录成功')
    router.push('/')
  } catch (error: any) {
    // 显示后端返回的具体错误信息（如"账号不存在"、"密码错误"）
    const detail = error.response?.data?.detail || '登录失败，请检查网络连接'
    ElMessage.error(detail)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  // Load site config
  try {
    const res = await configApi.getSite()
    if (res.data) {
      siteConfig.site_name = res.data.site_name || 'MCS-IoT'
      siteConfig.logo_url = res.data.logo_url || ''
    }
  } catch (e) {}

  // Load particles script if not exists
  if (!document.getElementById(loadParticlesParams.id)) {
    const script = document.createElement('script')
    script.src = loadParticlesParams.src
    script.id = loadParticlesParams.id
    script.async = true
    script.onload = () => {
      initParticles()
    }
    document.body.appendChild(script)
  } else {
    initParticles()
  }
})
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(145deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", Helvetica, Arial, sans-serif;
  position: relative;
  overflow: hidden;
}

#tsparticles {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1; /* Above background, below card */
  pointer-events: auto; /* Enable interactivity */
}


/* Light Mode Styles */
.login-container.light-mode {
  background: linear-gradient(135deg, #e0c3fc 0%, #8ec5fc 100%);
}

.login-container.light-mode .bg-orb {
  opacity: 0.6;
}

.login-container.light-mode .orb-1 {
  background: radial-gradient(circle, #ffffff 0%, transparent 70%);
}

.login-container.light-mode .orb-2 {
  background: radial-gradient(circle, #a18cd1 0%, transparent 70%);
}

.login-container.light-mode .orb-3 {
  background: radial-gradient(circle, #fbc2eb 0%, transparent 70%);
}

.login-container.light-mode .login-card {
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.4);
  box-shadow: 
    0 12px 40px rgba(0, 0, 0, 0.1),
    0 0 0 1px rgba(255, 255, 255, 0.5) inset;
}

.login-container.light-mode .login-header h1 {
  color: #333;
  text-shadow: none;
}

.login-container.light-mode .subtitle {
  color: #666;
}

.login-container.light-mode .logo-wrapper {
  background: rgba(255, 255, 255, 0.8);
  box-shadow: 
    0 8px 24px rgba(0, 0, 0, 0.1),
    0 0 0 1px rgba(255, 255, 255, 0.5) inset;
}

.login-container.light-mode .logo-placeholder {
  color: #667eea;
}

.login-container.light-mode :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.6);
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.05) inset;
}

.login-container.light-mode :deep(.el-input__wrapper:hover) {
  background: rgba(255, 255, 255, 0.8);
}

.login-container.light-mode :deep(.el-input__wrapper.is-focus) {
  background: #fff;
  box-shadow: 
    0 0 0 2px rgba(102, 126, 234, 0.6) inset,
    0 4px 12px rgba(102, 126, 234, 0.15);
}

.login-container.light-mode :deep(.el-input__inner) {
  color: #333;
}

.login-container.light-mode :deep(.el-input__inner::placeholder) {
  color: #999;
}

.login-container.light-mode :deep(.el-input__prefix-inner),
.login-container.light-mode :deep(.el-input__suffix-inner) {
  color: #888;
}

.login-container.light-mode .credits-content {
  background: rgba(255, 255, 255, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.login-container.light-mode .developer {
  color: #555;
}

.login-container.light-mode .developer strong {
  color: #333;
}

.login-container.light-mode .contact {
  color: #666;
}

.login-container.light-mode .contact a {
  color: #555;
}

.login-container.light-mode .contact a:hover {
  color: #667eea;
}

.login-container.light-mode .separator {
  color: #ccc;
}

/* Theme Toggle */
.theme-toggle {
  position: absolute;
  top: 32px;
  right: 32px;
  z-index: 20;
}

.theme-toggle .el-button {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #fff;
  transition: all 0.3s ease;
}

.login-container.light-mode .theme-toggle .el-button {
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.5);
  color: #666;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.theme-toggle .el-button:hover {
  transform: scale(1.1);
}

/* Animated Background Orbs */
.bg-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.5;
  animation: float 20s ease-in-out infinite;
}

.orb-1 {
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, #667eea 0%, transparent 70%);
  top: -200px;
  left: -100px;
  animation-delay: 0s;
}

.orb-2 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, #764ba2 0%, transparent 70%);
  bottom: -150px;
  right: -100px;
  animation-delay: -7s;
}

.orb-3 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, #f093fb 0%, transparent 70%);
  top: 50%;
  left: 60%;
  animation-delay: -14s;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  25% { transform: translate(30px, -30px) scale(1.05); }
  50% { transform: translate(-20px, 20px) scale(0.95); }
  75% { transform: translate(20px, 10px) scale(1.02); }
}

/* Login Card - Glassmorphism */
.login-card {
  width: 400px;
  padding: 48px 40px 40px;
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(40px) saturate(180%);
  -webkit-backdrop-filter: blur(40px) saturate(180%);
  border-radius: 28px;
  box-shadow: 
    0 32px 64px rgba(0, 0, 0, 0.4),
    0 0 0 1px rgba(255, 255, 255, 0.1) inset,
    0 -2px 6px rgba(0, 0, 0, 0.2) inset;
  border: 1px solid rgba(255, 255, 255, 0.15);
  position: relative;
  z-index: 10;
}

/* Header & Logo */
.login-header {
  text-align: center;
  margin-bottom: 36px;
}

.logo-wrapper {
  width: 88px;
  height: 88px;
  margin: 0 auto 20px;
  border-radius: 22px;
  background: linear-gradient(145deg, rgba(255,255,255,0.15), rgba(255,255,255,0.05));
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.3),
    0 0 0 1px rgba(255, 255, 255, 0.1) inset;
  overflow: hidden;
}

.logo-img {
  width: 64px;
  height: 64px;
  object-fit: contain;
}

.logo-placeholder {
  color: rgba(255, 255, 255, 0.8);
}

.login-header h1 {
  font-size: 28px;
  font-weight: 700;
  color: #ffffff;
  margin: 0 0 8px 0;
  letter-spacing: -0.02em;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
}

.subtitle {
  color: rgba(255, 255, 255, 0.6);
  margin: 0;
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0.02em;
}

/* Form Styling */
:deep(.el-form-item) {
  margin-bottom: 20px;
}

:deep(.el-input__wrapper) {
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.08);
  box-shadow: 
    0 0 0 1px rgba(255, 255, 255, 0.1) inset,
    0 2px 8px rgba(0, 0, 0, 0.15);
  padding: 14px 18px;
  transition: all 0.25s ease;
}

:deep(.el-input__wrapper:hover) {
  background: rgba(255, 255, 255, 0.12);
}

:deep(.el-input__wrapper.is-focus) {
  background: rgba(255, 255, 255, 0.15);
  box-shadow: 
    0 0 0 2px rgba(102, 126, 234, 0.6) inset,
    0 4px 16px rgba(102, 126, 234, 0.2);
}

:deep(.el-input__inner) {
  font-size: 15px;
  font-weight: 500;
  color: #ffffff;
}

:deep(.el-input__inner::placeholder) {
  color: rgba(255, 255, 255, 0.4);
}

:deep(.el-input__prefix-inner) {
  font-size: 18px;
  color: rgba(255, 255, 255, 0.5);
}

:deep(.el-input__suffix-inner) {
  color: rgba(255, 255, 255, 0.5);
}

/* Login Button */
.login-btn {
  width: 100%;
  height: 52px;
  border-radius: 14px;
  font-size: 16px;
  font-weight: 600;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  box-shadow: 
    0 8px 24px rgba(102, 126, 234, 0.4),
    0 0 0 1px rgba(255, 255, 255, 0.1) inset;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  letter-spacing: 0.05em;
}

.login-btn:hover {
  transform: translateY(-2px);
  box-shadow: 
    0 12px 32px rgba(102, 126, 234, 0.5),
    0 0 0 1px rgba(255, 255, 255, 0.15) inset;
  background: linear-gradient(135deg, #7c8ef5 0%, #8a5cb5 100%);
}

.login-btn:active {
  transform: translateY(0);
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.4);
}

/* Credentials Hint */
.credentials-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 24px;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  color: rgba(255, 255, 255, 0.5);
  font-size: 13px;
  font-weight: 500;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.credentials-hint .el-icon {
  font-size: 14px;
}

/* Footer Credits */
.login-credits {
  position: absolute;
  bottom: 32px;
  left: 0;
  right: 0;
  text-align: center;
  z-index: 10;
}

.credits-content {
  display: inline-block;
  padding: 16px 28px;
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(20px);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.credits-content p {
  margin: 0;
  line-height: 1.6;
}

.developer {
  color: rgba(255, 255, 255, 0.7);
  font-size: 13px;
  margin-bottom: 6px !important;
}

.developer strong {
  color: #ffffff;
  font-weight: 600;
}

.contact {
  color: rgba(255, 255, 255, 0.5);
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.contact a {
  color: rgba(255, 255, 255, 0.7);
  text-decoration: none;
  transition: color 0.2s ease;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.contact a:hover {
  color: #667eea;
}

.separator {
  color: rgba(255, 255, 255, 0.3);
}

/* Responsive */
@media (max-width: 480px) {
  .login-card {
    width: 90%;
    padding: 36px 28px;
    border-radius: 24px;
  }
  
  .login-header h1 {
    font-size: 24px;
  }
  
  .logo-wrapper {
    width: 72px;
    height: 72px;
  }
  
  .logo-img {
    width: 52px;
    height: 52px;
  }
  
  .login-credits {
    position: relative;
    bottom: auto;
    margin-top: 32px;
  }
}
</style>
