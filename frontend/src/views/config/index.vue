<!--
  MCS-IOT 全局系统配置页面 (System Settings Cluster)

  该文件是系统参数的集中控制中心，集成了站点个性化、通知服务及长连接配置。
  核心模块：
  1. 站点设置：管理站点名称、Logo 上传（联动图标展示）及浏览器标题预览。
  2. 邮件通知：配置 SMTP 授权信息，支持主流邮箱预设与多收件人管理。
  3. Webhook 联动：对接钉钉、飞书、企业微信等外部机器人，支持加签安全验证。
  4. 报警规则：全局配置报警消抖时长及基于周期的静默时段设置。
  5. MQTT 运维：精细化管理管理员、Worker 及设备接入的三类账号凭据。
  6. 交互特性：采用左侧导航+右侧滚动锚点联动的布局，提升配置效率。

  技术栈：Vue 3 (setup), Element Plus Dashboard UI, Axios Asset Upload.
-->
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
               <el-form-item label="Logo 图片">
                 <div class="logo-upload-area">
                   <el-button @click="triggerLogoInput" :loading="uploadingLogo" size="small">
                     <el-icon><Upload /></el-icon> 上传Logo
                   </el-button>
                   <el-button @click="clearLogo" :disabled="!siteConfig.logo_url" size="small" type="danger" plain>
                     清除
                   </el-button>
                   <input
                     ref="logoInputRef"
                     type="file"
                     accept="image/*"
                     style="display: none"
                     @change="handleLogoSelect"
                   />
                 </div>
                 <div v-if="siteConfig.logo_url" class="logo-preview">
                   <img :src="siteConfig.logo_url" alt="Logo Preview" />
                   <span class="preview-hint">此图片将用于左上角Logo和浏览器标签页图标</span>
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

      <!-- Admin Account Section -->
      <div id="section-admin" class="config-section">
        <div class="section-card glass-panel">
          <div class="card-header">
            <div class="header-title">
              <el-icon><User /></el-icon> 管理员账号
            </div>
            <el-button type="primary" size="small" @click="saveAdminPassword" :loading="savingAdminPwd">修改密码</el-button>
          </div>
          <div class="card-body">
             <el-form :model="adminPasswordForm" label-width="120px" label-position="left">
               <div class="mqtt-group">
                 <h5>修改登录密码</h5>
                 <el-form-item label="当前密码">
                   <el-input v-model="adminPasswordForm.current_password" type="password" show-password placeholder="请输入当前登录密码" />
                 </el-form-item>
                 <div class="form-row">
                   <el-form-item label="新密码" class="half-width">
                     <el-input v-model="adminPasswordForm.new_password" type="password" show-password placeholder="至少6位" />
                   </el-form-item>
                   <el-form-item label="确认密码" class="half-width">
                     <el-input v-model="adminPasswordForm.confirm_password" type="password" show-password placeholder="再次输入新密码" />
                   </el-form-item>
                 </div>
               </div>
               
               <el-alert 
                 title="修改密码后，部署信息中的密码记录将自动同步更新" 
                 type="info" 
                 show-icon 
                 :closable="false" 
                 class="mac-alert" 
               />
             </el-form>
          </div>
        </div>
      </div>

      <!-- Deploy Info Section -->
      <div id="section-deploy" class="config-section">
        <div class="section-card glass-panel">
          <div class="card-header">
            <div class="header-title">
              <el-icon><InfoFilled /></el-icon> 部署信息
            </div>
            <el-button size="small" @click="loadDeployInfo" :loading="loadingDeployInfo">刷新</el-button>
          </div>
          <div class="card-body">
            <div v-if="!deployInfo.exists" class="deploy-info-empty">
              <el-alert 
                :title="deployInfo.message || '部署信息文件不存在'" 
                type="warning" 
                show-icon 
                :closable="false" 
              />
              <p class="deploy-hint">该文件仅在首次使用 deploy.sh 脚本部署时自动生成，包含所有部署时设置的密码和配置。</p>
            </div>
            
            <div v-else class="deploy-info-content">
              <!-- 部署时间 -->
              <div class="info-group">
                <h5>📅 部署信息</h5>
                <div class="info-row">
                  <span class="info-label">部署时间:</span>
                  <code class="info-value">{{ deployInfo.parsed.deploy_time || '未知' }}</code>
                </div>
              </div>
              
              <!-- 域名 -->
              <div class="info-group" v-if="Object.keys(deployInfo.parsed.domains || {}).length > 0">
                <h5>🌐 域名配置</h5>
                <div v-for="(domain, name) in deployInfo.parsed.domains" :key="name" class="info-row">
                  <span class="info-label">{{ name }}:</span>
                  <a :href="domain" target="_blank" class="info-value link">{{ domain }}</a>
                </div>
              </div>
              
              <!-- 账号密码 -->
              <div class="info-group">
                <h5>🔑 账号密码</h5>
                <div class="credentials-grid">
                  <div class="credential-card" v-if="deployInfo.parsed.database?.password">
                    <div class="credential-title">数据库 (postgres)</div>
                    <div class="credential-password">
                      <code>{{ showPasswords ? deployInfo.parsed.database.password : '••••••••' }}</code>
                    </div>
                  </div>
                  <div class="credential-card" v-if="deployInfo.parsed.admin?.password">
                    <div class="credential-title">后台管理员 (admin)</div>
                    <div class="credential-password">
                      <code>{{ showPasswords ? deployInfo.parsed.admin.password : '••••••••' }}</code>
                    </div>
                  </div>
                  <div class="credential-card" v-if="deployInfo.parsed.mqtt?.password">
                    <div class="credential-title">MQTT (admin/worker/zhizinan)</div>
                    <div class="credential-password">
                      <code>{{ showPasswords ? deployInfo.parsed.mqtt.password : '••••••••' }}</code>
                    </div>
                  </div>
                </div>
                <el-button 
                  size="small" 
                  :type="showPasswords ? 'danger' : 'primary'" 
                  plain
                  @click="showPasswords = !showPasswords"
                  style="margin-top: 12px"
                >
                  <el-icon><View v-if="!showPasswords" /><Hide v-else /></el-icon>
                  {{ showPasswords ? '隐藏密码' : '显示密码' }}
                </el-button>
              </div>
              
              <el-alert 
                title="安全提示：此信息包含敏感凭据，请勿泄露给他人" 
                type="warning" 
                show-icon 
                :closable="false" 
                class="mac-alert" 
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Backup/Restore Section -->
      <div id="section-backup" class="config-section">
        <div class="section-card glass-panel">
          <div class="card-header">
            <div class="header-title">
              <el-icon><Download /></el-icon> 配置备份与恢复
            </div>
          </div>
          <div class="card-body">
            <div class="backup-restore-content">
              <!-- Export -->
              <div class="backup-group">
                <h5>📤 导出配置</h5>
                <p class="backup-desc">将当前所有系统配置导出为 JSON 文件，用于备份或迁移到新部署。</p>
                <el-button type="primary" @click="exportConfig" :loading="exporting">
                  <el-icon><Download /></el-icon>
                  导出配置 JSON
                </el-button>
              </div>
              
              <el-divider />
              
              <!-- Import -->
              <div class="backup-group">
                <h5>📥 导入配置</h5>
                <p class="backup-desc">从 JSON 文件恢复配置。支持向后兼容：新版本中新增的配置项会保留默认值。</p>
                
                <div class="import-area">
                  <el-upload
                    class="config-uploader"
                    :auto-upload="false"
                    :show-file-list="false"
                    accept=".json"
                    @change="handleConfigFileSelect"
                  >
                    <el-button type="success" plain>
                      <el-icon><Upload /></el-icon>
                      选择 JSON 文件
                    </el-button>
                  </el-upload>
                  
                  <div v-if="selectedConfigFile" class="selected-file">
                    <span class="file-name">{{ selectedConfigFile.name }}</span>
                    <el-button size="small" type="primary" @click="importConfig" :loading="importing">
                      确认导入
                    </el-button>
                    <el-button size="small" @click="selectedConfigFile = null">取消</el-button>
                  </div>
                </div>
                
                <div v-if="importResult" class="import-result" :class="importResult.success ? 'success' : 'error'">
                  <div class="result-title">{{ importResult.message }}</div>
                  <div class="result-stats">
                    成功导入: {{ importResult.imported_count }} 项，跳过: {{ importResult.skipped_count }} 项
                  </div>
                  <div v-if="importResult.source_export_time" class="result-meta">
                    原导出时间: {{ importResult.source_export_time }}
                  </div>
                  <div v-if="importResult.errors && importResult.errors.length > 0" class="result-errors">
                    <div v-for="err in importResult.errors" :key="err" class="error-item">{{ err }}</div>
                  </div>
                </div>
              </div>
              
              <el-alert 
                title="提示：导入配置后请刷新页面以查看更新后的设置" 
                type="info" 
                show-icon 
                :closable="false" 
                class="mac-alert" 
              />
            </div>
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
import { Setting, Monitor, Message, Connection, Bell, User, Upload, InfoFilled, View, Hide, Download } from '@element-plus/icons-vue'
import { configApi, uploadApi, usersApi } from "../../api";

const saving = ref(false);
const uploadingLogo = ref(false);
const logoInputRef = ref<HTMLInputElement | null>(null);
const activeSection = ref("section-site");
const alarmTimeRange = ref<[Date, Date] | null>(null);

const navItems = [
  { id: 'section-site', label: '站点设置', icon: 'Monitor' },
  { id: 'section-email', label: '邮件通知', icon: 'Message' },
  { id: 'section-webhook', label: 'Webhook', icon: 'Connection' },
  { id: 'section-alarm', label: '报警规则', icon: 'Bell' },
  { id: 'section-admin', label: '管理员账号', icon: 'User' },
  { id: 'section-deploy', label: '部署信息', icon: 'InfoFilled' },
  { id: 'section-backup', label: '配置备份', icon: 'Download' },
];

/* --- Config Objects --- */
const siteConfig = reactive({ site_name: "", logo_url: "", browser_title: "" });
const emailConfig = reactive({ enabled: false, smtp_host: "smtp.qq.com", smtp_port: 465, sender: "", password: "", receivers: [] as string[] });
const webhookConfig = reactive({ enabled: false, url: "", platform: "custom", secret: "", keyword: "" });
const alarmGeneralConfig = reactive({ debounce_minutes: 10, time_restriction_enabled: false, time_restriction_days: [1, 2, 3, 4, 5], time_restriction_start: "08:00", time_restriction_end: "18:00" });

/* --- Admin Password --- */
const savingAdminPwd = ref(false);
const adminPasswordForm = reactive({ current_password: "", new_password: "", confirm_password: "" });

/* --- Deploy Info --- */
const loadingDeployInfo = ref(false);
const showPasswords = ref(false);
const deployInfo = reactive({
  exists: false,
  message: "",
  parsed: {
    deploy_time: "",
    domains: {} as Record<string, string>,
    database: { password: "" },
    admin: { password: "" },
    mqtt: { password: "" }
  }
});

async function loadDeployInfo() {
  loadingDeployInfo.value = true;
  try {
    const res = await configApi.getDeployInfo();
    Object.assign(deployInfo, res.data);
  } catch (error) {
    console.error("Failed to load deploy info", error);
  } finally {
    loadingDeployInfo.value = false;
  }
}

/* --- Config Export/Import --- */
const exporting = ref(false);
const importing = ref(false);
const selectedConfigFile = ref<File | null>(null);
const importResult = ref<any>(null);

async function exportConfig() {
  exporting.value = true;
  try {
    const res = await configApi.exportConfig();
    const data = res.data;
    
    // 生成文件名
    const timestamp = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '');
    const filename = `mcs-iot-config-${timestamp}.json`;
    
    // 下载 JSON 文件
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    ElMessage.success(`配置已导出: ${filename}`);
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || "导出失败");
  } finally {
    exporting.value = false;
  }
}

function handleConfigFileSelect(uploadFile: any) {
  selectedConfigFile.value = uploadFile.raw;
  importResult.value = null;
}

async function importConfig() {
  if (!selectedConfigFile.value) return;
  
  importing.value = true;
  try {
    const text = await selectedConfigFile.value.text();
    const configData = JSON.parse(text);
    
    const res = await configApi.importConfig(configData);
    importResult.value = res.data;
    
    if (res.data.success) {
      ElMessage.success(`配置导入成功: ${res.data.imported_count} 项`);
      // 重新加载所有配置
      await loadAll();
    }
  } catch (error: any) {
    if (error instanceof SyntaxError) {
      importResult.value = { success: false, message: "JSON 格式无效", imported_count: 0, skipped_count: 0 };
    } else {
      importResult.value = { success: false, message: error.response?.data?.detail || "导入失败", imported_count: 0, skipped_count: 0 };
    }
    ElMessage.error(importResult.value.message);
  } finally {
    importing.value = false;
    selectedConfigFile.value = null;
  }
}

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
    const [site, email, webhook, alarm] = await Promise.all([
      configApi.getSite(),
      configApi.getEmail(),
      configApi.getWebhook(),
      configApi.getAlarmGeneral()
    ]);
    
    Object.assign(siteConfig, site.data);
    Object.assign(emailConfig, email.data);
    Object.assign(webhookConfig, webhook.data);
    Object.assign(alarmGeneralConfig, alarm.data);
    
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

async function saveAdminPassword() {
  // 验证表单
  if (!adminPasswordForm.current_password) {
    ElMessage.error("请输入当前密码");
    return;
  }
  if (!adminPasswordForm.new_password || adminPasswordForm.new_password.length < 6) {
    ElMessage.error("新密码至少6位");
    return;
  }
  if (adminPasswordForm.new_password !== adminPasswordForm.confirm_password) {
    ElMessage.error("两次输入的新密码不一致");
    return;
  }
  
  savingAdminPwd.value = true;
  try {
    await usersApi.changeAdminPassword(adminPasswordForm.current_password, adminPasswordForm.new_password);
    ElMessage.success("密码修改成功");
    // 清空表单
    adminPasswordForm.current_password = "";
    adminPasswordForm.new_password = "";
    adminPasswordForm.confirm_password = "";
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || "密码修改失败");
  } finally {
    savingAdminPwd.value = false;
  }
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



function handleTimeRangeChange(val: [Date, Date] | null) {
  if (val) {
    alarmGeneralConfig.time_restriction_start = val[0].toTimeString().slice(0, 5);
    alarmGeneralConfig.time_restriction_end = val[1].toTimeString().slice(0, 5);
  }
}

/* --- Logo Upload --- */
function triggerLogoInput() {
  logoInputRef.value?.click();
}

async function handleLogoSelect(event: Event) {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];
  if (!file) return;
  
  uploadingLogo.value = true;
  try {
    const res = await uploadApi.uploadImage(file);
    siteConfig.logo_url = res.data.url;
    ElMessage.success("Logo 上传成功");
  } catch (error: any) {
    const detail = error.response?.data?.detail || "上传失败";
    ElMessage.error(detail);
  } finally {
    uploadingLogo.value = false;
    if (target) target.value = "";
  }
}

function clearLogo() {
  siteConfig.logo_url = "";
  ElMessage.success("Logo 已清除");
}

onMounted(() => {
  loadAll();
  loadDeployInfo();
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

.logo-upload-area {
  display: flex;
  gap: 12px;
  align-items: center;
}

.preview-hint {
  display: block;
  font-size: 12px;
  color: #86868b;
  margin-top: 4px;
}

/* MQTT Readonly Credentials */
.mqtt-readonly-section {
  background: rgba(0, 0, 0, 0.02);
  padding: 16px;
  border-radius: 12px;
  margin-top: 16px;
}

.mqtt-readonly-section h5 {
  margin: 0 0 12px;
  color: #86868b;
  font-size: 13px;
}

.mqtt-credentials {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.credential-item {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.credential-label {
  font-size: 13px;
  color: #606266;
  min-width: 100px;
}

.credential-value {
  background: rgba(0, 0, 0, 0.04);
  padding: 4px 10px;
  border-radius: 6px;
  font-family: 'SF Mono', Monaco, monospace;
  font-size: 13px;
  color: #1d1d1f;
}

.credential-value.password {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-weight: 500;
}

.credential-sep {
  color: #c0c4cc;
  font-size: 12px;
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

/* Deploy Info Section */
.deploy-info-empty {
  text-align: center;
  padding: 20px;
}

.deploy-hint {
  color: #86868b;
  font-size: 13px;
  margin-top: 12px;
}

.deploy-info-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.info-group {
  background: rgba(255, 255, 255, 0.4);
  padding: 16px;
  border-radius: 12px;
}

.info-group h5 {
  margin: 0 0 12px;
  color: #1d1d1f;
  font-size: 14px;
}

.info-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.info-label {
  color: #86868b;
  font-size: 13px;
  min-width: 80px;
}

.info-value {
  background: rgba(0, 0, 0, 0.04);
  padding: 4px 10px;
  border-radius: 6px;
  font-family: 'SF Mono', Monaco, monospace;
  font-size: 13px;
  color: #1d1d1f;
}

.info-value.link {
  color: #0071e3;
  text-decoration: none;
}

.info-value.link:hover {
  text-decoration: underline;
}

.credentials-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.credential-card {
  background: rgba(0, 0, 0, 0.02);
  padding: 12px 16px;
  border-radius: 10px;
  border: 1px solid rgba(0, 0, 0, 0.05);
}

.credential-title {
  font-size: 12px;
  color: #86868b;
  margin-bottom: 6px;
}

.credential-password code {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 4px 10px;
  border-radius: 6px;
  font-family: 'SF Mono', Monaco, monospace;
  font-size: 13px;
  font-weight: 500;
}

/* Backup/Restore Section */
.backup-restore-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.backup-group {
  background: rgba(255, 255, 255, 0.4);
  padding: 20px;
  border-radius: 12px;
}

.backup-group h5 {
  margin: 0 0 8px;
  color: #1d1d1f;
  font-size: 15px;
}

.backup-desc {
  color: #86868b;
  font-size: 13px;
  margin: 0 0 16px;
}

.import-area {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.selected-file {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: rgba(103, 194, 58, 0.1);
  border-radius: 8px;
  border: 1px solid rgba(103, 194, 58, 0.3);
}

.file-name {
  flex: 1;
  font-family: 'SF Mono', Monaco, monospace;
  font-size: 13px;
  color: #1d1d1f;
}

.import-result {
  padding: 16px;
  border-radius: 10px;
  margin-top: 12px;
}

.import-result.success {
  background: rgba(103, 194, 58, 0.1);
  border: 1px solid rgba(103, 194, 58, 0.3);
}

.import-result.error {
  background: rgba(245, 108, 108, 0.1);
  border: 1px solid rgba(245, 108, 108, 0.3);
}

.result-title {
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 8px;
}

.result-stats {
  font-size: 13px;
  color: #86868b;
}

.result-meta {
  font-size: 12px;
  color: #a0a0a5;
  margin-top: 4px;
}

.result-errors {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
}

.error-item {
  font-size: 12px;
  color: #f56c6c;
  padding: 4px 0;
}
</style>

