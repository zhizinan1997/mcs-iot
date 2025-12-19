<template>
  <div class="health-check-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>🔍 系统自检</span>
          <el-button type="primary" @click="runHealthCheck" :loading="running" :disabled="running">
            {{ running ? '正在检测...' : '开始自检' }}
          </el-button>
        </div>
      </template>

      <!-- Progress Bar -->
      <div v-if="running || completed" class="progress-section">
        <el-progress 
          :percentage="progress" 
          :status="progressStatus"
          :stroke-width="20"
          :format="progressFormat"
        />
        <div class="progress-text">
          {{ statusMessage }}
        </div>
      </div>

      <!-- Results Summary -->
      <div v-if="completed && results" class="summary-section">
        <el-row :gutter="20">
          <el-col :span="6">
            <el-statistic title="检查项" :value="results.total_checks" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="通过" :value="results.passed">
              <template #suffix>
                <span style="color: #67c23a;">✓</span>
              </template>
            </el-statistic>
          </el-col>
          <el-col :span="6">
            <el-statistic title="警告" :value="results.warnings">
              <template #suffix>
                <span style="color: #e6a23c;">⚠</span>
              </template>
            </el-statistic>
          </el-col>
          <el-col :span="6">
            <el-statistic title="错误" :value="results.errors">
              <template #suffix>
                <span style="color: #f56c6c;">✕</span>
              </template>
            </el-statistic>
          </el-col>
        </el-row>
      </div>

      <!-- Check Results List -->
      <div v-if="checkResults.length > 0" class="results-section">
        <el-divider content-position="left">检测结果</el-divider>
        
        <el-timeline>
          <el-timeline-item
            v-for="item in checkResults"
            :key="item.id"
            :type="getTimelineType(item.status)"
            :hollow="item.status === 'pending'"
            :timestamp="item.latency_ms ? `${item.latency_ms}ms` : ''"
            placement="top"
          >
            <el-card :class="['result-card', `result-${item.status}`]">
              <div class="result-header">
                <span class="result-icon">{{ getStatusIcon(item.status) }}</span>
                <span class="result-name">{{ item.name }}</span>
                <el-tag 
                  :type="getTagType(item.status)" 
                  size="small"
                >
                  {{ getStatusText(item.status) }}
                </el-tag>
              </div>
              <div class="result-message">{{ item.message }}</div>
              
              <!-- Error Details and Solution -->
              <div v-if="item.error" class="result-error">
                <el-alert type="error" :closable="false">
                  <template #title>错误详情</template>
                  <code>{{ item.error }}</code>
                </el-alert>
              </div>
              
              <div v-if="item.solution" class="result-solution">
                <el-alert type="warning" :closable="false">
                  <template #title>💡 可能原因与解决方案</template>
                  {{ item.solution }}
                </el-alert>
              </div>
              
              <!-- Details -->
              <div v-if="item.details && Object.keys(item.details).length" class="result-details">
                <el-descriptions :column="2" size="small" border>
                  <el-descriptions-item 
                    v-for="(value, key) in item.details" 
                    :key="key"
                    :label="key"
                  >
                    {{ typeof value === 'object' ? JSON.stringify(value) : value }}
                  </el-descriptions-item>
                </el-descriptions>
              </div>
            </el-card>
          </el-timeline-item>
        </el-timeline>
      </div>

      <!-- Initial State -->
      <div v-if="!running && !completed" class="empty-state">
        <el-empty description="点击「开始自检」按钮检查系统运行状况">
          <template #image>
            <div style="font-size: 80px;">🩺</div>
          </template>
        </el-empty>
        
        <div class="tips">
          <h4>自检将检查以下系统组件：</h4>
          <el-row :gutter="20">
            <el-col :span="8">
              <ul>
                <li>数据库 (TimescaleDB) 连接</li>
                <li>缓存服务 (Redis) 连接</li>
                <li>MQTT 代理 (Mosquitto) 状态</li>
                <li>后台工作进程 (Worker)</li>
                <li>授权状态 (License)</li>
              </ul>
            </el-col>
            <el-col :span="8">
              <ul>
                <li>数据库网络连通性</li>
                <li>Redis 网络连通性</li>
                <li>MQTT 网络连通性</li>
                <li>数据库表结构完整性</li>
                <li>数据库存储空间</li>
              </ul>
            </el-col>
            <el-col :span="8">
              <ul>
                <li>Redis 内存使用</li>
                <li>设备统计</li>
                <li>报警系统状态</li>
                <li>R2 归档配置</li>
                <li>AI 接口配置</li>
              </ul>
            </el-col>
          </el-row>
        </div>
      </div>
    </el-card>
    
    <!-- Support Info -->
    <div class="support-info">
      <el-icon><InfoFilled /></el-icon>
      技术支持邮箱: <a href="mailto:zinanzhi@gmail.com">zinanzhi@gmail.com</a>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { InfoFilled } from '@element-plus/icons-vue'
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
const statusMessage = ref('')
const results = ref<HealthCheckResults | null>(null)
const checkResults = ref<CheckResult[]>([])

const progressStatus = computed(() => {
  if (!completed.value) return ''
  if (results.value?.errors && results.value.errors > 0) return 'exception'
  if (results.value?.warnings && results.value.warnings > 0) return 'warning'
  return 'success'
})

function progressFormat(percentage: number) {
  return `${percentage}%`
}

function getTimelineType(status: string) {
  switch (status) {
    case 'ok': return 'success'
    case 'warning': return 'warning'
    case 'error': return 'danger'
    default: return 'info'
  }
}

function getTagType(status: string) {
  switch (status) {
    case 'ok': return 'success'
    case 'warning': return 'warning'
    case 'error': return 'danger'
    default: return 'info'
  }
}

function getStatusIcon(status: string) {
  switch (status) {
    case 'ok': return '✅'
    case 'warning': return '⚠️'
    case 'error': return '❌'
    default: return '⏳'
  }
}

function getStatusText(status: string) {
  switch (status) {
    case 'ok': return '通过'
    case 'warning': return '警告'
    case 'error': return '异常'
    default: return '检测中'
  }
}

async function runHealthCheck() {
  running.value = true
  completed.value = false
  progress.value = 0
  checkResults.value = []
  results.value = null
  statusMessage.value = '正在初始化系统检测...'

  try {
    // 初始化延时
    await new Promise<void>(resolve => setTimeout(resolve, 500))
    
    // 模拟进度动画 - 前期缓慢增长
    statusMessage.value = '正在连接各系统组件...'
    const progressInterval = setInterval(() => {
      if (progress.value < 15) {
        progress.value += 1
      }
    }, 100)

    await new Promise<void>(resolve => setTimeout(resolve, 1500))
    statusMessage.value = '正在执行深度检测...'
    
    // 调用 API
    const response = await api.get('/health-check/run')
    
    clearInterval(progressInterval)
    
    // 获取结果
    const allResults = response.data.results as CheckResult[]
    const totalItems = allResults.length
    
    // 计算每项延时 (总共约12秒显示所有项目, 每项约800ms)
    const delayPerItem = 800
    
    for (let i = 0; i < allResults.length; i++) {
      const item = allResults[i]
      if (item) {
        // 显示当前正在检测的项目
        statusMessage.value = `正在检测: ${item.name}...`
        
        // 等待一段时间，模拟检测过程
        await new Promise<void>(resolve => setTimeout(resolve, delayPerItem))
        
        // 添加结果
        checkResults.value.push(item)
        
        // 更新进度 (15% 已经完成，剩余 85% 分配给所有项目)
        progress.value = 15 + Math.round(((i + 1) / totalItems) * 85)
      }
    }
    
    // 完成
    progress.value = 100
    results.value = response.data
    
    // 等待一下再显示最终结果
    await new Promise<void>(resolve => setTimeout(resolve, 300))
    
    statusMessage.value = response.data.overall_status === 'healthy' 
      ? '✅ 系统自检完成，所有组件运行正常' 
      : response.data.overall_status === 'warning'
      ? '⚠️ 系统自检完成，有部分项目需要关注'
      : '❌ 系统自检完成，发现异常请查看详情'
    
    completed.value = true
    
  } catch (error: any) {
    ElMessage.error('自检请求失败: ' + (error.response?.data?.detail || error.message))
    statusMessage.value = '❌ 自检失败，无法连接后端服务'
    progress.value = 100
    completed.value = true
  } finally {
    running.value = false
  }
}
</script>

<style scoped>
.health-check-page {
  padding: 0; /* Layout provides padding */
}

/* Glass Card Global Style */
:deep(.el-card) {
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.04);
  border-radius: 18px;
}

:deep(.el-card__header) {
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  padding: 16px 24px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header span {
  font-size: 17px;
  font-weight: 600;
  color: #1d1d1f;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* Progress Section */
.progress-section {
  margin-bottom: 32px;
  padding: 0 12px;
}

:deep(.el-progress-bar__outer) {
  background-color: rgba(0, 0, 0, 0.05) !important;
}

.progress-text {
  text-align: center;
  margin-top: 12px;
  color: #86868b;
  font-size: 13px;
  font-weight: 500;
}

/* Summary Section */
.summary-section {
  margin: 24px 0;
  padding: 24px;
  background: rgba(0, 0, 0, 0.02);
  border-radius: 12px;
}

:deep(.el-statistic__content) {
  font-weight: 600;
  color: #1d1d1f;
}

:deep(.el-statistic__head) {
  font-size: 13px;
  color: #86868b;
  margin-bottom: 4px;
}

/* Results Section */
.results-section {
  margin-top: 32px;
}

:deep(.el-divider__text) {
  background-color: transparent;
  color: #86868b;
  font-weight: 500;
  font-size: 13px;
}

:deep(.el-timeline-item__node) {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

/* Result Cards - Cleaner Look */
.result-card {
  margin-bottom: 0;
  background: rgba(255, 255, 255, 0.5) !important;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.02) !important;
  border: 1px solid rgba(0, 0, 0, 0.03) !important;
  transition: transform 0.2s ease;
}

.result-card:hover {
  transform: translateY(-1px);
  background: rgba(255, 255, 255, 0.8) !important;
}

/* Status Indicators */
.result-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.result-icon {
  font-size: 16px;
}

.result-name {
  font-weight: 600;
  flex: 1;
  color: #1d1d1f;
  font-size: 15px;
}

.result-message {
  color: #424245;
  margin-bottom: 12px;
  font-size: 14px;
  padding-left: 28px; /* Align with name */
}

/* Alerts inside cards */
:deep(.el-alert) {
  border-radius: 10px;
  padding: 12px;
}

.result-error, .result-solution {
  margin: 12px 0 12px 28px;
}

.result-error code {
  font-family: 'SF Mono', SFMono-Regular, ui-monospace, Menlo, monospace;
  font-size: 12px;
  background: rgba(0,0,0,0.05);
  padding: 2px 4px;
  border-radius: 4px;
  color: #d70015;
}

/* Details */
.result-details {
  margin-top: 12px;
  margin-left: 28px;
}

:deep(.el-descriptions__body) {
  background: transparent;
}

/* Empty State */
.empty-state {
  padding: 60px 0;
}

.tips {
  margin-top: 40px;
  padding: 24px;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.03);
}

.tips h4 {
  margin: 0 0 16px;
  color: #1d1d1f;
  font-weight: 600;
}

.tips ul {
  padding-left: 18px;
}

.tips li {
  margin-bottom: 8px;
  color: #86868b;
  font-size: 13px;
}

/* Support Info */
.support-info {
  margin-top: 24px;
  text-align: right;
  color: #86868b;
  font-size: 12px;
  font-weight: 500;
  opacity: 0.8;
}

.support-info a {
  color: #0071e3;
  text-decoration: none;
  transition: color 0.2s;
}

.support-info a:hover {
  color: #0077ed;
  text-decoration: underline;
}

/* Button override */
:deep(.el-button--primary) {
  background-color: #0071e3;
  border-color: #0071e3;
  border-radius: 18px;
  font-weight: 500;
  padding: 8px 16px;
}

:deep(.el-button--primary:hover) {
  background-color: #0077ed;
  border-color: #0077ed;
}

:deep(.el-button.is-disabled) {
  background-color: rgba(0, 113, 227, 0.3);
  border-color: transparent;
}
</style>
