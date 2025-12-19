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
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.progress-section {
  margin-bottom: 30px;
}

.progress-text {
  text-align: center;
  margin-top: 10px;
  color: #606266;
  font-size: 14px;
}

.summary-section {
  margin: 20px 0;
  padding: 20px;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e7ed 100%);
  border-radius: 8px;
}

.results-section {
  margin-top: 20px;
}

.result-card {
  margin-bottom: 0;
}

.result-card.result-ok {
  border-left: 3px solid #67c23a;
}

.result-card.result-warning {
  border-left: 3px solid #e6a23c;
}

.result-card.result-error {
  border-left: 3px solid #f56c6c;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.result-icon {
  font-size: 18px;
}

.result-name {
  font-weight: 600;
  flex: 1;
}

.result-message {
  color: #606266;
  margin-bottom: 10px;
}

.result-error {
  margin: 10px 0;
}

.result-error code {
  font-family: monospace;
  font-size: 12px;
  word-break: break-all;
}

.result-solution {
  margin: 10px 0;
}

.result-details {
  margin-top: 10px;
}

.empty-state {
  padding: 40px 0;
}

.tips {
  margin-top: 30px;
  text-align: left;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
}

.tips h4 {
  margin: 0 0 15px;
  color: #303133;
}

.tips ul {
  margin: 0;
  padding-left: 20px;
}

.tips li {
  margin-bottom: 5px;
  color: #606266;
}

.support-info {
  margin-top: 20px;
  text-align: right;
  color: #909399;
  font-size: 13px;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 5px;
}

.support-info a {
  color: #409eff;
  text-decoration: none;
}

.support-info a:hover {
  text-decoration: underline;
}
</style>
