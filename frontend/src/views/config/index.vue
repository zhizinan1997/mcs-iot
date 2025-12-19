<template>
  <div class="config-page">
    <el-tabs v-model="activeTab">
      <!-- Email Config -->
      <!-- Site Branding Config -->
      <el-tab-pane label="系统设置" name="site">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>系统品牌设置</span>
              <el-tag type="success">实时生效</el-tag>
            </div>
          </template>

          <el-form :model="siteConfig" label-width="120px">
            <el-form-item label="站点名称">
              <el-input 
                v-model="siteConfig.site_name" 
                placeholder="MCS-IoT"
                @input="previewTitle"
              >
                <template #append>左上角显示</template>
              </el-input>
            </el-form-item>

            <el-form-item label="Logo URL">
              <el-input 
                v-model="siteConfig.logo_url" 
                placeholder="https://example.com/logo.png"
              />
              <div v-if="siteConfig.logo_url" class="logo-preview">
                <img :src="siteConfig.logo_url" alt="Logo Preview" />
              </div>
            </el-form-item>

            <el-form-item label="浏览器标题">
              <el-input 
                v-model="siteConfig.browser_title" 
                placeholder="MCS-IoT Dashboard"
                @input="previewTitle"
              >
                <template #append>浏览器标签页标题</template>
              </el-input>
            </el-form-item>

            <el-form-item>
              <el-button 
                type="primary" 
                @click="saveSiteConfig" 
                :loading="saving"
              >保存配置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- Alarm Email Config -->
      <el-tab-pane label="邮件通知" name="email">
        <el-card>
          <el-form :model="emailConfig" label-width="120px">
            <el-form-item label="启用邮件通知">
              <el-switch v-model="emailConfig.enabled" />
            </el-form-item>
            <el-form-item label="SMTP 服务器">
              <el-input
                v-model="emailConfig.smtp_host"
                placeholder="smtp.qq.com"
              />
            </el-form-item>
            <el-form-item label="SMTP 端口">
              <el-input-number
                v-model="emailConfig.smtp_port"
                :min="1"
                :max="65535"
              />
            </el-form-item>
            <el-form-item label="发件人邮箱">
              <el-input
                v-model="emailConfig.sender"
                placeholder="your@email.com"
              />
            </el-form-item>
            <el-form-item label="邮箱密码/授权码">
              <el-input
                v-model="emailConfig.password"
                type="password"
                show-password
              />
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
              <el-button
                type="primary"
                @click="saveEmailConfig"
                :loading="saving"
                >保存配置</el-button
              >
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
            <el-form-item label="平台类型">
              <el-select v-model="webhookConfig.platform" style="width: 100%">
                <el-option label="自动检测" value="custom" />
                <el-option label="钉钉机器人" value="dingtalk" />
                <el-option label="飞书机器人" value="feishu" />
                <el-option label="企业微信机器人" value="wecom" />
              </el-select>
            </el-form-item>
            <el-form-item label="Webhook URL">
              <el-input
                v-model="webhookConfig.url"
                placeholder="粘贴机器人 Webhook 地址"
              />
            </el-form-item>
            <el-form-item
              label="加签密钥"
              v-if="webhookConfig.platform === 'dingtalk'"
            >
              <el-input
                v-model="webhookConfig.secret"
                placeholder="可选，钉钉机器人加签密钥"
                show-password
              />
              <div class="form-tip">
                如果机器人设置了加签安全，请填写 SEC 开头的密钥
              </div>
            </el-form-item>
            <el-form-item>
              <el-button
                type="primary"
                @click="saveWebhookConfig"
                :loading="saving"
                >保存配置</el-button
              >
              <el-button @click="testNotification('webhook')"
                >测试发送</el-button
              >
            </el-form-item>
          </el-form>

          <el-divider />

          <div class="tips">
            <h4>支持的平台:</h4>
            <ul>
              <li>
                <strong>钉钉机器人</strong> - 群设置 → 智能群助手 → 添加机器人
              </li>
              <li>
                <strong>飞书机器人</strong> - 群设置 → 群机器人 → 添加机器人
              </li>
              <li><strong>企业微信机器人</strong> - 群设置 → 添加群机器人</li>
            </ul>
            <p style="color: #e6a23c; margin-top: 10px">
              💡 提示：选择"自动检测"会根据 URL 自动识别平台类型
            </p>
          </div>
        </el-card>
      </el-tab-pane>

      <!-- MQTT Account Config -->
      <el-tab-pane label="MQTT账号" name="mqtt">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>MQTT 账号管理</span>
              <el-tag type="info">所有设备使用统一账号</el-tag>
            </div>
          </template>

          <el-form :model="mqttConfig" label-width="120px">
            <el-divider content-position="left">管理员账号</el-divider>
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="用户名">
                  <el-input
                    v-model="mqttConfig.admin_user"
                    placeholder="admin"
                  />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="密码">
                  <el-input
                    v-model="mqttConfig.admin_pass"
                    type="password"
                    show-password
                    placeholder="管理员密码"
                  />
                </el-form-item>
              </el-col>
            </el-row>

            <el-divider content-position="left">Worker 服务账号</el-divider>
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="用户名">
                  <el-input
                    v-model="mqttConfig.worker_user"
                    placeholder="worker"
                  />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="密码">
                  <el-input
                    v-model="mqttConfig.worker_pass"
                    type="password"
                    show-password
                    placeholder="Worker 密码"
                  />
                </el-form-item>
              </el-col>
            </el-row>

            <el-divider content-position="left">设备统一账号</el-divider>
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="用户名">
                  <el-input
                    v-model="mqttConfig.device_user"
                    placeholder="device"
                  />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="密码">
                  <el-input
                    v-model="mqttConfig.device_pass"
                    type="password"
                    show-password
                    placeholder="设备统一密码"
                  />
                </el-form-item>
              </el-col>
            </el-row>

            <el-form-item>
              <el-button
                type="primary"
                @click="saveMqttConfig"
                :loading="saving"
                >保存并重载</el-button
              >
              <el-button @click="reloadMqtt">仅重载配置</el-button>
            </el-form-item>
          </el-form>

          <el-divider />

          <div class="tips">
            <h4>使用说明:</h4>
            <ul>
              <li><strong>管理员账号</strong> - 用于 MQTT 调试工具连接</li>
              <li><strong>Worker 账号</strong> - 后台服务连接使用</li>
              <li>
                <strong>设备账号</strong> - 所有硬件设备使用此统一账号连接
              </li>
            </ul>

            <el-alert
              title="重要提示"
              type="warning"
              :closable="false"
              style="margin-top: 10px"
            >
              <template #default>
                <p>
                  修改
                  <strong>Worker 账号密码</strong>
                  后，需要管理员执行以下命令重启 Worker 容器：
                </p>
                <code
                  style="
                    background: #f5f5f5;
                    padding: 4px 8px;
                    border-radius: 4px;
                  "
                  >docker-compose restart worker</code
                >
              </template>
            </el-alert>

            <p style="color: #e6a23c; margin-top: 10px">
              ⚠️ 修改设备密码后，所有硬件设备也需要更新固件配置
            </p>
          </div>
        </el-card>
      </el-tab-pane>
    </el-tabs>


  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { configApi } from "../../api";

const activeTab = ref("site");
const saving = ref(false);

const emailConfig = reactive({
  enabled: false,
  smtp_host: "smtp.qq.com",
  smtp_port: 465,
  sender: "",
  password: "",
  receivers: [] as string[],
});

const webhookConfig = reactive({
  enabled: false,
  url: "",
  platform: "custom",
  secret: "",
});

const dashboardConfig = reactive({
  title: "MCS-IoT Dashboard",
  refresh_rate: 5,
  background_image: "",
});

const mqttConfig = reactive({
  admin_user: "admin",
  admin_pass: "",
  worker_user: "worker",
  worker_pass: "",
  device_user: "device",
  device_pass: "",
});







async function loadConfigs() {
  try {
    const [emailRes, webhookRes, dashboardRes] = await Promise.all([
      configApi.getEmail(),
      configApi.getWebhook(),
      configApi.getDashboard(),
    ]);
    Object.assign(emailConfig, emailRes.data);
    Object.assign(webhookConfig, webhookRes.data);
    Object.assign(dashboardConfig, dashboardRes.data);
  } catch (error) {
    console.error("Failed to load configs:", error);
  }
}

async function saveEmailConfig() {
  saving.value = true;
  try {
    await configApi.updateEmail(emailConfig);
    ElMessage.success("邮件配置已保存");
  } catch (error) {
    ElMessage.error("保存失败");
  } finally {
    saving.value = false;
  }
}

async function saveWebhookConfig() {
  saving.value = true;
  try {
    await configApi.updateWebhook(webhookConfig);
    ElMessage.success("Webhook配置已保存");
  } catch (error) {
    ElMessage.error("保存失败");
  } finally {
    saving.value = false;
  }
}



async function testNotification(channel: string) {
  ElMessage.info(`正在发送 ${channel} 测试通知...`);
  try {
    const response = await configApi.testNotification(channel);
    ElMessage.success(response.data.message || "测试通知发送成功");
  } catch (error: any) {
    const detail = error.response?.data?.detail || "发送失败，请检查配置";
    ElMessage.error(detail);
  }
}

async function saveMqttConfig() {
  saving.value = true;
  try {
    await configApi.updateMqtt(mqttConfig);
    ElMessage.success("MQTT 配置已保存并生效");
  } catch (error: any) {
    const detail = error.response?.data?.detail || "保存失败";
    ElMessage.error(detail);
  } finally {
    saving.value = false;
  }
}

async function reloadMqtt() {
  try {
    await configApi.reloadMqtt();
    ElMessage.success("Mosquitto 配置已重载");
  } catch (error: any) {
    const detail = error.response?.data?.detail || "重载失败";
    ElMessage.error(detail);
  }
}

async function loadMqttConfig() {
  try {
    const res = await configApi.getMqtt();
    Object.assign(mqttConfig, res.data);
  } catch (error) {
    console.error("Failed to load MQTT config:", error);
  }
}

// Site Config
const siteConfig = reactive({
  site_name: "",
  logo_url: "",
  browser_title: ""
})

async function loadSiteConfig() {
  try {
    const res = await configApi.getSite()
    Object.assign(siteConfig, res.data)
  } catch (error) {
    console.error("Failed to load site config:", error)
  }
}

async function saveSiteConfig() {
  saving.value = true
  try {
    const data = await configApi.updateSite(siteConfig)
    ElMessage.success("站点设置已保存")
    // Update document title immediately
    if (data.data.browser_title) {
      document.title = data.data.browser_title
    }
    // Update favicon if logo_url is set
    if (data.data.logo_url) {
      updateFavicon(data.data.logo_url)
    }
  } catch (error: any) {
    ElMessage.error("保存失败")
  } finally {
    saving.value = false
  }
}

function updateFavicon(url: string) {
  let link = document.querySelector("link[rel~='icon']") as HTMLLinkElement
  if (!link) {
    link = document.createElement('link')
    link.rel = 'icon'
    document.head.appendChild(link)
  }
  link.href = url
}

function previewTitle() {
  if (siteConfig.browser_title) {
    document.title = siteConfig.browser_title
  }
}

onMounted(() => {
  loadConfigs(); // This already loads email, webhook, dashboard  
  loadMqttConfig();
  loadSiteConfig();
});
</script>

<style scoped>
.config-page {
  width: 100%;
  height: 100%;
  padding: 24px;
  box-sizing: border-box;
  background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%);
  min-height: calc(100vh - 100px);
}

/* Tabs styling */
:deep(.el-tabs__header) {
  margin-bottom: 20px;
}

:deep(.el-tabs__item) {
  font-size: 15px;
  font-weight: 500;
  padding: 0 20px;
}

:deep(.el-tabs__item.is-active) {
  color: #409eff;
}

/* Card styling */
:deep(.el-card) {
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  border: none;
  overflow: hidden;
}

:deep(.el-card__header) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 16px 20px;
  border-bottom: none;
}

:deep(.el-card__body) {
  padding: 24px;
}

/* Form styling */
:deep(.el-form-item) {
  margin-bottom: 22px;
}

:deep(.el-form-item__label) {
  font-weight: 500;
  color: #606266;
}

:deep(.el-input__wrapper),
:deep(.el-select__wrapper) {
  border-radius: 8px;
}

:deep(.el-input-number) {
  width: 100%;
}

:deep(.el-divider__text) {
  font-weight: 600;
  color: #409eff;
  background: transparent;
}

/* Card header */
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.card-header span {
  font-size: 16px;
  font-weight: 600;
}

.card-header .el-tag {
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
}

/* Tips section */
.tips {
  background: linear-gradient(135deg, #f8f9fa 0%, #f1f3f5 100%);
  border-radius: 10px;
  padding: 16px 20px;
  margin-top: 16px;
  border-left: 4px solid #409eff;
}

.tips h4 {
  margin: 0 0 12px;
  color: #303133;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.tips h4::before {
  content: "💡";
}

.tips ul {
  margin: 0;
  padding-left: 20px;
}

.tips li {
  margin-bottom: 8px;
  color: #606266;
  line-height: 1.6;
}

.tips li strong {
  color: #303133;
}

/* Form tip */
.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 6px;
  line-height: 1.5;
}

/* Logo preview */
.logo-preview {
  margin-top: 12px;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 8px;
  display: inline-block;
}

.logo-preview img {
  max-height: 48px;
  max-width: 200px;
  display: block;
}

/* Zone color */
.zone-color {
  display: inline-block;
  width: 24px;
  height: 24px;
  border-radius: 6px;
  border: 2px solid rgba(0, 0, 0, 0.1);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

/* Upload area */
.upload-area {
  display: flex;
  gap: 12px;
  align-items: center;
}

/* Background preview */
.bg-preview {
  border: 2px dashed #dcdfe6;
  border-radius: 10px;
  padding: 16px;
  background: #fafafa;
  transition: all 0.3s;
}

.bg-preview:hover {
  border-color: #409eff;
}

.bg-preview img {
  max-width: 400px;
  max-height: 225px;
  display: block;
  border-radius: 6px;
}

/* Color dot */
.color-dot {
  display: inline-block;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid rgba(0, 0, 0, 0.1);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.15);
}

/* Button styling */
:deep(.el-button--primary) {
  border-radius: 8px;
  font-weight: 500;
  padding: 10px 24px;
}

:deep(.el-button--default) {
  border-radius: 8px;
}

/* Divider styling */
:deep(.el-divider) {
  margin: 24px 0;
}

:deep(.el-divider--horizontal) {
  border-color: #e4e7ed;
}

/* Alert styling */
:deep(.el-alert) {
  border-radius: 8px;
}

/* Switch styling */
:deep(.el-switch) {
  --el-switch-on-color: #67c23a;
}
</style>
