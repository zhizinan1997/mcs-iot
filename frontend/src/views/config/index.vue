<template>
  <div class="config-page-wrapper">
    <!-- Sidebar Navigation -->
    <div class="config-sidebar glass-panel">
      <div class="sidebar-header">
        <h3><el-icon><Setting /></el-icon> 系统配置</h3>
      </div>
      <div class="nav-menu">
        <div 
          v-for="item in navItems" 
          :key="item.id"
          class="nav-item"
          :class="{ active: activeSection === item.id }"
          @click="scrollToSection(item.id)"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </div>
      </div>
    </div>

    <!-- Main Content Area -->
    <div class="config-content full-scroll" @scroll="handleScroll">
      
      <!-- Site Branding Section -->
      <div id="section-site" class="config-section">
        <div class="section-card glass-panel">
           <div class="card-header">
             <div class="header-title">
               <el-icon><Monitor /></el-icon> 站点设置
             </div>
             <el-button type="primary" size="small" @click="saveSiteConfig" :loading="saving">保存配置</el-button>
           </div>
           <div class="card-body">
             <el-form :model="siteConfig" label-width="120px" label-position="left">
               <el-form-item label="站点名称">
                <el-input v-model="siteConfig.site_name" placeholder="MCS-IoT" @input="previewTitle">
                   <template #append>左上角显示</template>
                </el-input>
               </el-form-item>
               <el-form-item label="Logo URL">
                <el-input v-model="siteConfig.logo_url" placeholder="https://example.com/logo.png" />
                <div v-if="siteConfig.logo_url" class="logo-preview">
                  <img :src="siteConfig.logo_url" alt="Logo Preview" />
                </div>
               </el-form-item>
               <el-form-item label="浏览器标题">
                <el-input v-model="siteConfig.browser_title" placeholder="MCS-IoT Dashboard" @input="previewTitle">
                  <template #append>标签页标题</template>
                </el-input>
               </el-form-item>
             </el-form>
           </div>
        </div>
      </div>

      <!-- Email Section -->
      <div id="section-email" class="config-section">
        <div class="section-card glass-panel">
          <div class="card-header">
            <div class="header-title">
              <el-icon><Message /></el-icon> 邮件通知
            </div>
            <div class="header-actions">
              <button class="mac-action-btn" @click="testNotification('email')">测试发送</button>
              <el-button type="primary" size="small" @click="saveEmailConfig" :loading="saving">保存配置</el-button>
            </div>
          </div>
          <div class="card-body">
            <el-form :model="emailConfig" label-width="120px" label-position="left">
              <el-form-item label="启用邮件通知">
                <el-switch v-model="emailConfig.enabled" />
              </el-form-item>
              
              <div v-if="emailConfig.enabled" class="expanded-form">
                <el-form-item label="快速配置">
                  <el-button-group>
                    <el-button size="small" @click="apply163Preset">163邮箱</el-button>
                    <el-button size="small" @click="applyQQPreset">QQ邮箱</el-button>
                  </el-button-group>
                </el-form-item>
                <div class="form-row">
                  <el-form-item label="SMTP 服务器" class="half-width">
                    <el-input v-model="emailConfig.smtp_host" placeholder="smtp.qq.com" />
                  </el-form-item>
                  <el-form-item label="SMTP 端口" class="half-width">
                    <el-input-number v-model="emailConfig.smtp_port" :min="1" :max="65535" controls-position="right" />
                  </el-form-item>
                </div>
                <div class="form-row">
                  <el-form-item label="发件人邮箱" class="half-width">
                    <el-input v-model="emailConfig.sender" placeholder="your@email.com" />
                  </el-form-item>
                  <el-form-item label="授权码/密码" class="half-width">
                    <el-input v-model="emailConfig.password" type="password" show-password />
                  </el-form-item>
                </div>
                <el-form-item label="收件人列表">
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
              </div>
            </el-form>
          </div>
        </div>
      </div>

      <!-- Webhook Section -->
      <div id="section-webhook" class="config-section">
        <div class="section-card glass-panel">
          <div class="card-header">
            <div class="header-title">
              <el-icon><Connection /></el-icon> Webhook 机器人
            </div>
            <div class="header-actions">
              <button class="mac-action-btn" @click="testNotification('webhook')">测试发送</button>
              <el-button type="primary" size="small" @click="saveWebhookConfig" :loading="saving">保存配置</el-button>
            </div>
          </div>
          <div class="card-body">
            <el-form :model="webhookConfig" label-width="120px" label-position="left">
               <el-form-item label="启用 Webhook">
                 <el-switch v-model="webhookConfig.enabled" />
               </el-form-item>
               
               <div v-if="webhookConfig.enabled" class="expanded-form">
                 <el-form-item label="平台类型">
                   <el-radio-group v-model="webhookConfig.platform">
                     <el-radio-button label="custom">自动检测</el-radio-button>
                     <el-radio-button label="dingtalk">钉钉</el-radio-button>
                     <el-radio-button label="feishu">飞书</el-radio-button>
                     <el-radio-button label="wecom">企业微信</el-radio-button>
                   </el-radio-group>
                 </el-form-item>
                 <el-form-item label="Webhook URL">
                   <el-input v-model="webhookConfig.url" placeholder="粘贴机器人 Webhook 地址" />
                 </el-form-item>
                 <el-form-item label="加签密钥" v-if="webhookConfig.platform === 'dingtalk'">
                   <el-input v-model="webhookConfig.secret" show-password placeholder="可选，钉钉机器人加签密钥" />
                 </el-form-item>
                 <el-form-item label="触发关键词">
                   <el-input v-model="webhookConfig.keyword" placeholder="如果不涉及安全设置可留空" />
                 </el-form-item>
               </div>
            </el-form>
          </div>
        </div>
      </div>

      <!-- Alarm Section -->
      <div id="section-alarm" class="config-section">
        <div class="section-card glass-panel">
          <div class="card-header">
            <div class="header-title">
              <el-icon><Bell /></el-icon> 报警规则
            </div>
            <el-button type="primary" size="small" @click="saveAlarmGeneralConfig" :loading="saving">保存配置</el-button>
          </div>
          <div class="card-body">
             <el-form :model="alarmGeneralConfig" label-width="120px" label-position="left">
               <el-form-item label="报警消抖">
                  <div class="control-row">
                    <el-input-number v-model="alarmGeneralConfig.debounce_minutes" :min="1" :max="1440" />
                    <span class="unit-text">分钟内不重复报警</span>
                  </div>
               </el-form-item>
               
               <el-divider class="glass-divider" />
               
               <el-form-item label="静默时段">
                 <el-switch v-model="alarmGeneralConfig.time_restriction_enabled" inactive-text="全天接收通知" active-text="仅特定时段接收" />
               </el-form-item>
               
               <div v-if="alarmGeneralConfig.time_restriction_enabled" class="expanded-form">
                 <el-form-item label="接收日期">
                   <el-checkbox-group v-model="alarmGeneralConfig.time_restriction_days">
                      <el-checkbox-button v-for="day in 7" :key="day" :value="day">
                        周{{ ['一','二','三','四','五','六','日'][day-1] }}
                      </el-checkbox-button>
                   </el-checkbox-group>
                 </el-form-item>
                 <el-form-item label="接收时间">
                    <el-time-picker
                      is-range
                      v-model="alarmTimeRange"
                      range-separator="至"
                      start-placeholder="开始时间"
                      end-placeholder="结束时间"
                      format="HH:mm"
                      @change="handleTimeRangeChange"
                    />
                 </el-form-item>
               </div>
             </el-form>
          </div>
        </div>
      </div>

      <!-- MQTT Section -->
      <div id="section-mqtt" class="config-section">
        <div class="section-card glass-panel">
          <div class="card-header">
            <div class="header-title">
              <el-icon><Link /></el-icon> MQTT 服务
            </div>
            <div class="header-actions">
              <button class="mac-action-btn" @click="reloadMqtt">重载服务</button>
              <el-button type="primary" size="small" @click="saveMqttConfig" :loading="saving">保存配置</el-button>
            </div>
          </div>
          <div class="card-body">
             <el-form :model="mqttConfig" label-width="120px" label-position="left">
               <div class="mqtt-grid">
                 <div class="mqtt-group">
                   <h5>管理员账号 (调试)</h5>
                   <el-form-item label="用户名"><el-input v-model="mqttConfig.admin_user" /></el-form-item>
                   <el-form-item label="密码"><el-input v-model="mqttConfig.admin_pass" type="password" show-password /></el-form-item>
                 </div>
                 
                 <div class="mqtt-group">
                   <h5>Worker 服务账号</h5>
                   <el-form-item label="用户名"><el-input v-model="mqttConfig.worker_user" /></el-form-item>
                   <el-form-item label="密码"><el-input v-model="mqttConfig.worker_pass" type="password" show-password /></el-form-item>
                 </div>
                 
                 <div class="mqtt-group full-width">
                   <h5>设备接入账号 (统一)</h5>
                   <div class="form-row">
                     <el-form-item label="用户名" class="half-width"><el-input v-model="mqttConfig.device_user" /></el-form-item>
                     <el-form-item label="密码" class="half-width"><el-input v-model="mqttConfig.device_pass" type="password" show-password /></el-form-item>
                   </div>
                 </div>
               </div>
               
               <el-alert title="注意：修改 Worker 账号密码后需要手动重启后端容器" type="warning" show-icon :closable="false" class="mac-alert" />
             </el-form>
          </div>
        </div>
      </div>

      <div class="spacer"></div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { Setting, Monitor, Message, Connection, Bell, Link } from '@element-plus/icons-vue'
import { configApi } from "../../api";

const saving = ref(false);
const activeSection = ref("section-site");
const alarmTimeRange = ref<[Date, Date] | null>(null);

const navItems = [
  { id: 'section-site', label: '站点设置', icon: 'Monitor' },
  { id: 'section-email', label: '邮件通知', icon: 'Message' },
  { id: 'section-webhook', label: 'Webhook', icon: 'Connection' },
  { id: 'section-alarm', label: '报警规则', icon: 'Bell' },
  { id: 'section-mqtt', label: 'MQTT服务', icon: 'Link' },
];

/* --- Config Objects --- */
const siteConfig = reactive({ site_name: "", logo_url: "", browser_title: "" });
const emailConfig = reactive({ enabled: false, smtp_host: "smtp.qq.com", smtp_port: 465, sender: "", password: "", receivers: [] as string[] });
const webhookConfig = reactive({ enabled: false, url: "", platform: "custom", secret: "", keyword: "" });
const alarmGeneralConfig = reactive({ debounce_minutes: 10, time_restriction_enabled: false, time_restriction_days: [1, 2, 3, 4, 5], time_restriction_start: "08:00", time_restriction_end: "18:00" });
const mqttConfig = reactive({ admin_user: "admin", admin_pass: "", worker_user: "worker", worker_pass: "", device_user: "device", device_pass: "" });

/* --- Actions --- */
function scrollToSection(id: string) {
  const el = document.getElementById(id);
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    activeSection.value = id;
  }
}

function handleScroll(e: Event) {
  const container = e.target as HTMLElement;
  const scrollTop = container.scrollTop;
  
  // Iterate through sections to find which one is currently in view
  // We use a threshold (e.g., 100px) to determine "active" area
  let currentId = 'section-site';
  
  for (const item of navItems) {
    const el = document.getElementById(item.id);
    if (!el) continue;
    
    // Check if the section top is above the "trigger line" (viewport top + offset)
    if (el.offsetTop - 180 <= scrollTop) {
      currentId = item.id;
    }
  }
  
  activeSection.value = currentId;
}

/* --- Loaders --- */
async function loadAll() {
  try {
    const [site, email, webhook, alarm, mqtt] = await Promise.all([
      configApi.getSite(),
      configApi.getEmail(),
      configApi.getWebhook(),
      configApi.getAlarmGeneral(),
      configApi.getMqtt()
    ]);
    
    Object.assign(siteConfig, site.data);
    Object.assign(emailConfig, email.data);
    Object.assign(webhookConfig, webhook.data);
    Object.assign(alarmGeneralConfig, alarm.data);
    Object.assign(mqttConfig, mqtt.data);
    
    // Parse time range
    if (alarmGeneralConfig.time_restriction_start && alarmGeneralConfig.time_restriction_end) {
      const today = new Date().toISOString().split('T')[0];
      alarmTimeRange.value = [
        new Date(`${today}T${alarmGeneralConfig.time_restriction_start}`),
        new Date(`${today}T${alarmGeneralConfig.time_restriction_end}`)
      ];
    }
  } catch (err) {
    console.error(err);
  }
}

/* --- Savers --- */
async function saveSiteConfig() {
  await saveWrapper(() => configApi.updateSite(siteConfig), "站点设置已保存");
  if (siteConfig.browser_title) document.title = siteConfig.browser_title;
}

async function saveEmailConfig() {
  await saveWrapper(() => configApi.updateEmail(emailConfig), "邮件配置已保存");
}

async function saveWebhookConfig() {
  await saveWrapper(() => configApi.updateWebhook(webhookConfig), "Webhook配置已保存");
}

async function saveAlarmGeneralConfig() {
  await saveWrapper(() => configApi.updateAlarmGeneral(alarmGeneralConfig), "报警规则已保存");
}

async function saveMqttConfig() {
  await saveWrapper(() => configApi.updateMqtt(mqttConfig), "MQTT配置已保存");
}

/* --- Helpers --- */
async function saveWrapper(apiCall: () => Promise<any>, successMsg: string) {
  saving.value = true;
  try {
    await apiCall();
    ElMessage.success(successMsg);
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || "保存失败");
  } finally {
    saving.value = false;
  }
}

function previewTitle() {
  if (siteConfig.browser_title) document.title = siteConfig.browser_title;
}

function apply163Preset() {
  emailConfig.smtp_host = "smtp.163.com";
  emailConfig.smtp_port = 465;
  ElMessage.success("已应用163邮箱配置");
}

function applyQQPreset() {
  emailConfig.smtp_host = "smtp.qq.com";
  emailConfig.smtp_port = 465;
  ElMessage.success("已应用QQ邮箱配置");
}

async function testNotification(type: string) {
  try {
    const res = await configApi.testNotification(type);
    ElMessage.success(res.data.message || "测试发送成功");
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || "发送失败");
  }
}

async function reloadMqtt() {
  try {
    await configApi.reloadMqtt();
    ElMessage.success("服务已重载");
  } catch (e) { ElMessage.error("重载失败"); }
}

function handleTimeRangeChange(val: [Date, Date] | null) {
  if (val) {
    alarmGeneralConfig.time_restriction_start = val[0].toTimeString().slice(0, 5);
    alarmGeneralConfig.time_restriction_end = val[1].toTimeString().slice(0, 5);
  }
}

onMounted(() => {
  loadAll();
});
</script>

<style scoped>
.config-page-wrapper {
  display: flex;
  height: 100%;
  padding: 24px;
  gap: 24px;
  box-sizing: border-box;
}

/* Sidebar */
.config-sidebar {
  width: 200px;
  flex-shrink: 0;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.5);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.6);
  padding: 20px 12px;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 0 16px 16px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  margin-bottom: 12px;
}

.sidebar-header h3 {
  margin: 0;
  font-size: 16px;
  color: #1d1d1f;
  display: flex;
  align-items: center;
  gap: 8px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  border-radius: 10px;
  cursor: pointer;
  color: #6e6e73;
  transition: all 0.2s;
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 4px;
}

.nav-item:hover {
  background: rgba(0, 0, 0, 0.03);
  color: #1d1d1f;
}

.nav-item.active {
  background: #0071e3;
  color: #fff;
  box-shadow: 0 4px 12px rgba(0, 113, 227, 0.2);
}

/* Main Content */
.config-content {
  flex: 1;
  overflow-y: auto;
  border-radius: 20px;
  padding-right: 8px; /* Space for scrollbar */
}

.config-section {
  margin-bottom: 32px;
  scroll-margin-top: 20px; /* Offset for scrollIntoView */
}

/* Glass Panels */
.glass-panel {
  background: rgba(255, 255, 255, 0.65);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.04);
}

.card-header {
  padding: 16px 24px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(255, 255, 255, 0.3);
}

.header-title {
  font-size: 16px;
  font-weight: 600;
  color: #1d1d1f;
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-body {
  padding: 24px;
}

/* Form Styles */
.form-row {
  display: flex;
  gap: 20px;
}

.half-width {
  flex: 1;
}

.full-width {
  width: 100%;
}

.expanded-form {
  background: rgba(255, 255, 255, 0.4);
  border-radius: 12px;
  padding: 20px;
  margin-top: 16px;
}

.mac-action-btn {
  background: transparent;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  padding: 5px 12px;
  font-size: 13px;
  cursor: pointer;
  color: #606266;
  margin-right: 12px;
}
.mac-action-btn:hover {
  border-color: #0071e3;
  color: #0071e3;
}

.mqtt-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.mqtt-group {
  background: rgba(255, 255, 255, 0.4);
  padding: 16px;
  border-radius: 12px;
}

.mqtt-group h5 {
  margin: 0 0 16px;
  color: #86868b;
  font-size: 13px;
}

.mac-alert {
  margin-top: 24px;
  border-radius: 12px;
}

.control-row {
  display: flex;
  gap: 12px;
  align-items: center;
}

.unit-text {
  font-size: 13px;
  color: #86868b;
}

.logo-preview img {
  height: 40px;
  margin-top: 8px;
  border-radius: 4px;
}

.spacer {
  height: 100px;
}

/* Scrollbar */
.full-scroll::-webkit-scrollbar {
  width: 8px;
}
.full-scroll::-webkit-scrollbar-track {
  background: transparent;
}
.full-scroll::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 4px;
}
.full-scroll::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.2);
}
</style>
