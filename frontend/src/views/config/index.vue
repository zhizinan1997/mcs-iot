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

      <!-- Weather Config -->
      <el-tab-pane label="天气设置" name="weather">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>天气接口设置</span>
              <el-tag :type="weatherConfig.enabled ? 'success' : 'info'">
                {{ weatherConfig.enabled ? "已启用" : "未启用" }}
              </el-tag>
            </div>
          </template>
          <el-form :model="weatherConfig" label-width="120px">
            <el-form-item label="启用天气">
              <el-switch v-model="weatherConfig.enabled" />
            </el-form-item>
            <el-form-item label="所在地区">
              <el-cascader
                v-model="selectedRegion"
                :options="provinceAndCityData"
                :props="{ value: 'label' }"
                placeholder="请选择省/市"
                @change="handleRegionChange"
                style="width: 100%"
              />
            </el-form-item>
            <el-form-item label="城市拼音">
              <el-input v-model="weatherConfig.city_pinyin" disabled placeholder="自动生成" />
            </el-form-item>
            <el-form-item label="API 私钥">
              <el-input v-model="weatherConfig.api_key" placeholder="请输入 Seniverse API Key" type="password" show-password />
              <div class="form-tip">
                请前往 <a href="https://www.seniverse.com/" target="_blank" style="color: #409EFF">心知天气 (Seniverse)</a> 申请免费 API Key
              </div>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveWeatherConfig" :loading="saving">保存配置</el-button>
            </el-form-item>
          </el-form>
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
              <el-input-number
                v-model="dashboardConfig.refresh_rate"
                :min="1"
                :max="60"
              />
            </el-form-item>
            <el-form-item>
              <el-button
                type="primary"
                @click="saveDashboardConfig"
                :loading="saving"
                >保存配置</el-button
              >
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- Zones Config -->
      <!-- Screen Management (Formerly Zones Config) -->
      <el-tab-pane label="大屏显示管理" name="screen">
        <el-card>
          <el-tabs type="border-card">
            <el-tab-pane label="显示仪表设置">
              <div class="card-header" style="margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;">
                <span>选择在大屏上显示的仪表</span>
                <el-button type="primary" size="small" @click="fetchInstruments">
                  <el-icon><Refresh /></el-icon> 刷新列表
                </el-button>
              </div>
              
              <el-table :data="instruments" stripe v-loading="loadingInstruments" style="width: 100%">
                <el-table-column label="显示" width="80" align="center">
                  <template #default="{ row }">
                    <el-switch 
                      v-model="row.is_displayed" 
                      @change="handleInstrumentDisplayChange(row)"
                      :loading="row.saving"
                    />
                  </template>
                </el-table-column>
                <el-table-column label="颜色" width="60" align="center">
                  <template #default="{ row }">
                    <span class="color-dot" :style="{ backgroundColor: row.color }"></span>
                  </template>
                </el-table-column>
                <el-table-column prop="name" label="仪表名称" min-width="150" />
                <el-table-column prop="description" label="描述" min-width="200" />
                <el-table-column prop="sensor_count" label="关联传感器数" width="120" align="center" />
              </el-table>
            </el-tab-pane>
          </el-tabs>
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

      <!-- Archive Config (R2) -->
      <el-tab-pane label="数据归档" name="archive">
        <el-card>
          <template #header>
            <div
              class="card-header"
              style="display: flex; align-items: center; gap: 12px"
            >
              <span>Cloudflare R2 归档配置</span>
              <el-tag
                :type="archiveConfig.enabled ? 'success' : 'info'"
                size="small"
              >
                {{ archiveConfig.enabled ? "已启用" : "未启用" }}
              </el-tag>
            </div>
          </template>

          <el-form :model="archiveConfig" label-width="140px">
            <el-form-item label="启用数据归档">
              <el-switch v-model="archiveConfig.enabled" />
            </el-form-item>

            <el-form-item label="本地保留天数">
              <el-slider
                v-model="archiveConfig.local_retention_days"
                :min="1"
                :max="30"
                show-input
                style="width: 100%"
              />
              <div class="form-tip" style="margin-top: 8px">
                本地数据库保留最近 {{ archiveConfig.local_retention_days }} 天的数据
              </div>
            </el-form-item>

            <el-form-item label="R2 保留天数">
              <el-slider
                v-model="archiveConfig.r2_retention_days"
                :min="7"
                :max="365"
                show-input
                style="width: 100%"
              />
              <div class="form-tip" style="margin-top: 8px">
                R2 备份保留 {{ archiveConfig.r2_retention_days }} 天，超过后自动删除
              </div>
            </el-form-item>

            <el-divider content-position="left">R2 存储配置</el-divider>

            <el-form-item label="Endpoint URL">
              <el-input
                v-model="archiveConfig.r2_endpoint"
                placeholder="https://<account-id>.r2.cloudflarestorage.com"
              />
              <div class="form-tip">Cloudflare R2 端点地址</div>
            </el-form-item>

            <el-form-item label="Bucket 名称">
              <el-input
                v-model="archiveConfig.r2_bucket"
                placeholder="mcs-archive"
              />
            </el-form-item>

            <el-form-item label="Access Key ID">
              <el-input
                v-model="archiveConfig.r2_access_key"
                placeholder="R2 Access Key"
              />
            </el-form-item>

            <el-form-item label="Secret Access Key">
              <el-input
                v-model="archiveConfig.r2_secret_key"
                type="password"
                show-password
                placeholder="R2 Secret Key"
              />
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                @click="saveArchiveConfig"
                :loading="saving"
              >
                保存配置
              </el-button>
              <el-button
                @click="testArchiveConnection"
                :loading="testingArchive"
              >
                测试连接
              </el-button>
              <el-button
                type="info"
                @click="fetchStorageStats"
                :loading="loadingStats"
              >
                查看存储空间
              </el-button>
            </el-form-item>
          </el-form>

          <!-- Storage Stats Display -->
          <el-card v-if="storageStats" class="storage-stats-card" style="margin-top: 20px;">
            <template #header>
              <span>存储空间统计</span>
            </template>
            <el-row :gutter="20">
              <el-col :span="12">
                <el-statistic title="本地数据库" :value="storageStats.local_db.size_human">
                  <template #suffix>
                    <span style="font-size: 12px; color: #909399;">({{ storageStats.local_db.row_count.toLocaleString() }} 条记录)</span>
                  </template>
                </el-statistic>
              </el-col>
              <el-col :span="12">
                <el-statistic title="R2 备份" :value="storageStats.r2.size_human">
                  <template #suffix>
                    <span style="font-size: 12px; color: #909399;">
                      <template v-if="storageStats.r2.file_count">({{ storageStats.r2.file_count }} 个文件)</template>
                      <template v-else-if="storageStats.r2.message">{{ storageStats.r2.message }}</template>
                    </span>
                  </template>
                </el-statistic>
              </el-col>
            </el-row>
          </el-card>

          <el-divider />

          <div class="tips">
            <h4>归档说明:</h4>
            <ul>
              <li>每天 <strong>00:00</strong> 自动执行归档任务</li>
              <li>备份 <strong>{{ archiveConfig.local_retention_days }} 天前</strong>的数据到 R2</li>
              <li>上传成功后自动删除本地旧数据</li>
              <li>R2 中超过 <strong>{{ archiveConfig.r2_retention_days }} 天</strong>的备份自动清理</li>
            </ul>

            <el-alert
              title="数据安全"
              type="info"
              :closable="false"
              style="margin-top: 10px"
            >
              <template #default>
                <p>
                  归档数据以 CSV.GZ 格式存储，按日期命名（如 sensor_data_20231219.csv.gz）
                </p>
              </template>
            </el-alert>
          </div>
        </el-card>
      </el-tab-pane>
    </el-tabs>


  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { configApi, instrumentsApi } from "../../api";
import { provinceAndCityData } from 'element-china-area-data';
import { pinyin } from 'pinyin-pro';

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

const archiveConfig = reactive({
  enabled: false,
  local_retention_days: 3,
  r2_retention_days: 30,
  r2_endpoint: "",
  r2_bucket: "",
  r2_access_key: "",
  r2_secret_key: "",
});

const testingArchive = ref(false);
const loadingStats = ref(false);
const storageStats = ref<any>(null);

// Instruments state
const instruments = ref<any[]>([]); // Define type for instruments
const loadingInstruments = ref(false);

// Instruments Management
async function fetchInstruments() {
  loadingInstruments.value = true;
  try {
    const res = await instrumentsApi.list();
    // Ensure is_displayed is boolean
    instruments.value = res.data.data.map((i: any) => ({
      ...i,
      is_displayed: i.is_displayed !== false, // Default true
      saving: false,
    }));
  } catch (error) {
    console.error("Failed to fetch instruments:", error);
  } finally {
    loadingInstruments.value = false;
  }
}

async function handleInstrumentDisplayChange(row: any) {
  row.saving = true;
  try {
    await instrumentsApi.update(row.id, {
      name: row.name,
      description: row.description,
      color: row.color,
      sort_order: row.sort_order,
      zone_id: row.zone_id,
      is_displayed: row.is_displayed,
    });
    ElMessage.success("更新成功");
  } catch (error) {
    console.error("Update failed:", error);
    row.is_displayed = !row.is_displayed; // Revert on error
    ElMessage.error("更新失败");
  } finally {
    row.saving = false;
  }
}



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

async function saveDashboardConfig() {
  saving.value = true;
  try {
    await configApi.updateDashboard(dashboardConfig);
    ElMessage.success("大屏配置已保存");
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

async function loadArchiveConfig() {
  try {
    const res = await configApi.getArchive();
    Object.assign(archiveConfig, res.data);
  } catch (error) {
    console.error("Failed to load archive config:", error);
  }
}

async function fetchStorageStats() {
  loadingStats.value = true;
  try {
    const res = await configApi.getArchiveStats();
    storageStats.value = res.data;
    ElMessage.success("存储统计已更新");
  } catch (error: any) {
    const detail = error.response?.data?.detail || "获取存储统计失败";
    ElMessage.error(detail);
  } finally {
    loadingStats.value = false;
  }
}

async function saveArchiveConfig() {
  saving.value = true;
  try {
    await configApi.updateArchive(archiveConfig);
    ElMessage.success("归档配置已保存");
  } catch (error: any) {
    const detail = error.response?.data?.detail || "保存失败";
    ElMessage.error(detail);
  } finally {
    saving.value = false;
  }
}

async function testArchiveConnection() {
  testingArchive.value = true;
  ElMessage.info("正在测试 R2 连接...");
  try {
    // 先保存配置
    await configApi.updateArchive(archiveConfig);
    // 再测试连接
    const response = await configApi.testArchive();
    ElMessage.success(response.data.message || "R2 连接成功");
  } catch (error: any) {
    const detail = error.response?.data?.detail || "连接测试失败";
    ElMessage.error(detail);
  } finally {
    testingArchive.value = false;
  }
}

// Site Config
const siteConfig = reactive({
  site_name: "",
  logo_url: "",
  browser_title: ""
})

// Weather Config
const weatherConfig = reactive({
  enabled: true,
  province: '',
  city: '',
  city_pinyin: '',
  api_key: ''
});

const selectedRegion = ref<string[]>([]);

async function loadWeatherConfig() {
  try {
    const res = await configApi.getWeather();
    Object.assign(weatherConfig, res.data);
    if (weatherConfig.province && weatherConfig.city) {
      selectedRegion.value = [weatherConfig.province, weatherConfig.city];
    }
  } catch (error) {
    console.error("Failed to load weather config:", error);
  }
}

async function saveWeatherConfig() {
  saving.value = true;
  try {
    await configApi.updateWeather(weatherConfig);
    ElMessage.success("天气配置已保存");
  } catch (error) {
    ElMessage.error("保存失败");
  } finally {
    saving.value = false;
  }
}

const handleRegionChange = (value: string[]) => {
  if (value && value.length === 2) {
    weatherConfig.province = value[0] || '';
    weatherConfig.city = value[1] || '';
    
    let cityName = value[1] || '';
    if (cityName.endsWith('市')) cityName = cityName.slice(0, -1);
    else if (cityName.endsWith('地区')) cityName = cityName.slice(0, -2);
    else if (cityName.endsWith('盟')) cityName = cityName.slice(0, -1);
    else if (cityName.endsWith('自治州')) cityName = cityName.slice(0, -3);

    // Special case: Direct-controlled municipalities
    const municipalities = ['北京市', '上海市', '天津市', '重庆市'];
    if (municipalities.includes(value[0] || '')) {
        cityName = value[0] || '';
        if (cityName.endsWith('市')) cityName = cityName.slice(0, -1);
    } else if (cityName === '市辖区' || cityName === '县') {
        cityName = value[0] || '';
        if (cityName.endsWith('市')) cityName = cityName.slice(0, -1);
    }

    if (cityName) {
      const py = pinyin(cityName, { toneType: 'none', type: 'array' }) as string[];
      weatherConfig.city_pinyin = py.join('');
    }
  }
};

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
  loadArchiveConfig();
  loadSiteConfig();
  loadWeatherConfig();
  fetchInstruments();
});
</script>

<style scoped>
.config-page {
  width: 100%;
  height: 100%;
  padding: 20px;
  box-sizing: border-box;
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

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-preview {
  margin-top: 8px;
}

.logo-preview img {
  max-height: 40px;
  max-width: 200px;
}

.zone-color {
  display: inline-block;
  width: 20px;
  height: 20px;
  border-radius: 4px;
  border: 1px solid rgba(0, 0, 0, 0.1);
}

.upload-area {
  display: flex;
  gap: 10px;
  align-items: center;
}

.bg-preview {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 10px;
  background: #f5f7fa;
}

.bg-preview img {
  max-width: 400px;
  max-height: 225px;
  display: block;
}

.color-dot {
  display: inline-block;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 1px solid rgba(0, 0, 0, 0.1);
}
</style>
