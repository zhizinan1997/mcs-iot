<template>
  <div class="config-page">
    <el-tabs v-model="activeTab">
      <!-- Email Config -->
      <el-tab-pane label="邮件通知" name="email">
        <el-card>
          <el-form :model="emailConfig" label-width="120px">
            <el-form-item label="启用邮件通知">
              <el-switch v-model="emailConfig.enabled" />
            </el-form-item>
            <el-form-item label="SMTP 服务器">
              <el-input v-model="emailConfig.smtp_host" placeholder="smtp.qq.com" />
            </el-form-item>
            <el-form-item label="SMTP 端口">
              <el-input-number v-model="emailConfig.smtp_port" :min="1" :max="65535" />
            </el-form-item>
            <el-form-item label="发件人邮箱">
              <el-input v-model="emailConfig.sender" placeholder="your@email.com" />
            </el-form-item>
            <el-form-item label="邮箱密码/授权码">
              <el-input v-model="emailConfig.password" type="password" show-password />
            </el-form-item>
            <el-form-item label="收件人">
              <el-select
                v-model="emailConfig.receivers"
                multiple
                filterable
                allow-create
                default-first-option
                placeholder="输入邮箱后回车添加"
                style="width: 100%"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveEmailConfig" :loading="saving">保存配置</el-button>
              <el-button @click="testNotification('email')">测试发送</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- Webhook Config -->
      <el-tab-pane label="Webhook通知" name="webhook">
        <el-card>
          <el-form :model="webhookConfig" label-width="120px">
            <el-form-item label="启用Webhook">
              <el-switch v-model="webhookConfig.enabled" />
            </el-form-item>
            <el-form-item label="Webhook URL">
              <el-input 
                v-model="webhookConfig.url" 
                placeholder="钉钉/飞书/企业微信机器人地址"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveWebhookConfig" :loading="saving">保存配置</el-button>
              <el-button @click="testNotification('webhook')">测试发送</el-button>
            </el-form-item>
          </el-form>
          
          <el-divider />
          
          <div class="tips">
            <h4>支持的平台:</h4>
            <ul>
              <li>钉钉机器人 (群设置 → 智能群助手 → 添加机器人)</li>
              <li>飞书机器人 (群设置 → 群机器人 → 添加机器人)</li>
              <li>企业微信机器人</li>
            </ul>
          </div>
        </el-card>
      </el-tab-pane>

      <!-- Dashboard Config -->
      <el-tab-pane label="大屏配置" name="dashboard">
        <el-card>
          <el-form :model="dashboardConfig" label-width="120px">
            <el-form-item label="大屏标题">
              <el-input v-model="dashboardConfig.title" />
            </el-form-item>
            <el-form-item label="刷新频率(秒)">
              <el-input-number v-model="dashboardConfig.refresh_rate" :min="1" :max="60" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveDashboardConfig" :loading="saving">保存配置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { configApi } from '../../api'

const activeTab = ref('email')
const saving = ref(false)

const emailConfig = reactive({
  enabled: false,
  smtp_host: 'smtp.qq.com',
  smtp_port: 465,
  sender: '',
  password: '',
  receivers: [] as string[]
})

const webhookConfig = reactive({
  enabled: false,
  url: ''
})

const dashboardConfig = reactive({
  title: 'MCS-IoT Dashboard',
  refresh_rate: 5,
  background_image: ''
})

async function loadConfigs() {
  try {
    const [emailRes, webhookRes, dashboardRes] = await Promise.all([
      configApi.getEmail(),
      configApi.getWebhook(),
      configApi.getDashboard()
    ])
    Object.assign(emailConfig, emailRes.data)
    Object.assign(webhookConfig, webhookRes.data)
    Object.assign(dashboardConfig, dashboardRes.data)
  } catch (error) {
    console.error('Failed to load configs:', error)
  }
}

async function saveEmailConfig() {
  saving.value = true
  try {
    await configApi.updateEmail(emailConfig)
    ElMessage.success('邮件配置已保存')
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function saveWebhookConfig() {
  saving.value = true
  try {
    await configApi.updateWebhook(webhookConfig)
    ElMessage.success('Webhook配置已保存')
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function saveDashboardConfig() {
  saving.value = true
  try {
    await configApi.updateDashboard(dashboardConfig)
    ElMessage.success('大屏配置已保存')
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function testNotification(channel: string) {
  ElMessage.info(`测试 ${channel} 通知...`)
  // TODO: Call test API
}

onMounted(loadConfigs)
</script>

<style scoped>
.config-page {
  max-width: 800px;
}

.tips {
  color: #909399;
  font-size: 14px;
}

.tips h4 {
  margin: 0 0 8px;
  color: #606266;
}

.tips ul {
  margin: 0;
  padding-left: 20px;
}

.tips li {
  margin-bottom: 4px;
}
</style>
