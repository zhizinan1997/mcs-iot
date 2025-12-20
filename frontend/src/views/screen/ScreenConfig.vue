<template>
  <div class="screen-config-page">
    <el-card>
      <el-form :model="dashboardConfig" label-width="120px">
        <el-form-item label="展示大屏标题">
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

      <el-divider>布局设置</el-divider>

      <el-alert
        title="1920×1080 最佳全屏显示比例"
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 20px;"
      >
        <template #default>
          以下为 1920×1080 分辨率下的推荐布局比例。建议在浏览器中按 <strong>F11</strong> 全屏显示大屏页面以获得最佳效果。
        </template>
      </el-alert>
      
      <el-form :model="layoutConfig" label-width="140px" class="layout-form-container">
        <div class="layout-grid">
          <!-- Main Structure Group -->
          <div class="layout-group">
            <div class="layout-section">
              <div class="section-header">
                <el-icon class="section-icon"><Monitor /></el-icon>
                <span class="section-title">水平分割（主区域）</span>
              </div>
              <el-form-item label="左侧+中间区域">
                <el-slider v-model="layoutConfig.left" :min="50" :max="90" :step="1" show-input input-size="small" />
              </el-form-item>
              <el-form-item label="右侧区域">
                <el-slider v-model="layoutConfig.right" :min="10" :max="50" :step="1" show-input input-size="small" />
              </el-form-item>
            </div>

            <div class="layout-section">
              <div class="section-header">
                <el-icon class="section-icon"><DataLine /></el-icon>
                <span class="section-title">垂直分割（左侧区域）</span>
              </div>
              <el-form-item label="主内容区高度">
                <el-slider v-model="layoutConfig.mainHeight" :min="50" :max="90" :step="1" show-input input-size="small" />
              </el-form-item>
              <el-form-item label="趋势图区高度">
                <el-slider v-model="layoutConfig.trendHeight" :min="10" :max="50" :step="1" show-input input-size="small" />
              </el-form-item>
            </div>
          </div>

          <!-- Internal Structure Group -->
          <div class="layout-group">
             <div class="layout-section">
              <div class="section-header">
                <el-icon class="section-icon"><Grid /></el-icon>
                <span class="section-title">左栏内部分割</span>
              </div>
              <el-form-item label="左栏宽度">
                <el-slider v-model="layoutConfig.leftInner" :min="20" :max="50" :step="1" show-input input-size="small" />
              </el-form-item>
              <el-form-item label="中间栏宽度">
                <el-slider v-model="layoutConfig.centerInner" :min="50" :max="80" :step="1" show-input input-size="small" />
              </el-form-item>
            </div>

            <div class="layout-section">
              <div class="section-header">
                <el-icon class="section-icon"><Files /></el-icon>
                <span class="section-title">左栏面板高度</span>
              </div>
              <el-form-item label="仪表概览高度">
                <el-slider v-model="layoutConfig.leftPanel1" :min="10" :max="60" :step="1" show-input input-size="small" />
              </el-form-item>
              <el-form-item label="安全监管高度">
                <el-slider v-model="layoutConfig.leftPanel2" :min="20" :max="70" :step="1" show-input input-size="small" />
              </el-form-item>
              <el-form-item label="AI分析高度">
                <el-slider v-model="layoutConfig.leftPanel3" :min="10" :max="40" :step="1" show-input input-size="small" />
              </el-form-item>
            </div>
          </div>
        </div>

        <div class="form-actions">
          <el-button @click="resetLayoutDefaults" :icon="RefreshLeft">重置默认</el-button>
          <el-button
            type="primary"
            @click="saveLayoutConfig"
            :loading="savingLayout"
            :icon="Check"
            >保存布局配置</el-button
          >
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { Monitor, DataLine, Grid, Files, RefreshLeft, Check } from '@element-plus/icons-vue';
import { configApi } from "../../api";

const saving = ref(false);
const savingLayout = ref(false);

const dashboardConfig = reactive({
  title: "MCS-IoT Dashboard",
  refresh_rate: 5,
  background_image: "",
});

const defaultLayoutSizes = {
  left: 75,
  center: 0,
  right: 25,
  mainHeight: 70,
  trendHeight: 30,
  leftInner: 35,
  centerInner: 65,
  leftPanel1: 35,
  leftPanel2: 34,
  leftPanel3: 27
};

const layoutConfig = reactive({ ...defaultLayoutSizes });

async function loadDashboardConfig() {
  try {
    const res = await configApi.getDashboard();
    Object.assign(dashboardConfig, res.data);
  } catch (error) {
    console.error("Failed to load dashboard config:", error);
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

async function loadLayoutConfig() {
  try {
    const res = await configApi.getScreenLayout();
    if (res.data) {
      Object.assign(layoutConfig, res.data);
    }
  } catch (error) {
    console.error("Failed to load layout config:", error);
  }
}

async function saveLayoutConfig() {
  savingLayout.value = true;
  try {
    await configApi.updateScreenLayout(layoutConfig);
    ElMessage.success("布局配置已保存");
  } catch (error) {
    ElMessage.error("保存失败");
  } finally {
    savingLayout.value = false;
  }
}

function resetLayoutDefaults() {
  Object.assign(layoutConfig, defaultLayoutSizes);
  ElMessage.info("已重置为默认值，请点击保存布局以生效");
}

onMounted(() => {
  loadDashboardConfig();
  loadLayoutConfig();
});
</script>

<style scoped>
.screen-config-page {
  padding: 24px;
  height: 100%;
}

:deep(.el-card) {
  height: 100%;
  border-radius: 24px !important;
  border: 1px solid rgba(255, 255, 255, 0.6) !important;
  background: rgba(255, 255, 255, 0.65) !important;
  backdrop-filter: blur(20px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.04) !important;
  display: flex;
  flex-direction: column;
  overflow: auto;
}

:deep(.el-card__body) {
  padding: 32px;
}

.layout-form-container {
  max-width: 100%;
}

.layout-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 24px;
  margin-bottom: 24px;
}

.layout-group {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.layout-section {
  background: white;
  border-radius: 16px;
  padding: 24px;
  border: 1px solid rgba(0, 0, 0, 0.05);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.02);
  transition: all 0.3s ease;
}

.layout-section:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.06);
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 24px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
}

.section-icon {
  font-size: 20px;
  color: #409eff;
  background: rgba(64, 158, 255, 0.1);
  padding: 8px;
  border-radius: 8px;
}

.section-title {
  font-weight: 600;
  color: #303133;
  font-size: 16px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}

:deep(.el-slider) {
  width: 100%;
}

:deep(.el-slider__input) {
  width: 90px;
}

:deep(.el-form-item__label) {
  font-weight: 500;
  color: #606266;
}
</style>
