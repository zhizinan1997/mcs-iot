<template>
  <div class="archive-page full-scroll">
    <div class="glass-panel">
      <!-- Header -->
      <div class="panel-header">
        <div class="header-content">
          <div class="icon-box">
            <el-icon :size="24" color="#ff9f0a"><Box /></el-icon>
          </div>
          <div class="title-group">
            <h3>Cloudflare R2 数据归档</h3>
            <p class="subtitle">自动备份历史数据到云端对象存储</p>
          </div>
        </div>
        <div class="header-actions">
           <el-switch 
            v-model="archiveConfig.enabled" 
            active-text="已启用" 
            inactive-text="已禁用" 
            inline-prompt
          />
        </div>
      </div>

      <el-divider class="glass-divider" />

      <div class="panel-content">
        <!-- Configuration Section -->
        <div class="config-grid">
           <!-- Retention Settings -->
           <div class="config-card glass-inset">
             <h4>数据保留策略</h4>
             
             <div class="setting-item">
               <span class="label">本地数据库保留</span>
               <div class="control">
                 <el-slider
                  v-model="archiveConfig.local_retention_days"
                  :min="1"
                  :max="30"
                  show-input
                  size="small"
                />
                <span class="unit">天</span>
               </div>
               <p class="hint">最近 {{ archiveConfig.local_retention_days }} 天的数据保留在本地，更早的数据将归档或删除</p>
             </div>

             <div class="setting-item">
               <span class="label">云端 R2 保留</span>
               <div class="control">
                 <el-slider
                  v-model="archiveConfig.r2_retention_days"
                  :min="7"
                  :max="365"
                  show-input
                  size="small"
                />
                <span class="unit">天</span>
               </div>
               <p class="hint">云端备份文件保留 {{ archiveConfig.r2_retention_days }} 天后自动清理</p>
             </div>
           </div>

           <!-- Connection Settings -->
           <div class="config-card glass-inset">
             <h4>R2 存储桶连接</h4>
             <el-form :model="archiveConfig" label-width="120px" label-position="left">
               <el-form-item label="Bucket 名称">
                  <el-input v-model="archiveConfig.r2_bucket" placeholder="mcs-archive" />
               </el-form-item>
               <el-form-item label="Endpoint URL">
                  <el-input v-model="archiveConfig.r2_endpoint" placeholder="https://<account-id>.r2.cloudflarestorage.com" />
               </el-form-item>
               <el-form-item label="Access Key ID">
                  <el-input v-model="archiveConfig.r2_access_key" placeholder="R2 Access Key" />
               </el-form-item>
               <el-form-item label="Secret Key">
                  <el-input v-model="archiveConfig.r2_secret_key" type="password" show-password placeholder="R2 Secret Key" />
               </el-form-item>
             </el-form>
             
             <div class="form-actions">
                <el-button type="primary" @click="saveArchiveConfig" :loading="saving" round>保存配置</el-button>
                <el-button @click="testArchiveConnection" :loading="testingArchive" round>测试连接</el-button>
             </div>
           </div>
        </div>

        <!-- Stats & Files -->
        <div class="data-section">
          <!-- Stats Cards -->
          <div class="stats-row">
            <div class="stat-card glass-inset" v-loading="loadingStats">
              <div class="stat-icon local"><el-icon><DataLine /></el-icon></div>
              <div class="stat-info">
                <span class="label">本地存储占用</span>
                <span class="value">{{ storageStats?.local_db.size_human || '-' }}</span>
                <span class="sub-text">{{ storageStats?.local_db.row_count.toLocaleString() || 0 }} 条记录</span>
              </div>
              <el-button link class="refresh-btn" @click="fetchStorageStats"><el-icon><Refresh /></el-icon></el-button>
            </div>
            
            <div class="stat-card glass-inset" v-loading="loadingStats">
              <div class="stat-icon cloud"><el-icon><UploadFilled /></el-icon></div>
              <div class="stat-info">
                <span class="label">R2 云端占用</span>
                <span class="value">{{ storageStats?.r2.size_human || '-' }}</span>
                <span class="sub-text">{{ storageStats?.r2.file_count || 0 }} 个文件</span>
              </div>
            </div>
          </div>

          <!-- File List -->
          <div class="files-list glass-inset">
            <div class="list-header">
              <h4>归档文件列表</h4>
              <el-button size="small" @click="fetchArchiveFiles" :loading="loadingFiles" circle>
                <el-icon><Refresh /></el-icon>
              </el-button>
            </div>
            
            <el-table 
              :data="archiveFiles" 
              style="width: 100%" 
              height="300"
              class="glass-table"
              v-loading="loadingFiles"
            >
              <el-table-column prop="name" label="文件名" min-width="200">
                <template #default="{ row }">
                   <div class="file-name">
                     <el-icon><Document /></el-icon> {{ row.name }}
                   </div>
                </template>
              </el-table-column>
              <el-table-column prop="size_human" label="大小" width="120" />
              <el-table-column prop="last_modified" label="归档时间" width="180">
                <template #default="{ row }">{{ formatTime(row.last_modified) }}</template>
              </el-table-column>
              <el-table-column label="操作" width="100" fixed="right" align="right">
                <template #default="{ row }">
                  <el-button link type="primary" @click="downloadFile(row)">下载</el-button>
                </template>
              </el-table-column>
              <template #empty>
                <el-empty description="暂无归档文件" :image-size="60" />
              </template>
            </el-table>
          </div>
        </div>

        <!-- Help -->
        <div class="help-section">
          <el-collapse class="mac-collapse">
            <el-collapse-item name="1">
              <template #title>
                 <span class="help-title"><el-icon><InfoFilled /></el-icon> 功能说明与费用提示</span>
              </template>
              <div class="help-content">
                <div class="help-grid">
                  <div class="help-item">
                    <h5>📋 工作流程</h5>
                    <p>每天 00:00 自动将 {{ archiveConfig.local_retention_days }} 天前的 sensor_data 导出为 CSV.GZ 上传至 R2，成功后删除本地数据。</p>
                  </div>
                  <div class="help-item">
                    <h5>💰 费用说明</h5>
                    <p>Cloudflare R2 提供每月 10GB 免费存储 + 100万次读取。超出后 $0.015/GB/月。</p>
                  </div>
                  <div class="help-item">
                    <h5>📥 数据恢复</h5>
                    <p>下载文件后使用 <code>gunzip</code> 解压，并使用 PostgreSQL <code>COPY</code> 命令导入。</p>
                  </div>
                </div>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { Box, DataLine, UploadFilled, Document, Refresh, InfoFilled } from '@element-plus/icons-vue'
import { configApi } from "../../api";

const saving = ref(false);
const testingArchive = ref(false);
const loadingStats = ref(false);
const loadingFiles = ref(false);
const storageStats = ref<any>(null);
const archiveFiles = ref<any[]>([]);

const archiveConfig = reactive({
  enabled: false,
  local_retention_days: 3,
  r2_retention_days: 30,
  r2_endpoint: "",
  r2_bucket: "",
  r2_access_key: "",
  r2_secret_key: "",
});

async function loadArchiveConfig() {
  try {
    const res = await configApi.getArchive();
    Object.assign(archiveConfig, res.data);
  } catch (error) {
    console.error("Failed to load archive config:", error);
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
  try {
    await configApi.updateArchive(archiveConfig);
    const response = await configApi.testArchive();
    ElMessage.success(response.data.message || "R2 连接成功");
  } catch (error: any) {
    const detail = error.response?.data?.detail || "连接测试失败";
    ElMessage.error(detail);
  } finally {
    testingArchive.value = false;
  }
}

async function fetchStorageStats() {
  loadingStats.value = true;
  try {
    const res = await configApi.getArchiveStats();
    storageStats.value = res.data;
  } catch (error: any) {
    /* Silent fail for init load */
  } finally {
    loadingStats.value = false;
  }
}

async function fetchArchiveFiles() {
  loadingFiles.value = true;
  try {
    const res = await configApi.listArchiveFiles();
    archiveFiles.value = res.data.files || [];
  } catch (error: any) {
    console.error("Failed to list files:", error)
  } finally {
    loadingFiles.value = false;
  }
}

function formatTime(time: string) {
  if (!time) return '-';
  try {
    return new Date(time).toLocaleString('zh-CN');
  } catch {
    return time
  }
}

function downloadFile(file: any) {
  if (file.download_url) {
    window.open(file.download_url, '_blank');
  } else {
    ElMessage.error("下载链接不可用");
  }
}

onMounted(() => {
  loadArchiveConfig();
  // Delay stats loading slightly to prioritize page render
  setTimeout(() => {
    fetchStorageStats();
    fetchArchiveFiles();
  }, 500)
});
</script>

<style scoped>
.archive-page {
  padding: 24px;
  height: 100%;
  box-sizing: border-box;
}

.full-scroll {
  overflow-y: auto;
}

/* Common Glass Panel */
.glass-panel {
  min-height: 100%;
  border-radius: 24px;
  border: 1px solid rgba(255, 255, 255, 0.6);
  background: rgba(255, 255, 255, 0.65);
  backdrop-filter: blur(20px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.04);
  display: flex;
  flex-direction: column;
}

.panel-header {
  padding: 24px 32px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.icon-box {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: rgba(255, 159, 10, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
}

.title-group h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1d1d1f;
}

.title-group .subtitle {
  margin: 4px 0 0;
  font-size: 13px;
  color: #86868b;
}

.glass-divider {
  margin: 0;
  border-color: rgba(0,0,0,0.05);
}

.panel-content {
  padding: 32px;
  flex: 1;
}

/* Config Grid */
.config-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  margin-bottom: 24px;
}

.glass-inset {
  background: rgba(255, 255, 255, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 16px;
  padding: 24px;
}

.config-card h4 {
  margin: 0 0 20px;
  font-size: 15px;
  color: #1d1d1f;
  font-weight: 600;
}

.setting-item {
  margin-bottom: 24px;
}

.setting-item .label {
  display: block;
  font-size: 14px;
  color: #1d1d1f;
  margin-bottom: 8px;
  font-weight: 500;
}

.setting-item .control {
  display: flex;
  align-items: center;
  gap: 12px;
}

.setting-item .unit {
  font-size: 13px;
  color: #86868b;
  width: 24px;
}

.setting-item .hint {
  margin: 6px 0 0;
  font-size: 12px;
  color: #86868b;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}

/* Stats Row */
.stats-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  margin-bottom: 24px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 20px;
  position: relative;
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.stat-icon.local { background: rgba(0, 113, 227, 0.1); color: #0071e3; }
.stat-icon.cloud { background: rgba(48, 209, 88, 0.1); color: #30d158; }

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-info .label {
  font-size: 13px;
  color: #86868b;
  margin-bottom: 4px;
}

.stat-info .value {
  font-size: 24px;
  font-weight: 600;
  color: #1d1d1f;
  font-family: 'SF Pro Display', sans-serif;
}

.stat-info .sub-text {
  font-size: 12px;
  color: #86868b;
  margin-top: 2px;
}

.refresh-btn {
  position: absolute;
  top: 16px;
  right: 16px;
}

/* File List */
.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.list-header h4 {
  margin: 0;
}

.file-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

.glass-table {
  background: transparent !important;
}
:deep(.el-table) {
  background-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(0,0,0,0.02);
}
:deep(.el-table th.el-table__cell) {
  background: rgba(0,0,0,0.02);
}
:deep(.el-table tr) {
  background-color: transparent;
}

/* Help */
.help-section {
  margin-top: 24px;
}
.mac-collapse {
  border: none;
  --el-collapse-header-bg-color: transparent;
  --el-collapse-content-bg-color: transparent;
}
.help-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #86868b;
}
.help-content {
  background: rgba(255, 255, 255, 0.4);
  border-radius: 12px;
  padding: 20px;
}
.help-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 24px;
}
.help-item h5 {
  margin: 0 0 8px;
  color: #1d1d1f;
  font-weight: 600;
}
.help-item p {
  margin: 0;
  font-size: 13px;
  color: #6e6e73;
  line-height: 1.5;
}
</style>
