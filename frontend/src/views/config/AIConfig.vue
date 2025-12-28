<!--
  MCS-IOT AI 接口配置页面 (AI Model Configuration)

  该文件负责管理系统的 AI 增强功能，集成大语言模型以生成智能化洞察。
  主要职责：
  1. 接口设置：配置 OpenRouter 或兼容接口的 API Key 与模型名称 (如 GPT-4)。
  2. 连接校验：提供“测试连接”功能，实时验证配置的有效性。
  3. 商业联动：提供快速购买 API 额度的跳转链接，确保服务的持续性。
  4. 视觉交互：采用深色渐变 Hero 区域与简洁的表单卡片设计。

  技术栈：Vue 3 (setup), Element Plus Form, Pinia.
-->
<template>
  <div class="ai-config-page">
    <div class="ai-container">
      <!-- Hero Section -->
      <div class="hero-section">
        <div class="ai-icon-wrapper">
          <el-icon class="ai-icon"><Cpu /></el-icon>
        </div>
        <h2 class="hero-title">AI 智能助手</h2>
        <p class="hero-subtitle">启用 AI 能力，自动生成平台运行状况的智能总结与洞察。</p>
      </div>

      <!-- Config Card -->
      <div class="config-card glass-panel">
        <el-form :model="form" label-position="top" size="large">
          <el-form-item label="API 接口地址">
            <el-input :value="fixedApiUrl" disabled>
              <template #prefix><el-icon><Link /></el-icon></template>
            </el-input>
          </el-form-item>
          
          <el-form-item label="API Key">
            <el-input 
              v-model="form.api_key" 
              type="password" 
              show-password 
              placeholder="sk-..." 
              autocomplete="new-password"
            >
              <template #prefix><el-icon><Key /></el-icon></template>
            </el-input>
          </el-form-item>
          
          <el-form-item label="模型名称">
            <el-input 
              v-model="form.model" 
              placeholder="gpt-3.5-turbo"
            >
              <template #prefix><el-icon><Connection /></el-icon></template>
            </el-input>
          </el-form-item>

          <div class="action-buttons">
            <el-button @click="testConnection" :loading="testing" round>
              <el-icon><MagicStick /></el-icon> 测试连接
            </el-button>
            <el-button type="primary" @click="saveConfig" :loading="loading" round>
              保存配置
            </el-button>
          </div>
        </el-form>
      </div>

      <!-- Purchase Section -->
      <div class="purchase-section" @click="goToPurchase">
        <div class="purchase-content">
          <div class="purchase-icon">
            <el-icon><ShoppingCart /></el-icon>
          </div>
          <div class="purchase-text">
            <div class="purchase-title">获取 API Key</div>
            <div class="purchase-desc">前往 Ryan AI 获取稳定高速的 API 服务</div>
          </div>
          <el-icon><ArrowRight /></el-icon>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { configApi } from '../../api'
import { ElMessage } from 'element-plus'
import { Cpu, Link, Key, Connection, MagicStick, ShoppingCart, ArrowRight } from '@element-plus/icons-vue'

const loading = ref(false)
const testing = ref(false)
const fixedApiUrl = 'https://newapi2.zhizinan.top/v1'

const form = reactive({
  api_key: '',
  model: 'gpt-3.5-turbo'
})

async function testConnection() {
  if (!form.api_key) {
    ElMessage.warning('请先填写 API Key')
    return
  }
  testing.value = true
  try {
    const res = await configApi.testAI(form)
    ElMessage.success('连接成功: ' + res.data.message)
  } catch (e: any) {
    console.error(e)
    ElMessage.error('连接失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    testing.value = false
  }
}

async function loadConfig() {
  loading.value = true
  try {
    const res = await configApi.getAI()
    if (res.data) {
      Object.assign(form, {
        api_key: res.data.api_key || '',
        model: res.data.model || 'gpt-3.5-turbo'
      })
    }
  } catch (e) {
    console.error('Failed to load AI config', e)
    ElMessage.error('加载配置失败')
  } finally {
    loading.value = false
  }
}

async function saveConfig() {
  loading.value = true
  try {
    await configApi.updateAI(form)
    ElMessage.success('AI 配置已保存')
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    loading.value = false
  }
}

function goToPurchase() {
  window.open('https://zhizinan.top', '_blank')
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.ai-config-page {
  display: flex;
  justify-content: center;
  padding: 40px 20px;
  min-height: 100%;
  box-sizing: border-box;
}

.ai-container {
  width: 100%;
  max-width: 480px;
  display: flex;
  flex-direction: column;
  gap: 32px;
}

/* Hero Section */
.hero-section {
  text-align: center;
}

.ai-icon-wrapper {
  width: 64px;
  height: 64px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 20px;
  box-shadow: 0 10px 25px rgba(118, 75, 162, 0.3);
}

.ai-icon {
  font-size: 32px;
  color: white;
}

.hero-title {
  font-size: 24px;
  font-weight: 700;
  color: #1d1d1f;
  margin: 0 0 8px;
}

.hero-subtitle {
  font-size: 14px;
  color: #86868b;
  margin: 0;
  line-height: 1.5;
}

/* Glass Panel */
.glass-panel {
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(20px);
  border-radius: 24px;
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.04);
  padding: 32px;
}

/* Form Styles */
:deep(.el-form-item__label) {
  font-weight: 500;
  color: #1d1d1f !important;
}

:deep(.el-input__wrapper) {
  border-radius: 12px;
  padding: 8px 12px;
  background-color: rgba(255, 255, 255, 0.5);
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.1) inset !important;
}

:deep(.el-input__wrapper:hover) {
  background-color: #fff;
}

:deep(.el-input__wrapper.is-focus) {
  background-color: #fff;
  box-shadow: 0 0 0 2px #0071e3 inset !important;
}

.model-tips {
  margin-top: 8px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.model-tips .el-tag {
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.2s;
}

.model-tips .el-tag:hover {
  transform: translateY(-1px);
  background: #f5f7fa;
}

.action-buttons {
  margin-top: 32px;
  display: grid;
  grid-template-columns: 1fr 1.5fr;
  gap: 16px;
}

:deep(.el-button) {
  height: 44px;
  font-weight: 500;
  font-size: 15px;
}

/* Purchase Section */
.purchase-section {
  background: white;
  border-radius: 20px;
  padding: 20px;
  cursor: pointer;
  border: 1px solid rgba(0, 0, 0, 0.05);
  transition: all 0.2s;
}

.purchase-section:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.06);
}

.purchase-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.purchase-icon {
  width: 40px;
  height: 40px;
  background: #fdf6ec;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #e6a23c;
  font-size: 20px;
}

.purchase-text {
  flex: 1;
}

.purchase-title {
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 4px;
}

.purchase-desc {
  font-size: 13px;
  color: #86868b;
}
</style>

