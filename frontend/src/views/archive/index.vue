<template>
  <div class="archive-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>Cloudflare R2 归档配置</span>
          <el-tag :type="archiveConfig.enabled ? 'success' : 'info'" size="small">
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

      <!-- R2 Backup Files List -->
      <el-card class="files-card" style="margin-top: 20px;">
        <template #header>
          <div class="card-header">
            <span>R2 备份文件列表</span>
            <el-button size="small" @click="fetchArchiveFiles" :loading="loadingFiles">
              刷新列表
            </el-button>
          </div>
        </template>
        
        <el-empty v-if="!archiveFiles.length && !loadingFiles" description="暂无备份文件" />
        
        <el-table v-else :data="archiveFiles" stripe v-loading="loadingFiles" style="width: 100%">
          <el-table-column prop="name" label="文件名" min-width="200" />
          <el-table-column prop="size_human" label="大小" width="100" />
          <el-table-column prop="last_modified" label="修改时间" width="180">
            <template #default="{ row }">
              {{ formatTime(row.last_modified) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button size="small" type="primary" @click="downloadFile(row)">
                下载
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-divider />

      <div class="tips">
        <h4>🗄️ 数据归档功能说明</h4>
        
        <el-alert type="info" :closable="false" style="margin-bottom: 15px;">
          <template #title>什么是数据归档？</template>
          <template #default>
            <p>数据归档功能将传感器历史数据备份到 Cloudflare R2 云存储，确保数据安全的同时减少本地数据库负担。</p>
          </template>
        </el-alert>
        
        <h5>📋 工作流程</h5>
        <ul>
          <li>每天 <strong>00:00</strong> 自动执行归档任务</li>
          <li>将 <strong>{{ archiveConfig.local_retention_days }} 天前</strong>的 sensor_data 表数据导出为 CSV.GZ 压缩文件</li>
          <li>文件命名格式：<code>archive/sensor_data_YYYYMMDD.csv.gz</code></li>
          <li>上传成功后自动删除本地对应日期的数据</li>
          <li>R2 中超过 <strong>{{ archiveConfig.r2_retention_days }} 天</strong>的备份会自动清理</li>
        </ul>
        
        <h5>💾 归档文件内容</h5>
        <ul>
          <li>CSV 格式包含：时间戳、设备SN、电压原值、浓度值(PPM)、温度、湿度、电量、信号强度、序列号</li>
          <li>使用 GZIP 压缩，通常可节省 80-90% 存储空间</li>
          <li>文件按日期分隔，便于查找和恢复特定日期的数据</li>
        </ul>
        
        <h5>📥 数据恢复</h5>
        <ul>
          <li>点击文件列表中的"下载"按钮获取备份文件</li>
          <li>使用 <code>gunzip</code> 命令解压：<code>gunzip sensor_data_20241219.csv.gz</code></li>
          <li>使用 PostgreSQL 的 <code>COPY</code> 命令导入：
            <code>COPY sensor_data FROM '/path/to/file.csv' WITH CSV HEADER;</code>
          </li>
        </ul>
        
        <h5>💰 Cloudflare R2 费用说明</h5>
        <el-alert type="warning" :closable="false">
          <template #default>
            <p><strong>免费额度：</strong>每月 10GB 存储 + 100万次读取 + 1000万次写入</p>
            <p><strong>超出部分：</strong>$0.015/GB/月 存储费 (约每 GB 每月 0.1 元人民币)</p>
            <p>对于大多数中小型部署，免费额度完全够用</p>
          </template>
        </el-alert>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage } from "element-plus";
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
  ElMessage.info("正在测试 R2 连接...");
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
    ElMessage.success("存储统计已更新");
  } catch (error: any) {
    const detail = error.response?.data?.detail || "获取存储统计失败";
    ElMessage.error(detail);
  } finally {
    loadingStats.value = false;
  }
}

async function fetchArchiveFiles() {
  loadingFiles.value = true;
  try {
    const res = await configApi.listArchiveFiles();
    archiveFiles.value = res.data.files || [];
    if (res.data.message) {
      ElMessage.info(res.data.message);
    }
  } catch (error: any) {
    const detail = error.response?.data?.detail || "获取文件列表失败";
    ElMessage.error(detail);
  } finally {
    loadingFiles.value = false;
  }
}

function formatTime(time: string) {
  if (!time) return '-';
  const date = new Date(time);
  return date.toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' });
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
});
</script>

<style scoped>
.archive-page {
  padding: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.form-tip {
  color: #909399;
  font-size: 12px;
}

.tips {
  color: #606266;
  font-size: 14px;
}

.tips h4 {
  margin: 0 0 15px;
  color: #303133;
  font-size: 16px;
}

.tips h5 {
  margin: 15px 0 8px;
  color: #409eff;
  font-size: 14px;
}

.tips ul {
  margin: 0;
  padding-left: 20px;
}

.tips li {
  margin-bottom: 6px;
  line-height: 1.6;
}

.tips code {
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: monospace;
  color: #e6a23c;
}

.tips p {
  margin: 5px 0;
}
</style>
