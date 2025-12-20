<template>
  <div class="logs-page">
    <!-- Main Content Card -->
    <div class="glass-panel main-panel">
      <!-- Toolbar -->
      <div class="toolbar">
        <div class="filter-section">
          <el-select 
            v-model="selectedService" 
            placeholder="所有服务" 
            clearable 
            class="mac-select"
            popper-class="mac-dropdown"
          >
            <template #prefix><el-icon><Monitor /></el-icon></template>
            <el-option label="Backend" value="backend" />
            <el-option label="Worker" value="worker" />
            <el-option label="Frontend" value="frontend" />
            <el-option label="Database" value="database" />
            <el-option label="Redis" value="redis" />
            <el-option label="MQTT" value="mosquitto" />
          </el-select>
          
          <el-select 
            v-model="selectedLevel" 
            placeholder="所有级别" 
            clearable 
            class="mac-select"
            popper-class="mac-dropdown"
          >
            <template #prefix><el-icon><Filter /></el-icon></template>
            <el-option label="Error" value="error">
              <span class="dot error"></span>Error
            </el-option>
            <el-option label="Warning" value="warning">
              <span class="dot warning"></span>Warning
            </el-option>
            <el-option label="Info" value="info">
              <span class="dot info"></span>Info
            </el-option>
          </el-select>
        </div>

        <div class="actions-section">
          <el-button-group>
            <el-button class="mac-btn" @click="loadLogs" :loading="loading">
              <el-icon><Refresh /></el-icon>
            </el-button>
            <el-button class="mac-btn" @click="clearLogs" :loading="clearing">
              <el-icon><Delete /></el-icon>
            </el-button>
          </el-button-group>
        </div>
      </div>

      <!-- Logs Area -->
      <div class="logs-area custom-scroll" ref="logsContainer">
        <div v-if="loading && logs.length === 0" class="state-placeholder">
          <div class="spinner"></div>
          <span>加载中...</span>
        </div>
        
        <div v-else-if="logs.length === 0" class="state-placeholder">
          <el-icon :size="40"><Document /></el-icon>
          <span>暂无日志</span>
        </div>

        <div 
          v-else
          v-for="(log, idx) in filteredLogs" 
          :key="idx"
          class="log-row"
          :class="log.level"
        >
          <div class="col-index">{{ idx + 1 }}</div>
          <div class="col-time">{{ log.timestamp.split(' ')[1] }}</div>
          <div class="col-service">
            <span class="service-tag" :class="log.service">{{ getServiceShortName(log.service) }}</span>
          </div>
          <div class="col-message">{{ log.message }}</div>
        </div>
      </div>

      <!-- Status Footer -->
      <div class="status-footer">
        <div class="stat-group">
          <div class="stat-pill" :class="{ active: stats.error > 0 }">
            <span class="dot error"></span> {{ stats.error }} 错误
          </div>
          <div class="stat-pill" :class="{ active: stats.warning > 0 }">
            <span class="dot warning"></span> {{ stats.warning }} 警告
          </div>
        </div>
        <div class="update-time" v-if="lastUpdate">
          最后更新: {{ formatTime(lastUpdate) }}
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
.logs-page {
  padding: 24px;
  height: 100%;
  box-sizing: border-box;
}

.main-panel {
  height: 100%;
  border-radius: 24px;
  border: 1px solid rgba(255, 255, 255, 0.6);
  background: rgba(255, 255, 255, 0.65);
  backdrop-filter: blur(20px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.04);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Toolbar */
.toolbar {
  padding: 16px 24px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.filter-section {
  display: flex;
  gap: 12px;
}

.mac-select {
  width: 140px;
}

:deep(.mac-select .el-input__wrapper) {
  background: rgba(255, 255, 255, 0.5);
  box-shadow: none !important;
  border: 1px solid rgba(0, 0, 0, 0.05);
  border-radius: 8px;
}

:deep(.mac-select .el-input__wrapper:hover) {
  background: rgba(255, 255, 255, 0.8);
}

.mac-btn {
  background: rgba(255, 255, 255, 0.5);
  border: 1px solid rgba(0, 0, 0, 0.05);
  color: #606266;
}

.mac-btn:hover {
  background: #fff;
  color: #0071e3;
}

/* Logs Area */
.logs-area {
  flex: 1;
  overflow-y: auto;
  font-family: 'SF Mono', 'Menlo', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  background: rgba(255, 255, 255, 0.3);
}

.log-row {
  display: flex;
  padding: 8px 24px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.02);
  align-items: flex-start;
  line-height: 1.5;
  transition: background 0.1s;
}

.log-row:hover {
  background: rgba(255, 255, 255, 0.5);
}

.col-index {
  width: 40px;
  color: #8e8e93;
  flex-shrink: 0;
}

.col-time {
  width: 80px;
  color: #8e8e93;
  flex-shrink: 0;
}

.col-service {
  width: 90px;
  flex-shrink: 0;
  display: flex;
  justify-content: center;
}

.service-tag {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
  text-transform: uppercase;
}

.col-message {
  flex: 1;
  color: #1d1d1f;
  word-break: break-all;
  padding-left: 12px;
}

/* Service Colors */
.service-tag.backend { background: rgba(0, 113, 227, 0.1); color: #0071e3; }
.service-tag.worker { background: rgba(175, 82, 222, 0.1); color: #af52de; }
.service-tag.frontend { background: rgba(255, 149, 0, 0.1); color: #ff9500; }
.service-tag.database { background: rgba(52, 199, 89, 0.1); color: #34c759; }
.service-tag.redis { background: rgba(255, 59, 48, 0.1); color: #ff3b30; }
.service-tag.mosquitto { background: rgba(142, 142, 147, 0.1); color: #8e8e93; }

/* Levels */
.log-row.error .col-message { color: #ff3b30; }
.log-row.warning .col-message { color: #ff9f0a; }

/* Status Footer */
.status-footer {
  padding: 12px 24px;
  border-top: 1px solid rgba(0, 0, 0, 0.05);
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #86868b;
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.2);
}

.stat-group {
  display: flex;
  gap: 12px;
}

.stat-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 2px 8px;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.03);
  transition: all 0.2s;
}

.stat-pill.active {
  background: #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  font-weight: 500;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.dot.error { background: #ff3b30; }
.dot.warning { background: #ff9f0a; }
.dot.info { background: #34c759; }

.state-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #86868b;
  gap: 16px;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid rgba(0, 113, 227, 0.1);
  border-left-color: #0071e3;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Scrollbar */
.custom-scroll::-webkit-scrollbar {
  width: 10px;
}
.custom-scroll::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scroll::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 5px;
  border: 2px solid transparent;
  background-clip: content-box;
}
.custom-scroll::-webkit-scrollbar-thumb:hover {
  background-color: rgba(0, 0, 0, 0.2);
}
</style>
