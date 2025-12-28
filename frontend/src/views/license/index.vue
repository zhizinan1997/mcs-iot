<!--
  MCS-IOT 授权管理页面 (License & Security Management)

  该文件负责系统的版权激活、硬件绑定验证及程序完整性校验。
  主要职责：
  1. 设备 ID 生成：基于服务器硬件特征（MAC、主机名等）生成的唯一编码，作为授权凭证。
  2. 离线/在线激活：通过与云端 Worker 通讯验证授权文件，管理过期时间与宽限期。
  3. 安全审计：实时监测核心代码是否被篡改（Tamper Detection），确保运行环境安全。
  4. 权限分级：根据授权状态动态启用/禁用 AI 分析、云归档等高级功能。

  技术栈：Vue 3 (setup), Element Plus UI & Alerts, Navigator Clipboard API.
-->
<template>
  <div class="license-page">
    <el-card class="glass-card">
      <!-- Header removed -->
      
      <!-- Device ID Section -->
      <div class="device-section">
        <div class="device-icon">
          <el-icon :size="32" color="#0071e3"><Monitor /></el-icon>
        </div>
        <div class="device-info">
          <h3>设备编码 (Device ID)</h3>
          <p class="subtitle">请将此编码发送给管理员以获取授权</p>
          <div class="code-box">
            <span class="code">{{ licenseInfo.device_id || '加载中...' }}</span>
            <el-button text bg circle @click="copyDeviceId">
              <el-icon><CopyDocument /></el-icon>
            </el-button>
          </div>
        </div>
        <div class="status-badge">
          <el-tag :type="statusTagType" size="large" effect="dark" round>
            {{ statusText }}
          </el-tag>
        </div>
      </div>

      <!-- Detail Grid -->
      <div class="detail-grid">
        <div class="detail-item glass-inset">
          <span class="label">客户名称</span>
          <span class="value">{{ licenseInfo.customer || '-' }}</span>
        </div>
        <div class="detail-item glass-inset">
          <span class="label">有效期至</span>
          <span class="value">{{ licenseInfo.expires_at || '-' }}</span>
        </div>
        <div class="detail-item glass-inset">
          <span class="label">上次验证</span>
          <span class="value">{{ formatTime(licenseInfo.last_check) || '-' }}</span>
        </div>
      </div>

      <!-- Action Area -->
      <div class="action-area">
        <el-button 
          type="primary" 
          size="large" 
          @click="verifyLicense" 
          :loading="verifying" 
          round
          class="verify-btn"
        >
          <el-icon><Refresh /></el-icon> 立即验证授权
        </el-button>
        
        <div class="grace-info" v-if="licenseInfo.grace_remaining_days">
          <el-icon color="#e6a23c"><WarningFilled /></el-icon>
          <span>宽限期还剩 <b>{{ licenseInfo.grace_remaining_days }}</b> 天</span>
        </div>
      </div>

      <!-- Alerts -->
      <div class="alert-section">
        <div class="mac-alert success" v-if="!licenseInfo.tampered">
          <div class="icon-wrapper"><el-icon><Check /></el-icon></div>
          <div class="alert-content">
            <h4>代码完整性验证通过</h4>
            <p>系统核心代码未被篡改，运行环境安全。</p>
          </div>
        </div>

        <div class="mac-alert danger" v-else>
          <div class="icon-wrapper"><el-icon><WarningFilled /></el-icon></div>
          <div class="alert-content">
            <h4>代码完整性校验失败</h4>
            <p>检测到核心代码被修改，请立即停止使用并联系技术支持。</p>
          </div>
        </div>

        <div class="mac-alert warning" v-if="licenseInfo.status === 'unlicensed' || licenseInfo.status === 'expired'">
          <div class="icon-wrapper"><el-icon><Lock /></el-icon></div>
          <div class="alert-content">
            <h4>功能受限</h4>
            <p>当前处于未授权状态，高级功能（AI分析、云归档、报警通知）已禁用。</p>
          </div>
        </div>
      </div>

      <!-- Mechanism Collapse -->
      <div class="mechanism-group">
        <el-collapse class="mac-collapse">
          <el-collapse-item name="1">
            <template #title>
              <span class="collapse-title"><el-icon><InfoFilled /></el-icon> 关于授权机制</span>
            </template>
            <div class="collapse-content">
              <p>设备编码基于以下硬件信息动态生成：</p>
              <ul>
                <li><strong>主机名</strong> - 服务器唯一标识</li>
                <li><strong>MAC 地址</strong> - 网卡物理地址</li>
                <li><strong>硬件特征</strong> - CPU/主板信息</li>
              </ul>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>

    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { CopyDocument, Refresh, WarningFilled, Check, Lock, InfoFilled, Monitor } from '@element-plus/icons-vue'
import { configApi } from '../../api'
import { emitLicenseUpdate } from '../../utils/licenseEvent'

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
  tampered?: boolean
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
    if (res.data) {
      Object.assign(licenseInfo, res.data)
    }
  } catch (error) {
    console.error('Failed to fetch local license info:', error)
  }
}

async function verifyLicense() {
  verifying.value = true
  try {
    const res = await configApi.verifyLicense()
    if (res.data) {
        Object.assign(licenseInfo, res.data)
    }
    
    if (res.data.valid) {
      ElMessage.success('授权验证成功')
    } else {
        // Even if valid is false, we might have got updated status/error from backend
        if (res.data.error) {
             ElMessage.warning(res.data.error)
        }
    }
    
    // 验证完成后，重新获取最新状态（包含 last_check 等信息）
    await fetchLicenseInfo()
    
    // 通知 MainLayout 刷新右上角授权状态
    emitLicenseUpdate()
  } catch (error: any) {
    const detail = error.response?.data?.detail || '无法连接到授权服务器'
    ElMessage.warning(detail)
    // If verify fails, fall back to local info to ensure we at least show Device ID
    await fetchLicenseInfo()
  } finally {
    verifying.value = false
  }
}

onMounted(async () => {
  // First fetch local info to show Device ID immediately
  await fetchLicenseInfo()
  // Then try to verify (which will also refresh and emit event)
  await verifyLicense()
})

async function copyDeviceId() {
  try {
    await navigator.clipboard.writeText(licenseInfo.device_id)
    ElMessage.success('设备编码已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败，请手动复制')
  }
}

function formatTime(isoString?: string) {
  if (!isoString) return ''
  try {
    return new Date(isoString).toLocaleString('zh-CN')
  } catch {
    return isoString
  }
}
</script>

<style scoped>
.license-page {
  padding: 24px;
  height: 100%;
  box-sizing: border-box;
}

.glass-card {
  height: 100%;
  border-radius: 24px !important;
  border: 1px solid rgba(255, 255, 255, 0.6) !important;
  background: rgba(255, 255, 255, 0.65) !important;
  backdrop-filter: blur(20px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.04) !important;
  display: flex;
  flex-direction: column;
}

:deep(.el-card__body) {
  padding: 32px !important;
  overflow-y: auto;
}

/* Device Section */
.device-section {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 24px;
  background: white;
  border-radius: 20px;
  margin-bottom: 24px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.03);
}

.device-icon {
  width: 64px;
  height: 64px;
  background: rgba(0, 113, 227, 0.08);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.device-info {
  flex: 1;
}

.device-info h3 {
  margin: 0;
  font-size: 18px;
  color: #1d1d1f;
  font-weight: 600;
}

.subtitle {
  margin: 4px 0 12px;
  color: #86868b;
  font-size: 13px;
}

.code-box {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #f5f5f7;
  padding: 8px 16px;
  border-radius: 10px;
  width: fit-content;
}

.code {
  font-family: 'SF Mono', monospace;
  font-size: 16px;
  font-weight: 600;
  color: #1d1d1f;
  letter-spacing: 1px;
}

/* Detail Grid */
.detail-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 32px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  padding: 16px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.5);
}

.detail-item .label {
  font-size: 12px;
  color: #86868b;
  margin-bottom: 4px;
}

.detail-item .value {
  font-size: 15px;
  font-weight: 600;
  color: #1d1d1f;
}

/* Action Area */
.action-area {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 32px;
}

.verify-btn {
  padding: 12px 32px;
  font-size: 16px;
  height: auto;
  box-shadow: 0 4px 12px rgba(0, 113, 227, 0.2);
}

.grace-info {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #e6a23c;
  background: rgba(230, 162, 60, 0.1);
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 14px;
}

/* Mac Alerts */
.mac-alert {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 16px;
  border-radius: 16px;
  margin-bottom: 16px;
}

.mac-alert.success { background: rgba(52, 199, 89, 0.1); }
.mac-alert.danger { background: rgba(255, 59, 48, 0.1); }
.mac-alert.warning { background: rgba(255, 149, 0, 0.1); }

.icon-wrapper {
  margin-top: 2px;
  font-size: 18px;
}
.mac-alert.success .icon-wrapper { color: #34c759; }
.mac-alert.danger .icon-wrapper { color: #ff3b30; }
.mac-alert.warning .icon-wrapper { color: #ff9500; }

.alert-content h4 {
  margin: 0 0 4px;
  font-size: 15px;
  font-weight: 600;
  color: #1d1d1f;
}

.alert-content p {
  margin: 0;
  font-size: 13px;
  color: #424245;
  line-height: 1.4;
}

/* Collapse Override */
.mac-collapse {
  border: none;
}
:deep(.el-collapse-item__header) {
  background: transparent;
  border: none;
  font-size: 14px;
  color: #86868b;
}
:deep(.el-collapse-item__wrap) {
  background: transparent;
  border: none;
}
:deep(.el-collapse-item__content) {
  color: #6e6e73;
  font-size: 13px;
}
</style>
