<template>
  <div class="logs-page mac-style">
    <div class="glass-container">
      <!-- 顶部工具栏 (macOS 风格) -->
      <div class="toolbar">
        <div class="title-section">
          <div class="window-controls">
            <span class="dot red"></span>
            <span class="dot yellow"></span>
            <span class="dot green"></span>
          </div>
          <span class="page-title">服务器日志</span>
        </div>
        
        <div class="actions-section">
          <!-- 筛选器组 -->
          <div class="filter-group glass-input-group">
            <el-select 
              v-model="selectedService" 
              placeholder="全部服务" 
              clearable 
              class="mac-select"
              popper-class="mac-select-dropdown"
            >
              <template #prefix><el-icon><Monitor /></el-icon></template>
              <el-option label="Backend (后端)" value="backend" />
              <el-option label="Worker (任务)" value="worker" />
              <el-option label="Frontend (前端)" value="frontend" />
              <el-option label="Database (数据库)" value="database" />
              <el-option label="Redis (缓存)" value="redis" />
              <el-option label="MQTT (消息队列)" value="mosquitto" />
            </el-select>
            
            <el-select 
              v-model="selectedLevel" 
              placeholder="全部级别" 
              clearable 
              class="mac-select"
              popper-class="mac-select-dropdown"
            >
              <template #prefix><el-icon><Filter /></el-icon></template>
              <el-option label="错误 (Error)" value="error">
                <span class="level-dot error"></span>Error
              </el-option>
              <el-option label="警告 (Warning)" value="warning">
                <span class="level-dot warning"></span>Warning
              </el-option>
              <el-option label="信息 (Info)" value="info">
                <span class="level-dot info"></span>Info
              </el-option>
            </el-select>
          </div>

          <!-- 操作按钮 -->
          <div class="action-buttons">
            <el-button class="mac-btn glass-btn" @click="loadLogs" :loading="loading" circle title="刷新">
              <el-icon><Refresh /></el-icon>
            </el-button>
            <el-button class="mac-btn glass-btn danger" @click="clearLogs" :loading="clearing" circle title="清空日志">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
        </div>
      </div>

      <!-- 状态指示条 -->
      <div class="status-bar">
        <div class="stat-item error" :class="{ active: stats.error > 0 }">
          <span class="stat-dot"></span>
          <span class="stat-label">错误</span>
          <span class="stat-value">{{ stats.error }}</span>
        </div>
        <div class="stat-item warning" :class="{ active: stats.warning > 0 }">
          <span class="stat-dot"></span>
          <span class="stat-label">警告</span>
          <span class="stat-value">{{ stats.warning }}</span>
        </div>
        <div class="stat-item info">
          <span class="stat-dot"></span>
          <span class="stat-label">信息</span>
          <span class="stat-value">{{ stats.info }}</span>
        </div>
        <div class="divider"></div>
        <div class="stat-item total">
          <span class="stat-label">总计</span>
          <span class="stat-value">{{ logs.length }}</span>
        </div>
        <div class="last-update" v-if="lastUpdate">
          更新于: {{ formatTime(lastUpdate) }}
        </div>
      </div>

      <!-- 终端风格日志输出 -->
      <div class="terminal-window">
        <div class="logs-container custom-scroll" ref="logsContainer">
          <div v-if="loading && logs.length === 0" class="placeholder">
            <div class="loading-spinner"></div>
            <span>正在加载系统日志...</span>
          </div>
          
          <div v-else-if="logs.length === 0" class="placeholder">
            <el-icon :size="48"><Document /></el-icon>
            <span>暂无日志数据</span>
          </div>

          <div 
            v-else
            v-for="(log, idx) in filteredLogs" 
            :key="idx"
            class="log-line"
            :class="log.level"
          >
            <div class="line-gutter">{{ idx + 1 }}</div>
            <div class="line-content">
              <span class="time">[{{ log.timestamp.split(' ')[1] }}]</span>
              <span class="service" :class="log.service">{{ getServiceShortName(log.service) }}</span>
              <span class="message">{{ log.message }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Delete, Monitor, Filter, Document } from '@element-plus/icons-vue'
import axios from 'axios'

interface LogEntry {
  timestamp: string
  level: string
  service: string
  message: string
  raw: string
}

const logs = ref<LogEntry[]>([])
const loading = ref(false)
const clearing = ref(false)
const selectedService = ref('')
const selectedLevel = ref('')
const lastUpdate = ref<Date | null>(null)
let refreshTimer: number | null = null

const filteredLogs = computed(() => {
  let result = logs.value
  if (selectedService.value) {
    result = result.filter(log => log.service === selectedService.value)
  }
  if (selectedLevel.value) {
    result = result.filter(log => log.level === selectedLevel.value)
  }
  return result
})

const stats = computed(() => ({
  error: logs.value.filter(l => l.level === 'error').length,
  warning: logs.value.filter(l => l.level === 'warning').length,
  info: logs.value.filter(l => l.level === 'info').length,
}))

async function loadLogs() {
  loading.value = true
  try {
    const params: Record<string, any> = { lines: 100 }
    if (selectedService.value) params.service = selectedService.value
    if (selectedLevel.value) params.level = selectedLevel.value
    
    const res = await axios.get('/api/logs', { params })
    logs.value = res.data.logs || []
    lastUpdate.value = new Date()
  } catch (error: any) {
    ElMessage.error('加载日志失败')
  } finally {
    loading.value = false
  }
}

async function clearLogs() {
  clearing.value = true
  try {
    await axios.delete('/api/logs')
    ElMessage.success('日志已清空')
    logs.value = []
  } catch (error: any) {
    ElMessage.error('清空失败')
  } finally {
    clearing.value = false
  }
}

function getServiceShortName(service: string) {
  const map: Record<string, string> = {
    backend: 'API',
    worker: 'WRK',
    frontend: 'WEB',
    database: 'DB',
    redis: 'RDS',
    mosquitto: 'MQTT'
  }
  return map[service] || service.substring(0, 3).toUpperCase()
}

function formatTime(date: Date) {
  return date.toLocaleTimeString('en-US', { hour12: false })
}

onMounted(() => {
  loadLogs()
  refreshTimer = window.setInterval(loadLogs, 30000)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&family=Inter:wght@400;500;600&display=swap');

.logs-page {
  padding: 24px;
  height: calc(100vh - 84px); /* Adjust based on layout */
  box-sizing: border-box;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: transparent;
}

/* Glass Container */
.glass-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border-radius: 24px;
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow: 
    0 8px 32px 0 rgba(31, 38, 135, 0.07),
    inset 0 0 0 1px rgba(255, 255, 255, 0.4);
  overflow: hidden;
  transition: all 0.3s ease;
}

/* Toolbar */
.toolbar {
  padding: 16px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  background: rgba(255, 255, 255, 0.4);
}

.title-section {
  display: flex;
  align-items: center;
  gap: 16px;
}

.window-controls {
  display: flex;
  gap: 8px;
}

.dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  box-shadow: 0 1px 2px rgba(0,0,0,0.1);
}

.dot.red { background: #FF5F56; border: 1px solid #E0443E; }
.dot.yellow { background: #FFBD2E; border: 1px solid #DEA123; }
.dot.green { background: #27C93F; border: 1px solid #1AAB29; }

.page-title {
  font-weight: 600;
  font-size: 16px;
  color: #333;
  letter-spacing: -0.02em;
}

.actions-section {
  display: flex;
  gap: 16px;
  align-items: center;
}

.glass-input-group {
  display: flex;
  gap: 10px;
}

/* macOS Select Styles Override */
:deep(.mac-select .el-input__wrapper) {
  background: rgba(255, 255, 255, 0.5);
  box-shadow: none !important;
  border-radius: 8px;
  padding: 4px 12px;
  border: 1px solid rgba(0,0,0,0.08);
  transition: all 0.2s;
}

:deep(.mac-select .el-input__wrapper:hover),
:deep(.mac-select .el-input__wrapper.is-focus) {
  background: rgba(255, 255, 255, 0.8);
  border-color: rgba(0,0,0,0.15);
}

:deep(.mac-select .el-input__inner) {
  font-size: 13px;
  font-weight: 500;
  color: #333;
}

/* Glass Button */
.glass-btn.mac-btn {
  background: rgba(255, 255, 255, 0.5);
  border: 1px solid rgba(0,0,0,0.08);
  color: #555;
  width: 36px;
  height: 36px;
  transition: all 0.2s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.glass-btn.mac-btn:hover {
  background: rgba(255, 255, 255, 0.9);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
  color: #000;
}

.glass-btn.mac-btn:active {
  transform: scale(0.95);
}

.glass-btn.danger:hover {
  background: rgba(255, 59, 48, 0.1);
  color: #FF3B30;
  border-color: rgba(255, 59, 48, 0.3);
}

/* Status Bar */
.status-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 24px;
  background: rgba(255, 255, 255, 0.3);
  border-bottom: 1px solid rgba(0,0,0,0.05);
  font-size: 12px;
  color: #666;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 6px;
  transition: all 0.2s;
}

.stat-item.active {
  background: rgba(255, 255, 255, 0.5);
  box-shadow: 0 1px 4px rgba(0,0,0,0.05);
  font-weight: 500;
}

.stat-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.stat-item.error .stat-dot { background: #FF3B30; box-shadow: 0 0 6px rgba(255, 59, 48, 0.4); }
.stat-item.error.active { color: #FF3B30; }

.stat-item.warning .stat-dot { background: #FF9F0A; box-shadow: 0 0 6px rgba(255, 159, 10, 0.4); }
.stat-item.warning.active { color: #8a5700; }

.stat-item.info .stat-dot { background: #32D74B; }
.stat-item.total .stat-label { font-weight: 600; }

.divider {
  width: 1px;
  height: 14px;
  background: rgba(0,0,0,0.1);
  margin: 0 4px;
}

.last-update {
  margin-left: auto;
  font-variant-numeric: tabular-nums;
  opacity: 0.6;
}

/* Terminal Window */
.terminal-window {
  flex: 1;
  background: rgba(30, 30, 30, 0.95);
  backdrop-filter: blur(10px);
  margin: 0;
  overflow: hidden;
  position: relative;
  display: flex;
  flex-direction: column;
}

.logs-container {
  flex: 1;
  overflow-y: auto;
  padding: 16px 0;
  font-family: 'JetBrains Mono', 'SF Mono', 'Menlo', monospace;
  font-size: 13px;
  line-height: 1.6;
}

.log-line {
  display: flex;
  padding: 2px 16px;
  color: #e0e0e0;
  transition: background 0.1s;
}

.log-line:hover {
  background: rgba(255,255,255,0.05);
}

.log-line.error { color: #FF6B6B; }
.log-line.warning { color: #FFD93D; }

.line-gutter {
  width: 40px;
  text-align: right;
  padding-right: 16px;
  color: #555;
  user-select: none;
  font-size: 12px;
}

.line-content {
  flex: 1;
  display: flex;
  gap: 12px;
  align-items: flex-start;
  word-break: break-all;
}

.time {
  color: #666;
  white-space: nowrap;
}

.service {
  display: inline-block;
  padding: 0 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  min-width: 45px;
  text-align: center;
}

/* Service Colors */
.service.backend { background: rgba(52, 120, 246, 0.2); color: #5B9BFF; }
.service.worker { background: rgba(175, 82, 222, 0.2); color: #D58BFF; }
.service.frontend { background: rgba(255, 149, 0, 0.2); color: #FFB340; }
.service.database { background: rgba(48, 209, 88, 0.2); color: #5EEA7D; }
.service.redis { background: rgba(255, 59, 48, 0.2); color: #FF6B6B; }
.service.mosquitto { background: rgba(142, 142, 147, 0.2); color: #A0A0A0; }

.message {
  flex: 1;
}

.placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #666;
  gap: 16px;
}

/* Scrollbar Customization */
.custom-scroll::-webkit-scrollbar {
  width: 10px;
  background: transparent;
}

.custom-scroll::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.15);
  border-radius: 5px;
  border: 2px solid rgba(30, 30, 30, 0.95);
}

.custom-scroll::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.25);
}

/* Loading Animation */
.loading-spinner {
  width: 24px;
  height: 24px;
  border: 2px solid rgba(255,255,255,0.1);
  border-left-color: #3478F6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
