<template>
  <div class="screen-display-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>大屏显示管理</span>
          <el-button type="primary" size="small" @click="fetchInstruments">
            <el-icon><Refresh /></el-icon> 刷新列表
          </el-button>
        </div>
      </template>

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
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-desc {
  margin-bottom: 20px;
  color: #606266;
}

.color-dot {
  display: inline-block;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 1px solid rgba(0, 0, 0, 0.1);
}
</style>
