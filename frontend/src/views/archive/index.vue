<!--
  MCS-IOT 云端数据归档管理页面 (Cloud Data Backup & Archiving)

  该文件负责管理历史传感器数据的异地备份与本地空间释放逻辑。
  主要职责：
  1. 多云存储集成：支持 Cloudflare R2、腾讯云 COS 与 阿里云 OSS 的无缝切换。
  2. 自动化策略：配置数据保留时长（Retention），到期自动导出为 CSV.GZ 并上传至云端。
  3. 运维工具：提供立即手动备份、手动清理本地过期数据、文件在线管理（下载/删除）等功能。
  4. 存储看板：实时监测本地数据库占用空间与云端对象存储的资源消耗。

  技术栈：Vue 3 (setup), Element Plus Table & Dialog, S3-compatible Service API.
-->
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
               <p class="hint">云端备份文件保留 {{ archiveConfig.cloud_retention_days }} 天后自动清理</p>
             </div>
           </div>

           <!-- Connection Settings -->
           <div class="config-card glass-inset">
             <h4>云存储连接</h4>
             <el-form :model="archiveConfig" label-width="120px" label-position="left">
               <!-- Provider Selection -->
               <el-form-item label="存储提供商">
                 <el-radio-group v-model="archiveConfig.provider" @change="onProviderChange">
                   <el-radio value="cloudflare">Cloudflare R2</el-radio>
                   <el-radio value="tencent">腾讯云 COS</el-radio>
                   <el-radio value="alibaba">阿里云 OSS</el-radio>
                 </el-radio-group>
               </el-form-item>
               
               <!-- Common Fields -->
               <el-form-item label="Bucket 名称">
                  <el-input v-model="archiveConfig.bucket" placeholder="mcs-archive" />
               </el-form-item>
               
               <!-- Cloudflare R2 Specific -->
               <el-form-item label="账户 ID" v-if="archiveConfig.provider === 'cloudflare'">
                  <el-input v-model="archiveConfig.account_id" placeholder="Cloudflare 账户 ID">
                    <template #prepend>https://</template>
                    <template #append>.r2.cloudflarestorage.com</template>
                  </el-input>
               </el-form-item>
               
               <!-- Tencent COS Region -->
               <el-form-item label="存储区域" v-if="archiveConfig.provider === 'tencent'">
                  <el-select v-model="archiveConfig.region" placeholder="选择区域" style="width: 100%">
                    <el-option label="广州 (ap-guangzhou)" value="ap-guangzhou" />
                    <el-option label="上海 (ap-shanghai)" value="ap-shanghai" />
                    <el-option label="北京 (ap-beijing)" value="ap-beijing" />
                    <el-option label="成都 (ap-chengdu)" value="ap-chengdu" />
                    <el-option label="重庆 (ap-chongqing)" value="ap-chongqing" />
                    <el-option label="南京 (ap-nanjing)" value="ap-nanjing" />
                    <el-option label="香港 (ap-hongkong)" value="ap-hongkong" />
                    <el-option label="新加坡 (ap-singapore)" value="ap-singapore" />
                  </el-select>
               </el-form-item>
               
               <!-- Alibaba OSS Region -->
               <el-form-item label="存储区域" v-if="archiveConfig.provider === 'alibaba'">
                  <el-select v-model="archiveConfig.region" placeholder="选择区域" style="width: 100%">
                    <el-option label="杭州 (oss-cn-hangzhou)" value="oss-cn-hangzhou" />
                    <el-option label="上海 (oss-cn-shanghai)" value="oss-cn-shanghai" />
                    <el-option label="北京 (oss-cn-beijing)" value="oss-cn-beijing" />
                    <el-option label="深圳 (oss-cn-shenzhen)" value="oss-cn-shenzhen" />
                    <el-option label="成都 (oss-cn-chengdu)" value="oss-cn-chengdu" />
                    <el-option label="香港 (oss-cn-hongkong)" value="oss-cn-hongkong" />
                    <el-option label="美西 (oss-us-west-1)" value="oss-us-west-1" />
                  </el-select>
               </el-form-item>
               
               <el-form-item label="Access Key ID">
                  <el-input v-model="archiveConfig.access_key" placeholder="Access Key" />
               </el-form-item>
               <el-form-item label="Secret Key">
                  <el-input v-model="archiveConfig.secret_key" type="password" show-password placeholder="Secret Key" />
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

          <!-- Manual Cleanup Actions -->
          <div class="cleanup-section glass-inset">
            <div class="cleanup-header">
              <h4>手动清理本地数据</h4>
              <p class="hint">清理指定时间之前的传感器数据，释放本地存储空间</p>
            </div>
            <div class="cleanup-actions">
              <el-button 
                type="warning" 
                size="small" 
                @click="confirmCleanup(3)" 
                :loading="cleaningUp === 3"
                round
              >
                <el-icon><Delete /></el-icon> 清理 3 天前数据
              </el-button>
              <el-button 
                type="warning" 
                size="small" 
                @click="confirmCleanup(7)" 
                :loading="cleaningUp === 7"
                round
              >
                <el-icon><Delete /></el-icon> 清理 7 天前数据
              </el-button>
              <el-button 
                type="danger" 
                size="small" 
                @click="confirmCleanup(30)" 
                :loading="cleaningUp === 30"
                round
              >
                <el-icon><Delete /></el-icon> 清理 30 天前数据
              </el-button>
            </div>
          </div>

          <!-- File List -->
          <div class="files-list glass-inset">
            <div class="list-header">
              <h4>归档文件列表</h4>
              <div class="list-actions">
                <el-button type="primary" size="small" @click="manualBackup" :loading="backingUp" round>
                  <el-icon><Upload /></el-icon> 立即备份今日数据
                </el-button>
                <el-button size="small" @click="fetchArchiveFiles" :loading="loadingFiles" circle>
                  <el-icon><Refresh /></el-icon>
                </el-button>
              </div>
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
              <el-table-column label="操作" width="140" fixed="right" align="right">
                <template #default="{ row }">
                  <el-button link type="primary" @click="downloadFile(row)">下载</el-button>
                  <el-button link type="danger" @click="confirmDeleteFile(row)" :loading="deletingFile === row.key">删除</el-button>
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
import { ElMessage, ElMessageBox } from "element-plus";
import { Box, DataLine, UploadFilled, Document, Refresh, InfoFilled, Upload, Delete } from '@element-plus/icons-vue'
import { configApi } from "../../api";

const saving = ref(false);
const testingArchive = ref(false);
const loadingStats = ref(false);
const loadingFiles = ref(false);
const backingUp = ref(false);
const cleaningUp = ref<number | null>(null);
const deletingFile = ref<string | null>(null);
const storageStats = ref<any>(null);
const archiveFiles = ref<any[]>([]);

const archiveConfig = reactive({
  enabled: false,
  local_retention_days: 3,
  cloud_retention_days: 30,
  // 新版统一字段
  provider: "cloudflare",
  bucket: "",
  access_key: "",
  secret_key: "",
  account_id: "",  // Cloudflare R2
  region: "",      // 腾讯云/阿里云
  // 兼容旧版字段
  r2_retention_days: 30,
  r2_account_id: "",
  r2_bucket: "",
  r2_access_key: "",
  r2_secret_key: "",
});

function onProviderChange() {
  // 切换提供商时清空特定字段
  archiveConfig.account_id = "";
  archiveConfig.region = "";
}

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

async function manualBackup() {
  backingUp.value = true;
  try {
    const res = await configApi.backupArchive();
    if (res.data.status === 'empty') {
      ElMessage.warning(res.data.message || "今日暂无数据可备份");
    } else {
      ElMessage.success(res.data.message || "备份成功！");
      // 刷新文件列表和统计
      fetchArchiveFiles();
      fetchStorageStats();
    }
  } catch (error: any) {
    const detail = error.response?.data?.detail || "备份失败";
    ElMessage.error(detail);
  } finally {
    backingUp.value = false;
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

async function confirmDeleteFile(file: any) {
  try {
    await ElMessageBox.confirm(
      `确定要删除文件 "${file.name}" 吗？\n\n此操作不可恢复！`,
      '确认删除',
      {
        confirmButtonText: '确认删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    await deleteArchiveFile(file.key)
  } catch {
    // User cancelled
  }
}

async function deleteArchiveFile(key: string) {
  deletingFile.value = key;
  try {
    const res = await configApi.deleteArchiveFile(key);
    ElMessage.success(res.data.message || "文件已删除");
    // 刷新文件列表和统计
    fetchArchiveFiles();
    fetchStorageStats();
  } catch (error: any) {
    const detail = error.response?.data?.detail || "删除失败";
    ElMessage.error(detail);
  } finally {
    deletingFile.value = null;
  }
}

async function confirmCleanup(days: number) {
  try {
    await ElMessageBox.confirm(
      `确定要删除 ${days} 天前的所有传感器数据吗？\n\n此操作不可恢复，请确保已备份重要数据！`,
      '确认清理',
      {
        confirmButtonText: '确认删除',
        cancelButtonText: '取消',
        type: 'warning',
        dangerouslyUseHTMLString: true
      }
    )
    await cleanupData(days)
  } catch {
    // User cancelled
  }
}

async function cleanupData(days: number) {
  cleaningUp.value = days;
  try {
    const res = await configApi.cleanupData(days);
    if (res.data.status === 'empty') {
      ElMessage.info(res.data.message || "没有需要清理的数据");
    } else {
      ElMessage.success(res.data.message || `成功清理 ${res.data.deleted_rows} 条数据`);
      // 刷新统计
      fetchStorageStats();
    }
  } catch (error: any) {
    const detail = error.response?.data?.detail || "清理失败";
    ElMessage.error(detail);
  } finally {
    cleaningUp.value = null;
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
.list-actions {
  display: flex;
  align-items: center;
  gap: 12px;
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

/* Cleanup Section */
.cleanup-section {
  margin-bottom: 24px;
}

.cleanup-header {
  margin-bottom: 16px;
}

.cleanup-header h4 {
  margin: 0 0 4px;
  font-size: 15px;
  color: #1d1d1f;
  font-weight: 600;
}

.cleanup-header .hint {
  margin: 0;
  font-size: 12px;
  color: #86868b;
}

.cleanup-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
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
