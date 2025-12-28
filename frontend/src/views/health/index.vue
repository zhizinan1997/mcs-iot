<!--
  MCS-IOT 系统健康自检页面 (System Health & Diagnostics)

  该文件用于全方位扫描系统组件状态，提供工业级的故障排查辅助。
  主要职责：
  1. 多维度扫描：涵盖数据库连接、Redis 缓存、MQTT Broker 响应、Worker 进程心跳及磁盘空间监测。
  2. 实时可视化：采用动画仪表盘形式展示扫描进度，逐项呈现检测结果。
  3. 故障修复建议：针对异常项提供具体的“建议方案” (Solution)，指导运维人员快速排障。
  4. 延迟监测：记录各项服务的毫秒级延迟，辅助性能评估。

  技术栈：Vue 3 (setup), Element Plus Icons & Animations, RESTful API Simulation.
-->
<template>
  <div class="health-page">
    <div class="health-container">
      
      <!-- Diagnostic Dashboard Header -->
      <div class="status-dashboard" :class="dashboardStatusClass">
        <div class="status-ring-wrapper">
          <div class="status-ring">
            <el-icon v-if="!running && !completed" class="status-icon"><FirstAidKit /></el-icon>
            <el-icon v-else-if="running" class="status-icon is-loading"><Loading /></el-icon>
            <el-icon v-else-if="results?.overall_status === 'healthy'" class="status-icon success"><Check /></el-icon>
            <el-icon v-else class="status-icon warning"><Warning /></el-icon>
          </div>
        </div>
        
        <div class="status-info">
          <h2 class="status-title">{{ statusTitle }}</h2>
          <p class="status-desc">{{ statusMessage }}</p>
          
          <el-button 
            type="primary" 
            size="large" 
            round 
            @click="runHealthCheck" 
            :loading="running"
            class="action-btn"
          >
            {{ running ? '正在全面扫描...' : (completed ? '重新扫描' : '开始系统自检') }}
          </el-button>
        </div>
      </div>

      <!-- Stats Grid (Result Summary) -->
      <div class="stats-grid" v-if="completed && results">
        <div class="stat-card">
          <div class="stat-value">{{ results.total_checks }}</div>
          <div class="stat-label">检查项</div>
        </div>
        <div class="stat-card success">
          <div class="stat-value">{{ results.passed }}</div>
          <div class="stat-label">通过</div>
        </div>
        <div class="stat-card warning" :class="{ 'has-value': results.warnings > 0 }">
          <div class="stat-value">{{ results.warnings }}</div>
          <div class="stat-label">警告</div>
        </div>
        <div class="stat-card error" :class="{ 'has-value': results.errors > 0 }">
          <div class="stat-value">{{ results.errors }}</div>
          <div class="stat-label">异常</div>
        </div>
      </div>

      <!-- Live Scan List -->
      <div class="scan-list-wrapper" v-if="checkResults.length > 0">
        <div class="list-header">检测详情</div>
        <div class="scan-list">
           <div 
             v-for="item in checkResults" 
             :key="item.id" 
             class="scan-item"
             :class="item.status"
           >
             <div class="scan-icon">
               <el-icon v-if="item.status === 'ok'"><Check /></el-icon>
               <el-icon v-else-if="item.status === 'pending'"><Loading /></el-icon>
               <el-icon v-else-if="item.status === 'warning'"><WarningFilled /></el-icon>
               <el-icon v-else><CloseBold /></el-icon>
             </div>
             
             <div class="scan-content">
               <div class="scan-row-main">
                 <span class="scan-name">{{ item.name }}</span>
                 <span class="scan-latency" v-if="item.latency_ms">{{ item.latency_ms }}ms</span>
               </div>
               
               <div class="scan-details" v-if="item.error || item.message">
                 <div class="scan-message">{{ item.message }}</div>
                 <div class="scan-error" v-if="item.error">{{ item.error }}</div>
                 <div class="scan-solution" v-if="item.solution">
                   <el-icon><collection-tag /></el-icon> 建议: {{ item.solution }}
                 </div>
               </div>
             </div>
           </div>
        </div>
      </div>

      <!-- Support Info -->
      <div class="support-footer">
        遇到无法解决的问题？联系技术支持 team@mcs-iot.com
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { FirstAidKit, Check, CloseBold, Warning, WarningFilled, Loading, CollectionTag } from '@element-plus/icons-vue'
import api from '../../api'

interface CheckResult {
  id: string
  name: string
  status: 'ok' | 'warning' | 'error' | 'pending'
  message?: string
  error?: string
  solution?: string
  latency_ms?: number
  details?: Record<string, any>
}

interface HealthCheckResults {
  overall_status: string
  timestamp: number
  results: CheckResult[]
  total_checks: number
  passed: number
  warnings: number
  errors: number
}

const running = ref(false)
const completed = ref(false)
const progress = ref(0)
/* Removed unused statusMessage ref (it is now computed) */
const results = ref<HealthCheckResults | null>(null)
const checkResults = ref<CheckResult[]>([])

/* Computed Properties for UI Status */
const statusTitle = computed(() => {
  if (running.value) return '正在进行系统自检'
  if (!completed.value) return '系统健康诊断'
  if (results.value?.overall_status === 'healthy') return '系统运行正常'
  return '发现系统异常'
})

const statusMessage = computed(() => {
  if (running.value) return `检测进度 ${progress.value}% - 正在扫描关键组件...`
  if (!completed.value) return '即刻开始全方位系统诊断，确保各项服务稳定运行。'
  if (results.value?.overall_status === 'healthy') return '所有核心组件连接正常，未发现错误。'
  return '请检查下方异常列表并尝试建议的修复方案。'
})

const dashboardStatusClass = computed(() => {
  if (running.value) return 'is-running'
  if (!completed.value) return 'is-ready'
  return results.value?.overall_status === 'healthy' ? 'is-success' : 'is-error'
})

async function runHealthCheck() {
  running.value = true
  completed.value = false
  progress.value = 0
  checkResults.value = []
  results.value = null
  
  try {
    // Stage 1: Init
    await new Promise(r => setTimeout(r, 500))
    progress.value = 10
    
    // Stage 2: Call API
    const response = await api.get('/health-check/run')
    const allResults = response.data.results as CheckResult[]
    progress.value = 20
    
    // Stage 3: Simulate stream of results
    const delayPerItem = 600
    for (let i = 0; i < allResults.length; i++) {
      const item = allResults[i]
      if (item) {
        await new Promise(r => setTimeout(r, delayPerItem))
        checkResults.value.push(item)
        progress.value = 20 + Math.floor(((i + 1) / allResults.length) * 80)
      }
    }

    results.value = response.data
    completed.value = true
    progress.value = 100
    
  } catch (error: any) {
    ElMessage.error('自检请求失败')
    completed.value = true
  } finally {
    running.value = false
  }
}
</script>

<style scoped>
.health-page {
  padding: 40px 20px;
  min-height: 100%;
  box-sizing: border-box;
  display: flex;
  justify-content: center;
}

.health-container {
  width: 100%;
  max-width: 720px;
  display: flex;
  flex-direction: column;
  gap: 32px;
}

/* Dashboard Header */
.status-dashboard {
  background: white;
  border-radius: 24px;
  padding: 40px;
  text-align: center;
  box-shadow: 0 10px 30px rgba(0,0,0,0.04);
  transition: all 0.3s ease;
  border: 1px solid rgba(0,0,0,0.05);
}

.status-ring-wrapper {
  display: flex;
  justify-content: center;
  margin-bottom: 24px;
}

.status-ring {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: #f5f5f7;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36px;
  transition: all 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.status-icon { color: #86868b; }
.status-icon.success { color: #32d74b; }
.status-icon.warning { color: #ff9f0a; }

.status-dashboard.is-running .status-ring {
  background: #e3f2fd;
  color: #0071e3;
  animation: pulse 2s infinite;
}

.status-dashboard.is-success .status-ring {
  background: #d1fae5;
  transform: scale(1.1);
}

.status-dashboard.is-error .status-ring {
  background: #fee2e2;
  color: #ef4444;
}

.status-title {
  font-size: 24px;
  font-weight: 700;
  color: #1d1d1f;
  margin: 0 0 8px;
}

.status-desc {
  font-size: 15px;
  color: #86868b;
  margin: 0 0 24px;
}

.action-btn {
  width: 180px;
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(0,113,227,0.2);
}

@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(0, 113, 227, 0.4); }
  70% { box-shadow: 0 0 0 15px rgba(0, 113, 227, 0); }
  100% { box-shadow: 0 0 0 0 rgba(0, 113, 227, 0); }
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-top: 16px;
}

.stat-card {
  background: white;
  padding: 16px;
  border-radius: 16px;
  text-align: center;
  box-shadow: 0 2px 8px rgba(0,0,0,0.02);
  border: 1px solid rgba(0,0,0,0.03);
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #1d1d1f;
  line-height: 1.2;
}

.stat-label {
  font-size: 12px;
  color: #86868b;
  margin-top: 4px;
}

.stat-card.success .stat-value { color: #32d74b; }
.stat-card.warning.has-value .stat-value { color: #ff9f0a; }
.stat-card.error.has-value .stat-value { color: #ff3b30; }

/* Scan List */
.scan-list-wrapper {
  background: white;
  border-radius: 20px;
  padding: 24px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.02);
}

.list-header {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
  color: #1d1d1f;
}

.scan-item {
  display: flex;
  gap: 16px;
  padding: 16px;
  border-bottom: 1px solid #f5f5f7;
  transition: all 0.2s;
}

.scan-item:last-child {
  border-bottom: none;
}

.scan-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: #f5f5f7;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  color: #86868b;
}

.scan-item.ok .scan-icon { background: #e8f5e9; color: #32d74b; }
.scan-item.warning .scan-icon { background: #fff3e0; color: #ff9f0a; }
.scan-item.error .scan-icon { background: #ffebee; color: #ef4444; }

.scan-content {
  flex: 1;
}

.scan-row-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.scan-name {
  font-weight: 600;
  color: #1d1d1f;
}

.scan-latency {
  font-size: 12px;
  color: #86868b;
  font-family: monospace;
  background: #f5f5f7;
  padding: 2px 6px;
  border-radius: 4px;
}

.scan-message {
  font-size: 13px;
  color: #424245;
  margin-bottom: 4px;
}

.scan-error {
  font-size: 12px;
  color: #ef4444;
  background: #fff5f5;
  padding: 4px 8px;
  border-radius: 4px;
  margin-top: 4px;
  font-family: monospace;
}

.scan-solution {
  font-size: 12px;
  color: #e6a23c;
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.support-footer {
  text-align: center;
  font-size: 12px;
  color: #999;
  margin-top: 20px;
}
</style>
