<template>
  <div class="license-page">
    <el-card class="license-card">
      <template #header>
        <div class="card-header">
          <span>授权管理</span>
          <el-tag :type="statusTagType" size="large">{{ statusText }}</el-tag>
        </div>
      </template>

      <!-- Device ID Section -->
      <div class="device-id-section">
        <h3>设备编码</h3>
        <div class="device-id-box">
          <span class="device-id">{{ licenseInfo.device_id || '加载中...' }}</span>
          <el-button type="primary" size="small" @click="copyDeviceId">
            <el-icon><CopyDocument /></el-icon> 复制
          </el-button>
        </div>
        <p class="hint">请将此编码发送给管理员以获取授权</p>
      </div>

      <el-divider />

      <!-- License Status Section -->
      <div class="status-section">
        <h3>授权状态</h3>
        
        <el-descriptions :column="1" border>
          <el-descriptions-item label="状态">
            <el-tag :type="statusTagType">{{ statusText }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="客户名称" v-if="licenseInfo.customer">
            {{ licenseInfo.customer }}
          </el-descriptions-item>
          <el-descriptions-item label="有效期至" v-if="licenseInfo.expires_at">
            {{ licenseInfo.expires_at }}
          </el-descriptions-item>
          <el-descriptions-item label="上次验证" v-if="licenseInfo.last_check">
            {{ formatTime(licenseInfo.last_check) }}
          </el-descriptions-item>
          <el-descriptions-item label="宽限期剩余" v-if="licenseInfo.grace_remaining_days">
            <span class="grace-warning">{{ licenseInfo.grace_remaining_days }} 天</span>
          </el-descriptions-item>
        </el-descriptions>

        <el-button 
          type="primary" 
          @click="verifyLicense" 
          :loading="verifying" 
          style="margin-top: 20px;"
        >
          <el-icon><Refresh /></el-icon> 立即验证
        </el-button>
      </div>

      <!-- Grace Period Warning -->
      <el-alert
        v-if="licenseInfo.status === 'grace'"
        title="宽限期警告"
        type="warning"
        :closable="false"
        show-icon
        style="margin-top: 20px;"
      >
        <template #default>
          <p>
            授权验证失败，系统正处于宽限期。
            <strong>剩余 {{ licenseInfo.grace_remaining_days }} 天</strong> 后系统将进入限制模式。
          </p>
        </template>
      </el-alert>

      <!-- Unlicensed Warning -->
      <el-alert
        v-if="licenseInfo.status === 'unlicensed' || licenseInfo.status === 'expired'"
        title="未授权"
        type="error"
        :closable="false"
        show-icon
        style="margin-top: 20px;"
      >
        <template #default>
          <p>系统未授权或授权已过期。以下功能将被限制：</p>
          <ul style="margin: 10px 0; padding-left: 20px;">
            <li>MQTT 外网数据接收</li>
            <li>AI 智能分析</li>
            <li>R2 云存储归档</li>
            <li>报警通知</li>
            <li>设备数量限制为 10 台</li>
          </ul>
        </template>
      </el-alert>

      <el-divider />

      <!-- Contact Section -->
      <div class="contact-section">
        <h3>获取授权</h3>
        <p>如需获取授权，请将上方设备编码发送至：</p>
        <div class="contact-email">
          <el-link type="primary" :href="'mailto:' + licenseInfo.contact">
            <el-icon><Message /></el-icon>
            {{ licenseInfo.contact || 'zinanzhi@gmail.com' }}
          </el-link>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { CopyDocument, Refresh, Message } from '@element-plus/icons-vue'
import { configApi } from '../../api'

interface LicenseInfo {
  device_id: string
  status: string
  expires_at?: string
  customer?: string
  last_check?: string
  grace_remaining_days?: number
  error?: string
  contact: string
  features: string[]
}

const licenseInfo = reactive<LicenseInfo>({
  device_id: '',
  status: 'unlicensed',
  contact: 'zinanzhi@gmail.com',
  features: []
})

const verifying = ref(false)

const statusText = computed(() => {
  switch (licenseInfo.status) {
    case 'active': return '已授权'
    case 'grace': return '宽限期'
    case 'expired': return '已过期'
    case 'unlicensed': return '未授权'
    default: return '未知'
  }
})

const statusTagType = computed(() => {
  switch (licenseInfo.status) {
    case 'active': return 'success'
    case 'grace': return 'warning'
    case 'expired': return 'danger'
    case 'unlicensed': return 'info'
    default: return 'info'
  }
})

async function fetchLicenseInfo() {
  try {
    const res = await configApi.getLicense()
    Object.assign(licenseInfo, res.data)
  } catch (error) {
    console.error('Failed to fetch license info:', error)
    ElMessage.error('获取授权信息失败')
  }
}

async function verifyLicense() {
  verifying.value = true
  try {
    const res = await configApi.verifyLicense()
    Object.assign(licenseInfo, res.data)
    
    if (res.data.valid) {
      ElMessage.success('授权验证成功')
    } else {
      ElMessage.warning(res.data.error || '授权验证失败')
    }
  } catch (error: any) {
    const detail = error.response?.data?.detail || '验证失败'
    ElMessage.error(detail)
  } finally {
    verifying.value = false
  }
}

async function copyDeviceId() {
  try {
    await navigator.clipboard.writeText(licenseInfo.device_id)
    ElMessage.success('设备编码已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败，请手动复制')
  }
}

function formatTime(isoString: string) {
  if (!isoString) return ''
  try {
    return new Date(isoString).toLocaleString('zh-CN')
  } catch {
    return isoString
  }
}

onMounted(fetchLicenseInfo)
</script>

<style scoped>
.license-page {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.license-card {
  border-radius: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 18px;
  font-weight: 600;
}

.device-id-section {
  text-align: center;
  padding: 20px 0;
}

.device-id-section h3 {
  margin-bottom: 15px;
  color: #606266;
}

.device-id-box {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 15px;
  background: #f5f7fa;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 10px;
}

.device-id {
  font-family: 'Courier New', monospace;
  font-size: 24px;
  font-weight: bold;
  letter-spacing: 2px;
  color: #303133;
}

.hint {
  color: #909399;
  font-size: 13px;
}

.status-section h3,
.contact-section h3 {
  margin-bottom: 15px;
  color: #606266;
}

.grace-warning {
  color: #e6a23c;
  font-weight: bold;
  font-size: 16px;
}

.contact-section {
  text-align: center;
  padding: 10px 0;
}

.contact-email {
  margin-top: 15px;
  font-size: 18px;
}

.contact-email .el-link {
  font-size: 18px;
}
</style>
