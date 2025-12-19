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

      <!-- Code Integrity Status -->
      <el-divider />
      
      <div class="integrity-section">
        <h3>代码完整性状态</h3>
        
        <el-alert
          v-if="!licenseInfo.tampered"
          title="✓ 未检测到破解行为"
          type="success"
          :closable="false"
          show-icon
          style="margin-top: 12px;"
        >
          <template #default>
            <p>系统代码完整性验证通过，未发现非法修改。</p>
          </template>
        </el-alert>

        <el-alert
          v-else
          title="⚠️ 检测到代码被非法修改"
          type="error"
          :closable="false"
          show-icon
          style="margin-top: 12px;"
        >
          <template #default>
            <p><strong>严重警告：</strong>系统检测到授权验证代码被篡改！</p>
            <ul style="margin: 10px 0; padding-left: 20px;">
              <li>此行为已被记录并上报至授权服务器</li>
              <li>您的设备 ID 和违规记录已被永久保存</li>
              <li>此行为违反软件许可协议，可能导致法律责任</li>
              <li>请立即停止使用并联系技术支持</li>
            </ul>
          </template>
        </el-alert>
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

      <!-- Security Mechanism Section -->
      <div class="mechanism-section">
        <h3><el-icon><Warning /></el-icon> 授权机制说明</h3>
        
        <el-collapse>
          <el-collapse-item title="设备唯一编码生成" name="device-id">
            <p>设备编码基于以下硬件信息动态生成：</p>
            <ul>
              <li><strong>主机名</strong> - 服务器唯一标识</li>
              <li><strong>MAC 地址</strong> - 网卡物理地址</li>
              <li><strong>硬件特征</strong> - CPU/主板信息</li>
            </ul>
            <p class="security-note">
              这些信息经 <code>SHA-256</code> 安全哈希后生成不可逆的设备编码。
              更换硬件或迁移服务器将导致设备编码变化，需重新授权。
            </p>
          </el-collapse-item>
          
          <el-collapse-item title="动态激活验证" name="verification">
            <p>系统采用 <strong>云端动态验证</strong> 机制：</p>
            <ul>
              <li>每次启动时自动连接授权服务器校验</li>
              <li>每 24 小时自动重新验证</li>
              <li>验证设备编码与授权数据库匹配</li>
              <li>检查授权有效期和功能权限</li>
            </ul>
            <p class="security-note">
              <el-icon><Lock /></el-icon>
              授权服务器使用 TLS 加密通信，防止中间人攻击或伪造授权。
            </p>
          </el-collapse-item>
          
          <el-collapse-item title="宽限期与过期处理" name="grace">
            <p>当授权验证失败时：</p>
            <ul>
              <li><strong>宽限期 (3天)</strong> - 系统继续运行，但会显示警告</li>
              <li><strong>宽限期结束后</strong> - 高级功能被禁用</li>
            </ul>
            <el-alert type="info" :closable="false" style="margin-top: 10px;">
              <p>过期后被限制的功能包括：外网数据接收、AI 分析、云归档、报警通知，且设备数量限制为 10 台。</p>
            </el-alert>
          </el-collapse-item>
          
          <el-collapse-item title="防破解声明" name="security">
            <el-alert type="warning" :closable="false">
              <p><strong>⚠️ 安全警告</strong></p>
              <ul style="margin-top: 8px; padding-left: 20px;">
                <li>设备编码与硬件绑定，无法通过修改配置文件伪造</li>
                <li>授权状态由远程服务器实时验证，本地无有效授权数据</li>
                <li>任何尝试绕过授权的行为将被服务器记录并可能导致永久封禁</li>
                <li>未授权使用本系统属于违法行为，将追究法律责任</li>
              </ul>
            </el-alert>
          </el-collapse-item>
        </el-collapse>
      </div>

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
import { CopyDocument, Refresh, Message, Warning, Lock } from '@element-plus/icons-vue'
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
  // Then try to verify
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

function formatTime(isoString: string) {
  if (!isoString) return ''
  try {
    return new Date(isoString).toLocaleString('zh-CN')
  } catch {
    return isoString
  }
}

// Automatically verify license on every page load/refresh
onMounted(() => {
  verifyLicense()
})
</script>

<style scoped>
.license-page {
  padding: 0;
  max-width: 900px;
  margin: 0 auto;
}

.license-card {
  border-radius: 20px !important;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 18px;
  font-weight: 600;
  color: #1d1d1f;
}

.device-id-section {
  text-align: center;
  padding: 24px 0;
}

.device-id-section h3 {
  margin-bottom: 16px;
  color: #1d1d1f;
  font-weight: 600;
}

.device-id-box {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  background: linear-gradient(135deg, #f5f5f7 0%, #e8e8ed 100%);
  padding: 24px;
  border-radius: 16px;
  margin-bottom: 12px;
  border: 1px solid rgba(0, 0, 0, 0.05);
}

.device-id {
  font-family: 'SF Mono', SFMono-Regular, ui-monospace, Menlo, monospace;
  font-size: 26px;
  font-weight: 700;
  letter-spacing: 3px;
  color: #1d1d1f;
}

.hint {
  color: #86868b;
  font-size: 13px;
  font-weight: 500;
}

.status-section h3,
.contact-section h3,
.mechanism-section h3 {
  margin-bottom: 20px;
  color: #1d1d1f;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.grace-warning {
  color: #e6a23c;
  font-weight: 700;
  font-size: 16px;
}

.contact-section {
  text-align: center;
  padding: 16px 0;
}

.contact-email {
  margin-top: 20px;
  font-size: 18px;
}

.contact-email .el-link {
  font-size: 18px;
  font-weight: 600;
}

/* Mechanism Section */
.mechanism-section {
  padding: 16px 0;
}

.mechanism-section h3 {
  color: #86868b;
}

:deep(.el-collapse) {
  border: none;
}

:deep(.el-collapse-item__header) {
  background: rgba(0, 0, 0, 0.02);
  border-radius: 12px;
  padding: 0 16px;
  margin-bottom: 8px;
  font-weight: 600;
  color: #1d1d1f;
  border: none;
  height: 52px;
}

:deep(.el-collapse-item__wrap) {
  border: none;
}

:deep(.el-collapse-item__content) {
  padding: 16px 20px;
  color: #424245;
  line-height: 1.6;
}

.mechanism-section ul {
  padding-left: 20px;
  margin: 12px 0;
}

.mechanism-section li {
  margin-bottom: 8px;
}

.security-note {
  background: rgba(88, 86, 214, 0.05);
  border-radius: 10px;
  padding: 12px 16px;
  margin-top: 12px;
  color: #5856d6;
  font-size: 13px;
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.security-note code {
  background: rgba(0, 0, 0, 0.05);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'SF Mono', monospace;
  font-size: 12px;
}

/* Button styling */
:deep(.el-button--primary) {
  background-color: #0071e3;
  border-color: #0071e3;
  border-radius: 14px;
  font-weight: 600;
}

:deep(.el-button--primary:hover) {
  background-color: #0077ed;
}

/* Descriptions styling */
:deep(.el-descriptions) {
  border-radius: 12px;
  overflow: hidden;
}

/* Tag styling */
:deep(.el-tag) {
  border-radius: 8px;
  font-weight: 600;
}

/* Alert styling */
:deep(.el-alert) {
  border-radius: 14px;
}

/* Divider */
:deep(.el-divider) {
  margin: 28px 0;
}
</style>
