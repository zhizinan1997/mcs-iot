<!--
  MCS-IOT AI 接口配置页面 (AI Model Configuration)

  该文件负责管理系统的 AI 增强功能，集成大语言模型以生成智能化洞察。
  主要职责：
  1. 接口设置：配置 API Key 与模型名称。
  2. 总结间隔：配置 AI 每隔多少小时生成一次总结（基于整点时间）。
  3. 历史记录：展示 AI 总结历史，支持清空操作。
  4. 连接校验：提供"测试连接"功能，实时验证配置的有效性。

  技术栈：Vue 3 (setup), Element Plus Form.
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

          <el-form-item label="总结间隔">
            <el-select v-model="form.interval_hours" style="width: 100%">
              <el-option :value="1" label="每 1 小时 (00:00, 01:00, ...)" />
              <el-option :value="2" label="每 2 小时 (00:00, 02:00, 04:00, ...)" />
              <el-option :value="3" label="每 3 小时 (00:00, 03:00, 06:00, ...)" />
              <el-option :value="4" label="每 4 小时 (00:00, 04:00, 08:00, ...)" />
              <el-option :value="6" label="每 6 小时 (00:00, 06:00, 12:00, 18:00)" />
              <el-option :value="8" label="每 8 小时 (00:00, 08:00, 16:00)" />
              <el-option :value="12" label="每 12 小时 (00:00, 12:00)" />
            </el-select>
            <div class="interval-tip">以北京时间 00:00 为起点，按整点时间触发 AI 总结</div>
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

      <!-- History Section -->
      <div class="history-section glass-panel">
        <div class="history-header">
          <h3 class="history-title">
            <el-icon><Clock /></el-icon>
            AI 总结记录
          </h3>
          <el-button 
            type="danger" 
            text 
            @click="confirmClearHistory" 
            :loading="clearing"
            :disabled="historyList.length === 0"
          >
            <el-icon><Delete /></el-icon> 清空记录
          </el-button>
        </div>

        <div v-if="historyLoading" class="history-loading">
          <el-icon class="is-loading"><Loading /></el-icon>
          加载中...
        </div>

        <div v-else-if="historyList.length === 0" class="history-empty">
          <el-icon><DocumentDelete /></el-icon>
          <p>暂无 AI 总结记录</p>
        </div>

        <div v-else class="history-list">
          <div 
            v-for="item in historyList" 
            :key="item.id" 
            class="history-item"
            @click="toggleExpand(item.id)"
          >
            <div class="history-item-header">
              <div class="history-time">
                <el-tag size="small" type="info">{{ item.time_range }}</el-tag>
                <span class="history-date">{{ formatDate(item.created_at) }}</span>
              </div>
              <div class="history-stats">
                <el-tag size="small" :type="item.alarm_count > 0 ? 'warning' : 'success'">
                  {{ item.alarm_count }} 次报警
                </el-tag>
                <el-icon :class="{ expanded: expandedIds.includes(item.id) }">
                  <ArrowDown />
                </el-icon>
              </div>
            </div>
            <div v-if="expandedIds.includes(item.id)" class="history-content">
              {{ item.content }}
            </div>
          </div>
          
          <!-- Pagination -->
          <div v-if="historyTotal > pageSize" class="history-pagination">
            <el-pagination
              v-model:current-page="currentPage"
              :page-size="pageSize"
              :total="historyTotal"
              layout="prev, pager, next"
              small
              @current-change="loadHistory"
            />
          </div>
        </div>
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
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Cpu, Link, Key, Connection, MagicStick, ShoppingCart, ArrowRight,
  Clock, Delete, Loading, DocumentDelete, ArrowDown
} from '@element-plus/icons-vue'

const loading = ref(false)
const testing = ref(false)
const clearing = ref(false)
const historyLoading = ref(false)
const fixedApiUrl = 'https://newapi2.zhizinan.top/v1'

const form = reactive({
  api_key: '',
  model: 'gpt-3.5-turbo',
  interval_hours: 4
})

// History state
const historyList = ref<any[]>([])
const historyTotal = ref(0)
const currentPage = ref(1)
const pageSize = 10
const expandedIds = ref<number[]>([])

function toggleExpand(id: number) {
  const index = expandedIds.value.indexOf(id)
  if (index === -1) {
    expandedIds.value.push(id)
  } else {
    expandedIds.value.splice(index, 1)
  }
}

function formatDate(dateStr: string) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

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
        model: res.data.model || 'gpt-3.5-turbo',
        interval_hours: res.data.interval_hours || 4
      })
    }
  } catch (e) {
    console.error('Failed to load AI config', e)
    ElMessage.error('加载配置失败')
  } finally {
    loading.value = false
  }
}

async function loadHistory() {
  historyLoading.value = true
  try {
    const res = await configApi.getAIHistory(currentPage.value, pageSize)
    if (res.data) {
      historyList.value = res.data.data || []
      historyTotal.value = res.data.total || 0
    }
  } catch (e) {
    console.error('Failed to load AI history', e)
    // 静默失败，可能是表还未创建
    historyList.value = []
    historyTotal.value = 0
  } finally {
    historyLoading.value = false
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

async function confirmClearHistory() {
  try {
    await ElMessageBox.confirm(
      '确定要清空所有 AI 总结记录吗？此操作不可恢复。',
      '清空确认',
      {
        confirmButtonText: '确定清空',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    await clearHistory()
  } catch {
    // User cancelled
  }
}

async function clearHistory() {
  clearing.value = true
  try {
    const res = await configApi.clearAIHistory()
    ElMessage.success(res.data.message || '已清空所有记录')
    historyList.value = []
    historyTotal.value = 0
    currentPage.value = 1
  } catch (e: any) {
    ElMessage.error('清空失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    clearing.value = false
  }
}

function goToPurchase() {
  window.open('https://zhizinan.top', '_blank')
}

onMounted(() => {
  loadConfig()
  loadHistory()
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
  max-width: 520px;
  display: flex;
  flex-direction: column;
  gap: 24px;
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
  padding: 24px;
}

/* Form Styles */
:deep(.el-form-item__label) {
  font-weight: 500;
  color: #1d1d1f !important;
}

:deep(.el-input__wrapper),
:deep(.el-select__wrapper) {
  border-radius: 12px;
  padding: 8px 12px;
  background-color: rgba(255, 255, 255, 0.5);
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.1) inset !important;
}

:deep(.el-input__wrapper:hover),
:deep(.el-select__wrapper:hover) {
  background-color: #fff;
}

:deep(.el-input__wrapper.is-focus),
:deep(.el-select__wrapper.is-focused) {
  background-color: #fff;
  box-shadow: 0 0 0 2px #0071e3 inset !important;
}

.interval-tip {
  margin-top: 6px;
  font-size: 12px;
  color: #86868b;
}

.action-buttons {
  margin-top: 24px;
  display: grid;
  grid-template-columns: 1fr 1.5fr;
  gap: 16px;
}

:deep(.el-button) {
  height: 44px;
  font-weight: 500;
  font-size: 15px;
}

/* History Section */
.history-section {
  padding: 20px;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.history-title {
  font-size: 16px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.history-loading,
.history-empty {
  text-align: center;
  padding: 32px 0;
  color: #86868b;
}

.history-empty .el-icon {
  font-size: 40px;
  margin-bottom: 12px;
  color: #c0c4cc;
}

.history-empty p {
  margin: 0;
  font-size: 14px;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.history-item {
  background: rgba(255, 255, 255, 0.6);
  border-radius: 12px;
  padding: 12px 16px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid rgba(0, 0, 0, 0.05);
}

.history-item:hover {
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.history-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.history-time {
  display: flex;
  align-items: center;
  gap: 8px;
}

.history-date {
  font-size: 12px;
  color: #86868b;
}

.history-stats {
  display: flex;
  align-items: center;
  gap: 8px;
}

.history-stats .el-icon {
  transition: transform 0.2s;
  color: #86868b;
}

.history-stats .el-icon.expanded {
  transform: rotate(180deg);
}

.history-content {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed rgba(0, 0, 0, 0.08);
  font-size: 14px;
  line-height: 1.6;
  color: #333;
  white-space: pre-wrap;
}

.history-pagination {
  margin-top: 16px;
  display: flex;
  justify-content: center;
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
