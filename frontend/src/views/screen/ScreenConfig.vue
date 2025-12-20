<template>
  <div class="screen-config-page">
    <el-card>
      <!-- Header removed -->
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { configApi } from "../../api";

const saving = ref(false);

const dashboardConfig = reactive({
  title: "MCS-IoT Dashboard",
  refresh_rate: 5,
  background_image: "",
});

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

onMounted(() => {
  loadDashboardConfig();
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
}

:deep(.el-card__body) {
  padding: 32px;
}
</style>
