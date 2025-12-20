<template>
  <div class="screen-display-page">
    <el-card>
      <div class="toolbar" style="padding: 12px 24px; display: flex; justify-content: flex-end;">
        <el-button type="primary" size="small" @click="fetchInstruments">
          <el-icon><Refresh /></el-icon> 刷新列表
        </el-button>
      </div>

      <el-tabs type="border-card">
        <el-tab-pane label="显示仪表设置">
          <div class="section-desc">
            <span>选择在大屏上显示的仪表</span>
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { instrumentsApi } from "../../api";
import { Refresh } from "@element-plus/icons-vue";

// Instruments state
const instruments = ref<any[]>([]);
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

onMounted(() => {
  fetchInstruments();
});
</script>

<style scoped>
.screen-display-page {
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

/* Toolbar styling */
.toolbar {
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

/* Tabs Styling */
:deep(.el-tabs--border-card) {
  background: transparent;
  border: none;
  box-shadow: none;
}

:deep(.el-tabs--border-card > .el-tabs__header) {
  background: transparent;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

:deep(.el-tabs--border-card > .el-tabs__header .el-tabs__item.is-active) {
  background: rgba(255, 255, 255, 0.5);
  border-right: 1px solid rgba(0, 0, 0, 0.05);
  border-left: 1px solid rgba(0, 0, 0, 0.05);
  color: #0071e3;
  font-weight: 600;
}

:deep(.el-tabs--border-card > .el-tabs__content) {
  padding: 24px;
}

/* Table Styling */
:deep(.el-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(255, 255, 255, 0.5);
  background: transparent !important;
}

:deep(.el-table th.el-table__cell) {
  background-color: rgba(255, 255, 255, 0.5);
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  color: #86868b;
  font-weight: 600;
}

:deep(.el-table td.el-table__cell) {
  border-bottom: 1px solid rgba(0, 0, 0, 0.03);
}

:deep(.el-table--striped .el-table__body tr.el-table__row--striped td.el-table__cell) {
  background: rgba(255, 255, 255, 0.2);
}

:deep(.el-table--enable-row-hover .el-table__body tr:hover > td.el-table__cell) {
  background-color: rgba(255, 255, 255, 0.5);
}

.section-desc {
  margin-bottom: 20px;
  color: #6e6e73;
  font-size: 13px;
}

.color-dot {
  display: inline-block;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 1px solid rgba(0, 0, 0, 0.1);
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
</style>
